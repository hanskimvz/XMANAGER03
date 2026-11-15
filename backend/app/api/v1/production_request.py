"""
생산 요청서 API
생산 요청서 관리 CRUD API를 제공합니다.

v0.20.0: 생산 요청서 기능 추가
v0.22.0: 다중 제품 지원
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Header
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import date
from urllib.parse import unquote
import os
import uuid
from pathlib import Path

from app.api.v1.deps import get_db, handle_service_exception
from app.services.production_request_service import ProductionRequestService
from app.schemas.production_request import (
    ProductionRequestCreate,
    ProductionRequestUpdate,
    ProductionRequestResponse,
    ProductionRequestPaginatedResponse,
    ProductionRequestStatus,
    ProductionRequestApprove,
    ProductionRequestReject,
    ProductionRequestHold,
    ProductionRequestFlagsUpdate,
    ProductionNotesUpdate,
    BoxPlanUpdate,
    ProductionRequestShip,
)
from app.core.exceptions import AppException
from app.core.auth import require_auth, require_admin
from app.models.user import User
from app.services import production_notify
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal

router = APIRouter(prefix="/production-requests", tags=["생산 요청서 관리"])


def get_production_request_service(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
) -> ProductionRequestService:
    """ProductionRequestService 의존성 — 로그인 필수(①-4) + 행위자 기록(⑧)"""
    return ProductionRequestService(db, actor_id=user.id)


# ==================== 조회 ====================

@router.get("/pending/count")
def get_pending_count(
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """대기 중인 생산 요청서 개수 조회"""
    return {"count": service.get_pending_requests_count()}


@router.get("/pending", response_model=List[ProductionRequestResponse])
def get_pending_requests(
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(50, ge=1, le=100, description="조회 개수"),
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """대기 중인 생산 요청서 목록 조회 (REQUESTED 상태)"""
    return service.get_pending_requests(skip, limit)


@router.get("", response_model=ProductionRequestPaginatedResponse)
def get_production_request_list(
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    pr_status: Optional[str] = Query(None, alias="status", description="상태 필터(콤마 구분 다중 허용: 'REQUESTED,APPROVED')"),
    customer_id: Optional[int] = Query(None, description="고객사 ID"),
    priority: Optional[int] = Query(None, ge=0, le=2, description="우선순위"),
    from_date: Optional[date] = Query(None, description="요청일 시작"),
    to_date: Optional[date] = Query(None, description="요청일 종료"),
    is_draft: Optional[bool] = Query(None, description="초안 필터: false=초안제외(생산), true=초안만(영업), 미지정=전체"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(50, ge=1, le=1000, description="조회 개수"),
    order_by: str = Query("created_at", description="정렬 기준"),
    order_desc: bool = Query(True, description="내림차순 정렬 여부"),
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 목록 조회 (검색 및 필터링)"""
    items, total = service.search_production_requests_with_count(
        keyword=keyword,
        status=pr_status,
        customer_id=customer_id,
        priority=priority,
        from_date=from_date,
        to_date=to_date,
        is_draft=is_draft,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_desc=order_desc
    )

    # 항목 변환 (v0.22.0 다중 제품 지원)
    list_items = []
    for pr in items:
        # items 변환
        items_list = []
        if pr.items:
            for item in sorted(pr.items, key=lambda x: x.sort_order):
                items_list.append({
                    "id": item.id,
                    "production_request_id": item.production_request_id,
                    "product_part_id": item.product_part_id,
                    "custom_product_code": item.custom_product_code,
                    "custom_product_name": item.custom_product_name,
                    "requested_quantity": item.requested_quantity,
                    "ci_quantity": item.ci_quantity,
                    "uom": item.uom,
                    "line_remarks": item.line_remarks,
                    "customer_requirements": item.customer_requirements,
                    "attachment_files": item.attachment_files,
                    "work_order_id": item.work_order_id,
                    "sort_order": item.sort_order,
                    "product_part": {
                        "id": item.product_part.id,
                        "part_number": item.product_part.part_number,
                        "part_number_display": item.product_part.part_number_display,
                        "part_name": item.product_part.part_name,
                        "part_name_en": item.product_part.part_name_en,
                    } if item.product_part else None,
                })

        # 첫번째 항목으로 deprecated 필드 설정 (호환성)
        first_item = items_list[0] if items_list else None

        pr_dict = {
            "id": pr.id,
            "request_number": pr.request_number,
            "customer_id": pr.customer_id,
            # deprecated 필드 (호환성용 - 첫번째 제품)
            "product_part_id": first_item["product_part_id"] if first_item else pr.product_part_id,
            "requested_quantity": first_item["requested_quantity"] if first_item else pr.requested_quantity,
            "due_date": pr.due_date,
            "status": pr.status,
            "is_draft": pr.is_draft,
            "priority": pr.priority,
            "pi_number": pr.pi_number,
            "payment_status": pr.payment_status,
            "prepared_by_name": pr.prepared_by_name,
            "requested_at": pr.requested_at,
            "created_at": pr.created_at,
            # 진행 플래그/시각 — 목록에서 유지되도록 반드시 포함(누락 시 항상 False로 표기됨)
            "insert_shipped": pr.insert_shipped,
            "insert_not_applicable": pr.insert_not_applicable,
            "production_shipped": pr.production_shipped,
            "needs_review": pr.needs_review,
            "insert_shipped_at": pr.insert_shipped_at,
            "production_shipped_at": pr.production_shipped_at,
            "review_note": pr.review_note,
            "shipped_at": pr.shipped_at,
            "delivered_at": pr.delivered_at,
            "packing_list": pr.packing_list,
            "has_box_plan": bool(pr.box_plan),
            "customer": pr.customer,
            "product_part": first_item["product_part"] if first_item else pr.product_part,
            "work_order_count": len(pr.work_orders) if pr.work_orders else 0,
            # 요청 단위 첨부(도면/사진) — 영업 현황 배지용
            "attachment_files": pr.attachment_files,
            # v0.22.0: 다중 제품
            "item_count": len(items_list),
            "items": items_list,
        }
        list_items.append(pr_dict)

    return {
        "items": list_items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }


@router.get("/notify-recipients")
def get_notify_recipients(db: Session = Depends(get_db), user: User = Depends(require_auth)):
    """생산 단계별 알림 수신자(지정 인원) + 선택 후보 사용자 목록.

    recipients = {requested, in_progress, shipped}. (하위호환용 user_ids = requested)
    """
    recipients = production_notify.get_all_notify_recipients(db)
    users = db.query(User).filter(User.is_active == True).order_by(User.department, User.name).all()  # noqa: E712
    return {
        "recipients": recipients,
        "user_ids": recipients.get("requested", []),  # 하위호환
        "users": [
            {"id": u.id, "name": u.name, "department": u.department, "position": u.position}
            for u in users
        ],
    }


