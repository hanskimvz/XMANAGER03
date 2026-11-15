#!/usr/bin/env python3
"""
PostgreSQL DB 이관 도구

db_list.json 의 postgresql_org(원본) DB 를 postgresql_dst(대상) 로 그대로 복사한다.
    원본: pg_dump 로 읽기만 한다 (변경 없음).
    대상: 해당 스키마를 비우고(DROP SCHEMA ... CASCADE) 원본 내용으로 다시 채운다.

사용법 (backend/ 에서):
    python3 tool/import_db_postgresql.py                  # default_env(production) DB 이관
    python3 tool/import_db_postgresql.py --env development
    python3 tool/import_db_postgresql.py --env all        # databases 에 있는 것 전부
    python3 tool/import_db_postgresql.py --yes            # 확인 질문 생략
    python3 tool/import_db_postgresql.py --verify-only    # 복사 없이 원본/대상 행 수만 비교

필요: pg_dump / pg_restore (원본 서버 버전 이상), psycopg2
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2 import sql

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = TOOL_DIR / "db_list.json"
DEFAULT_DUMP_DIR = TOOL_DIR / "dump"

ORG_KEY = "postgresql_org"
DST_KEY = "postgresql_dst"


# ==================== 설정 ====================

def load_config(path: Path) -> dict:
    if not path.is_file():
        sys.exit(f"[오류] 설정 파일이 없습니다: {path}")
    with open(path, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    for key in (ORG_KEY, DST_KEY):
        if key not in cfg:
            sys.exit(f"[오류] {path.name} 에 '{key}' 항목이 없습니다.")
        for field in ("user", "password", "databases"):
            if not cfg[key].get(field):
                sys.exit(f"[오류] {path.name} 의 {key}.{field} 가 비어 있습니다.")
    return cfg


def conn_info(server: dict, dbname: str) -> dict:
    """서버 설정 + DB 이름 → 접속 정보. host 생략 시 localhost."""
    return {
        "host": server.get("host") or "localhost",
        "port": int(server.get("port") or 5432),
        "user": server["user"],
        "password": server["password"],
        "dbname": dbname,
    }


def label(ci: dict) -> str:
    return f"{ci['user']}@{ci['host']}:{ci['port']}/{ci['dbname']}"


def connect(ci: dict):
    try:
        return psycopg2.connect(
            host=ci["host"], port=ci["port"], user=ci["user"],
            password=ci["password"], dbname=ci["dbname"], connect_timeout=10,
        )
    except UnicodeDecodeError as e:
        # 한글 Windows 서버는 접속 거부 메시지를 cp949 로 보낸다(인코딩 협상 전).
        # psycopg2 가 UTF-8 로 풀다 실패하므로 cp949 로 다시 풀어 원래 메시지를 보여준다.
        message = bytes(e.object).decode("cp949", errors="replace")
        raise psycopg2.OperationalError(message) from None


# ==================== PostgreSQL 클라이언트 도구 ====================

def find_pg_tool(name: str) -> str:
    """pg_dump / pg_restore 경로. PATH 에 없으면 /usr/lib/postgresql/*/bin 의 최신 버전."""
    found = shutil.which(name)
    if found:
        return found
    candidates = glob.glob(f"/usr/lib/postgresql/*/bin/{name}")
    if candidates:
        return max(candidates, key=lambda p: int(re.search(r"/postgresql/(\d+)/", p).group(1)))
    sys.exit(f"[오류] {name} 을 찾을 수 없습니다. PostgreSQL 클라이언트를 설치하세요.")


def tool_major_version(tool: str) -> int:
    out = subprocess.run([tool, "--version"], capture_output=True, text=True).stdout
    m = re.search(r"(\d+)(?:\.\d+)?\s*(?:\(|$)", out.strip())
    return int(m.group(1)) if m else 0


def server_major_version(conn) -> int:
    return conn.server_version // 10000


def run_tool(cmd: list, ci: dict) -> subprocess.CompletedProcess:
    """비밀번호는 명령줄이 아닌 PGPASSWORD 환경변수로 전달."""
    env = {**os.environ, "PGPASSWORD": ci["password"], "PGCLIENTENCODING": "UTF8"}
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def pg_args(ci: dict) -> list:
    return ["-h", ci["host"], "-p", str(ci["port"]), "-U", ci["user"]]


# ==================== 조회 ====================

def list_tables(conn, schema: str) -> list:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = %s ORDER BY tablename", (schema,)
        )
        return [r[0] for r in cur.fetchall()]


def row_counts(conn, schema: str) -> dict:
    """테이블별 정확한 행 수. 권한이 없으면 None."""
    counts = {}
    for table in list_tables(conn, schema):
        try:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(
                    sql.Identifier(schema), sql.Identifier(table)))
                counts[table] = cur.fetchone()[0]
        except psycopg2.Error:
            conn.rollback()
            counts[table] = None
    conn.rollback()
    return counts


def list_extensions(conn) -> list:
    with conn.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension WHERE extname <> 'plpgsql' ORDER BY 1")
        return [r[0] for r in cur.fetchall()]


