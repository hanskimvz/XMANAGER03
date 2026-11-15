"""
DB관리자 API (설정 > DB관리자)
DB 서버의 데이터베이스/테이블 목록과 레코드 원본(raw data)을 조회한다.

- 읽기 전용: 모든 조회는 READ ONLY 트랜잭션 + statement_timeout 안에서 실행한다.
- ADMIN 전용: 라우터 전체에 require_admin 적용(RBAC_MODE 무관).
- 식별자(DB/스키마/테이블/컬럼)는 카탈로그에 실제 존재하는 이름만 허용하고,
  값은 전부 바인드 파라미터로 전달한다(SQL 인젝션 방지).
"""

import base64
import threading
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from app.core.auth import require_admin
from app.core.config import settings
from app.core.database import engine as main_engine

router = APIRouter(prefix="/admin/db", tags=["DB관리자"], dependencies=[Depends(require_admin)])

MAX_LIMIT = 1000
STATEMENT_TIMEOUT_MS = 20_000
MAX_BINARY_PREVIEW = 256  # bytea 는 앞부분만 base64 로 보여준다

# 값이 필요 없는 연산자 / 필요한 연산자
_NULL_OPS = {"is_null": "IS NULL", "not_null": "IS NOT NULL"}
_COMPARE_OPS = {"eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
_LIKE_OPS = {"contains", "not_contains", "starts", "ends"}


# ========== 스키마 ==========

class DatabaseInfo(BaseModel):
    name: str
    is_current: bool
    size_display: str


class TableInfo(BaseModel):
    schema_name: str
    name: str
    kind: str  # table | view | matview
    estimated_rows: Optional[int] = None


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    is_pk: bool


class SortSpec(BaseModel):
    column: str
    direction: str = "asc"  # asc | desc


class FilterSpec(BaseModel):
    column: str
    op: str = "contains"
    value: Optional[str] = None


class RowsRequest(BaseModel):
    database: str
    schema_name: str = "public"
    table: str
    limit: int = Field(100, ge=1, le=MAX_LIMIT)
    offset: int = Field(0, ge=0)
    sort: List[SortSpec] = []
    filters: List[FilterSpec] = []


class RowsResponse(BaseModel):
    columns: List[ColumnInfo]
    rows: List[List[Any]]
    total: int
    limit: int
    offset: int


# ========== 엔진/연결 ==========

_engines: Dict[str, Engine] = {}
_engines_lock = threading.Lock()


def _current_db_name() -> str:
    return make_url(settings.DATABASE_URL).database or ""


def _list_database_names() -> List[str]:
    with main_engine.connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT datname FROM pg_database "
            "WHERE NOT datistemplate AND datallowconn ORDER BY datname"
        ).fetchall()
    return [r[0] for r in rows]


def _get_engine(database: str) -> Engine:
    """대상 DB 엔진. 현재 DB는 앱 엔진을 재사용, 그 외는 풀 없는(NullPool) 엔진을 만들어 캐시."""
    if database == _current_db_name():
        return main_engine
    if database not in _list_database_names():
        raise HTTPException(status_code=404, detail=f"데이터베이스 '{database}'를 찾을 수 없습니다.")
    with _engines_lock:
        eng = _engines.get(database)
        if eng is None:
            url = make_url(settings.DATABASE_URL).set(database=database)
            eng = create_engine(url, poolclass=NullPool, connect_args={"client_encoding": "utf8"})
            _engines[database] = eng
        return eng


def _readonly_conn(database: str):
    """READ ONLY 트랜잭션 연결(컨텍스트 매니저). 블록을 벗어나면 롤백/반납된다."""
    conn = _get_engine(database).connect()
    try:
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        conn.exec_driver_sql(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
    except Exception:
        conn.close()
        raise
    return conn


def _qident(name: str) -> str:
    """식별자 인용. exec_driver_sql(pyformat)을 쓰므로 % 도 이스케이프."""
    return '"' + name.replace('"', '""').replace("%", "%%") + '"'


def _db_error(e: DBAPIError) -> HTTPException:
    msg = str(getattr(e, "orig", e)).strip().splitlines()
    return HTTPException(status_code=400, detail=f"DB 오류: {msg[0] if msg else '알 수 없는 오류'}")


def _jsonable(v: Any) -> Any:
    """DB 값을 원본에 가깝게 JSON 직렬화(Decimal 은 정밀도 유지를 위해 문자열)."""
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return v if v == v and v not in (float("inf"), float("-inf")) else str(v)
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (datetime, date, time)):
        return v.isoformat()
    if isinstance(v, timedelta):
        return str(v)
    if isinstance(v, (bytes, bytearray, memoryview)):
        b = bytes(v)
        head = base64.b64encode(b[:MAX_BINARY_PREVIEW]).decode("ascii")
        return f"<binary {len(b)} bytes> {head}{'…' if len(b) > MAX_BINARY_PREVIEW else ''}"
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x) for x in v]
    return str(v)


def _fetch_columns(conn, schema: str, table: str) -> List[ColumnInfo]:
    rows = conn.exec_driver_sql(
        """
        SELECT a.attname,
               format_type(a.atttypid, a.atttypmod),
               NOT a.attnotnull,
               EXISTS (
                   SELECT 1 FROM pg_index i
                   WHERE i.indrelid = c.oid AND i.indisprimary AND a.attnum = ANY(i.indkey)
               )
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %(schema)s AND c.relname = %(table)s
          AND c.relkind IN ('r', 'p', 'v', 'm')
          AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
        """,
        {"schema": schema, "table": table},
    ).fetchall()
    return [ColumnInfo(name=r[0], type=r[1], nullable=bool(r[2]), is_pk=bool(r[3])) for r in rows]


