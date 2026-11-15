"""
원가 관리 API (v0.18.0)
부품 가격 이력 및 원가 계산 API를 제공합니다.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.price_service import PriceService
from app.schemas.price_history import (
    PriceHistoryResponse,
    PriceHistoryListResponse,
    PartPriceInfo,
    PartStandardPriceUpdate,
    AvgPriceRequest,
    AvgPriceResponse,
    ExchangeRateCreate,
    ExchangeRateResponse,
    PriceType,
)
from app.core.exceptions import AppException

router = APIRouter(prefix="/prices", tags=["원가관리"])


def get_price_service(db: Session = Depends(get_db)) -> PriceService:
    return PriceService(db)


def handle_exception(e: AppException):
    """예외 처리"""
    # 예외 코드에 따라 HTTP 상태 코드 결정
    status_code_map = {
        "NOT_FOUND": 404,
        "ALREADY_EXISTS": 409,
        "VALIDATION_ERROR": 400,
        "INVALID_OPERATION": 400,
        "BUSINESS_RULE_VIOLATION": 422,
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
    }
    http_status = status_code_map.get(e.code, 500)
    raise HTTPException(
        status_code=http_status,
        detail={"message": e.message, "code": e.code}
    )


# ==================== 부품 원가 정보 ====================

@router.get("/parts/{part_id}", response_model=PartPriceInfo)
def get_part_price_info(
    part_id: int,
    service: PriceService = Depends(get_price_service)
):
    """
    부품 원가 정보 조회

    모든 가격 정보를 한 번에 조회합니다:
    - 기준단가 (사용자 입력)
    - 재고단가 (이동평균)
    - 최근단가 (최종 입고가)
    - 평균단가 (30일/90일/5건/10건)
    """
    try:
        return service.get_part_price_info(part_id)
    except AppException as e:
        handle_exception(e)


@router.patch("/parts/{part_id}/standard-price", response_model=PartPriceInfo)
def update_standard_price(
    part_id: int,
    data: PartStandardPriceUpdate,
    service: PriceService = Depends(get_price_service)
):
    """
    부품 기준단가 수정

    사용자가 직접 입력하는 목표/기준 단가를 수정합니다.
    변경 이력이 자동으로 기록됩니다.
    """
    try:
        service.update_standard_price(part_id, data)
        return service.get_part_price_info(part_id)
    except AppException as e:
        handle_exception(e)


@router.post("/parts/{part_id}/refresh-cache", response_model=PartPriceInfo)
def refresh_avg_price_cache(
    part_id: int,
    service: PriceService = Depends(get_price_service)
):
    """
    부품 평균단가 캐시 갱신

    평균단가 필드들을 재계산하여 업데이트합니다:
    - avg_price_30d: 최근 30일 평균
    - avg_price_90d: 최근 90일 평균
    - avg_price_last5: 최근 5건 평균
    - avg_price_last10: 최근 10건 평균
    """
    try:
        service.update_avg_price_cache(part_id)
        return service.get_part_price_info(part_id)
    except AppException as e:
        handle_exception(e)


# ==================== 평균단가 계산 ====================

@router.get("/parts/{part_id}/avg-price", response_model=AvgPriceResponse)
def calculate_avg_price(
    part_id: int,
    from_date: Optional[datetime] = Query(None, description="시작일"),
    to_date: Optional[datetime] = Query(None, description="종료일"),
    last_count: Optional[int] = Query(None, ge=1, le=100, description="최근 N건"),
    supplier_id: Optional[int] = Query(None, description="공급업체 필터"),
    service: PriceService = Depends(get_price_service)
):
    """
    부품 평균단가 계산

    기간별 또는 건수별로 평균단가를 계산합니다.

    - 기간별: from_date, to_date 파라미터 사용
    - 건수별: last_count 파라미터 사용 (최근 N건)
    - 공급업체 필터: supplier_id 파라미터로 특정 공급업체만

    반환값:
    - avg_price: 평균단가 (원화)
    - count: 계산에 사용된 건수
    - min_price: 최저가
    - max_price: 최고가
    """
    try:
        request = AvgPriceRequest(
            part_id=part_id,
            from_date=from_date,
            to_date=to_date,
            last_count=last_count,
            supplier_id=supplier_id
        )
        return service.calculate_avg_price(request)
    except AppException as e:
        handle_exception(e)


# ==================== 가격 이력 ====================

@router.get("/parts/{part_id}/history", response_model=PriceHistoryListResponse)
def get_price_history(
    part_id: int,
    price_type: Optional[PriceType] = Query(None, description="가격유형 필터"),
    supplier_id: Optional[int] = Query(None, description="공급업체 필터"),
    from_date: Optional[datetime] = Query(None, description="시작일"),
    to_date: Optional[datetime] = Query(None, description="종료일"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: PriceService = Depends(get_price_service)
):
    """
    부품 가격 이력 조회

    모든 가격 변동 이력을 조회합니다.

    가격유형(price_type):
    - PURCHASE: 구매 단가 (발주/입고 시)
    - STANDARD: 기준단가 변경
    - MANUAL: 수동 입력
    - QUOTE: 견적가
    """
    try:
        items, total = service.get_price_history(
            part_id=part_id,
            price_type=price_type.value if price_type else None,
            supplier_id=supplier_id,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit
        )

        # 응답 변환
        result_items = []
        for item in items:
            supplier_name = None
            if item.supplier:
                supplier_name = item.supplier.company_name
            result_items.append({
                **item.__dict__,
                "supplier_name": supplier_name
            })

        return {
            "items": result_items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + len(items) < total
        }
    except AppException as e:
        handle_exception(e)


# ==================== 환율 관리 ====================

@router.get("/exchange-rates/{currency_code}")
def get_exchange_rate(
    currency_code: str,
    date: Optional[datetime] = Query(None, description="기준일"),
    service: PriceService = Depends(get_price_service)
):
    """
    환율 조회

    특정 통화의 환율을 조회합니다.
    기준일이 없으면 현재 유효한 환율을 반환합니다.
    """
    try:
        rate = service.get_exchange_rate(currency_code, date)
        return {
            "currency_code": currency_code,
            "rate": rate,
            "date": date or datetime.now()
        }
    except AppException as e:
        handle_exception(e)


@router.post("/exchange-rates", response_model=ExchangeRateResponse, status_code=status.HTTP_201_CREATED)
def create_exchange_rate(
    data: ExchangeRateCreate,
    service: PriceService = Depends(get_price_service)
):
    """
    환율 등록

    새로운 환율을 등록합니다.
    기존 환율이 있으면 만료 처리됩니다.
    """
    try:
        return service.create_exchange_rate(data)
    except AppException as e:
        handle_exception(e)


@router.get("/convert")
def convert_currency(
    amount: float = Query(..., description="금액"),
    from_currency: str = Query(..., description="원본 통화"),
    to_currency: str = Query("KRW", description="대상 통화"),
    date: Optional[datetime] = Query(None, description="기준일"),
    service: PriceService = Depends(get_price_service)
):
    """
    통화 환산

    금액을 다른 통화로 환산합니다.
    현재는 모든 통화를 KRW로 환산하는 것만 지원합니다.
    """
    from decimal import Decimal

    if to_currency != "KRW":
        raise HTTPException(
            status_code=400,
            detail="현재는 KRW로의 환산만 지원합니다."
        )

    try:
        converted = service.convert_to_krw(Decimal(str(amount)), from_currency, date)
        rate = service.get_exchange_rate(from_currency, date)

        return {
            "original_amount": amount,
            "original_currency": from_currency,
            "converted_amount": float(converted),
            "converted_currency": to_currency,
            "exchange_rate": float(rate),
            "date": date or datetime.now()
        }
    except AppException as e:
        handle_exception(e)


# ==================== BOM 기반 원가 계산 (v0.18.0) ====================

@router.get("/parts/{part_id}/bom-cost")
def calculate_bom_cost(
    part_id: int,
    service: PriceService = Depends(get_price_service)
):
    """
    BOM 기반 원가 계산

    부품의 BOM 구성을 기반으로 원가를 계산합니다.

    - 단품 (BOM 없음): 기준단가/최근단가/재고단가 사용
    - 조립품 (BOM 있음): 하위 부품 단가 × 수량의 합계

    반환값:
    - cost_type: MANUAL(단품) / BOM(조립품)
    - material_cost: 재료비 (BOM 합산)
    - labor_cost: 가공비
    - overhead_cost: 경비
    - total_cost: 총원가
    - bom_items: BOM 구성품 상세 목록
    """
    try:
        return service.calculate_bom_cost(part_id)
    except AppException as e:
        handle_exception(e)


@router.get("/parts/{part_id}/bom-cost/breakdown")
def get_bom_cost_breakdown(
    part_id: int,
    service: PriceService = Depends(get_price_service)
):
    """
    BOM 원가 분석 (상세 내역)

    다단계 BOM의 원가 구성을 트리 형태로 반환합니다.

    반환값:
    - part_info: 부품 정보
    - cost_summary: 원가 요약 (재료비, 가공비, 경비, 총원가)
    - has_bom: BOM 존재 여부
    - bom_items: BOM 구성품 상세 목록
    """
    try:
        return service.get_bom_cost_breakdown(part_id)
    except AppException as e:
        handle_exception(e)


@router.post("/parts/{part_id}/bom-cost/save")
def save_calculated_cost(
    part_id: int,
    service: PriceService = Depends(get_price_service)
):
    """
    계산된 원가 저장

    BOM 기반으로 계산된 원가를 부품에 저장합니다.
    - cost_type: MANUAL/BOM
    - material_cost: 재료비
    - calculated_cost: 총원가
    - cost_calculated_at: 계산일시
    """
    try:
        part = service.save_calculated_cost(part_id)
        return service.get_part_price_info(part_id)
    except AppException as e:
        handle_exception(e)


@router.post("/parts/{part_id}/bom-cost/save-all")
def save_all_bom_costs(
    part_id: int,
    service: PriceService = Depends(get_price_service)
):
    """
    BOM 전체 원가 재계산 및 저장

    해당 부품과 모든 하위 BOM의 원가를 재귀적으로 계산하고 저장합니다.
    하위 → 상위 순서로 계산하여 정확한 원가 합산이 이루어집니다.

    반환값:
    - count: 계산된 부품 수
    - part_price_info: 최상위 부품의 원가 정보
    """
    try:
        count = service.save_all_bom_costs(part_id)
        price_info = service.get_part_price_info(part_id)
        return {
            "count": count,
            "message": f"{count}개 부품의 원가가 재계산되었습니다.",
            "part_price_info": price_info
        }
    except AppException as e:
        handle_exception(e)


@router.patch("/parts/{part_id}/labor-cost")
def update_labor_cost(
    part_id: int,
    labor_cost: float = Query(..., ge=0, description="가공비"),
    currency: str = Query("KRW", description="통화"),
    service: PriceService = Depends(get_price_service)
):
    """
    가공비 업데이트

    부품의 가공비(노무비)를 수정합니다.
    가공비는 BOM 원가 계산 시 재료비에 추가됩니다.
    """
    from decimal import Decimal
    try:
        service.update_labor_cost(part_id, Decimal(str(labor_cost)), currency)
        return service.get_part_price_info(part_id)
    except AppException as e:
        handle_exception(e)


@router.patch("/parts/{part_id}/overhead-cost")
def update_overhead_cost(
    part_id: int,
    overhead_cost: float = Query(..., ge=0, description="경비"),
    currency: str = Query("KRW", description="통화"),
    service: PriceService = Depends(get_price_service)
):
    """
    경비 업데이트

    부품의 경비(간접비용)를 수정합니다.
    경비는 BOM 원가 계산 시 재료비에 추가됩니다.
    """
    from decimal import Decimal
    try:
        service.update_overhead_cost(part_id, Decimal(str(overhead_cost)), currency)
        return service.get_part_price_info(part_id)
    except AppException as e:
        handle_exception(e)
