"""
대시보드 API
v0.28.0: 홈 화면 요약 데이터
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from app.core.database import get_db
from app.models.sales_activity import SalesActivity, SalesActivityLog
from app.models.production_request import ProductionRequest
from app.models.work_order import WorkOrder
from app.models.sales_document import SalesDocument

router = APIRouter(prefix="/dashboard", tags=["대시보드"])

INACTIVE_WEEKS = 8


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """홈 화면 요약 데이터 (한 번의 호출로 전체 현황)"""

    # 1. 영업 대응 현황 — 진행중 건수
    active_activities = db.query(sa_func.count(SalesActivity.id)).filter(
        SalesActivity.status.in_(["IN_PROGRESS", "WAITING"])
    ).scalar() or 0

    # 2. 대기 중인 생산요청
    pending_requests = db.query(sa_func.count(ProductionRequest.id)).filter(
        ProductionRequest.status == "REQUESTED"
    ).scalar() or 0

    # 3. 진행 중인 작업지시
    active_work_orders = db.query(sa_func.count(WorkOrder.id)).filter(
        WorkOrder.status.in_(["APPROVED", "ISSUED", "IN_PROGRESS", "INSPECTION", "PACKED"])
    ).scalar() or 0

    # 4. 미입금 PI
    unpaid_pis = db.query(sa_func.count(SalesDocument.id)).filter(
        SalesDocument.document_type == "PI",
        SalesDocument.status != "CANCELLED",
        SalesDocument.is_latest == True,  # noqa: E712
        SalesDocument.payment_status.in_(["UNPAID", None]),
    ).scalar() or 0

    # 5. 비활성 영업 (8주 이상 코멘트 없음, 등록 4주 이내는 제외)
    threshold = datetime.now(timezone.utc) - timedelta(weeks=INACTIVE_WEEKS)
    grace_period = datetime.now(timezone.utc) - timedelta(weeks=4)

    active_activity_list = db.query(SalesActivity).filter(
        SalesActivity.status.in_(["IN_PROGRESS", "WAITING"])
    ).all()

    inactive_count = 0
    if active_activity_list:
        ids = [a.id for a in active_activity_list]
        last_logs = db.query(
            SalesActivityLog.activity_id,
            sa_func.max(SalesActivityLog.created_at).label("last_log")
        ).filter(
            SalesActivityLog.activity_id.in_(ids)
        ).group_by(SalesActivityLog.activity_id).all()

        logged_map = {r.activity_id: r.last_log for r in last_logs}

        for a in active_activity_list:
            last_log = logged_map.get(a.id)
            if last_log:
                if last_log < threshold:
                    inactive_count += 1
            else:
                # 로그 없는 경우: 등록일이 4주 이전이면 비활성
                created = a.created_at
                if created and created < grace_period:
                    inactive_count += 1

    # 6. 최근 영업 활동 (최근 코멘트 기준 5건)
    recent_logs = db.query(SalesActivityLog).join(
        SalesActivity, SalesActivityLog.activity_id == SalesActivity.id
    ).order_by(SalesActivityLog.created_at.desc()).limit(5).all()

    recent_activities = []
    for log in recent_logs:
        activity = db.query(SalesActivity).filter(SalesActivity.id == log.activity_id).first()
        if activity:
            recent_activities.append({
                "id": activity.id,
                "title": activity.title,
                "customer_name": activity.customer_name,
                "log_content": log.content[:80],
                "logged_by": log.logged_by,
                "logged_at": log.created_at.isoformat() if log.created_at else None,
            })

    # 7. 대기 중인 생산요청 목록 (최근 5건)
    pending_list = db.query(ProductionRequest).filter(
        ProductionRequest.status == "REQUESTED"
    ).order_by(ProductionRequest.created_at.desc()).limit(5).all()

    pending_items = [{
        "id": pr.id,
        "request_number": pr.request_number,
        "customer_name": pr.customer.partner_name if pr.customer else None,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
    } for pr in pending_list]

    # 8. 미입금 PI 목록 (최근 5건)
    unpaid_list = db.query(SalesDocument).filter(
        SalesDocument.document_type == "PI",
        SalesDocument.status != "CANCELLED",
        SalesDocument.is_latest == True,  # noqa: E712
        SalesDocument.payment_status.in_(["UNPAID", None]),
    ).order_by(SalesDocument.created_at.desc()).limit(5).all()

    unpaid_items = [{
        "id": pi.id,
        "document_number": pi.document_number,
        "customer_name": pi.customer.partner_name if pi.customer else None,
        "total_amount": float(pi.total_amount) if pi.total_amount else 0,
        "currency": pi.currency,
    } for pi in unpaid_list]

    return {
        "cards": {
            "active_activities": active_activities,
            "pending_requests": pending_requests,
            "active_work_orders": active_work_orders,
            "unpaid_pis": unpaid_pis,
            "inactive_activities": inactive_count,
        },
        "recent_activities": recent_activities,
        "pending_items": pending_items,
        "unpaid_items": unpaid_items,
    }