# ========== API 엔드포인트 ==========

@router.get("/databases", response_model=List[DatabaseInfo])
def list_databases():
    """접속 가능한 데이터베이스 목록"""
    current = _current_db_name()
    try:
        with main_engine.connect() as conn:
            rows = conn.exec_driver_sql(
                "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database "
                "WHERE NOT datistemplate AND datallowconn ORDER BY datname"
            ).fetchall()
    except DBAPIError as e:
        raise _db_error(e)
    return [DatabaseInfo(name=r[0], is_current=(r[0] == current), size_display=r[1]) for r in rows]


@router.get("/tables", response_model=List[TableInfo])
def list_tables(database: str = Query(..., description="데이터베이스 이름")):
    """선택한 데이터베이스의 테이블/뷰 목록(행 수는 통계 기반 추정치)"""
    kinds = {"r": "table", "p": "table", "v": "view", "m": "matview"}
    try:
        conn = _readonly_conn(database)
        try:
            rows = conn.exec_driver_sql(
                """
                SELECT n.nspname, c.relname, c.relkind, CAST(c.reltuples AS BIGINT)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'p', 'v', 'm')
                  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                  AND n.nspname NOT LIKE 'pg\\_toast%%'
                  AND n.nspname NOT LIKE 'pg\\_temp%%'
                ORDER BY (n.nspname <> 'public'), n.nspname, c.relname
                """
            ).fetchall()
        finally:
            conn.close()
    except DBAPIError as e:
        raise _db_error(e)
    return [
        TableInfo(
            schema_name=r[0],
            name=r[1],
            kind=kinds.get(r[2], "table"),
            estimated_rows=(r[3] if r[2] in ("r", "p") and r[3] is not None and r[3] >= 0 else None),
        )
        for r in rows
    ]


@router.post("/rows", response_model=RowsResponse)
def query_rows(req: RowsRequest):
    """테이블 레코드 원본 조회(제한/정렬/필터)"""
    try:
        conn = _readonly_conn(req.database)
        try:
            columns = _fetch_columns(conn, req.schema_name, req.table)
            if not columns:
                raise HTTPException(
                    status_code=404,
                    detail=f"테이블 '{req.schema_name}.{req.table}'을 찾을 수 없습니다.",
                )
            names = {c.name for c in columns}

            # WHERE
            params: Dict[str, Any] = {}
            conds: List[str] = []
            for i, f in enumerate(req.filters):
                if f.column not in names:
                    raise HTTPException(status_code=400, detail=f"필터 컬럼 '{f.column}'이 없습니다.")
                col = _qident(f.column)
                key = f"f{i}"
                if f.op in _NULL_OPS:
                    conds.append(f"{col} {_NULL_OPS[f.op]}")
                    continue
                if f.value is None or f.value == "":
                    continue  # 값이 비어 있는 필터는 무시
                if f.op in _COMPARE_OPS:
                    conds.append(f"{col} {_COMPARE_OPS[f.op]} %({key})s")
                    params[key] = f.value
                elif f.op in _LIKE_OPS:
                    esc = f.value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    pattern = {
                        "contains": f"%{esc}%",
                        "not_contains": f"%{esc}%",
                        "starts": f"{esc}%",
                        "ends": f"%{esc}",
                    }[f.op]
                    neg = "NOT " if f.op == "not_contains" else ""
                    cond = f"CAST({col} AS TEXT) {neg}ILIKE %({key})s"
                    if neg:  # NULL 은 '포함하지 않음'에 해당
                        cond = f"({col} IS NULL OR {cond})"
                    conds.append(cond)
                    params[key] = pattern
                else:
                    raise HTTPException(status_code=400, detail=f"지원하지 않는 필터 연산자: {f.op}")
            where = f" WHERE {' AND '.join(conds)}" if conds else ""

            # ORDER BY — 지정이 없으면 PK 순(페이지 이동 시 순서 고정)
            orders: List[str] = []
            for s in req.sort:
                if s.column not in names:
                    raise HTTPException(status_code=400, detail=f"정렬 컬럼 '{s.column}'이 없습니다.")
                direction = "DESC" if s.direction.lower() == "desc" else "ASC"
                orders.append(f"{_qident(s.column)} {direction}")
            if not orders:
                orders = [f"{_qident(c.name)} ASC" for c in columns if c.is_pk]
            order_by = f" ORDER BY {', '.join(orders)}" if orders else ""

            target = f"{_qident(req.schema_name)}.{_qident(req.table)}"
            total = conn.exec_driver_sql(f"SELECT count(*) FROM {target}{where}", params).scalar() or 0
            result = conn.exec_driver_sql(
                f"SELECT * FROM {target}{where}{order_by} LIMIT %(_limit)s OFFSET %(_offset)s",
                {**params, "_limit": req.limit, "_offset": req.offset},
            )
            rows = [[_jsonable(v) for v in row] for row in result.fetchall()]
        finally:
            conn.close()
    except DBAPIError as e:
        raise _db_error(e)

    return RowsResponse(columns=columns, rows=rows, total=total, limit=req.limit, offset=req.offset)
