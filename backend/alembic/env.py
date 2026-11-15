"""
Alembic 환경 설정 파일
데이터베이스 마이그레이션을 위한 설정을 관리합니다.
"""
from logging.config import fileConfig
import sys
import os

# Windows 한글 로케일 PostgreSQL 환경에서 psycopg2 startup 디코딩 충돌 방지
# (libpq가 클라이언트 인코딩 협상 전에 서버 메시지를 받을 때 cp949 → UTF-8 변환 실패하는 케이스)
os.environ.setdefault("PGCLIENTENCODING", "UTF8")

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 우리의 설정과 모델 가져오기
from app.core.config import settings
from app.core.database import Base

# 이곳에 모든 모델을 import 해야 autogenerate가 작동합니다
from app.models import code_master  # 코드 마스터 테이블
from app.models import supplier, parts  # 공급업체, 부품 마스터
# from app.models import process, bom  # 나중에 추가

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# .env 파일의 DATABASE_URL을 Alembic 설정에 주입
config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 모델의 MetaData 객체 설정 (autogenerate 지원)
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "options" : "-c client_encoding=utf8"
        }
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
