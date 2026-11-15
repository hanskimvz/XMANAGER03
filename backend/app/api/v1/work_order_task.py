"""
작업지시서 공정 작업 API
v0.29.0
"""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.work_order_task import WorkOrderTask
from app.models.work_order import WorkOrder
from app.schemas.work_order_task import (
    WorkOrderTaskCreate, WorkOrderTaskUpdate, WorkOrderTaskResponse
)

router = APIRouter(prefix="/work-orders/{wo_id}/tasks", tags=["공정 작업"])


@router.get("", response_model=List[WorkOrderTaskResponse])
def get_tasks(wo_id: int, db: Session = Depends(get_db)):
    return db.query(WorkOrderTask).filter(
        WorkOrderTask.work_order_id == wo_id
    ).order_by(WorkOrderTask.sort_order).all()


@router.post("", response_model=WorkOrderTaskResponse, status_code=201)
def create_task(wo_id: int, data: WorkOrderTaskCreate, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="작업지시서를 찾을 수 없습니다")

    task = WorkOrderTask(
        work_order_id=wo_id,
        task_name=data.task_name,
        assigned_team=data.assigned_team,
        sort_order=data.sort_order,
        remarks=data.remarks,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}", response_model=WorkOrderTaskResponse)
def update_task(wo_id: int, task_id: int, data: WorkOrderTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(WorkOrderTask).filter(
        WorkOrderTask.id == task_id, WorkOrderTask.work_order_id == wo_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="공정을 찾을 수 없습니다")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/start", response_model=WorkOrderTaskResponse)
def start_task(wo_id: int, task_id: int, db: Session = Depends(get_db)):
    task = db.query(WorkOrderTask).filter(
        WorkOrderTask.id == task_id, WorkOrderTask.work_order_id == wo_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="공정을 찾을 수 없습니다")

    task.status = "IN_PROGRESS"
    task.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/complete", response_model=WorkOrderTaskResponse)
def complete_task(wo_id: int, task_id: int, db: Session = Depends(get_db)):
    task = db.query(WorkOrderTask).filter(
        WorkOrderTask.id == task_id, WorkOrderTask.work_order_id == wo_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="공정을 찾을 수 없습니다")

    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)

    # 전체 공정 완료 시 WO 상태 자동 업데이트
    all_tasks = db.query(WorkOrderTask).filter(WorkOrderTask.work_order_id == wo_id).all()
    all_completed = all(t.status == "COMPLETED" for t in all_tasks)
    if all_completed and len(all_tasks) > 0:
        wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
        if wo and wo.status in ("RECEIVED", "APPROVED", "ISSUED", "IN_PROGRESS"):
            wo.status = "INSPECTION"  # 전체 공정 완료 → 검사 단계로

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(wo_id: int, task_id: int, db: Session = Depends(get_db)):
    task = db.query(WorkOrderTask).filter(
        WorkOrderTask.id == task_id, WorkOrderTask.work_order_id == wo_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="공정을 찾을 수 없습니다")
    db.delete(task)
    db.commit()
