"""
공정 템플릿 API
v0.29.0
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.process_template import ProcessTemplate

router = APIRouter(prefix="/process-templates", tags=["공정 템플릿"])


class TemplateStepSchema(BaseModel):
    task_name: str
    assigned_team: Optional[str] = None
    sort_order: int = 0


class ProcessTemplateCreate(BaseModel):
    template_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    steps: List[TemplateStepSchema] = []


class ProcessTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[TemplateStepSchema]] = None
    is_active: Optional[bool] = None


class ProcessTemplateResponse(BaseModel):
    id: int
    template_name: str
    description: Optional[str] = None
    steps: list
    is_active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=List[ProcessTemplateResponse])
def get_templates(db: Session = Depends(get_db)):
    return db.query(ProcessTemplate).filter(ProcessTemplate.is_active == True).order_by(ProcessTemplate.template_name).all()


@router.post("", response_model=ProcessTemplateResponse, status_code=201)
def create_template(data: ProcessTemplateCreate, db: Session = Depends(get_db)):
    t = ProcessTemplate(
        template_name=data.template_name,
        description=data.description,
        steps=[s.model_dump() for s in data.steps],
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{template_id}", response_model=ProcessTemplateResponse)
def update_template(template_id: int, data: ProcessTemplateUpdate, db: Session = Depends(get_db)):
    t = db.query(ProcessTemplate).filter(ProcessTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "steps" and value is not None:
            setattr(t, key, [s if isinstance(s, dict) else s.model_dump() for s in value])
        else:
            setattr(t, key, value)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    t = db.query(ProcessTemplate).filter(ProcessTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")
    t.is_active = False
    db.commit()


@router.post("/{template_id}/apply/{wo_id}")
def apply_template(template_id: int, wo_id: int, db: Session = Depends(get_db)):
    """작업지시서에 템플릿의 공정을 적용"""
    from app.models.work_order import WorkOrder
    from app.models.work_order_task import WorkOrderTask

    t = db.query(ProcessTemplate).filter(ProcessTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")

    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="작업지시서를 찾을 수 없습니다")

    # 기존 공정이 있으면 추가 (덮어쓰지 않음)
    existing_count = db.query(WorkOrderTask).filter(WorkOrderTask.work_order_id == wo_id).count()

    for step in (t.steps or []):
        task = WorkOrderTask(
            work_order_id=wo_id,
            task_name=step.get("task_name", ""),
            assigned_team=step.get("assigned_team"),
            sort_order=existing_count + step.get("sort_order", 0),
        )
        db.add(task)

    db.commit()
    return {"message": f"'{t.template_name}' 템플릿 적용 완료 ({len(t.steps or [])}개 공정)"}
