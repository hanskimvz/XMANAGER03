"""
거래처 관리 API
공급업체와 고객사를 통합 관리합니다.

Service Layer를 통해 비즈니스 로직을 처리합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional
from io import BytesIO
from datetime import datetime
from urllib.parse import quote

from app.api.v1.deps import get_partner_service, handle_service_exception
from app.services.partner_service import BusinessPartnerService
from app.schemas.business_partner import (
    BusinessPartnerCreate,
    BusinessPartnerUpdate,
    BusinessPartnerResponse,
    BusinessPartnerListItem,
    BusinessPartnerPaginatedResponse,
)
from app.core.exceptions import AppException
from app.models.business_partner_contact import BusinessPartnerContact
from app.schemas.business_partner_contact import ContactCreate, ContactUpdate, ContactResponse
from app.models.business_partner_shipping_address import BusinessPartnerShippingAddress
from app.schemas.business_partner_shipping_address import (
    ShippingAddressCreate, ShippingAddressUpdate, ShippingAddressResponse,
)
from app.models.partner_note import PartnerNote
from app.schemas.partner_note import PartnerNoteCreate, PartnerNoteUpdate, PartnerNoteResponse
from app.models.partner_balance import PartnerBalanceTransaction

router = APIRouter(prefix="/partners", tags=["business-partners"])


@router.get("", response_model=BusinessPartnerPaginatedResponse)
def get_partners(
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    is_supplier: Optional[bool] = Query(None, description="공급업체 필터"),
    is_customer: Optional[bool] = Query(None, description="고객사 필터"),
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(20, ge=1, le=1000, description="최대 레코드 수"),
    order_by: str = Query("created_at", description="정렬 기준 (partner_code, partner_name, created_at 등)"),
    order_desc: bool = Query(True, description="내림차순 정렬 여부"),
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """
    거래처 목록 조회 (검색 및 필터링 지원) - 페이지네이션 및 정렬 지원

    - **keyword**: 거래처 코드 또는 거래처명으로 검색
    - **is_supplier**: 공급업체 필터 (True/False)
    - **is_customer**: 고객사 필터 (True/False)
    - **is_active**: 활성 여부 필터 (True/False)
    - **skip**: 건너뛸 레코드 수 (페이지네이션)
    - **limit**: 최대 레코드 수 (기본 20, 최대 1000)
    - **order_by**: 정렬 기준 컬럼 (기본: created_at)
    - **order_desc**: 내림차순 정렬 여부 (기본: True)
    """
    items, total = service.search_partners_with_count(
        keyword=keyword,
        is_supplier=is_supplier,
        is_customer=is_customer,
        is_active=is_active,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_desc=order_desc
    )
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }


@router.get("/suppliers", response_model=List[BusinessPartnerListItem])
def get_suppliers(
    is_active: Optional[bool] = Query(True, description="활성 여부 필터"),
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(100, ge=1, le=1000, description="최대 레코드 수"),
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """공급업체 목록 조회"""
    return service.get_suppliers(is_active=is_active, skip=skip, limit=limit)


@router.get("/customers", response_model=List[BusinessPartnerListItem])
def get_customers(
    is_active: Optional[bool] = Query(True, description="활성 여부 필터"),
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(100, ge=1, le=1000, description="최대 레코드 수"),
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """고객사 목록 조회"""
    return service.get_customers(is_active=is_active, skip=skip, limit=limit)


@router.get("/{partner_id}", response_model=BusinessPartnerResponse)
def get_partner(
    partner_id: int,
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 단건 조회

    - **partner_id**: 거래처 ID
    """
    try:
        return service.get_or_raise(partner_id)
    except AppException as e:
        handle_service_exception(e)


