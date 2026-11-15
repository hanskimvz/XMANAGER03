"""
애플리케이션 설정 파일
환경변수 및 기본 설정을 관리합니다.
"""

import json
import os
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from typing import Any, Dict, List, Tuple, Type
from pathlib import Path
from urllib.parse import quote

# Windows 한글 로케일 PostgreSQL 환경에서 psycopg2 가 서버 메시지를
# (libpq 클라이언트 인코딩 협상 전에) cp949 로 받아 UTF-8 디코딩에 실패하는
# 문제 방지. alembic/env.py 와 동일하게 런타임에서도 강제. (없으면 로그인 시 500)
os.environ.setdefault("PGCLIENTENCODING", "UTF8")


# ==================== backend/config.json ====================
# 서버별 설정(DB 접속 정보, API 포트 등)을 한 파일에 모은다.
# 우선순위: OS 환경변수 > config.json > .env.{production|development} > 코드 기본값
# 파일이 없으면 기존(.env) 동작 그대로. 다른 위치를 쓰려면 XMANAGER_CONFIG 환경변수로 경로 지정.
CONFIG_JSON_PATH = Path(
    os.getenv("XMANAGER_CONFIG") or Path(__file__).resolve().parents[2] / "config.json"
)

# config.json 의 "섹션.키" → Settings 필드명
_CONFIG_JSON_MAP = {
    ("server", "host"): "SERVER_HOST",
    ("server", "port"): "SERVER_PORT",
    ("storage", "path"): "STORAGE_PATH",
    ("storage", "upload"): "STORAGE_UPLOAD_DIR",
    ("storage", "approval"): "STORAGE_APPROVAL_DIR",
    ("storage", "sales_document"): "STORAGE_SALES_DOCUMENT_DIR",
    ("nextcloud", "base_path"): "NEXTCLOUD_BASE_PATH",
    ("nextcloud", "delivery_path"): "NEXTCLOUD_DELIVERY_PATH",
    ("security", "secret_key"): "SECRET_KEY",
    ("security", "access_token_expire_minutes"): "ACCESS_TOKEN_EXPIRE_MINUTES",
    ("security", "rbac_mode"): "RBAC_MODE",
    ("security", "cors_origins"): "BACKEND_CORS_ORIGINS",
    ("DATA.GO.KR", "api_key"): "DATA_GO_KR_API_KEY",
}


