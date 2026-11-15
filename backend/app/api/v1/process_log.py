"""
공정 로그 API 라우터
작업지시서 내 세부 공정별 시간 기록 + 리드타임 분석
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from app.core.database import get_db
from app.models.process_log import WorkOrderProcessLog
from app.models.work_order import WorkOrder
from app.schemas.process_log import (
    ProcessLogCreate,
    ProcessLogComplete,
    ProcessLogResponse,
    LeadTimeByProcess,
    LeadTimeSummary,
)

router = APIRouter(prefix="/process-logs", tags=["공정 로그"])


# ==================== 공정 기록 CRUD ====================

@router.get("/work-order/{wo_id}", response_model=List[ProcessLogResponse])
def get_logs_by_work_order(wo_id: int, db: Session = Depends(get_db)):
    """작업지시서의 공정 로그 조회"""
    logs = db.query(WorkOrderProcessLog).filter(
        WorkOrderProcessLog.work_order_id == wo_id
    ).order_by(WorkOrderProcessLog.sort_order, WorkOrderProcessLog.created_at).all()
    return logs


@router.post("/work-order/{wo_id}/start", response_model=ProcessLogResponse)
def start_process(wo_id: int, data: ProcessLogCreate, db: Session = Depends(get_db)):
    """공정 시작 기록"""
    # 작업지시서 존재 확인
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="작업지시서를 찾을 수 없습니다")

    log = WorkOrderProcessLog(
        work_order_id=wo_id,
        process_type=data.process_type,
        process_name=data.process_name or _default_process_name(data.process_type),
        started_at=datetime.now(timezone.utc),
        worker_name=data.worker_name,
        remarks=data.remarks,
        sort_order=data.sort_order,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/{log_id}/complete", response_model=ProcessLogResponse)
def complete_process(log_id: int, data: ProcessLogComplete, db: Session = Depends(get_db)):
    """공정 완료 기록 (소요시간 자동 계산)"""
    log = db.query(WorkOrderProcessLog).filter(WorkOrderProcessLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="공정 로그를 찾을 수 없습니다")
    if log.completed_at:
        raise HTTPException(status_code=400, detail="이미 완료된 공정입니다")

    log.completed_at = datetime.now(timezone.utc)

    # 소요시간 자동 계산 (시간 단위)
    if log.started_at:
        delta = log.completed_at - log.started_at
        log.duration_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))

    if data.remarks:
        log.remarks = data.remarks

    db.commit()
    db.refresh(log)
    return log


@router.delete("/{log_id}", status_code=204)
def delete_log(log_id: int, db: Session = Depends(get_db)):
    """공정 로그 삭제"""
    log = db.query(WorkOrderProcessLog).filter(WorkOrderProcessLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="공정 로그를 찾을 수 없습니다")
    db.delete(log)
    db.commit()


# ==================== 리드타임 분석 ====================

@router.get("/analytics/lead-time", response_model=LeadTimeSummary)
def get_lead_time_analysis(
    process_type: Optional[str] = Query(None, description="특정 공정만 필터"),
    days: int = Query(90, ge=7, le=365, description="분석 기간 (일)"),
    db: Session = Depends(get_db),
):
    """
    공정별 평균 리드타임 분석

    완료된 공정 로그(duration_hours가 있는 것)를 기반으로 공정별 평균/최소/최대 소요시간 산출
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(WorkOrderProcessLog).filter(
        WorkOrderProcessLog.duration_hours.isnot(None),
        WorkOrderProcessLog.completed_at >= cutoff,
    )

    if process_type:
        query = query.filter(WorkOrderProcessLog.process_type == process_type)

    logs = query.all()

    if not logs:
        return LeadTimeSummary(total_work_orders=0, avg_total_hours=0, by_process=[])

    # 공정별 그룹화
    from collections import defaultdict
    by_type = defaultdict(list)
    wo_ids = set()
    for log in logs:
        by_type[log.process_type].append(log)
        wo_ids.add(log.work_order_id)

    process_stats = []
    total_hours_sum = 0
    total_count = 0

    for ptype, plogs in sorted(by_type.items()):
        durations = [float(l.duration_hours) for l in plogs if l.duration_hours]
        if not durations:
            continue
        avg_h = sum(durations) / len(durations)
        process_stats.append(LeadTimeByProcess(
            process_type=ptype,
            process_name=plogs[0].process_name,
            avg_hours=round(avg_h, 2),
            min_hours=round(min(durations), 2),
            max_hours=round(max(durations), 2),
            count=len(durations),
        ))
        total_hours_sum += sum(durations)
        total_count += len(durations)

    avg_total = round(total_hours_sum / len(wo_ids), 2) if wo_ids else 0

    return LeadTimeSummary(
        total_work_orders=len(wo_ids),
        avg_total_hours=avg_total,
        by_process=process_stats,
    )


# ==================== 기본 공정명 ====================

def _default_process_name(process_type: str) -> str:
    """공정 타입에 대한 기본 표시명"""
    names = {
        "INSERT_CHECK": "인서트 재고 확인",
        "INSERT_ISSUE": "인서트 출고",
        "K1_PROCESSING": "K-1 가공",
        "ASSEMBLY": "커넥터 조립",
        "INSPECTION": "검사",
        "PACKING": "포장",
        "SHIPPING_PREP": "출하 준비",
    }
    return names.get(process_type, process_type)
