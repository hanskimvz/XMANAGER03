"""
문서 번호 자동 채번 유틸리티

v0.6.0: 입출고 관리 기능 추가
- 발주서 번호: PO-YYYYMMDD-NNN
- 작업지시서 번호: WO-YYYYMMDD-NNN
"""

from datetime import date
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder
from app.models.work_order import WorkOrder
from app.models.production_request import ProductionRequest


def generate_po_number(db: Session, order_date: date = None) -> str:
    """
    발주서 번호 자동 생성

    형식: PO-YYYYMMDD-NNN
    예: PO-20260115-001

    Args:
        db: SQLAlchemy 세션
        order_date: 발주일 (기본: 오늘)

    Returns:
        생성된 발주서 번호
    """
    if order_date is None:
        order_date = date.today()

    prefix = f"PO-{order_date.strftime('%Y%m%d')}-"

    # 해당 날짜의 마지막 번호 조회
    last_po = db.query(PurchaseOrder).filter(
        PurchaseOrder.po_number.like(f"{prefix}%")
    ).order_by(PurchaseOrder.po_number.desc()).first()

    if last_po:
        # 기존 번호에서 시퀀스 추출
        try:
            last_seq = int(last_po.po_number.split("-")[-1])
            next_seq = last_seq + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:03d}"


def generate_wo_number(db: Session, received_date: date = None) -> str:
    """
    작업지시서 번호 자동 생성

    형식: WO-YYYYMMDD-NNN
    예: WO-20260115-001

    Args:
        db: SQLAlchemy 세션
        received_date: 접수일 (기본: 오늘)

    Returns:
        생성된 작업지시서 번호
    """
    if received_date is None:
        received_date = date.today()

    prefix = f"WO-{received_date.strftime('%Y%m%d')}-"

    # 해당 날짜의 마지막 번호 조회
    last_wo = db.query(WorkOrder).filter(
        WorkOrder.wo_number.like(f"{prefix}%")
    ).order_by(WorkOrder.wo_number.desc()).first()

    if last_wo:
        # 기존 번호에서 시퀀스 추출
        try:
            last_seq = int(last_wo.wo_number.split("-")[-1])
            next_seq = last_seq + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:03d}"


# 노션 → X-Manager 이행: 특정 연도(2자리)는 이 순번 이상부터 시작.
# 노션에서 이미 사용한 번호와 겹치지 않게 하기 위함. 이행 후에는 영향 없음.
_PR_SEQ_MIN_BY_YEAR = {
    "26": 159,  # 2026년: 노션 생산스케줄이 26-158까지 사용 → X-Manager는 26-159부터
}


def generate_pr_number(db: Session, request_date: date = None) -> str:
    """
    생산 요청서 번호 자동 생성

    형식: YY-NNN (연도 2자리 - 연내 순번 3자리, 매년 1월 리셋)
    예: 26-099

    영업팀이 실제 운영 중인 생산스케줄 양식과 동일한 체계.

    Args:
        db: SQLAlchemy 세션
        request_date: 요청일 (기본: 오늘)

    Returns:
        생성된 생산 요청서 번호 (예: "26-099")
    """
    if request_date is None:
        request_date = date.today()

    yy = request_date.strftime("%y")  # '26'
    prefix = f"{yy}-"

    # 해당 연도의 마지막 번호 조회
    last_pr = db.query(ProductionRequest).filter(
        ProductionRequest.request_number.like(f"{prefix}%")
    ).order_by(ProductionRequest.request_number.desc()).first()

    if last_pr:
        try:
            last_seq = int(last_pr.request_number.split("-")[-1])
            next_seq = last_seq + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        next_seq = 1

    # 이행 override — 노션 사용 번호와 충돌 방지
    min_seq = _PR_SEQ_MIN_BY_YEAR.get(yy)
    if min_seq is not None and next_seq < min_seq:
        next_seq = min_seq

    return f"{prefix}{next_seq:03d}"
