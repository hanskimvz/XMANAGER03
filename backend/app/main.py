"""
X-Manager 메인 애플리케이션
FastAPI 애플리케이션의 진입점입니다.
"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from pydantic import ValidationError
from app.core.config import settings
import os
import traceback
import logging
import sys

# 보안 ⑥: 운영(production)은 INFO 레벨(민감정보/SQL 의 stdout 노출 방지), 그 외(dev)는 DEBUG.
_IS_PROD = os.getenv("APP_ENV", "").lower() == "production"
logging.basicConfig(level=logging.INFO if _IS_PROD else logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# CORS 미들웨어 설정
# 프론트엔드(Vue.js)에서 API 호출을 허용하기 위해 필요합니다.
# 네트워크 접속을 허용하기 위해 allow_origins=["*"] 사용 시 allow_credentials=False 필요
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,  # 허용할 도메인
    allow_credentials=False,  # allow_origins=["*"] 사용 시 False 필요
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST, PUT, DELETE 등)
    allow_headers=["*"],  # 모든 헤더 허용
)


# ==================== 감사 로그 미들웨어 ("누가 무슨 작업") ====================
# 쓰기 작업(POST/PUT/PATCH/DELETE) 및 에러(4xx/5xx, 단 401 폴링 제외)에 대해
# 로그인 사용자 이름 + 사람이 읽을 작업 라벨 + 상태코드를 한 줄로 남긴다.
# 예: INFO:app.audit:[작업] 정용호(cjh) · 결재 상신 → 400
_audit_logger = logging.getLogger("app.audit")
_AUDIT_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_user_name_cache: dict = {}  # user_id -> "이름(아이디)" (프로세스 수명 캐시)


def _audit_resolve_user(request: "Request") -> str:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return "비로그인"
    try:
        from app.core.auth import decode_token
        payload = decode_token(auth[7:])
        if not payload or "sub" not in payload:
            return "비로그인"
        uid = int(payload["sub"])
    except Exception:
        return "?"
    if uid in _user_name_cache:
        return _user_name_cache[uid]
    who = f"user#{uid}"
    try:
        from app.core.database import SessionLocal
        from app.models.user import User
        with SessionLocal() as db:
            u = db.query(User).filter(User.id == uid).first()
            if u:
                who = f"{u.name}({u.username})"
    except Exception:
        pass
    _user_name_cache[uid] = who
    return who


def _audit_action_label(method: str, path: str) -> str:
    p = path.rstrip("/")
    if "/approvals" in p:
        if p.endswith("/submit"): return "결재 상신"
        if p.endswith("/approve"): return "결재 승인"
        if p.endswith("/reject"): return "결재 반려"
        if p.endswith("/cancel"): return "결재 회수"
        if p.endswith("/resubmit"): return "결재 재상신"
        if p.endswith("/execute"): return "시행 완료"
        if p.endswith("/dates"): return "일자 수정(관리자)"
        if p.endswith("/correct") or "/actions/" in p: return "정정(관리자)"
        if "/comments" in p:
            return "결재 의견 삭제" if method == "DELETE" else "결재 의견 작성"
        if "/attachments" in p:
            return "첨부 삭제" if method == "DELETE" else "첨부 업로드"
        if method == "POST" and p.endswith("/approvals"): return "기안 생성"
        if method == "PUT": return "기안 수정"
        if method == "DELETE": return "결재 삭제"
    if p.endswith("/auth/login"): return "로그인"
    if p.endswith("/auth/refresh"): return "토큰 갱신"
    return f"{method} {path}"


@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)
    try:
        sc = response.status_code
        method = request.method
        # 화면 열람 비콘(/activity/view)은 자체적으로 [화면] 로그를 남기므로 [작업] 중복 제외
        if request.url.path.endswith("/activity/view"):
            return response
        # 쓰기 작업(모든 상태) 또는 실제 에러(401 폴링 제외)만 기록
        if method in _AUDIT_WRITE_METHODS or (sc >= 400 and sc != 401):
            who = _audit_resolve_user(request)
            action = _audit_action_label(method, request.url.path)
            _audit_logger.info("[작업] %s · %s → %s", who, action, sc)
    except Exception:
        pass
    return response


@app.get("/")
async def root():
    """
    루트 엔드포인트
    API 상태를 확인할 수 있습니다.
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "description": settings.PROJECT_DESCRIPTION,
    }


