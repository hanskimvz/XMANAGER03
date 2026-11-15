"""
관리자 API
DB 백업, 복원, 동기화 등 관리 기능을 제공합니다.
"""

import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from app.core.config import settings
from app.core.auth import require_admin

# v0.41.0: DB 백업/복원/동기화/삭제는 운영 치명적 작업 → 라우터 전체 ADMIN 전용으로 강제.
# (RBAC_MODE 와 무관하게 항상 적용 — 기존 무인증 Critical 결함 해소)
router = APIRouter(prefix="/admin", tags=["관리자"], dependencies=[Depends(require_admin)])

# PostgreSQL bin 경로 (환경에 맞게 수정)
PG_BIN_PATHS = [
    r"C:\Program Files\PostgreSQL\17\bin",
    r"C:\Program Files\PostgreSQL\16\bin",
    r"C:\Program Files\PostgreSQL\15\bin",
    r"C:\Program Files\PostgreSQL\14\bin",
]

def get_pg_bin_path() -> str:
    """PostgreSQL bin 경로 찾기"""
    for path in PG_BIN_PATHS:
        if os.path.exists(path):
            return path
    raise HTTPException(status_code=500, detail="PostgreSQL bin 경로를 찾을 수 없습니다.")

def get_db_config():
    """DB 연결 정보 파싱"""
    # make_url: ?client_encoding=utf8 같은 쿼리스트링과 URL 인코딩된 비밀번호를 올바르게 분리
    from sqlalchemy.engine import make_url
    url = make_url(settings.DATABASE_URL)
    return {
        "user": url.username or "",
        "password": url.password or "",
        "host": url.host or "localhost",
        "port": str(url.port or 5432),
        "dbname": url.database or ""
    }

def get_backup_dir() -> Path:
    """백업 디렉토리 경로"""
    backup_dir = settings.storage_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


# ========== 스키마 ==========

class BackupInfo(BaseModel):
    filename: str
    size: int
    size_display: str
    created_at: str
    is_daily: bool

class BackupListResponse(BaseModel):
    backups: List[BackupInfo]
    total_count: int
    total_size: str

class BackupResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None

class BackupRequest(BaseModel):
    source_db: str = "production"  # "production" or "development"

class RestoreRequest(BaseModel):
    filename: str
    target_db: str = "development"  # "production" or "development"

class SyncRequest(BaseModel):
    direction: str = "prod_to_dev"  # "prod_to_dev" or "dev_to_prod"

class ServerInfo(BaseModel):
    """서버 연결 정보"""
    name: str
    environment: str  # "production" or "development"
    database_name: str
    host: str
    port: str
    is_current: bool  # 현재 연결된 서버인지


class SystemInfoResponse(BaseModel):
    environment: str
    database: str
    storage_path: str
    backup_count: int
    total_backup_size: str
    # v0.12.0: 서버 정보 추가
    servers: List[ServerInfo] = []
    api_version: str = ""
    backend_host: str = ""
    backend_port: int = 0


# ========== 헬퍼 함수 ==========

