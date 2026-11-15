"""
전자결재 API 라우터 (v0.33.0)

설계노트 6장 14개 엔드포인트 1:1 매핑.
- 결재 본문: router(prefix="/approvals")
- 도장: seal_router(prefix="/users")
- 관리자(디폴트결재자/정정): admin_router(prefix="/admin")

불변식: actions/corrections 에 대한 DELETE/일반 UPDATE 엔드포인트는 만들지 않는다.
출력(/print, /pdf)은 WU5 범위 — 시그니처만 두고 501 반환.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse

from app.core.auth import require_admin, require_auth
from app.models.user import User
from app.api.v1.deps import get_approval_service, handle_service_exception
from app.services.approval_service import ApprovalService
from app.services.approval_attachment_service import ApprovalAttachmentService
from app.schemas.approval import (
    AdminDatesUpdate,
    ApprovalActionRequest,
    ApprovalAttachmentResponse,
    ApprovalCommentCreate,
    ApprovalCommentResponse,
    ApprovalCorrectionResponse,
    ApprovalDocumentCreate,
    ApprovalDocumentListItem,
    ApprovalDocumentResponse,
    ApprovalDocumentUpdate,
    AdminFullEditRequest,
    ApprovalFormResponse,
    ApprovalListResponse,
    ApprovalProjectCreate,
    ApprovalProjectResponse,
    ApprovalProjectUpdate,
    BoxType,
    CorrectionRequest,
    DefaultApproverUpdate,
    LeaveBalanceResponse,
    LinkablePredecessorItem,
    LinkableTripItem,
)
from app.services import leave_service, seal_service

router = APIRouter(prefix="/approvals", tags=["전자결재"])
seal_router = APIRouter(prefix="/users", tags=["전자결재-도장"])
admin_router = APIRouter(prefix="/admin", tags=["전자결재-관리자"])


# ==================== 직렬화 헬퍼 ====================

def _get_client_ip(request: Request) -> Optional[str]:
    """IP 추출: X-Forwarded-For 우선(맨 앞) → client.host."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def _serialize_detail(doc, service: ApprovalService, actor: User) -> ApprovalDocumentResponse:
    """문서 상세를 응답 스키마로 직렬화 (계산 필드 주입)."""
    resp = ApprovalDocumentResponse.model_validate(doc)
    resp.drafter_name = doc.drafter.name if doc.drafter else None
    # 편집 화면에서 '현재 로그인 사용자'가 아니라 문서의 실제 기안자를 표시하기 위해 함께 내려준다
    resp.drafter_position = doc.drafter.position if doc.drafter else None
    resp.drafter_department = doc.drafter.department if doc.drafter else None
    resp.verify_code = service._verify_code(doc.doc_number, doc.content)
    resp.can_act = service.can_act(doc, actor)
    resp.can_reject = service.can_reject(doc, actor)
    # 시행자/시행 상태 주입
    executor = getattr(doc, "executor", None)
    resp.executor_name = executor.name if executor else None
    resp.can_execute = bool(
        doc.executor_id and doc.executor_id == actor.id
        and doc.status == "APPROVED" and doc.execution_status == "PENDING"
    )

    # 양식 정보 주입
    form = getattr(doc, "form", None)
    if form is not None:
        resp.form_code = form.code
        resp.form_name = form.name
        resp.form_phase = form.phase
        # 이 문서가 PRE 면 짝이 되는 모든 POST 양식(linked_form_code==이 form.code)을 리스트로 주입
        if form.phase == "PRE":
            from app.models.approval import ApprovalForm as _Form
            post_forms = (
                service.db.query(_Form)
                .filter(
                    _Form.linked_form_code == form.code,
                    _Form.phase == "POST",
                    _Form.is_active.is_(True),
                )
                .order_by(_Form.sort_order, _Form.id)
                .all()
            )
            resp.followups = [
                {"form_code": f.code, "form_name": f.name} for f in post_forms
            ]
            if resp.followups:
                # 하위호환 — 첫 항목
                resp.followup_form_code = resp.followups[0]["form_code"]
                resp.followup_form_name = resp.followups[0]["form_name"]
            # 승인 완료된 PRE 문서 + 후속 양식 1개 이상일 때만 후속 작성 가능
            resp.can_create_followup = doc.status == "APPROVED" and len(resp.followups) > 0

    # 후속(이 문서를 related_document_id 로 가리키는) 문서 목록 주입
    resp.linked_documents = service.get_followups(doc)

    # 프로젝트 이름 주입
    project = getattr(doc, "project", None)
    if project is not None:
        resp.project_name = f"[{project.code}] {project.name}" if project.code else project.name

    # 관련 문서(정산서→출장신청서 등) 표시용 주입
    related = getattr(doc, "related_document", None)
    if related is not None:
        resp.related_doc_number = related.doc_number
        resp.related_title = related.title
    # 다중 관련 문서 목록 주입 (v0.55.0)
    resp.related_documents = service.get_related_documents(doc)

    # 참조자 이름/직급 주입
    for ref_resp, ref in zip(resp.references, doc.references):
        if ref.user:
            ref_resp.name = ref.user.name
            ref_resp.position = ref.user.position

    # 결재선 도장 SVG / 결재자 정보 주입
    for line_resp, line in zip(resp.lines, doc.lines):
        approver = line.approver
        if not line_resp.approver_name:
            line_resp.approver_name = approver.name if approver else None
        if not line_resp.approver_position:
            line_resp.approver_position = approver.position if approver else None
        if line.status == "APPROVED" and line.acted_at:
            seal_name = line.approver_name or (approver.name if approver else "")
            line_resp.seal_svg = seal_service.make_seal_svg(
                seal_name, line.acted_at.strftime("%Y-%m-%d")
            )

    # actions actor_name 주입
    for act_resp, act in zip(resp.actions, doc.actions):
        act_resp.actor_name = act.actor.name if act.actor else None
        act_resp.ip_address = None  # 일반 응답에는 IP 미노출 (ADMIN 전용 엔드포인트에서만)

    return resp