@router.get("/code/{partner_code}", response_model=BusinessPartnerResponse)
def get_partner_by_code(
    partner_code: str,
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 코드로 조회

    - **partner_code**: 거래처 코드
    """
    try:
        return service.get_by_code_or_raise(partner_code)
    except AppException as e:
        handle_service_exception(e)


@router.get("/{partner_id}/recent-orders")
def get_recent_orders(
    partner_id: int,
    limit: int = Query(10, ge=1, le=50, description="조회할 최근 주문 건수"),
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """
    거래처의 최근 주문(PI/CI) 이력 조회 (재주문 패널용)

    각 문서마다 대표 제품명과 품목 수를 함께 반환
    """
    from app.models.sales_document import SalesDocument
    from sqlalchemy.orm import joinedload
    from sqlalchemy import desc

    db = service.db

    docs = db.query(SalesDocument).options(
        joinedload(SalesDocument.items),
    ).filter(
        SalesDocument.customer_id == partner_id,
        SalesDocument.document_type.in_(["PI", "CI"]),
    ).order_by(desc(SalesDocument.document_date), desc(SalesDocument.id)).limit(limit).all()

    result = []
    for doc in docs:
        items_sorted = sorted(doc.items or [], key=lambda i: i.line_no or 0)
        rep_product = None
        if items_sorted:
            first = items_sorted[0]
            rep_product = first.product_code or (first.description or '').split('\n')[0] or None
        result.append({
            "id": doc.id,
            "document_type": doc.document_type,
            "document_number": doc.document_number,
            "document_date": doc.document_date.isoformat() if doc.document_date else None,
            "total_amount": float(doc.total_amount or 0),
            "currency": doc.currency,
            "status": doc.status,
            "payment_status": doc.payment_status,
            "representative_product": rep_product,
            "item_count": len(items_sorted),
        })
    return {"partner_id": partner_id, "documents": result}


@router.post("/{partner_id}/reorder/{source_doc_id}")
def create_reorder_activity(
    partner_id: int,
    source_doc_id: int,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """
    재주문 영업활동 자동 생성

    원본 PI/CI를 기반으로:
    1. 새 영업활동 생성 (제목: "재주문 - {원본 문서번호}")
    2. 영업활동 ID와 원본 문서 ID를 반환
    3. 프론트엔드는 견적서 생성 화면으로 이동하여 원본 품목을 복사할 수 있음
    """
    from app.models.sales_document import SalesDocument
    from app.models.sales_activity import SalesActivity, SalesActivityLog
    from app.models.business_partner import BusinessPartner

    db = service.db

    partner = db.query(BusinessPartner).filter(BusinessPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다")

    source_doc = db.query(SalesDocument).filter(
        SalesDocument.id == source_doc_id,
        SalesDocument.customer_id == partner_id,
    ).first()
    if not source_doc:
        raise HTTPException(status_code=404, detail="원본 문서를 찾을 수 없습니다")

    # 영업활동 생성
    activity = SalesActivity(
        customer_id=partner_id,
        customer_name=partner.partner_name,
        country=partner.country_name,
        title=f"재주문 - {source_doc.document_number}",
        status="IN_PROGRESS",
        inquiry_type="QUOTATION",  # 재주문은 견적 문의로 분류
        next_step=f"{source_doc.document_number} 기반 재주문 견적서 작성",
    )
    db.add(activity)
    db.flush()

    # 자동 로그 (재주문임을 명시)
    log = SalesActivityLog(
        activity_id=activity.id,
        log_type="COMMENT",
        content=f"📦 {source_doc.document_type} {source_doc.document_number} 기반 재주문으로 생성됨",
    )
    db.add(log)
    db.commit()
    db.refresh(activity)

    return {
        "activity_id": activity.id,
        "source_document_id": source_doc_id,
        "source_document_type": source_doc.document_type,
        "source_document_number": source_doc.document_number,
        "customer_id": partner_id,
    }


# ==================== 국내 업체 코드 자동 채번 (v0.31.0) ====================

@router.get("/generate-domestic-code/{partner_type}")
def generate_domestic_code(
    partner_type: str,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """
    국내 업체 코드 자동 채번

    partner_type: 'customer' → CUS001, CUS002, ...
    partner_type: 'supplier' → SUP001, SUP002, ...
    """
    from app.models.business_partner import BusinessPartner

    db = service.db

    if partner_type == 'customer':
        prefix = 'CUS'
    elif partner_type == 'supplier':
        prefix = 'SUP'
    else:
        raise HTTPException(status_code=400, detail="partner_type은 'customer' 또는 'supplier'만 가능합니다")

    # 해당 prefix로 시작하는 코드 중 최대 번호 조회
    existing = db.query(BusinessPartner.partner_code).filter(
        BusinessPartner.partner_code.like(f"{prefix}%")
    ).all()

    max_num = 0
    for (code,) in existing:
        try:
            num_part = code.replace(prefix, '')
            num = int(num_part)
            if num > max_num:
                max_num = num
        except (ValueError, TypeError):
            continue

    next_num = max_num + 1
    new_code = f"{prefix}{next_num:03d}"

    return {"code": new_code, "prefix": prefix, "number": next_num}


# ==================== 담당자 관리 (v0.31.0) ====================

def _sync_primary_contact_to_partner(db, partner_id: int):
    """기본 담당자 → business_partner.manager_name 동기화"""
    from app.models.business_partner import BusinessPartner
    primary = db.query(BusinessPartnerContact).filter(
        BusinessPartnerContact.partner_id == partner_id,
        BusinessPartnerContact.is_primary == True,
    ).first()
    partner = db.query(BusinessPartner).filter(BusinessPartner.id == partner_id).first()
    if partner:
        partner.manager_name = primary.name if primary else None
        partner.manager_position = primary.position if primary else None
        partner.manager_email = primary.email if primary else None
        partner.manager_mobile = primary.tel_mobile if primary else None
        db.commit()

@router.get("/{partner_id}/contacts", response_model=List[ContactResponse])
def get_contacts(
    partner_id: int,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 담당자 목록 조회"""
    db = service.db
    contacts = db.query(BusinessPartnerContact).filter(
        BusinessPartnerContact.partner_id == partner_id
    ).order_by(BusinessPartnerContact.is_primary.desc(), BusinessPartnerContact.sort_order).all()
    return contacts


@router.post("/{partner_id}/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    partner_id: int,
    data: ContactCreate,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 담당자 추가"""
    db = service.db
    # 파트너 존재 확인
    from app.models.business_partner import BusinessPartner
    partner = db.query(BusinessPartner).filter(BusinessPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다")

    # is_primary=True로 추가하면 기존 primary 해제
    if data.is_primary:
        db.query(BusinessPartnerContact).filter(
            BusinessPartnerContact.partner_id == partner_id,
            BusinessPartnerContact.is_primary == True,
        ).update({"is_primary": False})

    contact = BusinessPartnerContact(
        partner_id=partner_id,
        **data.model_dump(),
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    _sync_primary_contact_to_partner(db, partner_id)
    return contact


@router.put("/{partner_id}/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(
    partner_id: int,
    contact_id: int,
    data: ContactUpdate,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 담당자 수정"""
    db = service.db
    contact = db.query(BusinessPartnerContact).filter(
        BusinessPartnerContact.id == contact_id,
        BusinessPartnerContact.partner_id == partner_id,
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="담당자를 찾을 수 없습니다")

    update_data = data.model_dump(exclude_unset=True)

    # is_primary=True로 변경하면 기존 primary 해제
    if update_data.get("is_primary"):
        db.query(BusinessPartnerContact).filter(
            BusinessPartnerContact.partner_id == partner_id,
            BusinessPartnerContact.is_primary == True,
            BusinessPartnerContact.id != contact_id,
        ).update({"is_primary": False})

    for key, value in update_data.items():
        setattr(contact, key, value)

    db.commit()
    db.refresh(contact)
    _sync_primary_contact_to_partner(db, partner_id)
    return contact


@router.delete("/{partner_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    partner_id: int,
    contact_id: int,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 담당자 삭제"""
    db = service.db
    contact = db.query(BusinessPartnerContact).filter(
        BusinessPartnerContact.id == contact_id,
        BusinessPartnerContact.partner_id == partner_id,
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="담당자를 찾을 수 없습니다")
    db.delete(contact)
    db.commit()
    _sync_primary_contact_to_partner(db, partner_id)


# ==================== 거래처 배송지 (v0.58.0) ====================

@router.get("/{partner_id}/shipping-addresses", response_model=List[ShippingAddressResponse])
def get_shipping_addresses(partner_id: int, service: BusinessPartnerService = Depends(get_partner_service)):
    """거래처 배송지 목록"""
    return service.db.query(BusinessPartnerShippingAddress).filter(
        BusinessPartnerShippingAddress.partner_id == partner_id
    ).order_by(BusinessPartnerShippingAddress.is_default.desc(),
               BusinessPartnerShippingAddress.sort_order,
               BusinessPartnerShippingAddress.id).all()


@router.post("/{partner_id}/shipping-addresses", response_model=ShippingAddressResponse, status_code=status.HTTP_201_CREATED)
def create_shipping_address(partner_id: int, data: ShippingAddressCreate,
                            service: BusinessPartnerService = Depends(get_partner_service)):
    """거래처 배송지 추가"""
    from app.models.business_partner import BusinessPartner
    db = service.db
    if not db.query(BusinessPartner).filter(BusinessPartner.id == partner_id).first():
        raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다")
    if data.is_default:
        db.query(BusinessPartnerShippingAddress).filter(
            BusinessPartnerShippingAddress.partner_id == partner_id,
            BusinessPartnerShippingAddress.is_default == True,  # noqa: E712
        ).update({"is_default": False})
    addr = BusinessPartnerShippingAddress(partner_id=partner_id, **data.model_dump())
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return addr


@router.put("/{partner_id}/shipping-addresses/{address_id}", response_model=ShippingAddressResponse)
def update_shipping_address(partner_id: int, address_id: int, data: ShippingAddressUpdate,
                            service: BusinessPartnerService = Depends(get_partner_service)):
    """거래처 배송지 수정"""
    db = service.db
    addr = db.query(BusinessPartnerShippingAddress).filter(
        BusinessPartnerShippingAddress.id == address_id,
        BusinessPartnerShippingAddress.partner_id == partner_id,
    ).first()
    if not addr:
        raise HTTPException(status_code=404, detail="배송지를 찾을 수 없습니다")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("is_default"):
        db.query(BusinessPartnerShippingAddress).filter(
            BusinessPartnerShippingAddress.partner_id == partner_id,
            BusinessPartnerShippingAddress.is_default == True,  # noqa: E712
            BusinessPartnerShippingAddress.id != address_id,
        ).update({"is_default": False})
    for key, value in update_data.items():
        setattr(addr, key, value)
    db.commit()
    db.refresh(addr)
    return addr


@router.delete("/{partner_id}/shipping-addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipping_address(partner_id: int, address_id: int,
                            service: BusinessPartnerService = Depends(get_partner_service)):
    """거래처 배송지 삭제"""
    db = service.db
    addr = db.query(BusinessPartnerShippingAddress).filter(
        BusinessPartnerShippingAddress.id == address_id,
        BusinessPartnerShippingAddress.partner_id == partner_id,
    ).first()
    if not addr:
        raise HTTPException(status_code=404, detail="배송지를 찾을 수 없습니다")
    db.delete(addr)
    db.commit()


# ==================== 거래처 CRUD ====================

@router.post("", response_model=BusinessPartnerResponse, status_code=status.HTTP_201_CREATED)
def create_partner(
    partner_data: BusinessPartnerCreate,
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 생성

    - **partner_code**: 거래처 코드 (필수, 중복 불가)
    - **partner_name**: 거래처명 (필수)
    - **is_supplier**: 공급업체 여부
    - **is_customer**: 고객사 여부
    - 기타 정보는 선택적
    """
    try:
        return service.create_partner(partner_data)
    except AppException as e:
        handle_service_exception(e)


@router.put("/{partner_id}", response_model=BusinessPartnerResponse)
def update_partner(
    partner_id: int,
    partner_data: BusinessPartnerUpdate,
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 수정

    - **partner_id**: 거래처 ID
    - 수정할 필드만 전송 (부분 업데이트 지원)
    """
    try:
        return service.update_partner(partner_id, partner_data)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner(
    partner_id: int,
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 삭제

    - **partner_id**: 거래처 ID
    - 주의: 부품 마스터에서 참조 중인 거래처는 삭제할 수 없습니다
    """
    try:
        service.delete_partner(partner_id)
        return None
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{partner_id}/activate", response_model=BusinessPartnerResponse)
def activate_partner(
    partner_id: int,
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 활성화

    - **partner_id**: 거래처 ID
    """
    try:
        return service.activate(partner_id)
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{partner_id}/deactivate", response_model=BusinessPartnerResponse)
def deactivate_partner(
    partner_id: int,
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 비활성화

    - **partner_id**: 거래처 ID
    """
    try:
        return service.deactivate(partner_id)
    except AppException as e:
        handle_service_exception(e)


@router.get("/export/excel")
def export_partners_excel(
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    is_supplier: Optional[bool] = Query(None, description="공급업체 필터"),
    is_customer: Optional[bool] = Query(None, description="고객사 필터"),
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    order_by: str = Query("created_at", description="정렬 기준"),
    order_desc: bool = Query(True, description="내림차순 정렬 여부"),
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 목록 엑셀 다운로드 (v0.31.0 - 22 컬럼)

    컬럼: 기업코드, 거래처명, 사업자번호, 거래유형, 고객사여부, 공급업체여부,
          국가코드, 국가명, 거래시작년도, 대표자, 주소, 전화, 이메일, 웹사이트,
          담당자명, 담당자직책, 담당자이메일, 담당자휴대폰,
          결제조건, 납품조건, 기본마진율, 비고
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    # 모든 데이터 조회 (전체 필드 포함)
    db = service.db
    from app.models.business_partner import BusinessPartner

    query = db.query(BusinessPartner)
    if keyword:
        query = query.filter(
            (BusinessPartner.partner_code.ilike(f"%{keyword}%")) |
            (BusinessPartner.partner_name.ilike(f"%{keyword}%"))
        )
    if is_supplier is not None:
        query = query.filter(BusinessPartner.is_supplier == is_supplier)
    if is_customer is not None:
        query = query.filter(BusinessPartner.is_customer == is_customer)
    if is_active is not None:
        query = query.filter(BusinessPartner.is_active == is_active)

    # 정렬
    if order_by and hasattr(BusinessPartner, order_by):
        order_column = getattr(BusinessPartner, order_by)
        query = query.order_by(order_column.desc() if order_desc else order_column.asc())

    items = query.limit(10000).all()

    # 워크북 생성
    wb = Workbook()
    ws = wb.active
    ws.title = "거래처목록"

    # 스타일 정의
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 헤더 정의 (v0.31.0 - 22 컬럼)
    headers = [
        "기업코드", "거래처명", "사업자번호", "거래유형", "고객사여부", "공급업체여부",
        "국가코드", "국가명", "거래시작년도", "대표자", "주소",
        "전화", "이메일", "웹사이트",
        "담당자명", "담당자직책", "담당자이메일", "담당자휴대폰",
        "결제조건", "납품조건", "기본마진율", "비고"
    ]

    # 헤더 작성
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # 데이터 작성
    for row_idx, partner in enumerate(items, 2):
        ws.cell(row=row_idx, column=1, value=partner.partner_code or "").border = thin_border
        ws.cell(row=row_idx, column=2, value=partner.partner_name or "").border = thin_border
        ws.cell(row=row_idx, column=3, value=partner.business_number or "").border = thin_border
        ws.cell(row=row_idx, column=4, value=partner.trade_type or "EXPORT").border = thin_border
        ws.cell(row=row_idx, column=5, value="Y" if partner.is_customer else "N").border = thin_border
        ws.cell(row=row_idx, column=6, value="Y" if partner.is_supplier else "N").border = thin_border
        ws.cell(row=row_idx, column=7, value=partner.country_code or "").border = thin_border
        ws.cell(row=row_idx, column=8, value=partner.country_name or "").border = thin_border
        ws.cell(row=row_idx, column=9, value=partner.business_start_year or "").border = thin_border
        ws.cell(row=row_idx, column=10, value=partner.representative or "").border = thin_border
        ws.cell(row=row_idx, column=11, value=partner.address or "").border = thin_border
        ws.cell(row=row_idx, column=12, value=partner.tel or "").border = thin_border
        ws.cell(row=row_idx, column=13, value=partner.email or "").border = thin_border
        ws.cell(row=row_idx, column=14, value=partner.website or "").border = thin_border
        ws.cell(row=row_idx, column=15, value=partner.manager_name or "").border = thin_border
        ws.cell(row=row_idx, column=16, value=partner.manager_position or "").border = thin_border
        ws.cell(row=row_idx, column=17, value=partner.manager_email or "").border = thin_border
        ws.cell(row=row_idx, column=18, value=partner.manager_mobile or "").border = thin_border
        ws.cell(row=row_idx, column=19, value=partner.payment_terms or "").border = thin_border
        ws.cell(row=row_idx, column=20, value=partner.delivery_terms or "").border = thin_border
        margin = float(partner.default_margin_rate) if partner.default_margin_rate is not None else ""
        ws.cell(row=row_idx, column=21, value=margin).border = thin_border
        ws.cell(row=row_idx, column=22, value=partner.remark or "").border = thin_border

    # 열 너비 조정 (22 컬럼)
    column_widths = [10, 25, 15, 12, 12, 14, 10, 15, 12, 15, 40,
                     15, 25, 25, 15, 12, 25, 15, 20, 15, 12, 30]
    for col, width in enumerate(column_widths, 1):
        # A~Z 이후는 AA, AB... 처리
        if col <= 26:
            col_letter = chr(64 + col)
        else:
            col_letter = 'A' + chr(64 + col - 26)
        ws.column_dimensions[col_letter].width = width

    # 파일 저장
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # 파일명 생성 (한글 URL 인코딩)
    filename = f"거래처목록_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )


@router.post("/upload/excel")
def upload_partners_excel(
    file: UploadFile = File(...),
    service: BusinessPartnerService = Depends(get_partner_service)
):
    """
    거래처 엑셀 업로드 (v0.31.0 - 22 컬럼)

    컬럼 순서:
     1. 기업코드 (필수, 중복 시 업데이트)
     2. 거래처명 (신규 등록 시 필수)
     3. 사업자번호
     4. 거래유형 (DOMESTIC/EXPORT, 기본 EXPORT)
     5. 고객사여부 (Y/N)
     6. 공급업체여부 (Y/N)
     7. 국가코드
     8. 국가명
     9. 거래시작년도
    10. 대표자
    11. 주소
    12. 전화
    13. 이메일
    14. 웹사이트
    15. 담당자명
    16. 담당자직책
    17. 담당자이메일
    18. 담당자휴대폰
    19. 결제조건
    20. 납품조건
    21. 기본마진율
    22. 비고

    - 기업코드가 이미 존재하면 해당 거래처 정보 업데이트 (빈 셀은 기존 값 유지)
    - 기업코드가 없으면 새 거래처 생성
    """
    import openpyxl
    from app.models.business_partner import BusinessPartner
    from decimal import Decimal, InvalidOperation

    # 파일 확장자 확인
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다."
        )

    try:
        content = file.file.read()
        wb = openpyxl.load_workbook(BytesIO(content), data_only=True)
        ws = wb.active

        results = []
        success_count = 0
        updated_count = 0
        failed_count = 0

        db = service.db

        header_keywords = ['기업코드', '기업 코드', 'partner_code', 'code', '코드', '기업명']

        def get_cell_value(cell_value):
            """셀 값을 안전하게 추출"""
            if cell_value is None:
                return None
            if hasattr(cell_value, '__class__') and 'Formula' in cell_value.__class__.__name__:
                return None
            return cell_value

        def get_str(row, idx, max_len=None):
            """지정 인덱스의 셀을 문자열로 변환 (없으면 None, max_len 초과 시 자름)"""
            if len(row) <= idx:
                return None
            val = get_cell_value(row[idx])
            if val is None:
                return None
            s = str(val).strip()
            if not s:
                return None
            if max_len and len(s) > max_len:
                s = s[:max_len]
            return s

        def parse_yn(value):
            """Y/N 문자열을 bool로 변환 (None: 미지정)"""
            if value is None:
                return None
            v = str(value).strip().upper()
            if v in ('Y', 'YES', 'TRUE', '1', 'T', 'O'):
                return True
            if v in ('N', 'NO', 'FALSE', '0', 'F', 'X'):
                return False
            return None

        def parse_int(value):
            if value is None:
                return None
            try:
                return int(str(value).replace("년", "").strip())
            except (ValueError, TypeError):
                return None

        def parse_decimal(value):
            if value is None:
                return None
            try:
                s = str(value).replace("%", "").strip()
                return Decimal(s)
            except (ValueError, InvalidOperation, TypeError):
                return None

        for row_idx, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
            # 빈 행 스킵
            if not row or not row[0]:
                continue

            first_cell = get_cell_value(row[0])
            if first_cell is None:
                continue

            first_cell_str = str(first_cell).strip().lower()

            # 헤더 행 스킵
            if any(keyword.lower() in first_cell_str for keyword in header_keywords):
                continue

            try:
                # 22 컬럼 매핑
                # 23컬럼 매핑 (엑스빔테크_Contact_기업리스트 기준)
                # A=기업코드, B=기업명, C=국가, D=사업자번호, E=거래유형,
                # F=고객사여부, G=공급업체여부, H=국가코드, I=국가명,
                # J=거래시작년도, K=대표자, L=배송주소, M=배송담당자전화,
                # N=배송담당이메일, O=웹사이트, P=담당자명, Q=담당자직책,
                # R=담당자이메일, S=담당자휴대폰, T=결제조건, U=납품조건,
                # V=기본마진율, W=비고
                partner_code = get_str(row, 0, max_len=50)
                partner_name = get_str(row, 1, max_len=200)
                country_display = get_str(row, 2, max_len=100)  # C: 국가 (표시용)
                business_number = get_str(row, 3, max_len=20)
                trade_type = get_str(row, 4, max_len=10)
                if trade_type:
                    trade_type = trade_type.upper()
                    if trade_type not in ('DOMESTIC', 'EXPORT'):
                        trade_type = 'EXPORT'
                is_customer = parse_yn(get_str(row, 5))
                is_supplier = parse_yn(get_str(row, 6))
                country_code = get_str(row, 7, max_len=3)
                if country_code:
                    country_code = country_code.upper()
                country_name = get_str(row, 8, max_len=100)
                # C열(국가)이 있고 country_name이 없으면 C열 사용
                if not country_name and country_display:
                    country_name = country_display
                business_start_year = parse_int(get_cell_value(row[9]) if len(row) > 9 else None)
                representative = get_str(row, 10, max_len=100)
                address = get_str(row, 11)
                tel = get_str(row, 12, max_len=50)
                email = get_str(row, 13, max_len=200)
                website = get_str(row, 14)
                manager_name = get_str(row, 15, max_len=100)
                manager_position = get_str(row, 16, max_len=50)
                manager_email = get_str(row, 17, max_len=200)
                manager_mobile = get_str(row, 18, max_len=50)
                payment_terms = get_str(row, 19)
                delivery_terms = get_str(row, 20)
                default_margin_rate = parse_decimal(get_cell_value(row[21]) if len(row) > 21 else None)
                remark = get_str(row, 22)

                if not partner_code:
                    results.append({
                        "row": row_idx,
                        "partner_code": "",
                        "status": "failed",
                        "message": "기업코드가 비어있습니다."
                    })
                    failed_count += 1
                    continue

                # 기존 거래처 조회
                existing = db.query(BusinessPartner).filter(
                    BusinessPartner.partner_code == partner_code
                ).first()

                if existing:
                    # 기존 거래처 업데이트 (빈 셀은 기존 값 유지)
                    if partner_name:
                        existing.partner_name = partner_name
                    if business_number:
                        existing.business_number = business_number
                    if trade_type:
                        existing.trade_type = trade_type
                    if is_customer is not None:
                        existing.is_customer = is_customer
                    if is_supplier is not None:
                        existing.is_supplier = is_supplier
                    if country_code:
                        existing.country_code = country_code
                    if country_name:
                        existing.country_name = country_name
                    if business_start_year:
                        existing.business_start_year = business_start_year
                    if representative:
                        existing.representative = representative
                    if address:
                        existing.address = address
                    if tel:
                        existing.tel = tel
                    if email:
                        existing.email = email
                    if website:
                        existing.website = website
                    if manager_name:
                        existing.manager_name = manager_name
                    if manager_position:
                        existing.manager_position = manager_position
                    if manager_email:
                        existing.manager_email = manager_email
                    if manager_mobile:
                        existing.manager_mobile = manager_mobile
                    if payment_terms:
                        existing.payment_terms = payment_terms
                    if delivery_terms:
                        existing.delivery_terms = delivery_terms
                    if default_margin_rate is not None:
                        existing.default_margin_rate = default_margin_rate
                    if remark:
                        existing.remark = remark

                    db.commit()

                    results.append({
                        "row": row_idx,
                        "partner_code": partner_code,
                        "partner_id": existing.id,
                        "status": "updated",
                        "message": f"거래처 정보 업데이트: {partner_name or existing.partner_name}"
                    })
                    updated_count += 1
                else:
                    # 새 거래처 생성
                    if not partner_name:
                        results.append({
                            "row": row_idx,
                            "partner_code": partner_code,
                            "status": "failed",
                            "message": "신규 거래처는 거래처명이 필수입니다."
                        })
                        failed_count += 1
                        continue

                    # 고객사/공급업체 여부 미지정 시 기본값 (고객사)
                    if is_customer is None and is_supplier is None:
                        is_customer = True
                        is_supplier = False
                    else:
                        is_customer = is_customer if is_customer is not None else False
                        is_supplier = is_supplier if is_supplier is not None else False

                    new_partner = BusinessPartner(
                        partner_code=partner_code,
                        partner_name=partner_name,
                        business_number=business_number,
                        trade_type=trade_type or 'EXPORT',
                        is_customer=is_customer,
                        is_supplier=is_supplier,
                        country_code=country_code,
                        country_name=country_name,
                        business_start_year=business_start_year,
                        representative=representative,
                        address=address,
                        tel=tel,
                        email=email,
                        website=website,
                        manager_name=manager_name,
                        manager_position=manager_position,
                        manager_email=manager_email,
                        manager_mobile=manager_mobile,
                        payment_terms=payment_terms,
                        delivery_terms=delivery_terms,
                        default_margin_rate=default_margin_rate,
                        remark=remark,
                        is_active=True
                    )
                    db.add(new_partner)
                    db.commit()
                    db.refresh(new_partner)

                    results.append({
                        "row": row_idx,
                        "partner_code": partner_code,
                        "partner_id": new_partner.id,
                        "status": "success",
                        "message": f"신규 거래처 등록: {partner_name}"
                    })
                    success_count += 1

            except Exception as e:
                db.rollback()
                results.append({
                    "row": row_idx,
                    "partner_code": str(row[0]) if row[0] else "",
                    "status": "failed",
                    "message": f"처리 중 오류: {str(e)}"
                })
                failed_count += 1

        return {
            "success": True,
            "summary": {
                "total": success_count + updated_count + failed_count,
                "success_count": success_count,
                "updated_count": updated_count,
                "failed_count": failed_count
            },
            "results": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"엑셀 파일 처리 중 오류가 발생했습니다: {str(e)}"
        )


# ==================== 거래처 메모 (v0.32.0) ====================

@router.get("/{partner_id}/notes", response_model=List[PartnerNoteResponse])
def get_partner_notes(
    partner_id: int,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 메모 목록 조회 (고정 메모 우선, 최신순)"""
    db = service.db
    notes = db.query(PartnerNote).filter(
        PartnerNote.partner_id == partner_id
    ).order_by(PartnerNote.is_pinned.desc(), PartnerNote.created_at.desc()).all()
    return notes


@router.post("/{partner_id}/notes", response_model=PartnerNoteResponse, status_code=status.HTTP_201_CREATED)
def create_partner_note(
    partner_id: int,
    data: PartnerNoteCreate,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 메모 추가"""
    db = service.db
    note = PartnerNote(partner_id=partner_id, **data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.put("/{partner_id}/notes/{note_id}", response_model=PartnerNoteResponse)
def update_partner_note(
    partner_id: int,
    note_id: int,
    data: PartnerNoteUpdate,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 메모 수정"""
    db = service.db
    note = db.query(PartnerNote).filter(
        PartnerNote.id == note_id,
        PartnerNote.partner_id == partner_id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(note, key, value)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{partner_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner_note(
    partner_id: int,
    note_id: int,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 메모 삭제"""
    db = service.db
    note = db.query(PartnerNote).filter(
        PartnerNote.id == note_id,
        PartnerNote.partner_id == partner_id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    db.delete(note)
    db.commit()


# ==================== 거래처 통합 타임라인 (v0.32.0) ====================

@router.get("/{partner_id}/timeline")
def get_partner_timeline(
    partner_id: int,
    limit: int = Query(50, le=200),
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """
    거래처 통합 타임라인: 메모 + 영업활동 로그 + 문서 발행 이력을 시간순으로 통합
    """
    from sqlalchemy import union_all, literal, cast, String, Integer
    from app.models.sales_activity import SalesActivity, SalesActivityLog
    from app.models.sales_document import SalesDocument

    db = service.db
    timeline = []

    # 1) 거래처 메모
    notes = db.query(PartnerNote).filter(PartnerNote.partner_id == partner_id).all()
    for n in notes:
        timeline.append({
            "type": "NOTE",
            "note_type": n.note_type,
            "content": n.content,
            "is_pinned": n.is_pinned,
            "created_by": n.created_by,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "ref_id": n.id,
        })

    # 2) 영업활동 로그 (해당 거래처의 모든 활동)
    activity_ids = [a.id for a in db.query(SalesActivity.id).filter(
        SalesActivity.customer_id == partner_id
    ).all()]

    if activity_ids:
        logs = db.query(SalesActivityLog).filter(
            SalesActivityLog.activity_id.in_(activity_ids)
        ).all()

        # 활동 제목 맵
        activities = db.query(SalesActivity.id, SalesActivity.title).filter(
            SalesActivity.id.in_(activity_ids)
        ).all()
        title_map = {a.id: a.title for a in activities}

        for log in logs:
            timeline.append({
                "type": "ACTIVITY_LOG",
                "log_type": log.log_type,
                "content": log.content,
                "created_by": log.logged_by,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "ref_id": log.activity_id,
                "ref_title": title_map.get(log.activity_id, ""),
            })

    # 3) 문서 발행 이력
    docs = db.query(SalesDocument).filter(
        SalesDocument.customer_id == partner_id
    ).all()
    for d in docs:
        timeline.append({
            "type": "DOCUMENT",
            "doc_type": d.document_type,
            "doc_number": d.document_number,
            "doc_status": d.status,
            "content": f"{d.document_type} {d.document_number} 발행",
            "total_amount": float(d.total_amount) if d.total_amount else 0,
            "currency": d.currency or "USD",
            "created_by": None,
            "created_at": (d.document_date or d.created_at).isoformat() if (d.document_date or d.created_at) else None,
            "ref_id": d.id,
        })

    # 시간순 정렬 (최신 먼저), pinned 메모는 최상단
    def sort_key(item):
        pinned = 0 if item.get("is_pinned") else 1
        dt = item.get("created_at") or ""
        return (pinned, dt)

    timeline.sort(key=sort_key, reverse=True)
    # pinned는 항상 위로 (reverse 후 pinned=0이 위)
    timeline.sort(key=lambda x: 0 if x.get("is_pinned") else 1)

    return {"partner_id": partner_id, "items": timeline[:limit]}


# ==================== 선불 잔액 관리 (v0.32.0) ====================

@router.get("/{partner_id}/balance")
def get_partner_balance(
    partner_id: int,
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """거래처 선불 잔액 및 입출금 이력 조회"""
    db = service.db
    from sqlalchemy import desc, func as sa_func
    from decimal import Decimal

    transactions = db.query(PartnerBalanceTransaction).filter(
        PartnerBalanceTransaction.partner_id == partner_id
    ).order_by(desc(PartnerBalanceTransaction.created_at)).all()

    # 현재 잔액 = 마지막 거래의 balance_after (없으면 0)
    current_balance = float(transactions[0].balance_after) if transactions else 0
    currency = transactions[0].currency if transactions else "USD"

    return {
        "partner_id": partner_id,
        "current_balance": current_balance,
        "currency": currency,
        "transactions": [
            {
                "id": t.id,
                "type": t.transaction_type,
                "amount": float(t.amount),
                "currency": t.currency,
                "balance_after": float(t.balance_after),
                "reference_doc_number": t.reference_doc_number,
                "reference_doc_id": t.reference_doc_id,
                "memo": t.memo,
                "created_by": t.created_by,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ],
    }


@router.post("/{partner_id}/balance/deposit")
def deposit_balance(
    partner_id: int,
    amount: float = Query(..., gt=0, description="입금 금액"),
    currency: str = Query("USD", description="통화"),
    memo: str = Query("", description="메모"),
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """선불 잔액 충전 (입금)"""
    db = service.db
    from sqlalchemy import desc
    from decimal import Decimal

    # 현재 잔액 조회
    last = db.query(PartnerBalanceTransaction).filter(
        PartnerBalanceTransaction.partner_id == partner_id
    ).order_by(desc(PartnerBalanceTransaction.created_at)).first()

    current = Decimal(str(last.balance_after)) if last else Decimal("0")
    new_balance = current + Decimal(str(amount))

    # X-User-Name 헤더에서 처리자
    from fastapi import Request
    import inspect
    frame = inspect.currentframe()
    created_by = None

    txn = PartnerBalanceTransaction(
        partner_id=partner_id,
        transaction_type="DEPOSIT",
        amount=Decimal(str(amount)),
        currency=currency,
        balance_after=new_balance,
        memo=memo or "선불 입금",
        created_by=created_by,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return {
        "message": f"${amount:,.2f} 입금 완료. 잔액: ${float(new_balance):,.2f}",
        "balance": float(new_balance),
        "transaction_id": txn.id,
    }


@router.post("/{partner_id}/balance/deduct")
def deduct_balance(
    partner_id: int,
    amount: float = Query(..., gt=0, description="차감 금액"),
    currency: str = Query("USD", description="통화"),
    reference_doc_number: str = Query("", description="참조 문서번호"),
    reference_doc_id: int = Query(None, description="참조 문서 ID"),
    memo: str = Query("", description="메모"),
    service: BusinessPartnerService = Depends(get_partner_service),
):
    """선불 잔액 차감 (PI 입금 처리 시)"""
    db = service.db
    from sqlalchemy import desc
    from decimal import Decimal

    last = db.query(PartnerBalanceTransaction).filter(
        PartnerBalanceTransaction.partner_id == partner_id
    ).order_by(desc(PartnerBalanceTransaction.created_at)).first()

    current = Decimal(str(last.balance_after)) if last else Decimal("0")
    deduct_amount = Decimal(str(amount))

    if deduct_amount > current:
        raise HTTPException(status_code=400, detail=f"잔액 부족: 현재 ${float(current):,.2f}, 차감 요청 ${amount:,.2f}")

    new_balance = current - deduct_amount

    txn = PartnerBalanceTransaction(
        partner_id=partner_id,
        transaction_type="DEDUCT",
        amount=deduct_amount,
        currency=currency,
        balance_after=new_balance,
        reference_doc_number=reference_doc_number,
        reference_doc_id=reference_doc_id,
        memo=memo or f"{reference_doc_number} 입금 처리",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return {
        "message": f"${amount:,.2f} 차감 완료. 잔액: ${float(new_balance):,.2f}",
        "balance": float(new_balance),
        "transaction_id": txn.id,
    }