def alembic_version(conn, schema: str):
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT version_num FROM {}.alembic_version").format(
                sql.Identifier(schema)))
            row = cur.fetchone()
            return row[0] if row else None
    except psycopg2.Error:
        conn.rollback()
        return None


# ==================== 단계 ====================

def dump_source(org: dict, schema: str, dump_file: Path) -> None:
    pg_dump = find_pg_tool("pg_dump")
    cmd = [pg_dump, *pg_args(org), "-d", org["dbname"],
           "-n", schema, "-F", "c", "--no-owner", "--no-acl", "-f", str(dump_file)]
    result = run_tool(cmd, org)
    if result.returncode != 0:
        dump_file.unlink(missing_ok=True)
        hint = ""
        if "permission denied" in result.stderr or "lack SELECT privilege" in result.stderr:
            hint = (f"\n  → 원본 계정 '{org['user']}' 에 테이블/시퀀스 SELECT 권한이 부족합니다."
                    f"\n    원본 서버에서: GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {org['user']};"
                    f"\n                   GRANT SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {org['user']};")
        elif "server version mismatch" in result.stderr:
            hint = "\n  → pg_dump 버전이 원본 서버보다 낮습니다. 원본과 같거나 높은 버전의 클라이언트가 필요합니다."
        sys.exit(f"[오류] pg_dump 실패:\n{result.stderr.strip()}{hint}")


def ensure_extensions(src_conn, dst: dict) -> None:
    """스키마 단위 덤프에는 확장이 포함되지 않으므로 대상에 미리 만든다."""
    wanted = list_extensions(src_conn)
    if not wanted:
        return
    conn = connect(dst)
    conn.autocommit = True
    try:
        have = set(list_extensions(conn))
        for ext in wanted:
            if ext in have:
                continue
            try:
                with conn.cursor() as cur:
                    cur.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(ext)))
                print(f"  확장 생성: {ext}")
            except psycopg2.Error as e:
                print(f"  [경고] 확장 '{ext}' 생성 실패 — 복원이 실패하면 대상 서버에서 실행하세요:\n"
                      f"         sudo -u postgres psql -d {dst['dbname']} -c 'CREATE EXTENSION \"{ext}\";'\n"
                      f"         ({str(e).strip()})")
    finally:
        conn.close()


def reset_schema(dst: dict, schema: str) -> None:
    """대상 스키마를 통째로 비운다."""
    conn = connect(dst)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    finally:
        conn.close()


def restore_to_dest(dst: dict, schema: str, dump_file: Path) -> None:
    pg_restore = find_pg_tool("pg_restore")

    # 스키마는 reset_schema 가 이미 만들었으므로, 덤프 목록에서 스키마 생성 항목만 제외
    toc = subprocess.run([pg_restore, "-l", str(dump_file)], capture_output=True, text=True)
    if toc.returncode != 0:
        sys.exit(f"[오류] 덤프 목록 읽기 실패:\n{toc.stderr.strip()}")
    skip = re.compile(rf"^\d+;\s.*\s(SCHEMA - {re.escape(schema)}|COMMENT - SCHEMA {re.escape(schema)})\s")
    list_file = dump_file.with_suffix(".list")
    list_file.write_text(
        "\n".join(line for line in toc.stdout.splitlines() if not skip.match(line)) + "\n",
        encoding="utf-8",
    )

    try:
        # --single-transaction: 중간에 실패하면 전부 롤백 (반쯤 복원된 상태 방지)
        cmd = [pg_restore, *pg_args(dst), "-d", dst["dbname"],
               "--no-owner", "--no-acl", "--single-transaction",
               "-L", str(list_file), str(dump_file)]
        result = run_tool(cmd, dst)
    finally:
        list_file.unlink(missing_ok=True)
    if result.returncode != 0:
        sys.exit(f"[오류] pg_restore 실패 (대상 스키마는 비어 있는 상태입니다):\n{result.stderr.strip()}")


def verify(org: dict, dst: dict, schema: str) -> bool:
    src_conn, dst_conn = connect(org), connect(dst)
    try:
        src, dstc = row_counts(src_conn, schema), row_counts(dst_conn, schema)
        src_ver, dst_ver = alembic_version(src_conn, schema), alembic_version(dst_conn, schema)
    finally:
        src_conn.close()
        dst_conn.close()

    diffs, unknown = [], []
    for table in sorted(set(src) | set(dstc)):
        a, b = src.get(table, "없음"), dstc.get(table, "없음")
        if a is None or b is None:
            unknown.append(table)
        elif a != b:
            diffs.append((table, a, b))

    known = [v for v in src.values() if isinstance(v, int)]
    print(f"  테이블: 원본 {len(src)}개 / 대상 {len(dstc)}개")
    print(f"  행 수 : 원본 {sum(known):,}행 (권한 있는 테이블 기준)")
    print(f"  alembic: 원본 {src_ver} / 대상 {dst_ver}")
    if unknown:
        print(f"  [참고] 행 수를 셀 수 없는 테이블 {len(unknown)}개: {', '.join(unknown)}")
    if diffs:
        print(f"  [불일치] {len(diffs)}개 테이블 (원본이 운영 중이면 덤프 이후 변경분일 수 있음):")
        for table, a, b in diffs:
            print(f"    {table}: 원본 {a} / 대상 {b}")
    ok = not diffs and src_ver == dst_ver
    print("  결과: 일치" if ok else "  결과: 불일치 있음")
    return ok