@router.put("/notify-recipients")
def set_notify_recipients(payload: dict, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """생산 단계별 알림 수신자 지정(관리자).

    payload: {recipients: {requested:[int], in_progress:[int], shipped:[int]}}
    (하위호환: {user_ids:[int]} 를 주면 requested 로 저장)
    """
    mapping = payload.get("recipients")
    if not isinstance(mapping, dict):
        mapping = {"requested": payload.get("user_ids") or [], "in_progress": [], "shipped": []}
    saved = production_notify.set_all_notify_recipients(db, mapping)
    return {"recipients": saved}


@router.get("/calendar")
def production_request_calendar(
    from_date: date = Query(..., alias="from", description="조회 시작일(YYYY-MM-DD)"),
    to_date: date = Query(..., alias="to", description="조회 종료일(YYYY-MM-DD)"),
    customer_id: Optional[int] = Query(None, description="고객사 필터"),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """생산요청 캘린더용 경량 데이터 — 기간에 걸치는 납기일/요청일 마커.
    초안(is_draft)은 제외. 상태 필터/요청·납기 토글은 프런트에서 처리."""
    from sqlalchemy import or_, and_, func, cast, Date as SqlDate
    from sqlalchemy.orm import joinedload as _joinedload
    from app.models.production_request import ProductionRequest as PR
    ref_dt = func.coalesce(PR.requested_at, PR.created_at)
    q = (
        db.query(PR)
        .options(_joinedload(PR.customer))
        .filter(PR.is_draft.isnot(True))
        .filter(or_(
            PR.due_date.between(from_date, to_date),
            cast(ref_dt, SqlDate).between(from_date, to_date),
            # 납기 미정(활성) 건은 월 무관 항상 포함 → 상단 칩 노출용
            and_(PR.due_date.is_(None), PR.status.notin_(["DELIVERED", "CANCELLED", "REJECTED"])),
        ))
    )
    if customer_id:
        q = q.filter(PR.customer_id == customer_id)
    out = []
    for pr in q.all():
        out.append({
            "id": pr.id,
            "request_number": pr.request_number,
            "customer_name": pr.customer.partner_name if pr.customer else None,
            "due_date": pr.due_date.isoformat() if pr.due_date else None,
            "requested_at": (pr.requested_at or pr.created_at).isoformat() if (pr.requested_at or pr.created_at) else None,
            "status": pr.status,
            "priority": pr.priority,
        })
    return out


@router.get("/{pr_id}", response_model=ProductionRequestResponse)
def get_production_request(
    pr_id: int,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 상세 조회"""
    try:
        return service.get_or_raise(pr_id)
    except AppException as e:
        handle_service_exception(e)


# ==================== 생성/수정/삭제 ====================

@router.post("", response_model=ProductionRequestResponse, status_code=status.HTTP_201_CREATED)
def create_production_request(
    pr_in: ProductionRequestCreate,
    override_protection: bool = Query(False, description="전속(독점) 계약 위반 강제 진행 — 관리자만 유효"),
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    user: User = Depends(require_auth),
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 생성. 작성자(영업담당자)는 로그인 사용자명으로 자동 기록."""
    try:
        created_by_name = unquote(x_user_name) if x_user_name else None
        allow = bool(override_protection and getattr(user, "role", None) == "ADMIN")
        return service.create_production_request(pr_in, created_by_name=created_by_name, allow_protected_override=allow)
    except AppException as e:
        handle_service_exception(e)


@router.put("/{pr_id}", response_model=ProductionRequestResponse)
def update_production_request(
    pr_id: int,
    pr_in: ProductionRequestUpdate,
    override_protection: bool = Query(False, description="전속(독점) 계약 위반 강제 진행 — 관리자만 유효"),
    user: User = Depends(require_auth),
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 수정 (출고 완료 이전 상태에서 영업 수정 가능)"""
    try:
        allow = bool(override_protection and getattr(user, "role", None) == "ADMIN")
        return service.update_production_request(pr_id, pr_in, allow_protected_override=allow)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{pr_id}/submit", response_model=ProductionRequestResponse)
def submit_production_request_draft(
    pr_id: int,
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """초안(is_draft) 생산요청을 정식 전송 — 생산팀 노출 + 알림 발송(영업 '생산팀에 요청')."""
    try:
        return service.submit_draft(pr_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{pr_id}/withdraw-draft", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_draft_production_request(
    pr_id: int,
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """초안(임시) 생산요청 회수(삭제) — 영업이 아직 전송 안 한 임시 건만 가능.
    삭제(DELETE)와 달리 POST라 영업팀 권한(생산 create)으로 회수 가능. 정식 전송 건은 거부."""
    try:
        service.withdraw_draft(pr_id)
        return None
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{pr_id}/flags", response_model=ProductionRequestResponse)
def update_production_request_flags(
    pr_id: int,
    flags: ProductionRequestFlagsUpdate,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """진행 체크박스 토글 (인서트출고 / 생산출고 / 검토필요) — 모든 상태에서 가능"""
    try:
        return service.update_flags(
            pr_id,
            insert_shipped=flags.insert_shipped,
            production_shipped=flags.production_shipped,
            needs_review=flags.needs_review,
            review_note=flags.review_note,
            insert_shipped_at=flags.insert_shipped_at,
            production_shipped_at=flags.production_shipped_at,
            insert_not_applicable=flags.insert_not_applicable,
        )
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{pr_id}/production-notes", response_model=ProductionRequestResponse)
def update_production_notes(
    pr_id: int,
    notes: ProductionNotesUpdate,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 시작 단계 자료 저장 — 총괄자 메모 / 공정 확인표. 모든 상태에서 가능(update 가드 우회)."""
    try:
        return service.update_production_notes(
            pr_id,
            manager_memo=notes.manager_memo,
            process_checks=notes.process_checks,
        )
    except AppException as e:
        handle_service_exception(e)


class UpdateDueDateRequest(BaseModel):
    due_date: Optional[date] = None


@router.put("/{pr_id}/due-date", response_model=ProductionRequestResponse)
def update_due_date(
    pr_id: int,
    payload: UpdateDueDateRequest,
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """납기일 변경(영업 캘린더/현황에서 조정). 변경 시 생산팀에 알림 발송."""
    try:
        return service.update_due_date(pr_id, payload.due_date)
    except AppException as e:
        handle_service_exception(e)


@router.put("/{pr_id}/box-plan", response_model=ProductionRequestResponse)
def update_box_plan(
    pr_id: int,
    payload: BoxPlanUpdate,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """분할선적 박스 분할계획 저장 — 영업이 작성(자동생성 후 수기조정). 생산팀은 이를 보고 포장."""
    try:
        box_plan = None
        if payload.box_plan:
            box_plan = [
                {
                    "box_no": b.box_no,
                    "items": [
                        {
                            "pr_item_id": ln.pr_item_id,
                            "product_code": ln.product_code,
                            "quantity": float(ln.quantity),
                        }
                        for ln in b.items
                    ],
                    "remarks": b.remarks,
                    # 발행 추적 보존(이미 CI 발행된 박스)
                    "ci_document_id": b.ci_document_id,
                    "ci_number": b.ci_number,
                }
                for b in payload.box_plan
            ]
        return service.update_box_plan(pr_id, box_plan)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{pr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_request(
    pr_id: int,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 삭제 (REQUESTED 상태에서만)"""
    try:
        service.delete_production_request(pr_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 상태 전이 ====================

@router.post("/{pr_id}/approve", response_model=ProductionRequestResponse)
def approve_production_request(
    pr_id: int,
    request: ProductionRequestApprove,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 승인 (REQUESTED → APPROVED)"""
    try:
        return service.approve(pr_id, request)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{pr_id}/items/{item_id}/create-work-order")
def create_work_order_for_item(
    pr_id: int,
    item_id: int,
    service: ProductionRequestService = Depends(get_production_request_service),
    db=Depends(get_db),
):
    """생산요청 품목별 작업지시서 개별 생성 (v0.29.0)"""
    try:
        result = service.create_work_order_for_item(pr_id, item_id)
        return result
    except AppException as e:
        handle_service_exception(e)


@router.post("/{pr_id}/reject", response_model=ProductionRequestResponse)
def reject_production_request(
    pr_id: int,
    request: ProductionRequestReject,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 반려 (REQUESTED/HOLD → REJECTED)"""
    try:
        return service.reject(pr_id, request)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{pr_id}/hold", response_model=ProductionRequestResponse)
def hold_production_request(
    pr_id: int,
    request: ProductionRequestHold,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 보류 (REQUESTED → HOLD)"""
    try:
        return service.hold(pr_id, request)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{pr_id}/release-hold", response_model=ProductionRequestResponse)
def release_hold_production_request(
    pr_id: int,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 보류 해제 (HOLD → REQUESTED)"""
    try:
        return service.release_hold(pr_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{pr_id}/cancel", response_model=ProductionRequestResponse)
def cancel_production_request(
    pr_id: int,
    reason: Optional[str] = Query(None, description="취소 사유"),
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 취소"""
    try:
        return service.cancel(pr_id, reason)
    except AppException as e:
        handle_service_exception(e)


# ==================== 간편 상태 변경 (v0.32.0) ====================

@router.post("/{pr_id}/change-status", response_model=ProductionRequestResponse)
def change_production_request_status(
    pr_id: int,
    new_status: str = Query(..., description="변경할 상태"),
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """
    간편 생산 처리용 상태 변경 API
    상태 전이 규칙에 따라 유효한 전환만 허용
    """
    try:
        pr = service.get_or_raise(pr_id)
        target = ProductionRequestStatus(new_status)
        service._validate_transition(pr.status, target)
        prev_status = pr.status
        pr.status = target.value
        from datetime import datetime
        now = datetime.now()
        pr.updated_at = now
        pr.updated_by = service.actor_id
        # 반려 → 재요청(REQUESTED) 시 반려 사유 정리(재상신이므로)
        if target == ProductionRequestStatus.REQUESTED and prev_status == ProductionRequestStatus.REJECTED.value:
            pr.rejection_reason = None
        # 확인 취소(APPROVED → REQUESTED) 시 승인 정보 정리 → 다시 미확인 상태로
        if target == ProductionRequestStatus.REQUESTED and prev_status == ProductionRequestStatus.APPROVED.value:
            pr.approved_by = None
            pr.approved_at = None
        # 생산 시작(IN_PROGRESS) 진입 시 공정 확인표 표준 항목 시딩
        if target == ProductionRequestStatus.IN_PROGRESS:
            service.seed_process_checks_if_empty(pr)
        # 생산 출고(SHIPPED): 출고시각 기록 + 생산출고 플래그/시각 자동 세팅(수동 체크박스 대체)
        if target == ProductionRequestStatus.SHIPPED:
            pr.shipped_at = pr.shipped_at or now
            pr.production_shipped = True
            pr.production_shipped_at = pr.production_shipped_at or now
            if not pr.due_date:  # 출고 시 납기일 자동 입력(비어있을 때 = 출고일)
                pr.due_date = pr.shipped_at.date()
        # 발송 완료(DELIVERED): 발송시각 기록 — 영업팀이 처리
        if target == ProductionRequestStatus.DELIVERED:
            pr.delivered_at = pr.delivered_at or now
        service.db.commit()
        pr_full = service.repository.get_by_id_with_relations(pr_id)
        # 생산 시작(진행중 진입) → '진행' 단계 지정 인원에게 알림
        if target == ProductionRequestStatus.IN_PROGRESS and prev_status != ProductionRequestStatus.IN_PROGRESS.value:
            service._notify_stage_group(pr_full, "in_progress")
        # #3 출고 완료(change-status 경로) → 영업 담당자 + '출고' 단계 지정 인원(그룹)에게 알림
        if target == ProductionRequestStatus.SHIPPED:
            service._notify(lambda ns: ns.notify_production_shipped(pr_full, service.actor_id))
            service._notify_stage_group(pr_full, "shipped")
        return pr_full
    except (ValueError, KeyError):
        raise HTTPException(status_code=400, detail=f"유효하지 않은 상태: {new_status}")
    except AppException as e:
        handle_service_exception(e)


# ==================== 출고 처리 (packing list) (v0.77.0) ====================

def _packing_to_dicts(packing_list) -> Optional[list]:
    """PackingBox 리스트 → JSON 저장용 dict 리스트 (Decimal→float)."""
    if packing_list is None:
        return None
    out = []
    for b in packing_list:
        d = b.model_dump()
        for k in ("gross_weight", "net_weight", "length", "width", "height"):
            if d.get(k) is not None:
                d[k] = float(d[k])
        out.append(d)
    return out


@router.post("/{pr_id}/ship", response_model=ProductionRequestResponse)
def ship_production_request(
    pr_id: int,
    ship: ProductionRequestShip,
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """생산 출고 처리 — packing list와 함께 SHIPPED로 전환 (IN_PROGRESS/COMPLETED → SHIPPED)."""
    try:
        return service.ship_with_packing(pr_id, _packing_to_dicts(ship.packing_list))
    except AppException as e:
        handle_service_exception(e)


@router.put("/{pr_id}/packing-list", response_model=ProductionRequestResponse)
def update_packing_list(
    pr_id: int,
    ship: ProductionRequestShip,
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """출고 후 패킹 정보 수정 — 상태 전이 없이 packing list 만 갱신.

    실제 포장이 출고 이후 바뀐 경우(박스 재구성·중량 정정 등)를 반영한다.
    출고 상태/출고시각은 그대로 보존된다.
    """
    try:
        return service.update_packing_list(pr_id, _packing_to_dicts(ship.packing_list))
    except AppException as e:
        handle_service_exception(e)


# ==================== 출고 → CI 생성 연결 (v0.76.0) ====================

@router.post("/{pr_id}/create-ci")
def create_ci_from_production_request(
    pr_id: int,
    service: ProductionRequestService = Depends(get_production_request_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """생산 출고건에서 CI(Commercial Invoice) 생성 — 연결된 PI를 CI로 전환.

    출고(SHIPPED) 이후 영업팀이 발송 문서를 만드는 프로세스 연결점.
    - 연결된 PI를 품목의 pi_document_id(우선) 또는 pr.pi_number로 해결
    - 이미 생성된 CI가 있으면 새로 만들지 않고 기존 CI를 반환(중복 방지)
    - PI→CI 전환은 기존 sales 전환 엔진을 재사용(고객/품목/조건/수하인 승계)
    """
    from app.models.sales_document import SalesDocument, SalesDocumentLink
    from app.schemas.sales_document import ConvertToNextRequest
    from app.services.sales_document_service import SalesDocumentService

    pr = service.get_or_raise(pr_id)
    if pr.status not in ("SHIPPED", "DELIVERED"):
        raise HTTPException(status_code=400, detail="출고(생산 출고) 이후에만 CI를 생성할 수 있습니다.")

    # 1) 연결된 PI 문서 id 해결: 품목 pi_document_id 우선, 없으면 pi_number로 조회
    pi_ids: list = []
    for it in (pr.items or []):
        pid = getattr(it, "pi_document_id", None)
        if pid and pid not in pi_ids:
            pi_ids.append(pid)
    if not pi_ids and pr.pi_number:
        pi = db.query(SalesDocument).filter(
            SalesDocument.document_number == pr.pi_number,
            SalesDocument.document_type == "PI",
        ).order_by(SalesDocument.id.desc()).first()
        if pi:
            pi_ids = [pi.id]
    if not pi_ids:
        raise HTTPException(
            status_code=400,
            detail="연결된 PI가 없어 CI를 자동 생성할 수 없습니다. 영업관리에서 직접 생성하세요.",
        )

    # 2) 이미 생성된 CI가 있으면 반환(중복 방지)
    existing = (
        db.query(SalesDocument)
        .join(SalesDocumentLink, SalesDocumentLink.target_id == SalesDocument.id)
        .filter(SalesDocumentLink.source_id.in_(pi_ids), SalesDocument.document_type == "CI")
        .order_by(SalesDocument.id.desc())
        .first()
    )
    if existing:
        return {"ci_id": existing.id, "ci_number": existing.document_number, "already_exists": True}

    # 3) PI → CI 전환(고객/품목/조건/수하인 승계) — 기존 전환 엔진 재사용
    sales_service = SalesDocumentService(db)
    ci = sales_service.convert_multiple_to_next(pi_ids, ConvertToNextRequest(target_type="CI"))
    if not ci:
        raise HTTPException(status_code=400, detail="CI 전환에 실패했습니다. PI 상태를 확인하세요.")

    # CI 담당자 = 전환을 실행한 현재 사용자(해외 문서 → 영문명 우선). PI 승계값 대신 실제 발행자로 기록.
    # 이메일은 발행자 값으로 '항상' 덮어씀 — 없으면 공란(엉뚱한 승계 이메일 방지).
    prepared = (getattr(user, "name_en", None) or "").strip() or (getattr(user, "name", None) or "").strip()
    if prepared:
        ci.prepared_by = prepared
    ci.prepared_email = (getattr(user, "email", None) or "").strip() or None
    db.commit()

    # 4) 생산 packing list & 선적 정보를 CI에 승계
    _apply_packing_to_ci(db, pr, ci)
    # 전량 발행 → ci_quantity를 요청수량으로(분할선적 잔여 정합성)
    for it in (pr.items or []):
        it.ci_quantity = it.requested_quantity or 0
    db.commit()
    return {"ci_id": ci.id, "ci_number": ci.document_number, "already_exists": False}


def _collect_pi_ids_for_pr(db, pr) -> list:
    """생산요청에 연결된 PI 문서 id 목록(품목 pi_document_id 우선, 없으면 pi_number 조회)."""
    from app.models.sales_document import SalesDocument
    ids: list = []
    for it in (pr.items or []):
        pid = getattr(it, "pi_document_id", None)
        if pid and pid not in ids:
            ids.append(pid)
    if not ids and pr.pi_number:
        pi = db.query(SalesDocument).filter(
            SalesDocument.document_number == pr.pi_number,
            SalesDocument.document_type == "PI",
        ).order_by(SalesDocument.id.desc()).first()
        if pi:
            ids = [pi.id]
    return ids


class CreateCiMergedRequest(BaseModel):
    pr_ids: List[int]


@router.post("/create-ci-merged")
def create_ci_merged_from_production_requests(
    req: CreateCiMergedRequest,
    service: ProductionRequestService = Depends(get_production_request_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """여러 출고건(생산요청)을 하나의 CI로 합배송 발행 — 같은 고객만 허용."""
    from app.models.sales_document import SalesDocument
    from app.schemas.sales_document import ConvertToNextRequest
    from app.services.sales_document_service import SalesDocumentService

    pr_ids = list(dict.fromkeys(req.pr_ids or []))
    if len(pr_ids) < 2:
        raise HTTPException(status_code=400, detail="합배송은 2건 이상의 출고건을 선택해야 합니다.")

    prs = [service.get_or_raise(i) for i in pr_ids]

    # 검증: 모두 출고(SHIPPED/DELIVERED) + 같은 고객
    for pr in prs:
        if pr.status not in ("SHIPPED", "DELIVERED"):
            raise HTTPException(status_code=400, detail=f"{pr.request_number}: 출고 이후 건만 합배송할 수 있습니다.")
    cust_ids = {pr.customer_id for pr in prs}
    if len(cust_ids) > 1:
        raise HTTPException(status_code=400, detail="같은 고객의 출고건만 합배송할 수 있습니다.")

    # 연결 PI 수집(전체 합침)
    pi_ids: list = []
    for pr in prs:
        for pid in _collect_pi_ids_for_pr(db, pr):
            if pid not in pi_ids:
                pi_ids.append(pid)
    if not pi_ids:
        raise HTTPException(status_code=400, detail="연결된 PI가 없어 CI를 생성할 수 없습니다.")

    # 합배송 CI 발행(여러 PI → 1 CI). 합배송은 새 CI를 만든다(단일 중복방지 로직 미적용).
    sales_service = SalesDocumentService(db)
    ci = sales_service.convert_multiple_to_next(pi_ids, ConvertToNextRequest(target_type="CI"))
    if not ci:
        raise HTTPException(status_code=400, detail="CI 전환에 실패했습니다. PI 상태를 확인하세요.")

    # CI 담당자 = 전환 실행자(영문명 우선), 이메일 항상 발행자 값(없으면 공란)
    prepared = (getattr(user, "name_en", None) or "").strip() or (getattr(user, "name", None) or "").strip()
    if prepared:
        ci.prepared_by = prepared
    ci.prepared_email = (getattr(user, "email", None) or "").strip() or None
    db.commit()

    # packing list 합산(모든 출고건) + 선적정보(첫 건 기준)
    combined_boxes: list = []
    for pr in prs:
        combined_boxes.extend(pr.packing_list or [])
    _apply_packing_boxes_to_ci(db, ci, combined_boxes, prs[0])

    # 전량 발행 → 각 품목 ci_quantity를 요청수량으로(분할선적 잔여 정합성)
    for pr in prs:
        for it in (pr.items or []):
            it.ci_quantity = it.requested_quantity or 0
    db.commit()

    return {"ci_id": ci.id, "ci_number": ci.document_number, "merged_count": len(prs)}


def _line_product_info(db, it):
    """생산요청 품목 → (product_code, description, uom, unit_price, currency). PI 품목 우선, 없으면 커스텀/부품."""
    from app.models.sales_document import SalesDocumentItem
    product_code = None
    description = None
    uom = getattr(it, "uom", None)
    unit_price = None
    currency = None
    pi_item_id = getattr(it, "pi_item_id", None)
    if pi_item_id:
        pi_item = db.query(SalesDocumentItem).filter(SalesDocumentItem.id == pi_item_id).first()
        if pi_item:
            product_code = pi_item.product_code
            description = pi_item.description
            unit_price = float(pi_item.unit_price) if pi_item.unit_price is not None else None
            currency = pi_item.currency
            uom = uom or pi_item.uom
    if not product_code:
        p = getattr(it, "product_part", None)
        product_code = (p.part_number_display or p.part_number) if p else (getattr(it, "custom_product_code", None) or "-")
        description = (p.part_name if p else getattr(it, "custom_product_name", None))
    return product_code, description, uom, unit_price, currency


class CiSplitPreviewRequest(BaseModel):
    pr_ids: List[int]


@router.post("/ci-split-preview")
def ci_split_preview(
    req: CiSplitPreviewRequest,
    service: ProductionRequestService = Depends(get_production_request_service),
    db: Session = Depends(get_db),
):
    """분할선적 미리보기 — 선택 출고건들의 품목별 전량/기발행/잔여/단가."""
    prs = [service.get_or_raise(i) for i in dict.fromkeys(req.pr_ids or [])]
    if not prs:
        raise HTTPException(status_code=400, detail="출고건을 선택하세요.")
    lines = []
    doc_currency = None
    for pr in prs:
        for it in sorted(pr.items or [], key=lambda x: x.sort_order):
            ordered = float(it.requested_quantity or 0)
            issued = float(getattr(it, "ci_quantity", 0) or 0)
            code, desc, uom, price, cur = _line_product_info(db, it)
            if cur and not doc_currency:
                doc_currency = cur
            lines.append({
                "pr_id": pr.id, "pr_item_id": it.id,
                "product_code": code, "product_name": desc, "uom": uom,
                "ordered": ordered, "issued": issued, "remaining": round(ordered - issued, 3),
                "unit_price": price, "currency": cur,
                "is_custom": not it.product_part_id,
            })
    return {
        "customer": (prs[0].customer.partner_name if prs[0].customer else None),
        "currency": doc_currency or "USD",
        "lines": lines,
    }


class CiSplitLine(BaseModel):
    pr_item_id: int
    quantity: float
    unit_price: Optional[float] = None


class CreateCiSplitRequest(BaseModel):
    pr_ids: List[int]
    lines: List[CiSplitLine]
    document_date: Optional[date] = None


@router.post("/create-ci-split")
def create_ci_split(
    req: CreateCiSplitRequest,
    service: ProductionRequestService = Depends(get_production_request_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """분할선적 — 지정 품목·수량만으로 CI 발행. 잔여 검증 후 ci_quantity 누적."""
    from app.schemas.sales_document import ConvertToNextRequest
    from app.services.sales_document_service import SalesDocumentService

    prs = [service.get_or_raise(i) for i in dict.fromkeys(req.pr_ids or [])]
    if not prs:
        raise HTTPException(status_code=400, detail="출고건을 선택하세요.")
    if len({pr.customer_id for pr in prs}) > 1:
        raise HTTPException(status_code=400, detail="같은 고객의 출고건만 함께 발행할 수 있습니다.")

    item_map = {}
    for pr in prs:
        for it in (pr.items or []):
            item_map[it.id] = it

    ci_lines = []
    source_pi_ids = []
    for ln in req.lines:
        it = item_map.get(ln.pr_item_id)
        if not it:
            raise HTTPException(status_code=400, detail=f"품목(id={ln.pr_item_id})을 찾을 수 없습니다.")
        qty = float(ln.quantity or 0)
        if qty <= 0:
            continue
        remaining = float(it.requested_quantity or 0) - float(getattr(it, "ci_quantity", 0) or 0)
        if qty > remaining + 1e-6:
            raise HTTPException(status_code=400, detail=f"잔여({remaining:g})를 초과했습니다.")
        code, desc, uom, price, cur = _line_product_info(db, it)
        if ln.unit_price is not None:
            price = ln.unit_price
        if price is None:
            raise HTTPException(status_code=400, detail=f"'{code}' 단가가 없습니다. 단가를 입력하세요.")
        ci_lines.append({
            "product_code": code, "description": desc, "quantity": qty, "uom": uom,
            "unit_price": price, "currency": cur, "line_remarks": getattr(it, "line_remarks", None),
        })
        pid = getattr(it, "pi_document_id", None)
        if pid and pid not in source_pi_ids:
            source_pi_ids.append(pid)

    if not ci_lines:
        raise HTTPException(status_code=400, detail="발행할 수량을 입력하세요.")
    if not source_pi_ids:
        for pr in prs:
            for pid in _collect_pi_ids_for_pr(db, pr):
                if pid not in source_pi_ids:
                    source_pi_ids.append(pid)
    if not source_pi_ids:
        raise HTTPException(status_code=400, detail="연결된 PI가 없어 CI를 발행할 수 없습니다.")

    sales_service = SalesDocumentService(db)
    ci = sales_service.create_ci_from_lines(
        source_pi_ids, ci_lines, ConvertToNextRequest(target_type="CI", document_date=req.document_date)
    )
    if not ci:
        raise HTTPException(status_code=400, detail="CI 발행에 실패했습니다.")

    # 잔여 차감(ci_quantity 누적)
    for ln in req.lines:
        it = item_map.get(ln.pr_item_id)
        qty = float(ln.quantity or 0)
        if it and qty > 0:
            it.ci_quantity = (it.ci_quantity or 0) + Decimal(str(qty))
    db.commit()

    # 담당자 = 발행자, packing 합산
    prepared = (getattr(user, "name_en", None) or "").strip() or (getattr(user, "name", None) or "").strip()
    if prepared:
        ci.prepared_by = prepared
    ci.prepared_email = (getattr(user, "email", None) or "").strip() or None
    db.commit()
    combined_boxes = []
    for pr in prs:
        combined_boxes.extend(pr.packing_list or [])
    _apply_packing_boxes_to_ci(db, ci, combined_boxes, prs[0])

    return {"ci_id": ci.id, "ci_number": ci.document_number}


class CreateBoxCiRequest(BaseModel):
    document_date: Optional[date] = None


@router.post("/{pr_id}/box-plan/{box_no}/create-ci")
def create_box_ci(
    pr_id: int,
    box_no: int,
    req: CreateBoxCiRequest,
    service: ProductionRequestService = Depends(get_production_request_service),
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """박스 단위 CI 발행(분할선적) — 박스 분할계획의 1개 박스를 1 CI로 발행.

    내용물 = 박스 품목·수량, 배송비 = 박스당 운임(freight_per_box, PI/견적 승계).
    발행 후 해당 박스에 ci_number를 기록해 잔여박스를 추적한다.
    """
    from app.schemas.sales_document import ConvertToNextRequest
    from app.services.sales_document_service import SalesDocumentService
    from app.models.sales_document import SalesDocument

    pr = service.get_or_raise(pr_id)
    boxes = list(pr.box_plan or [])
    idx = next((i for i, b in enumerate(boxes) if int(b.get("box_no") or 0) == box_no), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"박스 {box_no}를 찾을 수 없습니다.")
    box = dict(boxes[idx])
    if box.get("ci_document_id"):
        raise HTTPException(status_code=400, detail=f"박스 {box_no}는 이미 CI({box.get('ci_number')})가 발행되었습니다.")

    item_map = {it.id: it for it in (pr.items or [])}
    ci_lines = []
    source_pi_ids = []
    accum = []  # [(item, qty)] — 잔여 차감용
    for ln in (box.get("items") or []):
        it = item_map.get(ln.get("pr_item_id"))
        if not it:
            raise HTTPException(status_code=400, detail="박스 품목을 생산요청에서 찾을 수 없습니다. 계획을 다시 저장하세요.")
        qty = float(ln.get("quantity") or 0)
        if qty <= 0:
            continue
        code, desc, uom, price, cur = _line_product_info(db, it)
        remaining = float(it.requested_quantity or 0) - float(getattr(it, "ci_quantity", 0) or 0)
        if qty > remaining + 1e-6:
            raise HTTPException(status_code=400, detail=f"'{code}' 잔여({remaining:g})를 초과했습니다.")
        if price is None:
            raise HTTPException(status_code=400, detail=f"'{code}' 단가가 없습니다. PI 단가를 확인하세요.")
        ci_lines.append({
            "product_code": code, "description": desc, "quantity": qty, "uom": uom,
            "unit_price": price, "currency": cur, "line_remarks": getattr(it, "line_remarks", None),
        })
        accum.append((it, qty))
        pid = getattr(it, "pi_document_id", None)
        if pid and pid not in source_pi_ids:
            source_pi_ids.append(pid)

    if not ci_lines:
        raise HTTPException(status_code=400, detail="박스에 발행할 품목/수량이 없습니다.")
    if not source_pi_ids:
        for pid in _collect_pi_ids_for_pr(db, pr):
            if pid not in source_pi_ids:
                source_pi_ids.append(pid)
    if not source_pi_ids:
        raise HTTPException(status_code=400, detail="연결된 PI가 없어 CI를 발행할 수 없습니다.")

    # 박스당 운임(freight_per_box) — 소스 PI/견적 승계값
    freight = None
    for pid in source_pi_ids:
        doc = db.query(SalesDocument).filter(SalesDocument.id == pid).first()
        if doc and getattr(doc, "freight_per_box", None) is not None:
            freight = doc.freight_per_box
            break

    sales_service = SalesDocumentService(db)
    ci = sales_service.create_ci_from_lines(
        source_pi_ids, ci_lines,
        ConvertToNextRequest(target_type="CI", document_date=req.document_date),
        shipping_fee_override=freight,
    )
    if not ci:
        raise HTTPException(status_code=400, detail="CI 발행에 실패했습니다.")

    # 잔여 차감(ci_quantity 누적)
    for it, qty in accum:
        it.ci_quantity = (it.ci_quantity or 0) + Decimal(str(qty))

    # 담당자 = 발행자
    prepared = (getattr(user, "name_en", None) or "").strip() or (getattr(user, "name", None) or "").strip()
    if prepared:
        ci.prepared_by = prepared
    ci.prepared_email = (getattr(user, "email", None) or "").strip() or None

    # 박스 발행 표시(잔여박스 추적) — JSON 재할당으로 변경 감지
    box["ci_document_id"] = ci.id
    box["ci_number"] = ci.document_number
    boxes[idx] = box
    pr.box_plan = boxes
    db.commit()

    return {"ci_id": ci.id, "ci_number": ci.document_number, "box_no": box_no}


def _apply_packing_to_ci(db, pr, ci) -> None:
    """생산요청의 packing list/출고 정보를 CI에 승계하고 요약값을 산출한다."""
    _apply_packing_boxes_to_ci(db, ci, pr.packing_list or [], pr)


def _apply_packing_boxes_to_ci(db, ci, boxes, primary_pr) -> None:
    """주어진 packing 박스 목록(합배송이면 여러 PR 합산)을 CI에 승계 + 선적정보(primary_pr 기준)."""
    changed = False
    if boxes:
        ci.packing_list = boxes
        total_boxes = 0
        total_gross = 0.0
        total_net = 0.0
        for b in boxes:
            qty = int(b.get("quantity") or 0) or 1
            total_boxes += qty
            total_gross += float(b.get("gross_weight") or 0) * qty
            total_net += float(b.get("net_weight") or 0) * qty
        ci.packaging_boxes = total_boxes or None
        ci.packaging_gross_weight = round(total_gross, 2) or None
        ci.packaging_net_weight = round(total_net, 2) or None
        # 단일 박스형이면 치수 요약(LxWxH)
        if len(boxes) == 1:
            b = boxes[0]
            dims = [b.get("length"), b.get("width"), b.get("height")]
            if all(x is not None for x in dims):
                ci.packaging_dimensions = " x ".join(str(_num(x)) for x in dims)
        changed = True
    # 선적 정보 기본값 승계(비어 있을 때만) — 대표(primary) PR 기준
    if not ci.ship_from:
        ci.ship_from = "Seoul, Korea"; changed = True
    if not ci.destination and getattr(primary_pr, "destination", None):
        ci.destination = primary_pr.destination; changed = True
    if not ci.shipment_date and getattr(primary_pr, "shipped_at", None):
        try:
            ci.shipment_date = primary_pr.shipped_at.date(); changed = True
        except Exception:
            pass
    if changed:
        db.commit()


def _num(x):
    """치수 표기: 정수면 정수로, 아니면 그대로."""
    try:
        f = float(x)
        return int(f) if f == int(f) else f
    except Exception:
        return x


# ==================== 첨부파일 관리 (v0.22.0) ====================

# 파일 업로드 디렉토리
from app.core.storage_paths import resolve_stored_path, upload_dir

# 업로드 폴더(config.json storage.upload) 아래에 저장 — 과거 경로는 resolve_stored_path 가 맞춰 준다
UPLOAD_DIR = upload_dir("production_requests")

# 허용 파일 확장자
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".doc", ".docx", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


@router.post("/{pr_id}/attachments")
async def upload_attachment(
    pr_id: int,
    file: UploadFile = File(...),
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """
    생산 요청서 첨부파일 업로드 (v0.22.0)

    지원 형식: PDF, Excel, Word, 이미지
    최대 크기: 200MB
    """
    try:
        # 요청서 존재 확인
        pr = service.get(pr_id)
        if not pr:
            raise HTTPException(status_code=404, detail="생산 요청서를 찾을 수 없습니다.")

        # 파일 확장자 검증
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 파일 크기 검증 (Content-Length가 있을 때만)
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"파일 크기가 너무 큽니다. 최대: {MAX_FILE_SIZE // 1024 // 1024}MB"
            )

        # 고유 파일명 생성
        unique_filename = f"{pr_id}_{uuid.uuid4().hex}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # 파일 저장
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # 첨부파일 정보 업데이트
        attachment_info = {
            "filename": file.filename,
            "filepath": str(file_path),
            "mimetype": file.content_type or "application/octet-stream",
            "size": len(contents)
        }

        # 기존 첨부파일 목록에 추가 — 새 리스트로 재할당 + flag_modified (JSON 변경 감지)
        from sqlalchemy.orm.attributes import flag_modified
        current_files = list(pr.attachment_files or [])
        current_files.append(attachment_info)
        pr.attachment_files = current_files
        flag_modified(pr, "attachment_files")
        service.db.commit()

        # 납품 폴더(도면 하위)에도 사본 저장 — 영업이 올린 도면/첨부가 납품현황 폴더에 함께 모이도록(best-effort)
        try:
            from app.services import nextcloud_service as ncs
            ncs.save_delivery_file(pr, "도면", file.filename or "drawing", contents)
        except Exception:
            pass

        return {
            "message": "파일이 업로드되었습니다.",
            "file": attachment_info,
            "total_files": len(current_files)
        }

    except AppException as e:
        handle_service_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")


@router.delete("/{pr_id}/attachments/{file_index}")
def delete_attachment(
    pr_id: int,
    file_index: int,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 첨부파일 삭제"""
    try:
        pr = service.get(pr_id)
        if not pr:
            raise HTTPException(status_code=404, detail="생산 요청서를 찾을 수 없습니다.")

        current_files = list(pr.attachment_files or [])
        if file_index < 0 or file_index >= len(current_files):
            raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다.")

        # 파일 삭제
        file_info = current_files[file_index]
        file_path = resolve_stored_path(file_info["filepath"])
        if file_path.exists():
            file_path.unlink()

        # 목록에서 제거 — 새 리스트 재할당 + flag_modified (JSON 변경 감지)
        from sqlalchemy.orm.attributes import flag_modified
        current_files.pop(file_index)
        pr.attachment_files = current_files
        flag_modified(pr, "attachment_files")
        service.db.commit()

        return {"message": "파일이 삭제되었습니다.", "total_files": len(current_files)}

    except AppException as e:
        handle_service_exception(e)
    except HTTPException:
        raise


@router.get("/{pr_id}/attachments/{file_index}/download")
def download_attachment(
    pr_id: int,
    file_index: int,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """생산 요청서 첨부파일 다운로드"""
    try:
        pr = service.get(pr_id)
        if not pr:
            raise HTTPException(status_code=404, detail="생산 요청서를 찾을 수 없습니다.")

        current_files = pr.attachment_files or []
        if file_index < 0 or file_index >= len(current_files):
            raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다.")

        file_info = current_files[file_index]
        file_path = resolve_stored_path(file_info["filepath"])

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        # 한글 파일명 인코딩 처리
        from urllib.parse import quote
        filename = file_info["filename"]
        try:
            filename.encode('latin-1')
            disposition = f"attachment; filename=\"{filename}\""
        except UnicodeEncodeError:
            encoded = quote(filename)
            disposition = f"attachment; filename*=UTF-8''{encoded}"

        return FileResponse(
            path=str(file_path),
            media_type=file_info.get("mimetype", "application/octet-stream"),
            headers={"Content-Disposition": disposition}
        )

    except AppException as e:
        handle_service_exception(e)
    except HTTPException:
        raise


@router.get("/{pr_id}/attachments/{file_index}/preview")
def preview_attachment(
    pr_id: int,
    file_index: int,
    service: ProductionRequestService = Depends(get_production_request_service)
):
    """
    생산 요청서 첨부파일 미리보기 (v0.22.0)

    PDF 및 이미지 파일은 브라우저에서 직접 볼 수 있습니다.
    """
    try:
        pr = service.get(pr_id)
        if not pr:
            raise HTTPException(status_code=404, detail="생산 요청서를 찾을 수 없습니다.")

        current_files = pr.attachment_files or []
        if file_index < 0 or file_index >= len(current_files):
            raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다.")

        file_info = current_files[file_index]
        file_path = resolve_stored_path(file_info["filepath"])

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        # 미리보기 가능한 MIME 타입
        mimetype = file_info.get("mimetype", "application/octet-stream")

        # Content-Disposition: 한글 파일명은 RFC 5987 형식으로 인코딩
        from urllib.parse import quote
        filename = file_info['filename']
        try:
            filename.encode('latin-1')
            disposition = f"inline; filename=\"{filename}\""
        except UnicodeEncodeError:
            encoded = quote(filename)
            disposition = f"inline; filename*=UTF-8''{encoded}"

        return FileResponse(
            path=str(file_path),
            media_type=mimetype,
            headers={"Content-Disposition": disposition}
        )

    except AppException as e:
        handle_service_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"첨부파일 미리보기 실패: {str(e)}")


# ==================== 품목별 도면/첨부 (v0.75.0) ====================

def _get_pr_item(service: ProductionRequestService, pr_id: int, item_id: int):
    from app.models.production_request import ProductionRequestItem
    item = service.db.query(ProductionRequestItem).filter(
        ProductionRequestItem.id == item_id,
        ProductionRequestItem.production_request_id == pr_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다.")
    return item


def _inline_disposition(filename: str) -> str:
    from urllib.parse import quote
    try:
        filename.encode('latin-1')
        return f"inline; filename=\"{filename}\""
    except UnicodeEncodeError:
        return f"inline; filename*=UTF-8''{quote(filename)}"


@router.post("/{pr_id}/items/{item_id}/attachments")
async def upload_item_attachment(
    pr_id: int, item_id: int,
    file: UploadFile = File(...),
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """품목별 도면/첨부 업로드 (v0.75.0)"""
    from sqlalchemy.orm.attributes import flag_modified
    try:
        item = _get_pr_item(service, pr_id, item_id)
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}")
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"파일 크기가 너무 큽니다. 최대: {MAX_FILE_SIZE // 1024 // 1024}MB")

        unique_filename = f"{pr_id}_{item_id}_{uuid.uuid4().hex}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        info = {"filename": file.filename, "filepath": str(file_path),
                "mimetype": file.content_type or "application/octet-stream", "size": len(contents)}
        files = list(item.attachment_files or [])
        files.append(info)
        item.attachment_files = files
        flag_modified(item, "attachment_files")
        service.db.commit()

        # 납품 폴더(도면 하위)에도 사본 저장(best-effort)
        try:
            from app.services import nextcloud_service as ncs
            pr = service.get(pr_id)
            if pr:
                ncs.save_delivery_file(pr, "도면", file.filename or "drawing", contents)
        except Exception:
            pass

        return {"message": "도면이 업로드되었습니다.", "file": info, "total_files": len(files)}
    except AppException as e:
        handle_service_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"도면 업로드 실패: {str(e)}")


@router.get("/{pr_id}/items/{item_id}/attachments/{file_index}/preview")
def preview_item_attachment(
    pr_id: int, item_id: int, file_index: int,
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """품목별 도면/첨부 미리보기"""
    try:
        item = _get_pr_item(service, pr_id, item_id)
        files = item.attachment_files or []
        if file_index < 0 or file_index >= len(files):
            raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다.")
        info = files[file_index]
        file_path = resolve_stored_path(info["filepath"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        return FileResponse(
            path=str(file_path),
            media_type=info.get("mimetype", "application/octet-stream"),
            headers={"Content-Disposition": _inline_disposition(info["filename"])},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"도면 미리보기 실패: {str(e)}")


@router.delete("/{pr_id}/items/{item_id}/attachments/{file_index}")
def delete_item_attachment(
    pr_id: int, item_id: int, file_index: int,
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """품목별 도면/첨부 삭제"""
    from sqlalchemy.orm.attributes import flag_modified
    try:
        item = _get_pr_item(service, pr_id, item_id)
        files = list(item.attachment_files or [])
        if file_index < 0 or file_index >= len(files):
            raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다.")
        removed = files.pop(file_index)
        try:
            resolve_stored_path(removed["filepath"]).unlink(missing_ok=True)
        except Exception:
            pass
        item.attachment_files = files
        flag_modified(item, "attachment_files")
        service.db.commit()
        return {"message": "삭제되었습니다.", "total_files": len(files)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"도면 삭제 실패: {str(e)}")


# ==================== 출고 포장사진 (납품 트리, 생산 권한) v0.86.0 ====================

def _packing_folder_of(service, pr, create: bool):
    """PR의 포장사진 폴더(납품 베이스 상대경로). 저장값 우선, 없으면 해석 후 저장."""
    from app.services import nextcloud_service as ncs
    stored = (getattr(pr, "packing_folder", None) or "").strip()
    if stored:
        return stored
    rel = ncs.resolve_packing_folder(pr, create=create)
    if create and rel:
        pr.packing_folder = rel
        service.db.commit()
    return rel


@router.get("/{pr_id}/packing-photos")
def list_packing_photos(pr_id: int, service: ProductionRequestService = Depends(get_production_request_service)):
    """포장사진 목록(이미지만) + 폴더 경로. 폴더 없으면 번호 prefix 매칭/생성."""
    from app.services import nextcloud_service as ncs
    if not ncs.delivery_enabled():
        return {"enabled": False, "folder": None, "photos": []}
    pr = service.get_or_raise(pr_id)
    rel = _packing_folder_of(service, pr, create=True)
    return {"enabled": True, "folder": rel, "photos": ncs.list_packing_photos(rel)}


@router.post("/{pr_id}/packing-photos")
async def upload_packing_photo(
    pr_id: int,
    file: UploadFile = File(...),
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """포장사진 업로드(이미지만). 최초 업로드 시 폴더 확정·저장."""
    from app.services import nextcloud_service as ncs
    if not ncs.delivery_enabled():
        raise HTTPException(status_code=503, detail="납품 파일 연동이 비활성화되어 있습니다 (NEXTCLOUD_DELIVERY_PATH 미설정).")
    pr = service.get_or_raise(pr_id)
    if not ncs.is_image_name(file.filename or ""):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드할 수 있습니다.")
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다. 최대: 50MB")
    rel = _packing_folder_of(service, pr, create=True)
    try:
        name = ncs.save_packing_photo(rel, file.filename or "photo", contents)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {e}")
    return {"message": "업로드되었습니다.", "name": name, "folder": rel}


@router.get("/{pr_id}/packing-photos/preview")
def preview_packing_photo(
    pr_id: int,
    name: str = Query(..., description="파일명"),
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """포장사진 인라인 미리보기(이미지 스트리밍)."""
    from app.services import nextcloud_service as ncs
    pr = service.get_or_raise(pr_id)
    rel = _packing_folder_of(service, pr, create=False)
    if not rel:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    try:
        full = ncs.packing_photo_abs(rel, name)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 경로")
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return FileResponse(path=full, headers={"Content-Disposition": "inline"})


@router.post("/{pr_id}/packing-photos/delete")
def delete_packing_photo(
    pr_id: int,
    name: str = Query(..., description="파일명"),
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """포장사진 삭제. (DELETE가 아닌 POST — 생산요청 삭제권한이 아닌 업로드와 동일 권한으로 처리)"""
    from app.services import nextcloud_service as ncs
    pr = service.get_or_raise(pr_id)
    rel = _packing_folder_of(service, pr, create=False)
    if not rel:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    try:
        full = ncs.packing_photo_abs(rel, name)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 경로")
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    try:
        os.remove(full)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"삭제 실패: {e}")
    return {"message": "삭제되었습니다."}


# ==================== 측정자료(손실값측정 엑셀 등) — 납품 폴더 하위 (생산 권한) ====================

def _measurement_folder_of(service, pr, create: bool):
    """PR의 측정자료 폴더(포장 폴더 하위 '측정자료'). 없으면 생성."""
    from app.services import nextcloud_service as ncs
    base = _packing_folder_of(service, pr, create=create)
    if not base:
        return None
    rel = f"{base}/{ncs.MEASUREMENT_SUBFOLDER}"
    if create:
        ncs.ensure_dir(rel, base=ncs._delivery_base())
    return rel


@router.get("/{pr_id}/measurement-files")
def list_measurement_files(pr_id: int, service: ProductionRequestService = Depends(get_production_request_service)):
    """측정자료(손실값측정 등) 파일 목록 + 폴더 경로."""
    from app.services import nextcloud_service as ncs
    if not ncs.delivery_enabled():
        return {"enabled": False, "folder": None, "files": []}
    pr = service.get_or_raise(pr_id)
    rel = _measurement_folder_of(service, pr, create=True)
    return {"enabled": True, "folder": rel, "files": ncs.list_delivery_files(rel) if rel else []}


@router.post("/{pr_id}/measurement-files")
async def upload_measurement_file(
    pr_id: int,
    file: UploadFile = File(...),
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """측정자료 업로드(엑셀·PDF 등 문서). 최초 업로드 시 폴더 확정·저장."""
    from app.services import nextcloud_service as ncs
    if not ncs.delivery_enabled():
        raise HTTPException(status_code=503, detail="납품 파일 연동이 비활성화되어 있습니다 (NEXTCLOUD_DELIVERY_PATH 미설정).")
    pr = service.get_or_raise(pr_id)
    if not ncs.is_allowed_doc_name(file.filename or ""):
        raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다. (엑셀·CSV·PDF·문서·이미지·zip만 가능)")
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다. 최대: 50MB")
    rel = _measurement_folder_of(service, pr, create=True)
    if not rel:
        raise HTTPException(status_code=500, detail="측정자료 폴더를 준비할 수 없습니다.")
    try:
        name = ncs.save_packing_photo(rel, file.filename or "file", contents)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {e}")
    return {"message": "업로드되었습니다.", "name": name, "folder": rel}


@router.get("/{pr_id}/measurement-files/download")
def download_measurement_file(
    pr_id: int,
    name: str = Query(..., description="파일명"),
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """측정자료 파일 다운로드(첨부)."""
    from app.services import nextcloud_service as ncs
    pr = service.get_or_raise(pr_id)
    rel = _measurement_folder_of(service, pr, create=False)
    if not rel:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    try:
        full = ncs.packing_photo_abs(rel, name)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 경로")
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    fname = os.path.basename(full)
    return FileResponse(path=full, filename=fname, headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.post("/{pr_id}/measurement-files/delete")
def delete_measurement_file(
    pr_id: int,
    name: str = Query(..., description="파일명"),
    service: ProductionRequestService = Depends(get_production_request_service),
):
    """측정자료 파일 삭제. (업로드와 동일 권한 — POST)"""
    from app.services import nextcloud_service as ncs
    pr = service.get_or_raise(pr_id)
    rel = _measurement_folder_of(service, pr, create=False)
    if not rel:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    try:
        full = ncs.packing_photo_abs(rel, name)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 경로")
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    try:
        os.remove(full)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"삭제 실패: {e}")
    return {"message": "삭제되었습니다."}
