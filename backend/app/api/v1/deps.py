"""
API Dependencies
API 라우터에서 공통으로 사용하는 의존성을 정의합니다.

FastAPI의 Depends를 통해 주입됩니다.
"""

import logging
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import (
    AppException,
    NotFoundException,
    ValidationException,
    BusinessRuleException,
    ForbiddenException,
)
from app.services.part_service import PartService
from app.services.partner_service import BusinessPartnerService
from app.services.code_master_service import CodeMasterService
from app.services.inventory_service import InventoryService
from app.services.inventory_lot_service import InventoryLotService
from app.services.purchase_order_service import PurchaseOrderService
from app.services.work_order_service import WorkOrderService
from app.services.approval_service import ApprovalService  # v0.33.0


# ==================== 데이터베이스 세션 ====================

def get_db() -> Generator:
    """
    데이터베이스 세션 의존성

    사용 예시:
        @router.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== 서비스 의존성 ====================

def get_part_service(db: Session = Depends(get_db)) -> PartService:
    """PartService 의존성"""
    return PartService(db)


def get_partner_service(db: Session = Depends(get_db)) -> BusinessPartnerService:
    """BusinessPartnerService 의존성"""
    return BusinessPartnerService(db)


def get_code_master_service(db: Session = Depends(get_db)) -> CodeMasterService:
    """CodeMasterService 의존성"""
    return CodeMasterService(db)


def get_inventory_service(db: Session = Depends(get_db)) -> InventoryService:
    """InventoryService 의존성"""
    return InventoryService(db)


def get_inventory_lot_service(db: Session = Depends(get_db)) -> InventoryLotService:
    """InventoryLotService 의존성"""
    return InventoryLotService(db)


def get_purchase_order_service(db: Session = Depends(get_db)) -> PurchaseOrderService:
    """PurchaseOrderService 의존성"""
    return PurchaseOrderService(db)


def get_work_order_service(db: Session = Depends(get_db)) -> WorkOrderService:
    """WorkOrderService 의존성"""
    return WorkOrderService(db)


def get_approval_service(db: Session = Depends(get_db)) -> ApprovalService:
    """ApprovalService 의존성 (v0.33.0)"""
    return ApprovalService(db)


# ==================== 페이지네이션 ====================

class PaginationParams:
    """페이지네이션 파라미터"""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="페이지 번호"),
        page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    ):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size
        self.limit = page_size


def get_pagination(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
) -> PaginationParams:
    """페이지네이션 의존성"""
    return PaginationParams(page=page, page_size=page_size)


# ==================== 예외 처리 헬퍼 ====================

_err_logger = logging.getLogger("app.error")


def handle_service_exception(e: Exception) -> None:
    """
    서비스 예외를 HTTP 예외로 변환 + **원인을 로그에 명확히 기록**.

    로그 예:
        WARNING [400 입력오류] 필수 입력 항목이 누락되었습니다: 품목 (필드: form_data)
        ERROR   [500 서버오류] ...  (스택트레이스 포함)

    사용 예시:
        try:
            result = service.create(data)
        except Exception as e:
            handle_service_exception(e)
    """
    # 사람이 읽을 원인 메시지 구성(도메인 예외의 message + field)
    _msg = getattr(e, "message", None) or str(e) or e.__class__.__name__
    _field = getattr(e, "field", None) or getattr(e, "rule", None)
    _cause = f"{_msg}" + (f" ({_field})" if _field else "")

    if isinstance(e, NotFoundException):
        _err_logger.warning("[404 없음] %s", _cause)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict())
    elif isinstance(e, ValidationException):
        _err_logger.warning("[400 입력오류] %s", _cause)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())
    elif isinstance(e, ForbiddenException):
        _err_logger.warning("[403 권한없음] %s", _cause)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.to_dict())
    elif isinstance(e, BusinessRuleException):
        _err_logger.warning("[422 규칙위반] %s", _cause)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.to_dict())
    elif isinstance(e, AppException):
        _err_logger.warning("[400 오류] %s", _cause)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())
    else:
        # 예상치 못한 예외는 500 + 스택트레이스까지 기록
        _err_logger.error("[500 서버오류] %s", _msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": str(e)}
        )


# ==================== 공통 응답 포맷 ====================

def create_response(
    data,
    message: str = "성공",
    pagination: Optional[PaginationParams] = None,
    total: Optional[int] = None
) -> dict:
    """
    공통 응답 포맷 생성

    Args:
        data: 응답 데이터
        message: 응답 메시지
        pagination: 페이지네이션 정보
        total: 전체 레코드 수

    Returns:
        포맷된 응답 딕셔너리
    """
    response = {
        "success": True,
        "message": message,
        "data": data,
    }

    if pagination and total is not None:
        response["pagination"] = {
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total": total,
            "total_pages": (total + pagination.page_size - 1) // pagination.page_size
        }

    return response