def _read_config_json() -> Dict[str, Any]:
    """config.json 원문(dict) 로드. 파일이 없으면 빈 dict."""
    if not CONFIG_JSON_PATH.is_file():
        return {}
    try:
        with open(CONFIG_JSON_PATH, encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{CONFIG_JSON_PATH} JSON 형식 오류: {e}") from e
    if not isinstance(data, dict):
        raise RuntimeError(f"{CONFIG_JSON_PATH} 최상위는 객체({{...}})여야 합니다.")
    return data


def _config_json_to_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """config.json 내용을 Settings 필드 값으로 변환."""
    out: Dict[str, Any] = {}

    db = data.get("database")
    if isinstance(db, dict):
        missing = [k for k in ("user", "password", "name") if not db.get(k)]
        if missing:
            raise RuntimeError(f"{CONFIG_JSON_PATH} database 항목 누락: {', '.join(missing)}")
        # 비밀번호 특수문자(@ : / 등)가 URL 을 깨지 않도록 인코딩
        out["DATABASE_URL"] = (
            f"postgresql://{quote(str(db['user']), safe='')}:{quote(str(db['password']), safe='')}"
            f"@{db.get('host', 'localhost')}:{int(db.get('port', 5432))}/{db['name']}"
            "?client_encoding=utf8"
        )

    for (section, key), field in _CONFIG_JSON_MAP.items():
        sec = data.get(section)
        if isinstance(sec, dict) and key in sec:
            out[field] = sec[key]
    return out


_CONFIG_JSON = _read_config_json()

# config.json 의 "env"(production|development) 로 APP_ENV 지정 — 실행 시 APP_ENV 를 따로 안 줘도 됨.
# OS 환경변수 APP_ENV 가 이미 있으면 그쪽이 우선.
if _CONFIG_JSON.get("env"):
    os.environ.setdefault("APP_ENV", str(_CONFIG_JSON["env"]))


class _ConfigJsonSource(PydanticBaseSettingsSource):
    """config.json 을 pydantic-settings 소스로 연결."""

    def get_field_value(self, field, field_name):  # 추상 메서드 구현(미사용)
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        return _config_json_to_settings(_CONFIG_JSON)


def get_env_file() -> str:
    """
    APP_ENV 환경변수에 따라 적절한 .env 파일 반환
    - production: .env.production
    - development: .env.development
    - 기본값: .env
    """
    app_env = os.getenv("APP_ENV", "").lower()
    if app_env == "production":
        return ".env.production"
    elif app_env == "development":
        return ".env.development"
    return ".env"


class Settings(BaseSettings):
    """
    애플리케이션 설정 클래스
    .env 파일에서 환경변수를 자동으로 로드합니다.
    """

    # 프로젝트 기본 정보
    PROJECT_NAME: str = "X-Manager"
    PROJECT_VERSION: str = "0.4.0"
    PROJECT_DESCRIPTION: str = "부품관리 및 BOM 통합 관리 시스템"

    # API 설정
    API_V1_PREFIX: str = "/api/v1"

    # 서버 설정 (run.py 가 이 값으로 uvicorn 기동)
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 5198

    # 데이터베이스 설정
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/xmanager"

    # 보안 설정
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # RBAC 강제 적용 모드 (v0.41.0)
    #   disabled : 권한/인증 검사 안 함 (기존 동작과 동일, 기본값)
    #   observe  : 로그인은 요구(미로그인 401), 권한 부족은 차단하지 않고 로그만 기록
    #   enforce  : 로그인 요구 + 권한 부족 시 403 차단
    # 운영 전환 순서: disabled → observe(로그 수집·역할 보강) → enforce. 문제 시 즉시 disabled.
    RBAC_MODE: str = "disabled"

    # CORS 설정 (개발 환경에서는 모든 출처 허용)
    BACKEND_CORS_ORIGINS: list = ["*"]  # 모든 출처 허용 (네트워크 접속용)

    # 파일 업로드 설정
    # config.json 의 "storage" 섹션으로 지정한다 (아래 값은 config.json 에 없을 때의 기본값).
    #   path           : 스토리지 루트. 절대 경로(예: /ext/FILES) 또는 backend/ 기준 상대 경로
    #   upload         : 첨부파일 폴더 (루트 아래)
    #   approval       : 결재 첨부 폴더 (루트 아래)
    #   sales_document : 영업 문서 PDF 폴더 (루트 아래)
    STORAGE_PATH: str = "../storage"
    STORAGE_UPLOAD_DIR: str = "uploads"
    STORAGE_APPROVAL_DIR: str = "approvals"
    STORAGE_SALES_DOCUMENT_DIR: str = "sales_documents"
    MAX_UPLOAD_SIZE: int = 200 * 1024 * 1024  # 200MB

    # 영업 문서 PDF 저장소 종류 (Phase 3). 저장 위치는 sales_documents_path.
    # 향후 클라우드 전환 시 PDF_STORAGE_BACKEND=s3|azure 등으로 확장 가능
    PDF_STORAGE_BACKEND: str = "local"  # local | s3 | azure (현재 local만 구현)

    # Nextcloud 연동(로컬 동기화 폴더 방식) — 이 경로 아래에 수출/국내판매 폴더가 있음.
    # 서버가 이 경로에 파일/폴더를 쓰면 Nextcloud 데스크톱 클라이언트가 자동 동기화.
    # 미설정('') 시 연동 비활성(폴더 생성/자동저장 안 함).
    NEXTCLOUD_BASE_PATH: str = ""  # 예: C:/Users/xbeam/Nextcloud/GBT
    # 납품/포장사진 전용 베이스(별도 트리) — 출고 포장사진이 {연도} 납품 리스트/{번호_기업명} 에 저장됨.
    # GBT 베이스와 분리(기존 파일허브 링크 보호). 예: C:/Users/xbeam/Nextcloud/XBT_공용/생산_영업_관리파일
    NEXTCLOUD_DELIVERY_PATH: str = ""

    # 공공데이터포털(data.go.kr) 서비스키 — 일정 캘린더 공휴일 표시용(한국천문연구원 특일 정보).
    # config.json 의 "DATA.GO.KR".api_key. 미설정('') 시 공휴일 조회 비활성(빈 목록).
    DATA_GO_KR_API_KEY: str = ""

    # 허용 파일 형식 (나중에 관리자 설정에서 수정 가능하도록)
    ALLOWED_DRAWING_EXTENSIONS: List[str] = [".pdf", ".dwg", ".dxf", ".step", ".stp", ".igs"]
    ALLOWED_PHOTO_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ALLOWED_DOCUMENT_EXTENSIONS: List[str] = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".hwp"]

    # 페이지네이션 기본값
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # 품번 코드 길이 설정 (변경 가능)
    # 품번 구조: [대분류]-[소분류]-[품목코드]-[재질]-[후처리]
    PART_CODE_PRODUCT_LINE_LENGTH: int = 3    # 대분류(제품라인) 길이: HB1, BI3 등
    PART_CODE_PART_GROUP_LENGTH: int = 3      # 소분류(품목군) 길이: DCP, PLP 등 (2~3자리)
    PART_CODE_ITEM_CODE_LENGTH: int = 5       # 품목코드 길이: 00001~99999
    PART_CODE_MATERIAL_LENGTH: int = 2        # 재질 길이: A6, S4 등
    PART_CODE_TREATMENT_LENGTH: int = 2       # 후처리 길이: NK, NN 등

    # 분류 코드 길이 설정
    PART_CODE_DEVELOPMENT_TYPE_LENGTH: int = 1  # 개발구분: D, S, M 등
    PART_CODE_PART_TYPE_LENGTH: int = 1         # 부품유형: P, E, O 등
    PART_CODE_DRAWING_TYPE_LENGTH: int = 1      # 도면여부: D, S, N
    PART_CODE_LEVEL_LENGTH: int = 1             # 레벨: F, P, K 등

    # 회사 정보 (발주서/견적서/작업지시서 출력용)
    COMPANY_NAME: str = "엑스빔테크(주)"
    COMPANY_NAME_EN: str = "XbeamTech Co., Ltd."
    COMPANY_REPRESENTATIVE: str = "김행정"
    COMPANY_BUSINESS_NUMBER: str = "123-45-67890"
    COMPANY_ADDRESS: str = "경기도 김포시 양촌읍 흥신로 239번길 29"
    COMPANY_TEL: str = "02-864-7280"
    COMPANY_FAX: str = "02-864-7281"
    COMPANY_EMAIL: str = "info@xbeamtech.com"
    COMPANY_PURCHASE_MANAGER: str = "박창현"  # 구매 담당자

    @property
    def storage_path(self) -> Path:
        """스토리지 절대 경로 반환"""
        base_path = Path(__file__).parent.parent.parent  # backend/
        return (base_path / self.STORAGE_PATH).resolve()

    @property
    def uploads_path(self) -> Path:
        """업로드(첨부파일) 경로 반환"""
        return self.storage_path / self.STORAGE_UPLOAD_DIR

    @property
    def approvals_path(self) -> Path:
        """결재 첨부 경로 반환"""
        return self.storage_path / self.STORAGE_APPROVAL_DIR

    @property
    def sales_documents_path(self) -> Path:
        """영업 문서 PDF 경로 반환"""
        return self.storage_path / self.STORAGE_SALES_DOCUMENT_DIR

    @property
    def temp_path(self) -> Path:
        """임시 파일 경로 반환"""
        return self.storage_path / "temp"

    def get_allowed_extensions(self, file_type: str) -> List[str]:
        """파일 타입별 허용 확장자 반환"""
        if file_type == "drawing":
            return self.ALLOWED_DRAWING_EXTENSIONS
        elif file_type == "photo":
            return self.ALLOWED_PHOTO_EXTENSIONS
        elif file_type == "document":
            return self.ALLOWED_DOCUMENT_EXTENSIONS
        else:
            return []

    class Config:
        """Pydantic 설정"""
        env_file = get_env_file()  # APP_ENV에 따라 적절한 .env 파일 로드
        env_file_encoding = 'utf-8'
        case_sensitive = True

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # 앞쪽이 우선: OS 환경변수 > config.json > .env 파일
        return (
            init_settings,
            env_settings,
            _ConfigJsonSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


# 전역 설정 인스턴스
settings = Settings()
