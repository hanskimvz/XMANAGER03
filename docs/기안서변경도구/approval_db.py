"""
전자결재 날짜 수정 도구 — 독립 DB 계층 (앱 패키지 비의존)

이 모듈은 backend 앱(app.*)을 import 하지 않는다. 날짜 수정에 필요한 4개 테이블의
최소 컬럼만 자체 정의하므로, 이 도구 폴더를 **어디로 옮겨도** 동작한다.

필요 조건(실행하는 파이썬에):
  - SQLAlchemy, psycopg2 (백엔드 .venv 를 쓰면 이미 설치돼 있음)

DB 접속 문자열 결정 순서:
  1) 환경변수 XMANAGER_DB_URL 이 있으면 그것
  2) 같은 폴더의 db_config.ini 의 [database] 섹션에서 APP_ENV(development/production) 선택
     - ini 가 없으면 템플릿을 자동 생성하고 안내 후 종료
"""

import configparser
import os
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    position = Column(String)


class ApprovalDocument(Base):
    __tablename__ = "approval_documents"
    id = Column(Integer, primary_key=True)
    doc_number = Column(String)
    status = Column(String)
    title = Column(Text)
    created_at = Column(DateTime(timezone=True))
    drafted_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    lines = relationship("ApprovalLine", backref="document")
    actions = relationship("ApprovalAction", backref="document")


class ApprovalLine(Base):
    __tablename__ = "approval_lines"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("approval_documents.id"))
    step_order = Column(Integer)
    approver_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String)
    acted_at = Column(DateTime(timezone=True))
    approver = relationship("User")


class ApprovalAction(Base):
    __tablename__ = "approval_actions"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("approval_documents.id"))
    actor_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    acted_at = Column(DateTime(timezone=True))
    actor = relationship("User")


# ==================== 접속 설정 ====================

CONFIG_NAME = "db_config.ini"
_TEMPLATE = """; 전자결재 날짜 수정 도구 — DB 접속 설정
; APP_ENV 환경변수로 development / production 중 선택(기본 development).
; 또는 환경변수 XMANAGER_DB_URL 로 직접 지정하면 이 파일보다 우선합니다.
[database]
development = postgresql://xmanager:xmanager1014@localhost:5432/xmanager_dev?client_encoding=utf8
production  = postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8
"""


def _config_dir() -> Path:
    """db_config.ini 위치 = 이 모듈이 있는 폴더(도구 번들 폴더)."""
    return Path(__file__).resolve().parent


def resolve_db_url() -> str:
    env_url = os.environ.get("XMANAGER_DB_URL")
    if env_url:
        return env_url

    ini = _config_dir() / CONFIG_NAME
    if not ini.exists():
        ini.write_text(_TEMPLATE, encoding="utf-8")
        raise RuntimeError(
            f"DB 설정파일을 새로 만들었습니다:\n  {ini}\n"
            "내용(접속 정보)을 확인/수정한 뒤 다시 실행하세요."
        )

    cp = configparser.ConfigParser()
    cp.read(ini, encoding="utf-8")
    if not cp.has_section("database"):
        raise RuntimeError(f"{ini} 에 [database] 섹션이 없습니다.")
    env = os.environ.get("APP_ENV", "development").lower()
    if env not in cp["database"]:
        env = "development"
    url = cp["database"].get(env, "").strip()
    if not url:
        raise RuntimeError(f"{ini} 의 [database] {env} 값이 비어 있습니다.")
    return url


_session_factory = None


def get_session():
    """설정에서 DB URL 을 해석해 새 세션을 만든다(엔진은 1회 생성 후 재사용)."""
    global _session_factory
    if _session_factory is None:
        engine = create_engine(resolve_db_url(), future=True)
        _session_factory = sessionmaker(bind=engine)
    return _session_factory()