# ==================== 실행 ====================

def migrate(org: dict, dst: dict, schema: str, args) -> bool:
    print(f"\n=== {org['dbname']} → {dst['dbname']} ===")
    print(f"  원본: {label(org)}")
    print(f"  대상: {label(dst)}")

    if (org["host"], org["port"], org["dbname"]) == (dst["host"], dst["port"], dst["dbname"]):
        sys.exit("[오류] 원본과 대상이 같은 DB 입니다. db_list.json 을 확인하세요.")

    try:
        src_conn = connect(org)
    except psycopg2.Error as e:
        sys.exit(f"[오류] 원본 접속 실패: {str(e).strip()}")
    try:
        dst_conn = connect(dst)
    except psycopg2.Error as e:
        src_conn.close()
        sys.exit(f"[오류] 대상 접속 실패: {str(e).strip()}\n"
                 f"  → 대상 DB 가 없으면 먼저 만드세요:\n"
                 f"    sudo -u postgres psql -c \"CREATE DATABASE {dst['dbname']} OWNER {dst['user']} "
                 f"ENCODING 'UTF8' TEMPLATE template0;\"")

    try:
        if args.verify_only:
            return verify(org, dst, schema)

        src_major = server_major_version(src_conn)
        dump_major = tool_major_version(find_pg_tool("pg_dump"))
        if dump_major and dump_major < src_major:
            sys.exit(f"[오류] pg_dump {dump_major} 로는 원본 서버 {src_major} 를 덤프할 수 없습니다.")
        if server_major_version(dst_conn) < src_major:
            print(f"  [경고] 대상 서버({server_major_version(dst_conn)})가 원본({src_major})보다 낮은 버전입니다.")

        src_tables = list_tables(src_conn, schema)
        dst_tables = list_tables(dst_conn, schema)
        if not src_tables:
            sys.exit(f"[오류] 원본 '{schema}' 스키마에 테이블이 없습니다 (권한 또는 스키마 이름 확인).")
        print(f"  원본 테이블 {len(src_tables)}개, 대상 기존 테이블 {len(dst_tables)}개")

        if dst_tables and not args.yes:
            answer = input(f"  대상 {label(dst)} 의 '{schema}' 스키마 테이블 {len(dst_tables)}개가 "
                           f"모두 삭제됩니다. 계속할까요? [y/N] ")
            if answer.strip().lower() not in ("y", "yes"):
                print("  취소했습니다.")
                return False
    finally:
        dst_conn.close()

    try:
        args.dump_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_file = args.dump_dir / f"{org['dbname']}_{stamp}.dump"

        print(f"[1/4] 원본 덤프 → {dump_file}")
        dump_source(org, schema, dump_file)
        print(f"      {dump_file.stat().st_size / 1024 / 1024:.1f} MB")

        print("[2/4] 대상 스키마 초기화")
        ensure_extensions(src_conn, dst)
        reset_schema(dst, schema)
    finally:
        src_conn.close()

    print("[3/4] 대상에 복원")
    restore_to_dest(dst, schema, dump_file)

    print("[4/4] 검증")
    ok = verify(org, dst, schema)

    if args.delete_dump:
        dump_file.unlink(missing_ok=True)
    else:
        print(f"  덤프 파일 보관: {dump_file}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="postgresql_org → postgresql_dst DB 이관")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="설정 파일 (기본: tool/db_list.json)")
    parser.add_argument("--env", default=None,
                        help="이관할 환경: production | development | all (기본: postgresql_org.default_env)")
    parser.add_argument("--dump-dir", type=Path, default=DEFAULT_DUMP_DIR, help="덤프 파일 저장 폴더")
    parser.add_argument("--delete-dump", action="store_true", help="완료 후 덤프 파일 삭제")
    parser.add_argument("--verify-only", action="store_true", help="복사하지 않고 원본/대상 비교만")
    parser.add_argument("-y", "--yes", action="store_true", help="대상 삭제 확인 질문 생략")
    args = parser.parse_args()

    cfg = load_config(args.config)
    org_cfg, dst_cfg = cfg[ORG_KEY], cfg[DST_KEY]

    env = args.env or org_cfg.get("default_env") or "production"
    envs = list(org_cfg["databases"]) if env == "all" else [env]

    all_ok = True
    for name in envs:
        if name not in org_cfg["databases"]:
            sys.exit(f"[오류] {ORG_KEY}.databases 에 '{name}' 이 없습니다.")
        if name not in dst_cfg["databases"]:
            sys.exit(f"[오류] {DST_KEY}.databases 에 '{name}' 이 없습니다.")
        org = conn_info(org_cfg, org_cfg["databases"][name])
        dst = conn_info(dst_cfg, dst_cfg["databases"][name])
        schema = org_cfg.get("schema") or "public"
        all_ok = migrate(org, dst, schema, args) and all_ok

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