def _serialize_list_item(doc, actor: Optional[User] = None) -> ApprovalDocumentListItem:
    item = ApprovalDocumentListItem.model_validate(doc)
    item.drafter_name = doc.drafter.name if doc.drafter else None
    # 양식 종류 / 프로젝트 (필터·표시용)
    form = getattr(doc, "form", None)
    if form is not None:
        item.form_code = form.code
        item.form_name = form.name
    project = getattr(doc, "project", None)
    if project is not None:
        item.project_name = f"[{project.code}] {project.name}" if project.code else project.name
    # 현재 결재자
    current = next((ln for ln in doc.lines if ln.step_order == doc.current_step), None)
    if current and current.approver:
        item.current_approver_name = current.approver.name
    # 조회자 기준 '내 차례' 여부 (결재대기함에서 조치 필요 건 구분)
    if actor is not None and current is not None:
        item.is_my_turn = (
            doc.status == "IN_PROGRESS"
            and current.status == "PENDING"
            and current.approver_id == actor.id
        )
    # 시행자 (purchase_category/execution_status 는 model → 스키마 자동)
    executor = getattr(doc, "executor", None)
    item.executor_name = executor.name if executor else None
    return item


# ==================== 고정 경로 (동적 /{id} 보다 먼저) ====================

@router.get("/pending-count")
def get_pending_count(
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """내 차례 결재 대기 건수."""
    try:
        return {"count": service.pending_count(actor)}
    except Exception as e:
        handle_service_exception(e)


@router.get("/linkable-trips", response_model=list[LinkableTripItem])
def get_linkable_trips(
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """정산서 작성 시 연결할 출장신청서 후보 (본인 기안 + APPROVED + TRIP)."""
    try:
        return [LinkableTripItem(**t) for t in service.list_linkable_trips(actor)]
    except Exception as e:
        handle_service_exception(e)


@router.get("/linkable-predecessors", response_model=list[LinkablePredecessorItem])
def get_linkable_predecessors(
    form_code: str = Query(..., description="작성하려는 사후(POST) 양식 code"),
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """사후(POST) 문서 작성 시 연결할 사전(PRE) 문서 후보.

    form_code 양식의 linked_form_code(=PRE code) 기준으로
    본인 기안 + APPROVED + 그 PRE 양식 문서를 반환한다.
    """
    try:
        return [
            LinkablePredecessorItem(**t)
            for t in service.list_linkable_predecessors(actor, form_code)
        ]
    except Exception as e:
        handle_service_exception(e)


@router.get("/calendar")
def get_calendar_events(
    date_from: Optional[str] = Query(None, description="조회 시작일 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="조회 종료일 YYYY-MM-DD"),
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """휴가/출장(TRIP/LEAVE) 일정 — 캘린더 표기용 (진행중/승인완료)."""
    try:
        return service.calendar_events(date_from=date_from, date_to=date_to)
    except Exception as e:
        handle_service_exception(e)


@router.get("/approvers")
def get_approver_candidates(
    keyword: Optional[str] = Query(None, description="이름/부서 검색어"),
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재자 선택용 사용자 후보 목록.

    기존 /users 는 ADMIN 전용이라 일반 기안자가 결재선을 지정할 수 없으므로,
    전자결재 모듈 내에 활성 사용자 최소 정보(id/name/position/department)를
    반환하는 비관리자 엔드포인트를 둔다(설계노트 8.2 / 사용자 목록 API 해결).
    """
    from app.models.user import User as UserModel
    q = service.db.query(UserModel).filter(UserModel.is_active == True)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((UserModel.name.ilike(like)) | (UserModel.department.ilike(like)))
    users = q.order_by(UserModel.name).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "position": u.position,
            "department": u.department,
        }
        for u in users
    ]


# ==================== 프로젝트 마스터 ====================

@router.get("/projects", response_model=list[ApprovalProjectResponse])
def list_projects(
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """활성 프로젝트 목록 (기안 시 선택용)."""
    try:
        return [ApprovalProjectResponse.model_validate(p) for p in service.list_projects(active_only=True)]
    except Exception as e:
        handle_service_exception(e)


# ==================== 프리폼 양식 ====================

@router.get("/forms", response_model=list[ApprovalFormResponse])
def list_forms(
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """활성 양식 목록(code, name, fields_schema)."""
    from app.models.approval import ApprovalForm
    forms = (
        service.db.query(ApprovalForm)
        .filter(ApprovalForm.is_active == True)
        .order_by(ApprovalForm.sort_order, ApprovalForm.id)
        .all()
    )
    return [ApprovalFormResponse.model_validate(f) for f in forms]


@router.get("/forms/{code}", response_model=ApprovalFormResponse)
def get_form(
    code: str,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """양식 단건 조회(code)."""
    from fastapi import HTTPException
    from app.models.approval import ApprovalForm
    form = service.db.query(ApprovalForm).filter(ApprovalForm.code == code).first()
    if not form:
        raise HTTPException(status_code=404, detail="양식을 찾을 수 없습니다")
    return ApprovalFormResponse.model_validate(form)


# ==================== 휴가 연차 잔여 ====================

@router.get("/leave-balance", response_model=LeaveBalanceResponse)
def get_leave_balance(
    user_id: Optional[int] = Query(None, description="대상 사용자(생략 시 본인). 타인 조회는 ADMIN만"),
    year: Optional[int] = Query(None, description="조회 연도(생략 시 올해)"),
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """연차 잔여 조회 {year, entitlement, used, remaining}."""
    from datetime import datetime as _dt
    try:
        target_id = user_id if user_id is not None else actor.id
        if target_id != actor.id and actor.role != "ADMIN":
            from app.core.exceptions import BusinessRuleException
            raise BusinessRuleException("타인의 연차는 관리자만 조회할 수 있습니다.", rule="LEAVE_VIEW_ADMIN")
        target_year = year if year is not None else _dt.now().year
        return leave_service.leave_balance(service.db, target_id, target_year)
    except Exception as e:
        handle_service_exception(e)


@router.get("/items-template.xlsx")
def items_template(actor: User = Depends(require_auth)):
    """구매기안서/지출결의서 품목 업로드용 엑셀 양식(품목명/수량/단가/거래처/비고)."""
    from io import BytesIO
    from openpyxl import Workbook
    from fastapi.responses import StreamingResponse
    wb = Workbook()
    ws = wb.active
    ws.title = "품목"
    ws.append(["품목명", "수량", "단가", "비고"])
    ws.append(["예) 스파이럴 탭 M1.6", 2, 65980, "견적서 첨부"])
    for i, w in enumerate([30, 8, 12, 24], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return StreamingResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=purchase_items_template.xlsx"},
    )


@router.post("/items-parse")
async def items_parse(file: UploadFile = File(...), actor: User = Depends(require_auth)):
    """업로드한 엑셀을 파싱해 품목 배열 반환. 헤더행(품목/품명 포함) 자동 스킵, 품목명 없는 행 무시."""
    from io import BytesIO
    from openpyxl import load_workbook
    try:
        data = await file.read()
        wb = load_workbook(BytesIO(data), data_only=True, read_only=True)
        ws = wb.active
    except Exception:
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx)을 읽을 수 없습니다")

    def _num(v):
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _s(v):
        return str(v).strip() if v is not None else ""

    rows = list(ws.iter_rows(values_only=True))
    start = 0
    if rows and any(isinstance(c, str) and ("품목" in c or "품명" in c) for c in rows[0] if c is not None):
        start = 1
    items = []
    for r in rows[start:]:
        if not r:
            continue
        name = _s(r[0]) if len(r) > 0 else ""
        if not name:
            continue
        items.append({
            "name": name,
            "qty": _num(r[1]) if len(r) > 1 else None,
            "unit_price": _num(r[2]) if len(r) > 2 else None,
            "note": _s(r[3]) if len(r) > 3 else "",
        })
    return {"items": items}


@router.get("", response_model=ApprovalListResponse)
@router.get("/", response_model=ApprovalListResponse, include_in_schema=False)
def get_box(
    box: BoxType = Query(..., description="drafted/pending/done/reference/execution (draft=하위호환)"),
    keyword: Optional[str] = Query(None),
    form_code: Optional[str] = Query(None, description="양식 종류 필터(form.code)"),
    project_id: Optional[int] = Query(None, description="프로젝트 필터"),
    category: Optional[str] = Query(None, description="구매 구분 필터(일반/과제/개발)"),
    execution_status: Optional[str] = Query(None, description="시행 상태 필터(PENDING/DONE)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재함 조회 (기안함/결재대기/완료함/시행함). form_code/project_id/category/시행상태 필터."""
    try:
        docs, total = service.get_box(
            box, actor, keyword=keyword, form_code=form_code,
            project_id=project_id, category=category, execution_status=execution_status,
            skip=skip, limit=limit,
        )
        items = [_serialize_list_item(d, actor) for d in docs]
        return ApprovalListResponse(items=items, total=total, skip=skip, limit=limit)
    except Exception as e:
        handle_service_exception(e)


# ==================== 생성 / 수정 ====================

@router.post("", response_model=ApprovalDocumentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ApprovalDocumentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_document(
    data: ApprovalDocumentCreate,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재 문서 임시저장(DRAFT) 생성."""
    try:
        doc = service.create_draft(data, actor)
        doc = service.get_detail(doc.id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


@router.put("/{id}", response_model=ApprovalDocumentResponse)
def update_document(
    id: int,
    data: ApprovalDocumentUpdate,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """DRAFT 문서 수정 (기안자만)."""
    try:
        service.update_draft(id, data, actor)
        doc = service.get_detail(id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


# ==================== 상태 전이 ====================

@router.post("/{id}/submit", response_model=ApprovalDocumentResponse)
def submit_document(
    id: int,
    request: Request,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """상신 (DRAFT→IN_PROGRESS)."""
    try:
        service.submit(id, actor, _get_client_ip(request))
        doc = service.get_detail(id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


@router.post("/{id}/approve", response_model=ApprovalDocumentResponse)
def approve_document(
    id: int,
    req: ApprovalActionRequest,
    request: Request,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """승인 (차례+본인)."""
    try:
        service.approve(id, req, actor, _get_client_ip(request))
        doc = service.get_detail(id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


@router.post("/{id}/reject", response_model=ApprovalDocumentResponse)
def reject_document(
    id: int,
    req: ApprovalActionRequest,
    request: Request,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """반려 (comment 필수, 즉시 종료)."""
    try:
        service.reject(id, req, actor, _get_client_ip(request))
        doc = service.get_detail(id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    id: int,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재 문서 소프트 삭제. 관리자는 상태 무관(승인 완료건 포함), 일반 사용자는
    본인이 작성한 임시저장(DRAFT) 문서만 삭제 가능. 목록/집계에서 제외, 감사용 보존."""
    try:
        service.soft_delete(id, actor)
    except Exception as e:
        handle_service_exception(e)


@router.post("/{id}/cancel", response_model=ApprovalDocumentResponse)
def cancel_document(
    id: int,
    request: Request,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """회수 (1차 결재자 처리 전, 기안자만)."""
    try:
        service.cancel(id, actor, _get_client_ip(request))
        doc = service.get_detail(id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


@router.post("/{id}/resubmit", response_model=ApprovalDocumentResponse)
def resubmit_document(
    id: int,
    request: Request,
    data: Optional[ApprovalDocumentUpdate] = None,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """재상신 (REJECTED 문서, 기안자만)."""
    try:
        service.resubmit(id, data, actor, _get_client_ip(request))
        doc = service.get_detail(id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


@router.post("/{id}/execute", response_model=ApprovalDocumentResponse)
def execute_document(
    id: int,
    request: Request,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """시행 완료 (승인완료+시행전 문서, 지정된 시행자만)."""
    try:
        service.execute(id, actor, _get_client_ip(request))
        doc = service.get_detail(id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


# ==================== 상세 조회 ====================

@router.get("/{id}", response_model=ApprovalDocumentResponse)
def get_document(
    id: int,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재 문서 상세 (열람권한 검증)."""
    try:
        doc = service.get_detail(id, actor)
        return _serialize_detail(doc, service, actor)
    except Exception as e:
        handle_service_exception(e)


# ==================== 첨부파일 ====================

def _get_attachment_service(service: ApprovalService = Depends(get_approval_service)) -> ApprovalAttachmentService:
    return ApprovalAttachmentService(service.db)


@router.post("/{id}/attachments", response_model=ApprovalAttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    id: int,
    file: UploadFile = File(...),
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
    att_service: ApprovalAttachmentService = Depends(_get_attachment_service),
):
    """첨부 업로드 (기안자 & DRAFT/IN_PROGRESS 단계)."""
    try:
        service.get_detail(id, actor)  # 열람권한 검증
        content = await file.read()
        att = att_service.save(id, file.filename, content, file.content_type, actor)
        return ApprovalAttachmentResponse.model_validate(att)
    except Exception as e:
        handle_service_exception(e)


@router.get("/{id}/attachments", response_model=list[ApprovalAttachmentResponse])
def list_attachments(
    id: int,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
    att_service: ApprovalAttachmentService = Depends(_get_attachment_service),
):
    """첨부 목록."""
    try:
        service.get_detail(id, actor)  # 열람권한 검증
        return [ApprovalAttachmentResponse.model_validate(a) for a in att_service.list(id)]
    except Exception as e:
        handle_service_exception(e)


@router.get("/{id}/attachments/{att_id}/download")
def download_attachment(
    id: int,
    att_id: int,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
    att_service: ApprovalAttachmentService = Depends(_get_attachment_service),
):
    """첨부 다운로드."""
    try:
        service.get_detail(id, actor)  # 열람권한 검증
        att = att_service.get(id, att_id)
        abs_path = att_service.abs_path(att)
        if not abs_path.exists():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
        return FileResponse(
            path=str(abs_path),
            media_type=att.content_type or "application/octet-stream",
            filename=att.original_name,
        )
    except Exception as e:
        handle_service_exception(e)


@router.delete("/{id}/attachments/{att_id}")
def delete_attachment(
    id: int,
    att_id: int,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
    att_service: ApprovalAttachmentService = Depends(_get_attachment_service),
):
    """첨부 삭제 (기안자 & DRAFT)."""
    try:
        service.get_detail(id, actor)  # 열람권한 검증
        att_service.delete(id, att_id, actor)
        return {"success": True, "message": "첨부파일이 삭제되었습니다"}
    except Exception as e:
        handle_service_exception(e)


# ==================== 결재 의견(댓글) ====================

def _serialize_comment(c, actor: User) -> ApprovalCommentResponse:
    return ApprovalCommentResponse(
        id=c.id,
        user_id=c.user_id,
        user_name=(c.user.name if c.user else None),
        content=c.content,
        created_at=c.created_at,
        can_delete=(actor.role == "ADMIN" or c.user_id == actor.id),
    )


@router.get("/{id}/comments", response_model=list[ApprovalCommentResponse])
def list_comments(
    id: int,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재 의견 목록 (열람 권한자만)."""
    try:
        comments = service.list_comments(id, actor)
        return [_serialize_comment(c, actor) for c in comments]
    except Exception as e:
        handle_service_exception(e)


@router.post("/{id}/comments", response_model=ApprovalCommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    id: int,
    req: ApprovalCommentCreate,
    request: Request,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재 의견 작성 (열람 권한자만). 작성 시 문서 연관자에게 알림."""
    try:
        c = service.add_comment(id, req.content, actor, _get_client_ip(request))
        return _serialize_comment(c, actor)
    except Exception as e:
        handle_service_exception(e)


@router.delete("/{id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    id: int,
    comment_id: int,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재 의견 삭제 (본인 또는 ADMIN)."""
    try:
        service.delete_comment(id, comment_id, actor)
    except Exception as e:
        handle_service_exception(e)


# ==================== 출력 (인쇄 HTML / PDF) ====================

@router.get("/{id}/print")
def print_document(
    id: int,
    include_history: bool = Query(True, description="처리 이력(상신/승인 일시) 출력 여부"),
    include_references: bool = Query(True, description="참조자 출력 여부"),
    include_print_date: bool = Query(True, description="출력일 표시 여부"),
    include_attachments: bool = Query(True, description="첨부파일 출력 여부(이미지는 본문에 포함)"),
    include_doc_number: bool = Query(True, description="문서번호/검증번호 표시 여부(메타표+푸터)"),
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """인쇄용 HTML 반환 (열람권한 검증 + @media print)."""
    try:
        doc = service.get_detail(id, actor)
        from app.services import approval_print_service
        html = approval_print_service.render_html(
            doc,
            show_history=include_history,
            show_references=include_references,
            show_print_date=include_print_date,
            show_attachments=include_attachments,
            show_doc_number=include_doc_number,
        )
        return HTMLResponse(content=html)
    except Exception as e:
        handle_service_exception(e)


@router.get("/{id}/pdf")
def download_pdf(
    id: int,
    include_history: bool = Query(True, description="처리 이력 출력 여부"),
    include_references: bool = Query(True, description="참조자 출력 여부"),
    include_print_date: bool = Query(True, description="출력일 표시 여부"),
    include_attachments: bool = Query(True, description="첨부파일 출력 여부"),
    include_doc_number: bool = Query(True, description="문서번호/검증번호 표시 여부"),
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """PDF 다운로드. GTK 미설치 환경에서는 503 + 인쇄(HTML) 안내."""
    try:
        doc = service.get_detail(id, actor)  # 열람권한 검증
        from app.services import approval_print_service
        html = approval_print_service.render_html(
            doc,
            show_history=include_history,
            show_references=include_references,
            show_print_date=include_print_date,
            show_attachments=include_attachments,
            show_doc_number=include_doc_number,
        )
        try:
            import weasyprint  # lazy import — GTK 런타임 필요
        except Exception:
            return Response(
                content="PDF 생성을 위한 GTK 런타임 미설치 — 인쇄(HTML)를 이용하세요.",
                media_type="text/plain; charset=utf-8",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            pdf_bytes = weasyprint.HTML(
                string=html,
                base_url=str(approval_print_service.TEMPLATE_DIR),
            ).write_pdf()
        except Exception:
            return Response(
                content="PDF 생성을 위한 GTK 런타임 미설치 — 인쇄(HTML)를 이용하세요.",
                media_type="text/plain; charset=utf-8",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        # 파일명: '기안서종류 - 제목' (파일명 금지문자 정리)
        import re as _re
        from urllib.parse import quote as _quote
        _form_name = (doc.form.name if getattr(doc, "form", None) else "기안서")
        _raw_name = f"{_form_name} - {doc.title or ''}".strip()
        _safe = _re.sub(r'[\\/:*?"<>|]+', " ", _raw_name).strip() or (doc.doc_number or "document")
        _fallback = (doc.doc_number or "document")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'inline; filename="{_fallback}.pdf"; '
                    f"filename*=UTF-8''{_quote(_safe + '.pdf')}"
                )
            },
        )
    except Exception as e:
        handle_service_exception(e)


# ==================== 도장 SVG ====================

@seal_router.get("/seal/{user_id}.svg")
def get_user_seal(
    user_id: int,
    actor: User = Depends(require_auth),
    service: ApprovalService = Depends(get_approval_service),
):
    """사용자 자동 도장 SVG (날짜 미지정 — 미리보기용)."""
    from app.models.user import User as UserModel
    user = service.db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    name = user.seal_text or user.name or ""
    svg = seal_service.make_seal_svg(name, "")
    return Response(content=svg, media_type="image/svg+xml")


# ==================== 관리자: 디폴트 결재자 ====================

@admin_router.get("/users/{id}/default-approver")
def get_default_approver(
    id: int,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """사용자 디폴트 결재자 조회."""
    from app.models.user import User as UserModel
    user = service.db.query(UserModel).filter(UserModel.id == id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    approver = None
    if user.approver_id:
        approver = service.db.query(UserModel).filter(UserModel.id == user.approver_id).first()
    return {
        "approver_id": user.approver_id,
        "approver_name": approver.name if approver else None,
    }


@admin_router.put("/users/{id}/default-approver")
def set_default_approver(
    id: int,
    data: DefaultApproverUpdate,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """사용자 디폴트 결재자 설정."""
    from fastapi import HTTPException
    from app.models.user import User as UserModel
    user = service.db.query(UserModel).filter(UserModel.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    user.approver_id = data.approver_id
    service.db.commit()
    service.db.refresh(user)
    approver = None
    if user.approver_id:
        approver = service.db.query(UserModel).filter(UserModel.id == user.approver_id).first()
    return {
        "approver_id": user.approver_id,
        "approver_name": approver.name if approver else None,
    }


# ==================== 관리자: 감사 이력 / 정정 ====================

@admin_router.get("/approvals/{id}/actions")
def get_actions_admin(
    id: int,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """결재 행위 원본 이력 (ip 포함, ADMIN 전용)."""
    doc = service.get_detail(id, admin)
    return [
        {
            "id": act.id,
            "actor_id": act.actor_id,
            "actor_name": act.actor.name if act.actor else None,
            "action": act.action,
            "comment": act.comment,
            "acted_at": act.acted_at,
            "ip_address": act.ip_address,
        }
        for act in doc.actions
    ]


@admin_router.put("/approvals/{id}/actions/{action_id}", response_model=ApprovalCorrectionResponse)
def correct_action_admin(
    id: int,
    action_id: int,
    req: CorrectionRequest,
    request: Request,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """관리자 사후 정정 (corrections INSERT + is_corrected=True).

    원본 actions 를 직접 삭제하지 않으며, 정정 이력으로만 기록한다.
    """
    try:
        correction = service.admin_correct(id, req, admin, _get_client_ip(request))
        return ApprovalCorrectionResponse.model_validate(correction)
    except Exception as e:
        handle_service_exception(e)


@admin_router.put("/approvals/{id}/dates", response_model=ApprovalDocumentResponse)
def admin_edit_dates(
    id: int,
    req: AdminDatesUpdate,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """관리자 전용: 시행일자(executed_at) / 결제·집행일(form_data.exec_date) 사후 수정.
    이력·정정표시를 남기지 않는 무흔적 수정."""
    try:
        service.admin_edit_dates(id, req.executed_at, req.exec_date)
        doc = service.get_detail(id, admin)
        return _serialize_detail(doc, service, admin)
    except Exception as e:
        handle_service_exception(e)


@admin_router.get("/approvals", response_model=ApprovalListResponse)
def search_approvals_admin(
    keyword: Optional[str] = Query(None, description="제목/문서번호 검색"),
    status: Optional[str] = Query(None, description="상태(DRAFT/IN_PROGRESS/APPROVED/REJECTED/CANCELED)"),
    drafter_id: Optional[int] = Query(None, description="기안자 ID"),
    date_from: Optional[str] = Query(None, description="생성일 시작(YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="생성일 종료(YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """[관리자] 전체 결재 문서 검색 (모든 사용자/상태)."""
    try:
        docs, total = service.search_all(
            keyword=keyword, status=status, drafter_id=drafter_id,
            date_from=date_from, date_to=date_to, skip=skip, limit=limit,
        )
        items = [_serialize_list_item(d) for d in docs]
        return ApprovalListResponse(items=items, total=total, skip=skip, limit=limit)
    except Exception as e:
        handle_service_exception(e)


@admin_router.put("/approvals/{id}/correct", response_model=ApprovalCorrectionResponse)
def correct_document_admin(
    id: int,
    req: CorrectionRequest,
    request: Request,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """[관리자] 결재 문서/결재선/이력의 오류(날짜·내용 등) 정정.

    원본을 덮어쓰되 변경분을 approval_corrections 에 기록하고 is_corrected 표식을 남긴다.
    정정 가능 필드: documents(title/content/drafted_at/completed_at),
    lines(comment/acted_at/approver_name/approver_position), actions(comment/acted_at).
    """
    try:
        correction = service.admin_correct(id, req, admin, _get_client_ip(request))
        return ApprovalCorrectionResponse.model_validate(correction)
    except Exception as e:
        handle_service_exception(e)


@admin_router.put("/approvals/{id}/full-edit", response_model=ApprovalDocumentResponse)
def full_edit_document_admin(
    id: int,
    req: AdminFullEditRequest,
    request: Request,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """[관리자] 결재 문서 전체 정정 — 작성 폼으로 제목·본문·품목표(form_data)·거래처·사유 등
    문서 내용 전체를 교체. 상태·결재선(승인/도장)은 보존하고, 변경 전/후를 정정 이력에 기록."""
    try:
        service.admin_full_update(id, req, req.reason, admin, _get_client_ip(request))
        doc = service.get_detail(id, admin)
        return _serialize_detail(doc, service, admin)
    except Exception as e:
        handle_service_exception(e)


@admin_router.get("/approvals/{id}/corrections", response_model=list[ApprovalCorrectionResponse])
def list_corrections_admin(
    id: int,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """[관리자] 문서 정정 이력 목록."""
    try:
        return [ApprovalCorrectionResponse.model_validate(c) for c in service.get_corrections(id)]
    except Exception as e:
        handle_service_exception(e)


# ==================== 관리자: 프로젝트 마스터 ====================

@admin_router.get("/projects", response_model=list[ApprovalProjectResponse])
def list_projects_admin(
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """[관리자] 전체 프로젝트 목록(비활성 포함)."""
    try:
        return [
            ApprovalProjectResponse.model_validate(p)
            for p in service.list_projects(active_only=False)
        ]
    except Exception as e:
        handle_service_exception(e)


@admin_router.post("/projects", response_model=ApprovalProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_admin(
    data: ApprovalProjectCreate,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """[관리자] 프로젝트 생성."""
    try:
        return ApprovalProjectResponse.model_validate(service.create_project(data))
    except Exception as e:
        handle_service_exception(e)


@admin_router.put("/projects/{id}", response_model=ApprovalProjectResponse)
def update_project_admin(
    id: int,
    data: ApprovalProjectUpdate,
    admin: User = Depends(require_admin),
    service: ApprovalService = Depends(get_approval_service),
):
    """[관리자] 프로젝트 수정(name/is_active/sort_order)."""
    try:
        return ApprovalProjectResponse.model_validate(service.update_project(id, data))
    except Exception as e:
        handle_service_exception(e)