@app.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트 (Route 53 Health Check 용)
    서버 + DB 연결 상태를 확인합니다.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )
    finally:
        db.close()  # 예외 시에도 반드시 반환(연결 누수 방지)


@app.get("/api/health")
async def api_health_check():
    """
    API 경로 헬스 체크 (Route 53 Health Check 경로: /api/health)
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )
    finally:
        db.close()  # 예외 시에도 반드시 반환(연결 누수 방지)


# 응답 검증 에러 핸들러 (보안 ④: 상세는 서버 로그에만, 운영 응답은 일반 메시지)
@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    logger.error(f"Response validation error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Response validation error"} if _IS_PROD
        else {"detail": "Response validation error", "errors": str(exc.errors())},
    )


# 전역 예외 핸들러 (보안 ④: traceback/내부정보 응답 노출 금지 — 전체 스택은 서버 로그에만)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"} if _IS_PROD
        else {"detail": f"Internal Server Error: {exc}"},  # 개발 편의(스택 미포함)
    )


# API 라우터 등록
from app.api.v1 import code_master, parts, supplier, files, business_partner, bom, inventory, purchase_order, work_order, admin, price, production_request, product_description_code, sales_document, process_log, sales_activity, auth, dashboard, work_order_task, process_template, approval, project, rbac, department, leave, announcement, notification, push, cloud_files, manual, free_board
# RBAC 가드(v0.41.0): 라우터 레벨로 module:action 권한 검사. RBAC_MODE=disabled 면 통과.
from app.core.rbac_guard import module_guard, login_guard

def _guard(module):
    return [Depends(module_guard(module))]

app.include_router(code_master.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("code"))
app.include_router(parts.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("part"))
# [DEPRECATED] supplier 라우터 - business_partner로 대체됨
# 하위 호환성을 위해 유지하지만, 새 개발에서는 business_partner 사용 권장
# 향후 버전에서 제거 예정
app.include_router(supplier.router, prefix=settings.API_V1_PREFIX, deprecated=True, dependencies=_guard("partner"))
app.include_router(business_partner.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("partner"))
# 파일 업로드 API (/api/v1/parts/{part_id}/upload/...)
app.include_router(files.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("part"))
# 파일 다운로드 API (/api/v1/files/...) — 공유 다운로드: 로그인만(D-4)
app.include_router(files.files_router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(login_guard())])
# 거래처 파일 업로드 API (/api/v1/partners/{partner_id}/upload/...)
app.include_router(files.partner_files_router, prefix=settings.API_V1_PREFIX, dependencies=_guard("partner"))
# BOM API
app.include_router(bom.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("bom"))
# 재고관리 API (v0.5.0)
app.include_router(inventory.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("inventory"))
# 입출고 관리 API (v0.6.0)
app.include_router(purchase_order.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("purchase"))
app.include_router(work_order.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("workorder"))
# 생산 요청서 API (v0.20.0)
app.include_router(production_request.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("production"))
# 관리자 API (DB 백업/복원/동기화) — 라우터 자체가 require_admin(admin.py)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
# DB관리자 API (설정 > DB관리자: DB/테이블 raw data 조회, 읽기 전용) — 라우터 자체가 require_admin
from app.api.v1 import db_browser
app.include_router(db_browser.router, prefix=settings.API_V1_PREFIX)
# 원가관리 API (v0.18.0)
app.include_router(price.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("price"))
# 제품 설명 코드 API (v0.24.0)
app.include_router(product_description_code.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("code"))
# Description 자동조합(compose)은 읽기 전용 헬퍼 — 견적 작성 등 모든 로그인 사용자 허용(로그인만)
app.include_router(product_description_code.compose_router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(login_guard())])
# 영업 문서 API (v0.24.0) - Quotation / PI / CI
app.include_router(sales_document.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("sales"))
# 영업 문서 삭제 — 로그인만(권한 판정은 엔드포인트: 관리자 전체 / CI 는 sales:ci_delete)
app.include_router(sales_document.delete_router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(login_guard())])
# 공정 로그 API (v0.24.0) - 세부 공정별 시간 기록 + 리드타임 분석
app.include_router(process_log.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("workorder"))
# 영업 대응 현황 API (v0.27.0)
app.include_router(sales_activity.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("sales_activity"))
# 파일 허브 (Nextcloud 동기화 폴더 브라우저) (v0.81.0) — 영업 권한 상속(생산팀 차단)
app.include_router(cloud_files.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("sales"))
app.include_router(manual.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(login_guard())])
# 인증 + 사용자 관리 API (v0.28.0) — A 예외: /auth 공개 + /users 자체 require_admin
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
# 대시보드 API (v0.28.0)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("dashboard"))
# 공정 작업 API (v0.29.0)
app.include_router(work_order_task.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("workorder"))
# 공정 템플릿 API (v0.29.0)
app.include_router(process_template.router, prefix=settings.API_V1_PREFIX, dependencies=_guard("workorder"))
# 전자결재 API (v0.33.0) — A 예외: 라우터 자체 require_auth/require_admin 유지
app.include_router(approval.router, prefix=settings.API_V1_PREFIX)
# 활동(화면 열람) 로그 — 로그인만 요구(엔드포인트 내부 require_auth), 모듈 RBAC 미적용
from app.api.v1 import activity as _activity
app.include_router(_activity.router, prefix=settings.API_V1_PREFIX)
app.include_router(approval.seal_router, prefix=settings.API_V1_PREFIX)
app.include_router(approval.admin_router, prefix=settings.API_V1_PREFIX)
# 공용 프로젝트 마스터 API (v0.38.0) — A 예외: 라우터 자체 require_auth/require_admin 유지
app.include_router(project.router, prefix=settings.API_V1_PREFIX)
# RBAC 관리 API (v0.40.0) — admin_router(prefix="/admin"), require_admin
app.include_router(rbac.admin_router, prefix=settings.API_V1_PREFIX)
# 부서 마스터 API (v0.43.0) — A 예외: 라우터 자체 require_auth/require_admin
app.include_router(department.router, prefix=settings.API_V1_PREFIX)
# 연차 관리 API (v0.45.0) — A 예외: 본인=require_auth, 관리=leave:manage(경영지원팀)
app.include_router(leave.router, prefix=settings.API_V1_PREFIX)
# 회사 공지사항 API (v0.50.0) — A 예외: 읽기=require_auth+부서필터, 쓰기=announcement:manage(경영지원팀)
app.include_router(announcement.router, prefix=settings.API_V1_PREFIX)
# 자유게시판 API (v1.02.0) — A 예외: require_auth(전 직원 열람/작성), 수정=본인, 삭제=본인/ADMIN
app.include_router(free_board.router, prefix=settings.API_V1_PREFIX)
# 일정 등록 API (v1.03.0) — A 예외: require_auth(전 직원 열람/등록), 수정·삭제=등록자/ADMIN
from app.api.v1 import schedule as schedule_api
app.include_router(schedule_api.router, prefix=settings.API_V1_PREFIX)
# 인앱 알림 API (v0.54.0) — 개인 알림함(require_auth, 본인 알림만)
app.include_router(notification.router, prefix=settings.API_V1_PREFIX)
# 웹푸시 API (v0.59.0) — 구독 저장/해제 + VAPID 공개키
app.include_router(push.router, prefix=settings.API_V1_PREFIX)
# 앱 설정 API (v0.49.0) — A 예외: GET require_auth / PUT require_admin
from app.api.v1 import settings as settings_api
app.include_router(settings_api.router, prefix=settings.API_V1_PREFIX)
# 공휴일 API — 일정 캘린더 표시용(data.go.kr 특일 정보 프록시, require_auth)
from app.api.v1 import holiday as holiday_api
app.include_router(holiday_api.router, prefix=settings.API_V1_PREFIX)


# RBAC 권한 부팅 동기화 (v0.40.0)
# 레지스트리 기준 permissions upsert + EMPLOYEE 기본 권한 부여.
@app.on_event("startup")
def _check_secret_key():
    """운영 SECRET_KEY/CORS 취약 설정 점검(보안 ③⑤). placeholder/약한 키면 기동 실패(JWT 위조 방지)."""
    if not _IS_PROD:
        return
    key = settings.SECRET_KEY or ""
    # placeholder 흔적(과거 .env.production 의 '...please-change...' 류 포함) + 길이 검사
    placeholder = any(w in key.lower() for w in ("change", "please", "placeholder", "example", "your-secret"))
    if key in {"xbeamtech-xmanager-secret-key-2026", ""} or len(key) < 32 or placeholder:
        raise RuntimeError(
            "운영 SECRET_KEY 가 취약/placeholder 입니다(.env.production). 32자 이상 강력한 난수로 설정하세요."
        )
    origins = settings.BACKEND_CORS_ORIGINS
    if origins in ("*", ["*"]) or (isinstance(origins, (list, tuple)) and "*" in origins):
        logger.warning("[SECURITY] 운영 CORS 가 전체 허용(*) 입니다. BACKEND_CORS_ORIGINS 를 운영 도메인으로 제한하세요.")
    # 안전망: 운영에서 RBAC_MODE=disabled 면 업무 API 가 무인증 노출(인터넷 공개). 배포 후 켜기 깜빡 방지.
    if (settings.RBAC_MODE or "disabled").lower() == "disabled":
        logger.warning(
            "[SECURITY] 운영인데 RBAC_MODE=disabled — 업무 API 가 무인증 상태입니다. "
            "관찰/차단(observe→enforce)으로 전환하세요(런북: 전자결재_시스템통합_수정사항.md §13.1)."
        )


@app.on_event("startup")
def _seed_default_departments():
    """기본 부서(영업팀/생산팀/경영지원팀) 시드 — 없을 때만(idempotent). v0.43.0."""
    from app.core.database import SessionLocal
    from app.models.department import Department

    defaults = [("SALES", "영업팀", 1), ("PRODUCTION", "생산팀", 2), ("MANAGEMENT", "경영지원팀", 3)]
    db = SessionLocal()
    try:
        existing = {d.code for d in db.query(Department).all()}
        added = 0
        for code, name, order in defaults:
            if code not in existing:
                db.add(Department(code=code, name=name, sort_order=order))
                added += 1
        if added:
            db.commit()
        logger.info(f"[DEPT] default departments seeded (added={added})")
    except Exception:
        logger.exception("[DEPT] 기본 부서 시드 실패")
    finally:
        db.close()


@app.on_event("startup")
def _sync_rbac_permissions():
    from app.core.database import SessionLocal
    from app.services.rbac_service import sync_permissions, ensure_default_role_grants, ensure_standard_roles

    db = SessionLocal()
    try:
        inserted = sync_permissions(db)
        granted = ensure_default_role_grants(db)
        std = ensure_standard_roles(db)  # v0.41.0 표준 역할(부서장/영업/생산/경영지원) 시드
        logger.info(f"[RBAC] permissions synced (inserted={inserted}), EMPLOYEE grants={granted}, standard roles created={std}")
    except Exception:
        logger.exception("[RBAC] 부팅 권한 동기화 실패")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    # 개발 서버 실행
    # 운영 환경에서는 uvicorn 명령어를 직접 사용하세요.
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True,  # 코드 변경 시 자동 재시작 (개발 환경)
    )