def format_size(size_bytes: int) -> str:
    """파일 크기를 읽기 쉬운 형식으로 변환"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def run_pg_command(cmd: List[str], env: dict) -> tuple:
    """PostgreSQL 명령 실행"""
    try:
        result = subprocess.run(
            cmd,
            env={**os.environ, **env},
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "타임아웃: 작업이 5분을 초과했습니다."
    except Exception as e:
        return False, "", str(e)


# ========== API 엔드포인트 ==========

@router.get("/system-info", response_model=SystemInfoResponse)
async def get_system_info():
    """시스템 정보 조회"""
    db_config = get_db_config()
    backup_dir = get_backup_dir()

    # 백업 파일 목록
    backup_files = list(backup_dir.glob("*.sql")) + list(backup_dir.glob("*.dump"))
    daily_dir = backup_dir / "daily"
    if daily_dir.exists():
        backup_files += list(daily_dir.glob("*.sql")) + list(daily_dir.glob("*.dump"))

    total_size = sum(f.stat().st_size for f in backup_files)

    # 현재 환경 확인
    app_env = os.getenv("APP_ENV", "default")

    # v0.12.0: 서버 정보 구성
    servers = [
        ServerInfo(
            name="운영 서버",
            environment="production",
            database_name="xmanager",
            host=db_config["host"],
            port=db_config["port"],
            is_current=(db_config["dbname"] == "xmanager")
        ),
        ServerInfo(
            name="개발 서버",
            environment="development",
            database_name="xmanager_dev",
            host=db_config["host"],
            port=db_config["port"],
            is_current=(db_config["dbname"] == "xmanager_dev")
        )
    ]

    return SystemInfoResponse(
        environment=app_env,
        database=db_config["dbname"],
        storage_path=str(settings.storage_path),
        backup_count=len(backup_files),
        total_backup_size=format_size(total_size),
        # v0.12.0: 서버 정보 추가
        servers=servers,
        api_version=settings.PROJECT_VERSION,
        backend_host=db_config["host"],
        backend_port=int(db_config["port"])
    )


@router.get("/backups", response_model=BackupListResponse)
async def list_backups():
    """백업 파일 목록 조회"""
    backup_dir = get_backup_dir()
    daily_dir = backup_dir / "daily"

    backups = []

    # 시간별 백업
    for f in backup_dir.glob("*.sql"):
        stat = f.stat()
        backups.append(BackupInfo(
            filename=f.name,
            size=stat.st_size,
            size_display=format_size(stat.st_size),
            created_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            is_daily=False
        ))

    for f in backup_dir.glob("*.dump"):
        stat = f.stat()
        backups.append(BackupInfo(
            filename=f.name,
            size=stat.st_size,
            size_display=format_size(stat.st_size),
            created_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            is_daily=False
        ))

    # 일별 백업
    if daily_dir.exists():
        for f in daily_dir.glob("*.sql"):
            stat = f.stat()
            backups.append(BackupInfo(
                filename=f"daily/{f.name}",
                size=stat.st_size,
                size_display=format_size(stat.st_size),
                created_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                is_daily=True
            ))
        for f in daily_dir.glob("*.dump"):
            stat = f.stat()
            backups.append(BackupInfo(
                filename=f"daily/{f.name}",
                size=stat.st_size,
                size_display=format_size(stat.st_size),
                created_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                is_daily=True
            ))

    # 최신순 정렬
    backups.sort(key=lambda x: x.created_at, reverse=True)

    total_size = sum(b.size for b in backups)

    return BackupListResponse(
        backups=backups,
        total_count=len(backups),
        total_size=format_size(total_size)
    )


@router.post("/backup", response_model=BackupResponse)
async def create_backup(request: BackupRequest = BackupRequest()):
    """DB 백업 생성 (운영 또는 개발)"""
    try:
        pg_bin = get_pg_bin_path()
        db_config = get_db_config()
        backup_dir = get_backup_dir()

        # 백업 대상 DB 결정
        if request.source_db == "development":
            backup_db_name = "xmanager_dev"
            db_label = "개발"
        else:
            backup_db_name = db_config["dbname"]  # xmanager
            db_label = "운영"

        # 백업 파일명 생성
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{backup_db_name}_{timestamp}.dump"
        filepath = backup_dir / filename

        # pg_dump 실행
        cmd = [
            os.path.join(pg_bin, "pg_dump"),
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-F", "c",  # custom format
            "-f", str(filepath),
            backup_db_name
        ]

        env = {"PGPASSWORD": db_config["password"]}
        success, stdout, stderr = run_pg_command(cmd, env)

        if success:
            return BackupResponse(
                success=True,
                message=f"{db_label} DB({backup_db_name}) 백업이 완료되었습니다.",
                filename=filename
            )
        else:
            raise HTTPException(status_code=500, detail=f"백업 실패: {stderr}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore", response_model=BackupResponse)
async def restore_backup(request: RestoreRequest):
    """백업에서 DB 복원"""
    try:
        pg_bin = get_pg_bin_path()
        backup_dir = get_backup_dir()

        # 백업 파일 확인
        if request.filename.startswith("daily/"):
            filepath = backup_dir / "daily" / request.filename.replace("daily/", "")
        else:
            filepath = backup_dir / request.filename

        if not filepath.exists():
            raise HTTPException(status_code=404, detail="백업 파일을 찾을 수 없습니다.")

        # 대상 DB 설정
        if request.target_db == "production":
            db_config = get_db_config()
        else:
            # 개발 DB
            db_config = get_db_config()
            db_config["dbname"] = "xmanager_dev"

        env = {"PGPASSWORD": db_config["password"]}

        # 1. 기존 연결 종료 및 DB 재생성
        psql_path = os.path.join(pg_bin, "psql")

        # DB 삭제 (연결 종료 후)
        terminate_cmd = [
            psql_path,
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-d", "postgres",
            "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_config['dbname']}' AND pid <> pg_backend_pid();"
        ]
        run_pg_command(terminate_cmd, env)

        drop_cmd = [
            psql_path,
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-d", "postgres",
            "-c", f"DROP DATABASE IF EXISTS {db_config['dbname']};"
        ]
        run_pg_command(drop_cmd, env)

        # DB 생성
        create_cmd = [
            psql_path,
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-d", "postgres",
            "-c", f"CREATE DATABASE {db_config['dbname']};"
        ]
        success, _, stderr = run_pg_command(create_cmd, env)
        if not success:
            raise HTTPException(status_code=500, detail=f"DB 생성 실패: {stderr}")

        # 2. pg_restore 실행
        restore_cmd = [
            os.path.join(pg_bin, "pg_restore"),
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-d", db_config["dbname"],
            str(filepath)
        ]

        success, stdout, stderr = run_pg_command(restore_cmd, env)

        # pg_restore는 경고도 stderr로 출력하므로, 실패 여부는 returncode로만 판단
        return BackupResponse(
            success=True,
            message=f"'{request.filename}'에서 '{db_config['dbname']}' DB로 복원되었습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=BackupResponse)
async def sync_databases(request: SyncRequest):
    """DB 동기화 (운영 ↔ 개발)"""
    try:
        pg_bin = get_pg_bin_path()
        db_config = get_db_config()
        env = {"PGPASSWORD": db_config["password"]}

        if request.direction == "prod_to_dev":
            source_db = db_config["dbname"]  # xmanager
            target_db = "xmanager_dev"
            direction_text = "운영 → 개발"
        else:
            source_db = "xmanager_dev"
            target_db = db_config["dbname"]  # xmanager
            direction_text = "개발 → 운영"

        psql_path = os.path.join(pg_bin, "psql")
        pg_dump_path = os.path.join(pg_bin, "pg_dump")
        pg_restore_path = os.path.join(pg_bin, "pg_restore")

        # 1. 대상 DB 연결 종료 및 재생성
        terminate_cmd = [
            psql_path,
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-d", "postgres",
            "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{target_db}' AND pid <> pg_backend_pid();"
        ]
        run_pg_command(terminate_cmd, env)

        drop_cmd = [
            psql_path,
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-d", "postgres",
            "-c", f"DROP DATABASE IF EXISTS {target_db};"
        ]
        run_pg_command(drop_cmd, env)

        create_cmd = [
            psql_path,
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-d", "postgres",
            "-c", f"CREATE DATABASE {target_db};"
        ]
        success, _, stderr = run_pg_command(create_cmd, env)
        if not success:
            raise HTTPException(status_code=500, detail=f"DB 생성 실패: {stderr}")

        # 2. 임시 파일로 덤프
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.dump', delete=False) as tmp:
            tmp_path = tmp.name

        dump_cmd = [
            pg_dump_path,
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-F", "c",
            "-f", tmp_path,
            source_db
        ]

        success, _, stderr = run_pg_command(dump_cmd, env)
        if not success:
            os.unlink(tmp_path)
            raise HTTPException(status_code=500, detail=f"덤프 실패: {stderr}")

        # 3. 복원
        restore_cmd = [
            pg_restore_path,
            "-U", db_config["user"],
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-d", target_db,
            tmp_path
        ]

        run_pg_command(restore_cmd, env)

        # 임시 파일 삭제
        os.unlink(tmp_path)

        return BackupResponse(
            success=True,
            message=f"동기화 완료: {direction_text} ({source_db} → {target_db})"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backups/{filename:path}", response_model=BackupResponse)
async def delete_backup(filename: str):
    """백업 파일 삭제"""
    try:
        backup_dir = get_backup_dir()

        if filename.startswith("daily/"):
            filepath = backup_dir / "daily" / filename.replace("daily/", "")
        else:
            filepath = backup_dir / filename

        if not filepath.exists():
            raise HTTPException(status_code=404, detail="백업 파일을 찾을 수 없습니다.")

        os.remove(filepath)

        return BackupResponse(
            success=True,
            message=f"'{filename}' 파일이 삭제되었습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
