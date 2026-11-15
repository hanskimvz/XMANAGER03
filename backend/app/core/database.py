"""
데이터베이스 연결 및 세션 관리
SQLAlchemy를 사용하여 PostgreSQL 데이터베이스와 연결합니다.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 데이터베이스 엔진 생성
# echo=True: SQL 쿼리를 콘솔에 출력 (개발 시 유용)
# connect_args: PostgreSQL 연결 시 클라이언트 인코딩을 UTF-8로 설정
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # Windows 한글 인코딩 에러 방지, 운영에서는 False로 변경
    pool_pre_ping=True,   # 연결 유효성 확인(끊긴 연결 자동 폐기)
    # 커넥션 풀 확대 — 기본(5+10=15)은 다중 사용자·병렬 요청에 부족해 고갈 발생(2026-07)
    pool_size=15,         # 상시 유지 연결 수
    max_overflow=25,      # 피크 시 추가 허용 (최대 40)
    pool_timeout=15,      # 연결 못 얻으면 15초 후 실패(30초 행 방지)
    pool_recycle=1800,    # 30분마다 연결 재활용(오래된/끊긴 연결 정리)
    connect_args={
        "client_encoding": "utf8",  # 한글 인코딩 지원
    }
)

# 세션 팩토리 생성
# autocommit=False: 명시적으로 commit 호출 필요
# autoflush=False: 명시적으로 flush 호출 필요
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base 클래스: 모든 모델이 상속받을 기본 클래스
Base = declarative_base()


def get_db():
    """
    데이터베이스 세션 의존성
    FastAPI의 Depends에서 사용됩니다.

    사용 예시:
    @app.get("/items")
    def read_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db  # 요청 처리 중 세션 제공
    finally:
        db.close()  # 요청 완료 후 세션 닫기


def init_db():
    """
    데이터베이스 초기화
    모든 테이블을 생성합니다.
    주의: Alembic 마이그레이션 사용 시 이 함수는 사용하지 않습니다.
    """
    Base.metadata.create_all(bind=engine)
