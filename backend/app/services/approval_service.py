"""
전자결재 서비스 (v0.33.0)

설계노트 4장. BaseService 비상속(메서드마다 commit 하는 BaseService 가 다중 테이블
원자성을 깨므로). 상태전이 메서드는 여러 row 변경 후 단일 self.db.commit(),
예외 시 self.db.rollback() 후 도메인 예외 재발생.

동시성: 상태전이 시 대상 문서 with_for_update() 잠금 + current_step 재검증.
"""

import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from sqlalchemy import DateTime as SADateTime, or_

from app.core.exceptions import (
    BusinessRuleException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)

# 한국 표준시(KST, UTC+9). 사용자가 화면에서 입력한 날짜/시각은 KST 벽시계 값이므로,
# tzinfo 없는 입력은 UTC가 아니라 KST로 해석해야 한다(안 그러면 표시 시 +9시간 어긋남).
_KST = timezone(timedelta(hours=9))

# 관리자가 사후 정정할 수 있는 필드 화이트리스트 (감사 무결성: 상태/ID 등은 정정 불가)
_CORRECTABLE_FIELDS = {
    "documents": {"title", "content", "drafted_at", "completed_at"},
    "lines": {"comment", "acted_at", "approver_name", "approver_position"},
    "actions": {"comment", "acted_at"},
}
from app.models.approval import (
    ApprovalAction,
    ApprovalAttachment,
    ApprovalCorrection,
    ApprovalDocument,
    ApprovalForm,
    ApprovalLine,
    ApprovalReference,
)
from app.models.project import Project
from app.models.user import User
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalDocumentCreate,
    ApprovalDocumentUpdate,
    BoxType,
    CorrectionRequest,
)
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services import seal_service
from app.services.project_service import ProjectService

# 상태 상수
STATUS_DRAFT = "DRAFT"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_CANCELED = "CANCELED"

LINE_WAITING = "WAITING"
LINE_PENDING = "PENDING"
LINE_APPROVED = "APPROVED"
LINE_REJECTED = "REJECTED"

DONE_STATUSES = (STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELED)

_DOC_NUMBER_MAX_RETRY = 5


class ApprovalService:
    """전자결재 서비스 (BaseService 비상속, 자체 트랜잭션 경계)."""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 내부 유틸 ====================

    @staticmethod
    def _now() -> datetime:
        """결재 기록 시각. **분 단위까지만** 남긴다(초/마이크로초 절사).

        문서 표시·인쇄는 모두 분 단위이므로 초까지 저장할 이유가 없고,
        저장값과 표시값의 정밀도를 일치시켜 시각 비교·정정 시 초 단위
        잔차로 불일치가 생기는 것을 막는다.
        """
        return datetime.now(timezone.utc).replace(second=0, microsecond=0)

    @staticmethod
    def _content_hash(content: Optional[str]) -> str:
        return hashlib.sha256((content or "").encode("utf-8")).hexdigest()

    @staticmethod
    def _verify_code(doc_number: str, content: Optional[str]) -> str:
        raw = (doc_number or "") + (content or "")
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:4].upper()

    # 문서번호 양식별 접두어 (양식코드 → 접두어). 미지정/일반 = AP
    _DOC_PREFIX = {
        "FREE": "AP",            # 일반 기안
        "PURCHASE": "PR",        # 구매 신청
        "MEETING_PLAN": "MA",    # 회의 안건서
        "MEETING": "MM",         # 회의록
        "TRIP": "TR",            # 출장 신청
        "EXPENSE": "TE",         # 출장 정산
        "LEAVE": "LV",           # 휴가
        "LEAVE_CANCEL": "LC",    # 휴가 취소 v0.56.0
        "MEETING_EXPENSE": "ME",  # 회의비 정산
        "DISBURSEMENT": "PE",    # 지출결의(구매 집행) v0.46.0
    }

    def _next_doc_number(self, form_code: Optional[str] = None) -> str:
        """문서번호 채번: {접두어}-{YYYY}-{NNNN} (접두어+연도별 연번 max+1).

        접두어는 양식별(_DOC_PREFIX), 미지정/일반은 'AP'. UNIQUE + IntegrityError 재시도와 병행.
        """
        year = self._now().strftime("%Y")
        code = (form_code or "").upper()
        prefix_code = self._DOC_PREFIX.get(code, "AP")
        prefix = f"{prefix_code}-{year}-"
        # 연번(마지막 세그먼트)을 숫자로 정렬 — 문자열 정렬은 9999→10000 경계에서 뒤집힘
        from sqlalchemy import func, cast, Integer
        last = (
            self.db.query(ApprovalDocument)
            .filter(ApprovalDocument.doc_number.like(f"{prefix}%"))
            .order_by(cast(func.split_part(ApprovalDocument.doc_number, "-", 3), Integer).desc())
            .first()
        )
        seq = 1
        if last and last.doc_number:
            try:
                seq = int(last.doc_number.split("-")[-1]) + 1
            except (IndexError, ValueError):
                seq = 1
        return f"{prefix}{seq:04d}"

    @staticmethod
    def _validate_lines_sequence(lines: List) -> None:
        """step_order 1..n 연속 검증."""
        if not lines:
            return
        orders = sorted(line.step_order for line in lines)
        expected = list(range(1, len(orders) + 1))
        if orders != expected:
            raise ValidationException(
                "결재선 순서(step_order)는 1부터 연속이어야 합니다.",
                field="lines",
            )

    def _get_locked(self, doc_id: int) -> ApprovalDocument:
        """상태전이용 — 대상 문서 with_for_update() 잠금. 소프트 삭제건은 없는 것으로 취급."""
        doc = (
            self.db.query(ApprovalDocument)
            .filter(ApprovalDocument.id == doc_id)
            .with_for_update()
            .first()
        )
        if not doc or doc.is_deleted:
            raise NotFoundException("결재 문서", doc_id)
        return doc

    @staticmethod
    def _current_line(doc: ApprovalDocument) -> Optional[ApprovalLine]:
        for line in doc.lines:
            if line.step_order == doc.current_step:
                return line
        return None

    def _replace_references(self, doc: ApprovalDocument, reference_ids: Optional[List[int]]) -> None:
        """참조자 전체 교체. None 이면 변경하지 않음."""
        if reference_ids is None:
            return
        # 중복 제거 + 기안자/순서 유지
        seen = set()
        unique_ids: List[int] = []
        for uid in reference_ids:
            if uid not in seen:
                seen.add(uid)
                unique_ids.append(uid)
        doc.references.clear()
        self.db.flush()
        for uid in unique_ids:
            doc.references.append(ApprovalReference(user_id=uid))

    def _resolve_related_document_id(self, related_document_id: Optional[int]) -> Optional[int]:
        """관련 문서 연결 검증 — 존재하지 않으면 관대하게 무시(None 반환)."""
        if related_document_id is None:
            return None
        exists = (
            self.db.query(ApprovalDocument.id)
            .filter(ApprovalDocument.id == related_document_id)
            .first()
        )
        return related_document_id if exists else None

    def _resolve_related_ids(self, single: Optional[int], multi: Optional[List[int]]) -> List[int]:
        """단일/다중 입력을 합쳐 존재하는 문서 id만 순서 보존·중복 제거하여 반환."""
        raw: List[int] = []
        if multi:
            raw.extend(multi)
        if single is not None:
            raw.append(single)
        seen, ordered = set(), []
        for i in raw:
            if i is None or i in seen:
                continue
            seen.add(i)
            ordered.append(i)
        if not ordered:
            return []
        existing = {
            r[0] for r in self.db.query(ApprovalDocument.id)
            .filter(ApprovalDocument.id.in_(ordered)).all()
        }
        return [i for i in ordered if i in existing]

    def _get_form(self, form_id: Optional[int]) -> Optional[ApprovalForm]:
        if form_id is None:
            return None
        return self.db.query(ApprovalForm).filter(ApprovalForm.id == form_id).first()

    def _validate_required_form_data(self, doc: ApprovalDocument) -> None:
        """submit 시 양식 required 필드 누락 검증(백엔드 최소검증)."""
        form = self._get_form(doc.form_id)
        if not form or not form.fields_schema:
            return
        data = doc.form_data or {}
        missing: List[str] = []
        for field in form.fields_schema:
            if not isinstance(field, dict):
                continue
            if field.get("required"):
                key = field.get("key")
                # 품목이 자유형식(FREE) 모드면 items 배열 대신 items_free(텍스트)로 충족 판단
                if key == "items" and data.get("items_mode") == "FREE":
                    if not str(data.get("items_free") or "").strip():
                        missing.append(field.get("label") or key or "?")
                    continue
                val = data.get(key) if key else None
                if (
                    val is None
                    or (isinstance(val, str) and not val.strip())
                    or (isinstance(val, (list, dict)) and len(val) == 0)  # 빈 표/목록도 누락 처리
                ):
                    missing.append(field.get("label") or key or "?")
        # 구매기안서: 구매 구분(일반/과제/개발) 필수 — 과제 여부로 RCMS 항목·세부항목 필수 여부가 갈림
        if form.code == "PURCHASE" and not (doc.purchase_category or "").strip():
            missing.append("구매 구분")
        # 과제 구매기안서: RCMS 항목·세부항목 필수 (양식 스키마 밖 필드 — 구매 구분이 '과제'일 때만)
        if form.code == "PURCHASE" and (doc.purchase_category or "") == "과제":
            for key, label in (("budget_item", "항목"), ("budget_detail", "세부항목")):
                if not str(data.get(key) or "").strip():
                    missing.append(label)
        if missing:
            raise ValidationException(
                f"필수 입력 항목이 누락되었습니다: {', '.join(missing)}",
                field="form_data",
            )

    # 지출결의서(지급 집행)는 구매기안서 외에 지출성 문서(출장정산서·회의비정산서)에서도 파생 가능
    DISBURSEMENT_PRE_CODES = ["PURCHASE", "EXPENSE", "MEETING_EXPENSE"]

    def _accepted_pre_codes(self, form: "ApprovalForm") -> List[str]:
        """POST 양식이 선행문서로 인정하는 PRE 양식 코드 목록.

        기본은 linked_form_code 단일. 단, 지출결의서는 지출성 문서 여러 종류를 인정.
        """
        if not form or not form.linked_form_code:
            return []
        if form.code == "DISBURSEMENT":
            return list(self.DISBURSEMENT_PRE_CODES)
        return [form.linked_form_code]

    def _validate_phase_link(self, doc: ApprovalDocument) -> None:
        """submit 시 단계형 연계 검증.

        문서 양식이 POST 면 related_document_id 가 반드시 있어야 하고, 그 대상이
        status=APPROVED 이며 form.code 가 이 문서 form 의 인정 선행코드 중 하나여야 한다.
        (PRE/NONE 양식은 검증 없음. 임시저장 단계에선 막지 않고 submit 에서만 검증.)
        """
        form = self._get_form(doc.form_id)
        if not form or form.phase != "POST":
            return
        pre_codes = self._accepted_pre_codes(form)
        # 짝 PRE code 미지정이면 강제 연결 검증 불가 — 통과
        if not pre_codes:
            return
        pre_forms = (
            self.db.query(ApprovalForm).filter(ApprovalForm.code.in_(pre_codes)).all()
        )
        pre_name = " / ".join(pf.name for pf in pre_forms) if pre_forms else ", ".join(pre_codes)

        # 다중 연결 지원: 관련 문서 중 하나 이상이 승인완료 + 짝 PRE 코드면 통과
        rel_ids = list(doc.related_document_ids or [])
        if not rel_ids and doc.related_document_id is not None:
            rel_ids = [doc.related_document_id]

        # 선행문서 미연결이면 시스템상 상신 통과 — 선행문서 존재 여부는
        # 최종 결재자가 판단(없으면 반려). 시스템 강제는 하지 않음.
        if not rel_ids:
            return

        # 연결한 경우엔 그 문서가 승인완료 + 짝 PRE 코드인지 검증
        ok = False
        relateds = (
            self.db.query(ApprovalDocument)
            .options(joinedload(ApprovalDocument.form))
            .filter(ApprovalDocument.id.in_(rel_ids))
            .all()
        )
        for r in relateds:
            rf = getattr(r, "form", None)
            if r.status == STATUS_APPROVED and rf is not None and rf.code in pre_codes:
                ok = True
                break
        if not ok:
            raise ValidationException(
                f"연결한 문서가 승인 완료된 {pre_name}가 아닙니다. "
                f"연결을 해제하거나 승인 완료된 {pre_name}를 연결하세요.",
                field="related_document_id",
            )

    def _fill_leave_days(self, doc: ApprovalDocument) -> None:
        """LEAVE 양식이면 form_data['days'] 가 없을 때 start/end 로 계산해 채움."""
        form = self._get_form(doc.form_id)
        if not form or form.code != "LEAVE":
            return
        data = dict(doc.form_data or {})
        if data.get("days") not in (None, "", 0):
            return
        from app.services import leave_service
        days = leave_service.compute_leave_days(
            data.get("leave_type"), data.get("start_date"), data.get("end_date")
        )
        if days is not None:
            data["days"] = days
            doc.form_data = data

    # ==================== 쓰기: 상태전이 ====================

    def create_draft(self, data: ApprovalDocumentCreate, actor: User) -> ApprovalDocument:
        """DRAFT 생성 + doc_number 채번. 단일 commit (IntegrityError 재시도)."""
        last_err: Optional[Exception] = None
        _form = self._get_form(data.form_id)
        _form_code = _form.code if _form else None
        for _ in range(_DOC_NUMBER_MAX_RETRY):
            try:
                self._validate_lines_sequence(data.lines)
                doc = ApprovalDocument(
                    doc_number=self._next_doc_number(_form_code),
                    form_id=data.form_id,
                    form_data=data.form_data,
                    title=data.title,
                    content=data.content,
                    status=STATUS_DRAFT,
                    current_step=0,
                    drafter_id=actor.id,
                    project_id=data.project_id,
                    purchase_category=data.purchase_category,
                    executor_id=data.executor_id,
                )
                _rel_ids = self._resolve_related_ids(data.related_document_id, data.related_document_ids)
                doc.related_document_ids = _rel_ids or None
                doc.related_document_id = _rel_ids[0] if _rel_ids else None
                self.db.add(doc)
                self.db.flush()

                for line_in in data.lines:
                    self.db.add(ApprovalLine(
                        document_id=doc.id,
                        step_order=line_in.step_order,
                        approver_id=line_in.approver_id,
                        status=LINE_WAITING,
                    ))

                self._replace_references(doc, data.reference_ids)

                self.db.commit()
                self.db.refresh(doc)
                return doc
            except IntegrityError as e:
                self.db.rollback()
                last_err = e
                continue
            except Exception:
                self.db.rollback()
                raise
        raise BusinessRuleException(
            "문서번호 채번에 실패했습니다. 다시 시도해주세요.",
            rule="DOC_NUMBER_GENERATION",
        )

    def update_draft(self, doc_id: int, data: ApprovalDocumentUpdate, actor: User) -> ApprovalDocument:
        """승인 전까지 기안자 수정 허용: DRAFT, 또는 진행중(IN_PROGRESS)이면서 아직 아무도 승인하지 않은 경우.
        actor==drafter. lines 전체 교체. 진행중 문서는 수정 후에도 진행중 유지(1차부터 재시작). 단일 commit."""
        try:
            doc = self._get_locked(doc_id)
            approved_exists = any(l.status == LINE_APPROVED for l in doc.lines)
            editable = doc.status == STATUS_DRAFT or (doc.status == STATUS_IN_PROGRESS and not approved_exists)
            if not editable:
                raise BusinessRuleException(
                    "승인 전(결재 진행 중이며 아무도 승인하지 않은 상태)까지만 수정할 수 있습니다. 이미 결재가 진행된 경우 회수 후 수정하세요.",
                    rule="UPDATE_BEFORE_APPROVAL_ONLY")
            if doc.drafter_id != actor.id:
                raise BusinessRuleException("기안자만 수정할 수 있습니다.", rule="DRAFTER_ONLY")

            if data.title is not None:
                doc.title = data.title
            if data.content is not None:
                doc.content = data.content
            if data.form_id is not None:
                doc.form_id = data.form_id
            if data.form_data is not None:
                doc.form_data = data.form_data
            # 관련 문서: 단일/다중 중 하나라도 오면 전체 교체(다중 우선)
            if data.related_document_ids is not None or data.related_document_id is not None:
                _rel_ids = self._resolve_related_ids(data.related_document_id, data.related_document_ids)
                doc.related_document_ids = _rel_ids or None
                doc.related_document_id = _rel_ids[0] if _rel_ids else None
            if data.project_id is not None:
                doc.project_id = data.project_id
            if data.purchase_category is not None:
                doc.purchase_category = data.purchase_category or None
            if data.executor_id is not None:
                doc.executor_id = data.executor_id or None

            if data.lines is not None:
                self._validate_lines_sequence(data.lines)
                # 전체 교체 (delete-orphan)
                doc.lines.clear()
                self.db.flush()
                for line_in in data.lines:
                    doc.lines.append(ApprovalLine(
                        step_order=line_in.step_order,
                        approver_id=line_in.approver_id,
                        status=LINE_WAITING,
                    ))

            self._replace_references(doc, data.reference_ids)

            # 진행중 문서를 수정한 경우: 결재선을 1차부터 다시(아직 승인 전이므로 안전)
            if doc.status == STATUS_IN_PROGRESS:
                doc.current_step = 1
                for line in doc.lines:
                    line.status = LINE_PENDING if line.step_order == 1 else LINE_WAITING

            self.db.commit()
            self.db.refresh(doc)
            return doc
        except Exception:
            self.db.rollback()
            raise

    def _dispatch_notifications(self, fn) -> None:
        """인앱 알림 발송(best-effort). 본 액션 commit 이후 호출 — 실패해도 액션은 유지."""
        import logging
        from app.services.notification_service import NotificationService
        try:
            fn(NotificationService(self.db))
            self.db.commit()
        except Exception:
            self.db.rollback()
            logging.getLogger(__name__).exception("알림 발송 실패(무시): doc 처리는 정상 완료됨")

    @staticmethod
    def _require_disbursement_executor(doc: ApprovalDocument) -> None:
        """지출결의서는 시행자(집행 담당)를 반드시 지정해야 상신/재상신 가능."""
        if doc.form and doc.form.code == "DISBURSEMENT" and not doc.executor_id:
            raise ValidationException(
                "지출결의서는 시행자(집행 담당)를 지정해야 상신할 수 있습니다.",
                field="executor_id",
            )

    def submit(self, doc_id: int, actor: User, ip: Optional[str]) -> ApprovalDocument:
        """DRAFT→IN_PROGRESS. actor==drafter. lines>=1. 단일 commit."""
        try:
            doc = self._get_locked(doc_id)
            if doc.status != STATUS_DRAFT:
                raise BusinessRuleException("임시저장(DRAFT) 상태에서만 상신할 수 있습니다.", rule="SUBMIT_DRAFT_ONLY")
            if doc.drafter_id != actor.id:
                raise BusinessRuleException("기안자만 상신할 수 있습니다.", rule="DRAFTER_ONLY")
            if not doc.lines:
                raise ValidationException("결재선이 1명 이상 지정되어야 합니다.", field="lines")

            self._validate_lines_sequence(doc.lines)
            self._validate_required_form_data(doc)
            self._validate_phase_link(doc)
            self._require_disbursement_executor(doc)
            self._fill_leave_days(doc)

            doc.status = STATUS_IN_PROGRESS
            doc.current_step = 1
            # 최초 상신 때만 기안일자 확정. 회수→재상신 시 원래 기안일자 유지(관리자 정정 제외).
            if doc.drafted_at is None:
                doc.drafted_at = self._now()
            doc.content_hash = self._content_hash(doc.content)

            for line in doc.lines:
                line.status = LINE_PENDING if line.step_order == 1 else LINE_WAITING

            self._record_action(doc, actor, "SUBMIT", None, ip)
            self.db.commit()
            self.db.refresh(doc)
            self._dispatch_notifications(lambda ns: ns.notify_approval_submitted(doc))
            return doc
        except Exception:
            self.db.rollback()
            raise

    def approve(self, doc_id: int, req: ApprovalActionRequest, actor: User, ip: Optional[str]) -> ApprovalDocument:
        """IN_PROGRESS만. 차례+본인 검증(ADMIN 예외 없음). 단일 commit."""
        try:
            doc = self._get_locked(doc_id)
            line = self._guard_turn(doc, actor)

            line.status = LINE_APPROVED
            line.acted_at = self._now()
            line.comment = req.comment
            self._snapshot_seal(line, actor)

            steps = [ln.step_order for ln in doc.lines]
            is_last = doc.current_step >= max(steps)
            if is_last:
                doc.status = STATUS_APPROVED
                doc.completed_at = self._now()
                # 지출결의서: 최종 승인 = 집행 완료 → 시행일(집행일) 기록 (v0.46.0)
                # 미입력 시 당일(승인일=집행일)로 기본 설정 (v0.46.1)
                if doc.form and doc.form.code == "DISBURSEMENT":
                    fd = dict(doc.form_data or {})
                    # 미입력 시 당일(KST 기준, completed_at 은 UTC라 +9h 보정)
                    kst_today = (doc.completed_at + timedelta(hours=9)).date().isoformat()
                    fd["exec_date"] = getattr(req, "exec_date", None) or kst_today
                    doc.form_data = fd
                    # 지출결의 최종 승인 = 집행 완료 → 연결된 발주서 대금지급 완료 처리
                    self._apply_disbursement_paid(doc, paid=True)
                # 시행자가 지정돼 있으면 → 시행 대기(시행전)로 전환
                if doc.executor_id:
                    doc.execution_status = "PENDING"
            else:
                doc.current_step += 1
                next_line = self._current_line(doc)
                if next_line:
                    next_line.status = LINE_PENDING

            self._record_action(doc, actor, "APPROVE", req.comment, ip)
            self.db.commit()
            self.db.refresh(doc)

            # 알림: 최종 승인이면 기안자에게, 아니면 다음 결재자에게
            def _notify_approve(ns):
                if doc.status == STATUS_APPROVED:
                    ns.notify_approval_approved(doc, actor.id)
                    # 시행자 지정 문서: 시행자에게 '시행하세요' 알림
                    if doc.executor_id and doc.execution_status == "PENDING":
                        ns.notify_execution_requested(doc, actor.id)
                else:
                    nxt = next((ln for ln in doc.lines if ln.step_order == doc.current_step), None)
                    if nxt:
                        ns.notify_approval_next(doc, nxt, actor.id)
            self._dispatch_notifications(_notify_approve)

            # 휴가취소(LEAVE_CANCEL) 최종 승인 → 원 휴가 USAGE 무효화(일수 복구). best-effort.
            if doc.status == STATUS_APPROVED and doc.form and doc.form.code == "LEAVE_CANCEL":
                self._void_canceled_leave(doc)
            # 출장정산서(EXPENSE) 최종 승인 + 개인카드 환급분 → 지출결의서 초안 자동생성. best-effort.
            if doc.status == STATUS_APPROVED and doc.form and doc.form.code == "EXPENSE":
                self._create_personal_disbursement(doc)
            # 구매기안서(PURCHASE) 최종 승인 + 발주서 자동생성 선택 → BOM 품목으로 발주서(DRAFT) 자동생성. best-effort.
            if doc.status == STATUS_APPROVED and doc.form and doc.form.code == "PURCHASE":
                self._create_purchase_order_from_approval(doc)
            return doc
        except Exception:
            self.db.rollback()
            raise

    def execute(self, doc_id: int, actor: User, ip: Optional[str]) -> ApprovalDocument:
        """시행 완료: 지정된 시행자만. 승인완료+시행전(PENDING)에서만. → 시행후(DONE)+시행일 기록."""
        try:
            doc = self._get_locked(doc_id)
            if not doc.executor_id or doc.executor_id != actor.id:
                raise BusinessRuleException("지정된 시행자만 시행 완료할 수 있습니다.", rule="EXECUTOR_ONLY")
            if doc.status != STATUS_APPROVED:
                raise BusinessRuleException("최종 승인된 문서만 시행할 수 있습니다.", rule="EXECUTE_APPROVED_ONLY")
            if doc.execution_status != "PENDING":
                raise BusinessRuleException("시행 대기(시행전) 상태에서만 시행 완료할 수 있습니다.", rule="EXECUTE_PENDING_ONLY")
            doc.execution_status = "DONE"
            doc.executed_at = self._now()
            self._record_action(doc, actor, "EXECUTE", None, ip)
            self.db.commit()
            self.db.refresh(doc)
            # 기안자에게 시행 완료 알림
            self._dispatch_notifications(lambda ns: ns.notify_execution_done(doc, actor.id))
            return doc
        except Exception:
            self.db.rollback()
            raise

    def _create_personal_disbursement(self, expense: ApprovalDocument) -> None:
        """출장정산서 최종 승인 시 개인카드 환급분으로 지출결의서 초안을 자동 생성·연결하고
        기안자에게 알림. best-effort — 실패해도 출장정산 승인은 유지."""
        import logging
        try:
            fd = expense.form_data or {}
            if not fd.get("has_personal"):
                return
            pe = [x for x in (fd.get("personal_expenses") or []) if x and (x.get("name") or x.get("amount"))]
            if not pe:
                return
            from app.models.approval import ApprovalForm
            disb_form = self.db.query(ApprovalForm).filter(ApprovalForm.code == "DISBURSEMENT").first()
            if not disb_form:
                return
            total = sum(float(x.get("amount") or 0) for x in pe)
            items = [{"name": x.get("name", ""), "qty": 1,
                      "unit_price": float(x.get("amount") or 0), "amount": float(x.get("amount") or 0)} for x in pe]
            acct = (fd.get("personal_account") or "").strip()
            drafter_name = expense.drafter.name if expense.drafter else ""
            note_parts = [f"출장정산서 {expense.doc_number} 개인카드 환급"]
            if acct:
                note_parts.append(f"입금계좌: {acct}")
            if fd.get("personal_note"):
                note_parts.append(str(fd["personal_note"]))
            new_doc = ApprovalDocument(
                doc_number=self._next_doc_number("DISBURSEMENT"),
                form_id=disb_form.id,
                form_data={
                    "vendor": (f"{drafter_name} (개인카드 환급)").strip(),
                    "items": items,
                    "amount": total,
                    "payment_method": fd.get("personal_payment_method") or "카드결제",
                    "request_note": "출장정산서 승인에 따른 개인카드 선지출 환급",
                    "note": " · ".join(note_parts),
                },
                title=f"[개인환급] {expense.title}",
                status=STATUS_DRAFT,
                current_step=0,
                drafter_id=expense.drafter_id,
                related_document_id=expense.id,
                related_document_ids=[expense.id],
            )
            self.db.add(new_doc)
            self.db.commit()
            self.db.refresh(new_doc)
            # 기안자에게 "초안 생성됨, 확인 후 상신" 알림
            try:
                from app.services.notification_service import NotificationService
                NotificationService(self.db).create(
                    recipient_id=expense.drafter_id, type="APPROVAL_REQUEST",
                    title="개인카드 환급 지출결의서 초안 생성",
                    message=f"{new_doc.doc_number} 초안이 생성됐습니다. 확인 후 상신하세요.",
                    link=f"/approvals/{new_doc.id}/edit",
                    related_type="approval_document", related_id=new_doc.id, commit=True)
            except Exception:
                self.db.rollback()
        except Exception:
            self.db.rollback()
            logging.getLogger(__name__).exception("개인환급 지출결의서 자동생성 실패(무시): 출장정산 승인은 완료됨")

    def _create_purchase_order_from_approval(self, doc: ApprovalDocument) -> None:
        """구매기안서 최종 승인 시 form_data.auto_po=True 면, BOM 품목(part_id 보유)으로
        발주서(DRAFT) 1건을 자동 생성. 공급업체=form_data.po_supplier_id. best-effort."""
        import logging
        try:
            fd = doc.form_data or {}
            if not fd.get("auto_po"):
                return
            if fd.get("auto_po_number"):
                return  # 이미 발주서 생성됨(중복 방지)
            supplier_id = fd.get("po_supplier_id")
            if not supplier_id:
                logging.getLogger(__name__).warning("발주서 자동생성 건너뜀: 공급업체(po_supplier_id) 미지정 — %s", doc.doc_number)
                return
            from decimal import Decimal as _Dec
            from datetime import date as _date
            from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderItemCreate
            from app.services.purchase_order_service import PurchaseOrderService

            po_items = []
            for it in (fd.get("items") or []):
                if not isinstance(it, dict):
                    continue
                pid = it.get("part_id")
                name = (str(it.get("name") or "")).strip()
                if not pid and not name:
                    continue  # part_id도 품목명도 없는 빈 행은 제외
                qty = float(it.get("qty") or 0)
                if qty <= 0:
                    qty = 1.0
                po_items.append(PurchaseOrderItemCreate(
                    # BOM 품목이면 part_id, 자유입력이면 custom_product_name 으로 담음(v0.91.0)
                    part_id=int(pid) if pid else None,
                    custom_product_name=None if pid else name,
                    ordered_quantity=_Dec(str(qty)),
                    unit_price=_Dec(str(it.get("unit_price") or 0)),
                    line_remarks=(str(it.get("note")).strip() or None) if it.get("note") else None,
                ))
            if not po_items:
                logging.getLogger(__name__).warning("발주서 자동생성 건너뜀: 담을 품목 없음 — %s", doc.doc_number)
                return

            po_in = PurchaseOrderCreate(
                supplier_id=int(supplier_id),
                order_date=_date.today(),
                remarks=f"구매기안서 {doc.doc_number} 승인에 따른 자동 발주",
                items=po_items,
            )
            po = PurchaseOrderService(self.db).create_purchase_order(po_in)  # 내부 commit, status=DRAFT

            # 기안 파생 발주서로 표시(항목 수정 잠금 기준) + 생성 번호를 기안서에 기록
            po.source_approval_id = doc.id
            fd2 = dict(fd)
            fd2["auto_po_number"] = po.po_number
            doc.form_data = fd2
            self.db.commit()

            # 기안자에게 알림
            try:
                from app.services.notification_service import NotificationService
                NotificationService(self.db).create(
                    recipient_id=doc.drafter_id, type="APPROVAL_REQUEST",
                    title="발주서 자동 생성",
                    message=f"{po.po_number}(임시저장) 이 생성됐습니다. 발주 관리에서 확인·확정하세요.",
                    link="/purchase-orders",
                    related_type="purchase_order", related_id=po.id, commit=True)
            except Exception:
                self.db.rollback()
        except Exception:
            self.db.rollback()
            logging.getLogger(__name__).exception("발주서 자동생성 실패(무시): 구매기안 승인은 완료됨")

    def create_purchase_draft_from_po(self, po_id: int, actor: User) -> ApprovalDocument:
        """발주서(PurchaseOrder) 기준으로 구매기안서(PURCHASE) 임시저장(DRAFT) 자동 생성.

        - 업체명·품목(part_id/수량/단가/비고) 자동 등록
        - 중복 생성은 PurchaseOrder.linked_approval_id 로 방지(멱등)
        - auto_po=False 고정 → 이 기안 승인 시 발주서를 또 만들지 않음(순환 방지)
        """
        from app.models.purchase_order import PurchaseOrder
        from app.models.parts import Part
        from app.models.approval import ApprovalForm
        from app.schemas.approval import ApprovalDocumentCreate

        po = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            raise NotFoundException("발주서", po_id)

        # 이미 생성된 구매기안이 있으면 그대로 반환(멱등)
        if po.linked_approval_id:
            existing = self.db.query(ApprovalDocument).filter(
                ApprovalDocument.id == po.linked_approval_id
            ).first()
            if existing:
                return existing

        form = self.db.query(ApprovalForm).filter(ApprovalForm.code == "PURCHASE").first()
        if not form:
            raise NotFoundException("구매기안서 양식(PURCHASE)", 0)

        supplier_name = po.supplier.partner_name if po.supplier else ""
        items = []
        total = 0.0
        for it in sorted(po.items, key=lambda x: x.id):
            part = self.db.query(Part).filter(Part.id == it.part_id).first() if it.part_id else None
            # BOM 품목이면 부품명, 자유입력이면 custom_product_name(v0.91.0)
            name = (
                (part.part_name if part else None)
                or (part.part_number if part else None)
                or getattr(it, "custom_product_name", None)
                or getattr(it, "custom_product_code", None)
                or (f"부품#{it.part_id}" if it.part_id else "(품목)")
            )
            qty = float(it.ordered_quantity or 0)
            price = float(it.unit_price or 0)
            amount = qty * price
            total += amount
            items.append({
                "name": name, "qty": qty, "unit_price": price,
                "note": it.line_remarks or "", "part_id": it.part_id, "amount": amount,
            })

        form_data = {
            "items_mode": "TABLE",
            "items_free": "",
            "items": items,
            "amount": total,
            "auto_po": False,          # 순환 방지: 승인해도 발주서 재생성 안 함
            "po_supplier_id": None,
            "supplier_name": supplier_name,  # 표시용
        }

        title = f"[구매기안] {supplier_name} · 발주 {po.po_number}"[:200]
        content = (f"발주서 <b>{po.po_number}</b>({supplier_name}) 기준으로 자동 생성된 "
                   f"구매기안서입니다. 결재선을 지정한 뒤 상신하세요.")

        data = ApprovalDocumentCreate(
            title=title, content=content, lines=[],
            form_id=form.id, form_data=form_data,
            purchase_category="일반",
        )
        doc = self.create_draft(data, actor)

        # 역방향 링크 저장(중복 방지)
        po.linked_approval_id = doc.id
        self.db.commit()
        return doc

    def create_disbursement_from_pos(self, po_ids: List[int], actor: User) -> ApprovalDocument:
        """선택한 여러 발주서(입고분)를 묶어 하나의 지출결의서(DISBURSEMENT) 임시저장 생성.

        각 발주서의 품목을 한 지출결의서 품목표로 합산. 거래처가 여러 곳이면 '복수 거래처'.
        source_po_ids를 form_data에 저장(추적). 상신은 사용자가 결재선·시행자 지정 후 진행.
        """
        from app.models.purchase_order import PurchaseOrder
        from app.models.parts import Part
        from app.models.approval import ApprovalForm
        from app.schemas.approval import ApprovalDocumentCreate

        if not po_ids:
            raise ValidationException("지출결의로 묶을 발주서를 선택하세요.", field="po_ids")
        pos = self.db.query(PurchaseOrder).filter(PurchaseOrder.id.in_(po_ids)).all()
        if not pos:
            raise NotFoundException("발주서", po_ids)

        form = self.db.query(ApprovalForm).filter(ApprovalForm.code == "DISBURSEMENT").first()
        if not form:
            raise NotFoundException("지출결의서 양식(DISBURSEMENT)", 0)

        items = []
        total = 0.0
        supplier_names = []
        po_numbers = []
        for po in sorted(pos, key=lambda x: x.id):
            po_numbers.append(po.po_number)
            sname = po.supplier.partner_name if po.supplier else ""
            if sname and sname not in supplier_names:
                supplier_names.append(sname)
            for it in sorted(po.items, key=lambda x: x.id):
                part = self.db.query(Part).filter(Part.id == it.part_id).first() if it.part_id else None
                name = (
                    (part.part_name if part else None)
                    or (part.part_number if part else None)
                    or getattr(it, "custom_product_name", None)
                    or getattr(it, "custom_product_code", None)
                    or (f"부품#{it.part_id}" if it.part_id else "(품목)")
                )
                qty = float(it.ordered_quantity or 0)
                price = float(it.unit_price or 0)
                amount = qty * price
                total += amount
                note = f"[{po.po_number}]" + (f" {it.line_remarks}" if it.line_remarks else "")
                items.append({
                    "name": name, "qty": qty, "unit_price": price,
                    "note": note.strip(), "part_id": it.part_id, "amount": amount,
                })

        vendor = supplier_names[0] if len(supplier_names) == 1 else (f"복수 거래처({len(supplier_names)})" if supplier_names else "")
        form_data = {
            "items_mode": "TABLE",
            "items_free": "",
            "items": items,
            "amount": total,
            "vendor": vendor,
            "source_po_ids": [po.id for po in pos],
            "note": f"발주서 {', '.join(po_numbers)} 입고분 지출결의",
        }

        title = f"[지출결의] {vendor} · 발주 {', '.join(po_numbers)}"[:200]
        content = (f"발주서 <b>{', '.join(po_numbers)}</b> 입고분에 대한 지출결의서입니다. "
                   f"결재선과 시행자(집행 담당)를 지정한 뒤 상신하세요.")

        data = ApprovalDocumentCreate(
            title=title, content=content, lines=[],
            form_id=form.id, form_data=form_data,
            purchase_category="일반",
        )
        doc = self.create_draft(data, actor)
        # 발주서에 지출결의 링크(지급 대기 표시 + 최종 승인 시 지급완료 처리 대상)
        for po in pos:
            po.disbursement_id = doc.id
        self.db.commit()
        return doc

    def _apply_disbursement_paid(self, doc: ApprovalDocument, paid: bool) -> None:
        """지출결의서 상태에 따라 연결된 발주서 대금지급 반영.
        최종 승인(집행 완료) → is_paid=True, 반려/취소 → 링크 해제·지급대기 복귀."""
        if not (doc.form and doc.form.code == "DISBURSEMENT"):
            return
        from app.models.purchase_order import PurchaseOrder
        fd = doc.form_data or {}
        po_ids = fd.get("source_po_ids") or []
        if not po_ids:
            return
        from datetime import date as _date
        for po in self.db.query(PurchaseOrder).filter(PurchaseOrder.id.in_(po_ids)).all():
            if paid:
                po.is_paid = True
                po.paid_date = _date.today()
                po.disbursement_id = doc.id
            else:
                # 이 지출결의로 인한 지급만 되돌림(다른 지출결의에 재묶이면 그때 갱신)
                if po.disbursement_id == doc.id:
                    po.is_paid = False
                    po.paid_date = None

    def _canceled_leave_target_ids(self, cancel_doc: ApprovalDocument) -> List[int]:
        """휴가취소 문서가 무효화 대상으로 삼을 수 있는 원 휴가 결재 id 목록.
        보안: 취소 기안자 **본인**이 기안한 **LEAVE** 양식 문서만 허용
        (타인 휴가·타 양식을 가리켜 남의 연차를 복구하는 조작 차단)."""
        rel_ids = list(cancel_doc.related_document_ids or [])
        if not rel_ids and cancel_doc.related_document_id is not None:
            rel_ids = [cancel_doc.related_document_id]
        if not rel_ids:
            return []
        rows = (
            self.db.query(ApprovalDocument)
            .join(ApprovalForm, ApprovalForm.id == ApprovalDocument.form_id)
            .filter(
                ApprovalDocument.id.in_(rel_ids),
                ApprovalForm.code == "LEAVE",
                ApprovalDocument.drafter_id == cancel_doc.drafter_id,
            )
            .all()
        )
        return [r.id for r in rows]

    def _void_canceled_leave(self, cancel_doc: ApprovalDocument) -> None:
        """휴가취소 문서가 참조하는 원 휴가 결재의 USAGE 원장을 무효화(잔여 복구). 실패해도 승인은 유지."""
        import logging
        try:
            from app.services import leave_accrual_service as _acc
            for rid in self._canceled_leave_target_ids(cancel_doc):
                _acc.void_usage_for_doc(self.db, rid)
        except Exception:
            self.db.rollback()
            logging.getLogger(__name__).exception("휴가취소 원장 무효화 실패(무시): 승인은 완료됨")

    def reject(self, doc_id: int, req: ApprovalActionRequest, actor: User, ip: Optional[str]) -> ApprovalDocument:
        """IN_PROGRESS만. comment 필수. 즉시 종료. 단일 commit.
        현재 대기중 결재자뿐 아니라 '이미 승인한 결재자'도 진행 중이면 반려 가능
        (예: 정 수석 승인 후 대표 구두 변경요청 → 정 수석이 반려하고 기안자가 수정·재상신). v0.90.x"""
        try:
            doc = self._get_locked(doc_id)
            line = self._guard_reject(doc, actor)

            if not req.comment or not req.comment.strip():
                raise ValidationException("반려 시 의견(comment)은 필수입니다.", field="comment")

            line.status = LINE_REJECTED
            line.acted_at = self._now()
            line.comment = req.comment
            self._snapshot_seal(line, actor)

            doc.status = STATUS_REJECTED
            doc.completed_at = self._now()
            # 지출결의 반려 → 연결된 발주서 지급 대기로 복귀
            self._apply_disbursement_paid(doc, paid=False)

            self._record_action(doc, actor, "REJECT", req.comment, ip)
            self.db.commit()
            self.db.refresh(doc)
            self._dispatch_notifications(lambda ns: ns.notify_approval_rejected(doc, actor.id))
            return doc
        except Exception:
            self.db.rollback()
            raise

    def cancel(self, doc_id: int, actor: User, ip: Optional[str]) -> ApprovalDocument:
        """회수: 최종 승인 전(IN_PROGRESS) 언제든. actor==drafter.
        이미 승인된 결재선까지 모두 초기화하고 임시저장(DRAFT)으로 되돌려 수정·재상신 가능. 단일 commit."""
        try:
            doc = self._get_locked(doc_id)
            if doc.drafter_id != actor.id:
                raise BusinessRuleException("기안자만 회수할 수 있습니다.", rule="DRAFTER_ONLY")
            if doc.status != STATUS_IN_PROGRESS:
                raise BusinessRuleException("결재 진행 중인 문서만 회수할 수 있습니다.", rule="CANCEL_IN_PROGRESS_ONLY")

            # 회수로 도장이 지워질 '이미 승인한' 결재자 — 초기화 전에 수집(회수 알림 대상)
            approved_ids = [ln.approver_id for ln in doc.lines if ln.status == LINE_APPROVED]

            # 결재선 전부 초기화 (이미 찍힌 도장/승인 이력 제거 — 재상신 시 1차부터 다시 시작)
            for line in doc.lines:
                line.status = LINE_WAITING
                line.acted_at = None
                line.comment = None
                line.seal_snapshot = None
                line.approver_name = None
                line.approver_position = None

            doc.status = STATUS_DRAFT
            doc.current_step = 0
            doc.completed_at = None

            self._record_action(doc, actor, "CANCEL", None, ip)
            self.db.commit()
            self.db.refresh(doc)
            if approved_ids:
                self._dispatch_notifications(
                    lambda ns: ns.notify_approval_recalled(doc, approved_ids, actor.id)
                )
            return doc
        except Exception:
            self.db.rollback()
            raise

    def resubmit(
        self,
        doc_id: int,
        data: Optional[ApprovalDocumentUpdate],
        actor: User,
        ip: Optional[str],
    ) -> ApprovalDocument:
        """REJECTED 문서만. actor==drafter. 본문/제목 수정 허용, 동일 결재선 재사용. 단일 commit."""
        try:
            doc = self._get_locked(doc_id)
            if doc.status != STATUS_REJECTED:
                raise BusinessRuleException("반려(REJECTED)된 문서만 재상신할 수 있습니다.", rule="RESUBMIT_REJECTED_ONLY")
            if doc.drafter_id != actor.id:
                raise BusinessRuleException("기안자만 재상신할 수 있습니다.", rule="DRAFTER_ONLY")

            if data is not None:
                if data.title is not None:
                    doc.title = data.title
                if data.content is not None:
                    doc.content = data.content
                if data.form_id is not None:
                    doc.form_id = data.form_id
                if data.form_data is not None:
                    doc.form_data = data.form_data
                # 관련 문서: 단일/다중 중 하나라도 오면 전체 교체(다중 우선)
                if data.related_document_ids is not None or data.related_document_id is not None:
                    _rel_ids = self._resolve_related_ids(data.related_document_id, data.related_document_ids)
                    doc.related_document_ids = _rel_ids or None
                    doc.related_document_id = _rel_ids[0] if _rel_ids else None
                if data.project_id is not None:
                    doc.project_id = data.project_id
                if data.purchase_category is not None:
                    doc.purchase_category = data.purchase_category or None
                if data.executor_id is not None:
                    doc.executor_id = data.executor_id or None
                if data.lines is not None:
                    self._validate_lines_sequence(data.lines)
                    doc.lines.clear()
                    self.db.flush()
                    for line_in in data.lines:
                        doc.lines.append(ApprovalLine(
                            step_order=line_in.step_order,
                            approver_id=line_in.approver_id,
                            status=LINE_WAITING,
                        ))
                self._replace_references(doc, data.reference_ids)

            if not doc.lines:
                raise ValidationException("결재선이 1명 이상 지정되어야 합니다.", field="lines")
            self._validate_lines_sequence(doc.lines)
            self._validate_required_form_data(doc)
            self._validate_phase_link(doc)
            self._require_disbursement_executor(doc)
            self._fill_leave_days(doc)

            # 새 사이클: 결재선 전부 리셋
            for line in doc.lines:
                line.status = LINE_PENDING if line.step_order == 1 else LINE_WAITING
                line.acted_at = None
                line.comment = None
                line.seal_snapshot = None
                line.approver_name = None
                line.approver_position = None

            doc.status = STATUS_IN_PROGRESS
            doc.current_step = 1
            doc.completed_at = None
            # 재상신(반려 후 등)에도 최초 기안일자 유지 — 원래 값이 없을 때만 채움(관리자 정정 제외).
            if doc.drafted_at is None:
                doc.drafted_at = self._now()
            doc.content_hash = self._content_hash(doc.content)

            self._record_action(doc, actor, "RESUBMIT", None, ip)
            self.db.commit()
            self.db.refresh(doc)
            return doc
        except Exception:
            self.db.rollback()
            raise

    def admin_correct(
        self,
        doc_id: int,
        req: CorrectionRequest,
        actor: User,
        ip: Optional[str],
    ) -> ApprovalCorrection:
        """관리자 사후 정정. reason 필수. corrections INSERT + is_corrected=True. 단일 commit.

        원본 actions/corrections 는 UPDATE/DELETE 하지 않는다.
        """
        try:
            if not req.reason or not req.reason.strip():
                raise ValidationException("정정 사유(reason)는 필수입니다.", field="reason")

            doc = self._get_locked(doc_id)

            target = self._resolve_correction_target(doc, req)
            if target is None or not hasattr(target, req.field_name):
                raise ValidationException(
                    f"정정 대상 필드를 찾을 수 없습니다: {req.target_table}.{req.field_name}",
                    field="field_name",
                )

            # 정정 가능 필드만 허용 (상태/ID/도장 등은 정정 불가)
            if req.field_name not in _CORRECTABLE_FIELDS.get(req.target_table, set()):
                raise ValidationException(
                    f"정정할 수 없는 필드입니다: {req.target_table}.{req.field_name}",
                    field="field_name",
                )

            old_raw = getattr(target, req.field_name)
            old_value = None if old_raw is None else str(old_raw)

            # 날짜/일시 필드는 문자열을 datetime 으로 변환 후 반영
            new_typed = self._coerce_correction_value(target, req.field_name, req.new_value)
            setattr(target, req.field_name, new_typed)

            correction = ApprovalCorrection(
                document_id=doc.id,
                target_table=req.target_table,
                target_id=req.target_id,
                field_name=req.field_name,
                old_value=old_value,
                new_value=req.new_value,
                reason=req.reason,
                corrected_by=actor.id,
                ip_address=ip,
            )
            self.db.add(correction)

            doc.is_corrected = True

            self.db.commit()
            self.db.refresh(correction)
            return correction
        except Exception:
            self.db.rollback()
            raise

    def admin_full_update(self, doc_id: int, data: "ApprovalDocumentUpdate", reason: str,
                          actor: User, ip: Optional[str]) -> ApprovalDocument:
        """[관리자] 결재 문서 '전체 정정' — 작성 폼으로 문서 내용 전체 교체.

        상태·결재선(승인/도장/처리이력)은 보존하고 문서 내용(제목/본문/form_data/거래처·품목 등)만
        교체한다. reason 필수. 변경 전/후 스냅샷을 approval_corrections에 기록 + is_corrected 표식 +
        본문 해시(content_hash) 재계산. 단일 commit.
        """
        import json
        try:
            if not reason or not reason.strip():
                raise ValidationException("정정 사유(reason)는 필수입니다.", field="reason")
            doc = self._get_locked(doc_id)

            before = {"title": doc.title, "content": doc.content, "form_data": doc.form_data}

            # 문서 '내용' 필드만 교체 — lines/status/current_step 은 건드리지 않음(승인·도장 보존)
            if data.title is not None:
                doc.title = data.title
            if data.content is not None:
                doc.content = data.content
            if data.form_id is not None:
                doc.form_id = data.form_id
            if data.form_data is not None:
                doc.form_data = data.form_data
            if data.related_document_ids is not None or data.related_document_id is not None:
                _rel = self._resolve_related_ids(data.related_document_id, data.related_document_ids)
                doc.related_document_ids = _rel or None
                doc.related_document_id = _rel[0] if _rel else None
            if data.project_id is not None:
                doc.project_id = data.project_id
            if data.purchase_category is not None:
                doc.purchase_category = data.purchase_category or None
            if data.executor_id is not None:
                doc.executor_id = data.executor_id or None
            self._replace_references(doc, data.reference_ids)

            # 본문 스냅샷 해시 갱신(위변조 대조 정합) + 정정 표식
            doc.content_hash = self._content_hash(doc.content)
            doc.is_corrected = True

            after = {"title": doc.title, "content": doc.content, "form_data": doc.form_data}
            self.db.add(ApprovalCorrection(
                document_id=doc.id,
                target_table="documents",
                target_id=doc.id,
                field_name="전체수정",
                old_value=json.dumps(before, ensure_ascii=False, default=str),
                new_value=json.dumps(after, ensure_ascii=False, default=str),
                reason=reason.strip(),
                corrected_by=actor.id,
                ip_address=ip,
            ))

            self.db.commit()
            self.db.refresh(doc)
            return doc
        except Exception:
            self.db.rollback()
            raise

    def admin_edit_dates(
        self,
        doc_id: int,
        executed_at,      # 시행일자(executed_at 컬럼). None=미변경, ""=지움
        exec_date,        # 결제/집행일(form_data.exec_date). None=미변경, ""=지움
    ) -> ApprovalDocument:
        """관리자 전용: 시행일자(executed_at) / 결제일(form_data.exec_date) 사후 수정.
        **이력/정정표시를 남기지 않는 무흔적 수정**(corrections 미기록, is_corrected 미변경). 단일 commit."""
        try:
            doc = self._get_locked(doc_id)

            # 시행일자 (executed_at, DateTime 컬럼)
            if executed_at is not None:
                s = str(executed_at).strip()
                if s == "":
                    doc.executed_at = None
                else:
                    from dateutil import parser as _dtp
                    try:
                        new_dt = _dtp.parse(s)
                    except (ValueError, OverflowError):
                        raise ValidationException(f"시행일자 형식을 해석할 수 없습니다: {executed_at}", field="executed_at")
                    if new_dt.tzinfo is None:
                        new_dt = new_dt.replace(tzinfo=_KST)  # 입력값은 KST 벽시계 시각 그대로
                    doc.executed_at = new_dt

            # 결제/집행일 (form_data.exec_date, JSONB)
            if exec_date is not None:
                fd = dict(doc.form_data or {})
                fd["exec_date"] = str(exec_date).strip() or None
                doc.form_data = fd  # 재할당(JSONB 변경 감지)

            self.db.commit()
            self.db.refresh(doc)
            return doc
        except Exception:
            self.db.rollback()
            raise

    # ==================== 읽기 ====================

    def get_box(
        self,
        box: BoxType,
        actor: User,
        keyword: Optional[str] = None,
        form_code: Optional[str] = None,
        project_id: Optional[int] = None,
        category: Optional[str] = None,
        execution_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ApprovalDocument], int]:
        """drafted/pending/done/reference 필터. 읽기 전용(commit 없음).

        하위호환: draft → drafted 와 동일 동작.
        - drafted(기안함): 내가 기안한 모든 상태 문서
        - pending(결재대기): 내 차례(line.status=PENDING) IN_PROGRESS 문서
        - done(완료함): 완료 상태 & (기안자 or 결재선 포함 or 참조자)
        - reference(참조함): 내가 참조자인 문서
        """
        box_val = box.value if isinstance(box, BoxType) else box
        if box_val == "draft":
            box_val = "drafted"
        query = self.db.query(ApprovalDocument).options(
            joinedload(ApprovalDocument.drafter),
            joinedload(ApprovalDocument.executor),
            joinedload(ApprovalDocument.form),
            joinedload(ApprovalDocument.project),
            joinedload(ApprovalDocument.lines).joinedload(ApprovalLine.approver),
        ).filter(ApprovalDocument.is_deleted.is_(False))  # 소프트 삭제 제외

        if box_val == "drafted":
            # 내가 기안한 모든 상태 문서
            query = query.filter(
                ApprovalDocument.drafter_id == actor.id,
            )
        elif box_val == "pending":
            # 결재대기: 내가 결재선에 포함된 '진행중' 문서.
            #   - 내 차례(line PENDING) = 지금 결재해야 할 건
            #   - 내가 이미 승인(line APPROVED) = 최종 승인 완료 전까지 진행 상황 추적용
            # (아직 내 차례가 오지 않은 WAITING 은 제외 — 앞 결재자 처리 대기)
            my_line = (
                self.db.query(ApprovalLine.document_id)
                .filter(
                    ApprovalLine.approver_id == actor.id,
                    ApprovalLine.status.in_([LINE_PENDING, LINE_APPROVED]),
                )
            )
            query = query.filter(
                ApprovalDocument.status == STATUS_IN_PROGRESS,
                ApprovalDocument.id.in_(my_line),
            )
        elif box_val == "done":
            # 내가 관련(기안자 or 결재선 포함 or 참조자)된 완료 문서
            line_sub = (
                self.db.query(ApprovalLine.document_id)
                .filter(ApprovalLine.approver_id == actor.id)
            )
            ref_sub = (
                self.db.query(ApprovalReference.document_id)
                .filter(ApprovalReference.user_id == actor.id)
            )
            query = query.filter(
                ApprovalDocument.status.in_(DONE_STATUSES),
                (ApprovalDocument.drafter_id == actor.id)
                | (ApprovalDocument.id.in_(line_sub))
                | (ApprovalDocument.id.in_(ref_sub)),
            )
        elif box_val == "reference":
            # 내가 참조자인 문서
            ref_sub = (
                self.db.query(ApprovalReference.document_id)
                .filter(ApprovalReference.user_id == actor.id)
            )
            query = query.filter(ApprovalDocument.id.in_(ref_sub))
        elif box_val == "execution":
            # 내가 시행자로 지정된 문서(시행전/시행후) — execution_status 로 세부 필터
            query = query.filter(ApprovalDocument.executor_id == actor.id,
                                 ApprovalDocument.execution_status.isnot(None))
        else:
            raise ValidationException(f"알 수 없는 box 값입니다: {box_val}", field="box")

        if category:
            query = query.filter(ApprovalDocument.purchase_category == category)
        if execution_status:
            query = query.filter(ApprovalDocument.execution_status == execution_status)

        if keyword:
            kw = f"%{keyword}%"
            # 문서번호·제목 + 기안자 이름으로 검색
            drafter_sub = self.db.query(User.id).filter(User.name.ilike(kw))
            query = query.filter(
                (ApprovalDocument.doc_number.ilike(kw))
                | (ApprovalDocument.title.ilike(kw))
                | (ApprovalDocument.drafter_id.in_(drafter_sub))
            )

        if form_code:
            # 양식 종류 필터 (join 다중성/카운트 왜곡 방지를 위해 form_id 서브쿼리 사용)
            form_sub = (
                self.db.query(ApprovalForm.id)
                .filter(ApprovalForm.code == form_code)
            )
            query = query.filter(ApprovalDocument.form_id.in_(form_sub))

        if project_id is not None:
            query = query.filter(ApprovalDocument.project_id == project_id)

        total = query.count()
        items = (
            query.order_by(ApprovalDocument.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def soft_delete(self, doc_id: int, actor: User) -> None:
        """결재 문서 소프트 삭제. 감사용으로 행은 보존, 목록/상세/휴가집계에서 제외.
        삭제된 휴가 결재는 다음 원장 동기화 때 잔여 복구됨.

        권한:
        - 관리자(ADMIN): 상태 무관(승인 완료건 포함) 삭제 가능.
        - 일반 사용자: 본인이 작성한 임시저장(DRAFT) 문서만 삭제 가능.
        """
        from datetime import datetime, timezone
        doc = self.db.query(ApprovalDocument).filter(ApprovalDocument.id == doc_id).first()
        if not doc or doc.is_deleted:
            raise NotFoundException("결재 문서", doc_id)

        is_admin = getattr(actor, "role", None) == "ADMIN"
        is_own_draft = doc.drafter_id == actor.id and doc.status == STATUS_DRAFT
        if not (is_admin or is_own_draft):
            raise ForbiddenException(
                "본인이 작성한 임시저장(DRAFT) 문서만 삭제할 수 있습니다."
            )

        doc.is_deleted = True
        doc.deleted_at = datetime.now(timezone.utc)
        doc.deleted_by = actor.id
        self.db.flush()
        # 승인된 휴가취소 문서를 삭제하면, 그 취소가 복구했던 연차를 되돌린다(원장 재차감).
        self._reverse_leave_cancel_effect(doc)
        self.db.commit()

    def _has_other_active_cancel(self, exclude_cancel_id: int, leave_doc_id: int) -> bool:
        """leave_doc_id 를 여전히 무효화하고 있는 다른 (승인+미삭제) 휴가취소 문서 존재 여부."""
        from sqlalchemy import or_
        q = (
            self.db.query(ApprovalDocument.id)
            .join(ApprovalForm, ApprovalForm.id == ApprovalDocument.form_id)
            .filter(
                ApprovalForm.code == "LEAVE_CANCEL",
                ApprovalDocument.status == STATUS_APPROVED,
                ApprovalDocument.is_deleted.is_(False),
                ApprovalDocument.id != exclude_cancel_id,
                or_(
                    ApprovalDocument.related_document_id == leave_doc_id,
                    ApprovalDocument.related_document_ids.contains([leave_doc_id]),
                ),
            )
        )
        return self.db.query(q.exists()).scalar()

    def _reverse_leave_cancel_effect(self, cancel_doc: ApprovalDocument) -> None:
        """휴가취소(LEAVE_CANCEL) 문서 삭제 시 원장 무효화(void)를 해제해 잔여를 원상복구.
        승인됐던 취소만 대상. 같은 휴가를 무효화하는 다른 유효 취소가 남아있으면 유지. 실패해도 삭제는 유지."""
        if not (cancel_doc.form and cancel_doc.form.code == "LEAVE_CANCEL"):
            return
        if cancel_doc.status != STATUS_APPROVED:
            return  # 승인 전 취소는 원장에 영향을 준 적이 없음
        import logging
        try:
            from app.services import leave_accrual_service as _acc
            for rid in self._canceled_leave_target_ids(cancel_doc):
                if self._has_other_active_cancel(cancel_doc.id, rid):
                    continue
                _acc.unvoid_usage_for_doc(self.db, rid)
            drafter = self.db.query(User).filter(User.id == cancel_doc.drafter_id).first()
            if drafter:
                _acc.sync_usage(self.db, drafter)
        except Exception:
            logging.getLogger(__name__).exception("휴가취소 삭제 원장 복구 실패(무시): 문서 삭제는 완료됨")

    def get_detail(self, doc_id: int, actor: User) -> ApprovalDocument:
        """열람권한 검증(기안자 | 결재선 포함자 | ADMIN). 읽기. 소프트 삭제건은 404."""
        doc = (
            self.db.query(ApprovalDocument)
            .options(
                joinedload(ApprovalDocument.drafter),
                joinedload(ApprovalDocument.executor),
                joinedload(ApprovalDocument.form),
                joinedload(ApprovalDocument.project),
                joinedload(ApprovalDocument.lines).joinedload(ApprovalLine.approver),
                joinedload(ApprovalDocument.actions).joinedload(ApprovalAction.actor),
                joinedload(ApprovalDocument.references).joinedload(ApprovalReference.user),
                joinedload(ApprovalDocument.attachments),
                joinedload(ApprovalDocument.related_document),
            )
            .filter(ApprovalDocument.id == doc_id)
            .first()
        )
        if not doc or doc.is_deleted:
            raise NotFoundException("결재 문서", doc_id)

        if not self._can_view(doc, actor):
            raise ForbiddenException("해당 문서를 열람할 권한이 없습니다.")

        return doc

    @staticmethod
    def _can_view(doc: ApprovalDocument, actor: User) -> bool:
        """열람 권한: 기안자 | 결재선 포함자 | 참조자 | ADMIN."""
        return (
            actor.role == "ADMIN"
            or doc.drafter_id == actor.id
            or any(line.approver_id == actor.id for line in doc.lines)
            or any(ref.user_id == actor.id for ref in doc.references)
        )

    # ==================== 결재 의견(댓글) ====================

    def list_comments(self, doc_id: int, actor: User) -> List["ApprovalComment"]:
        """열람 권한자만. 작성 시각 오름차순."""
        from app.models.approval_comment import ApprovalComment
        doc = self._get_doc_for_comment(doc_id)
        if not self._can_view(doc, actor):
            raise ForbiddenException("해당 문서를 열람할 권한이 없습니다.")
        return (
            self.db.query(ApprovalComment)
            .options(joinedload(ApprovalComment.user))
            .filter(ApprovalComment.document_id == doc_id)
            .order_by(ApprovalComment.created_at.asc(), ApprovalComment.id.asc())
            .all()
        )

    def add_comment(self, doc_id: int, content: str, actor: User, ip: Optional[str] = None) -> "ApprovalComment":
        """열람 권한자만 작성. 상태 무관. 작성 후 연관자 전원에게 알림(본인 제외)."""
        from app.models.approval_comment import ApprovalComment
        text = (content or "").strip()
        if not text:
            raise ValidationException("댓글 내용을 입력하세요.", field="content")
        doc = self._get_doc_for_comment(doc_id)
        if not self._can_view(doc, actor):
            raise ForbiddenException("해당 문서를 열람할 권한이 없습니다.")
        comment = ApprovalComment(document_id=doc_id, user_id=actor.id, content=text)
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        # 연관자 알림(best-effort)
        preview = text if len(text) <= 70 else text[:70] + "…"
        self._dispatch_notifications(
            lambda ns: ns.notify_approval_commented(doc, actor.id, preview)
        )
        return comment

    def delete_comment(self, doc_id: int, comment_id: int, actor: User) -> None:
        """본인 또는 ADMIN만 삭제."""
        from app.models.approval_comment import ApprovalComment
        comment = (
            self.db.query(ApprovalComment)
            .filter(ApprovalComment.id == comment_id, ApprovalComment.document_id == doc_id)
            .first()
        )
        if not comment:
            raise NotFoundException("댓글", comment_id)
        if not (actor.role == "ADMIN" or comment.user_id == actor.id):
            raise ForbiddenException("본인이 작성한 댓글만 삭제할 수 있습니다.")
        self.db.delete(comment)
        self.db.commit()

    def _get_doc_for_comment(self, doc_id: int) -> ApprovalDocument:
        """댓글용 문서 로드(결재선/참조자 포함, 소프트삭제 제외)."""
        doc = (
            self.db.query(ApprovalDocument)
            .options(
                joinedload(ApprovalDocument.lines),
                joinedload(ApprovalDocument.references),
            )
            .filter(ApprovalDocument.id == doc_id)
            .first()
        )
        if not doc or doc.is_deleted:
            raise NotFoundException("결재 문서", doc_id)
        return doc

    def _linkable_predecessor_rows(self, actor: User, pre_form_code, own_only: bool = True) -> List[dict]:
        """status=APPROVED + form.code in pre_form_code(s) 문서를 dict 로 반환.

        pre_form_code 는 단일 문자열 또는 코드 리스트(지출결의서처럼 복수 인정).
        own_only=True(기본): 본인 기안만(출장정산/회의록 — 보통 본인이 작성).
        own_only=False: 전사 공유(지출결의서 — 집행 요청자가 구매 기안자와 다를 수 있음).
        각 항목에 form_data 전체 + 편의(expense/start_date/end_date) 포함. 읽기 전용.
        """
        codes = [pre_form_code] if isinstance(pre_form_code, str) else list(pre_form_code)
        q = (
            self.db.query(ApprovalDocument)
            .join(ApprovalForm, ApprovalForm.id == ApprovalDocument.form_id)
            .filter(
                ApprovalDocument.status == STATUS_APPROVED,
                ApprovalForm.code.in_(codes),
                ApprovalDocument.is_deleted.is_(False),
            )
        )
        if own_only:
            q = q.filter(ApprovalDocument.drafter_id == actor.id)
        docs = q.order_by(ApprovalDocument.id.desc()).all()
        result: List[dict] = []
        for doc in docs:
            data = doc.form_data or {}
            expense_raw = data.get("expense")
            expense: Optional[float] = None
            if expense_raw not in (None, ""):
                try:
                    expense = float(expense_raw)
                except (ValueError, TypeError):
                    expense = None
            result.append({
                "id": doc.id,
                "doc_number": doc.doc_number,
                "title": doc.title,
                "form_data": data or None,
                "expense": expense,
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
            })
        return result

    def list_linkable_trips(self, actor: User) -> List[dict]:
        """정산서 연결용 출장신청서 후보 — 본인 기안 + status=APPROVED + form.code='TRIP'.

        하위호환 유지용. 일반화된 _linkable_predecessor_rows('TRIP') 위임. 읽기 전용.
        """
        return self._linkable_predecessor_rows(actor, "TRIP")

    def list_linkable_predecessors(self, actor: User, post_form_code: str) -> List[dict]:
        """사후(POST) 양식 작성 시 연결할 사전(PRE) 문서 후보.

        post_form_code 양식의 linked_form_code(=PRE code)를 찾아,
        본인 기안 + status=APPROVED + 그 PRE 양식 문서들을 반환. 읽기 전용.
        짝 PRE code 가 없으면 빈 리스트.
        """
        post_form = (
            self.db.query(ApprovalForm)
            .filter(ApprovalForm.code == post_form_code)
            .first()
        )
        if not post_form or not post_form.linked_form_code:
            return []
        # 지출결의서(구매 집행)는 전사 공유 — 집행 요청자가 구매 기안자와 달라도 연결 가능.
        # 그 외(출장정산/회의록)는 본인 기안만.
        own_only = post_form_code != "DISBURSEMENT"
        # 지출결의서는 구매기안서 외 지출성 문서(출장정산서·회의비정산서)도 선행으로 인정
        pre_codes = self._accepted_pre_codes(post_form)
        return self._linkable_predecessor_rows(actor, pre_codes, own_only=own_only)

    def get_followups(self, doc: ApprovalDocument) -> List[dict]:
        """해당 문서를 관련 문서로 참조하는 후속 문서 목록(단일/다중 모두).

        [{id, doc_number, title, status, form_name}]. 읽기 전용.
        """
        from sqlalchemy import or_
        rows = (
            self.db.query(ApprovalDocument)
            .outerjoin(ApprovalForm, ApprovalForm.id == ApprovalDocument.form_id)
            .filter(
                or_(
                    ApprovalDocument.related_document_id == doc.id,
                    ApprovalDocument.related_document_ids.contains([doc.id]),
                ),
                ApprovalDocument.is_deleted.is_(False),
            )
            .order_by(ApprovalDocument.id.desc())
            .all()
        )
        result: List[dict] = []
        for f in rows:
            form = getattr(f, "form", None)
            result.append({
                "id": f.id,
                "doc_number": f.doc_number,
                "title": f.title,
                "status": f.status,
                "form_name": form.name if form else None,
            })
        return result

    def get_related_documents(self, doc: ApprovalDocument) -> List[dict]:
        """이 문서가 연결한 관련 문서 목록(입력 순서 보존). [{id, doc_number, title, status, form_name}]."""
        ids = list(doc.related_document_ids or [])
        if not ids and doc.related_document_id is not None:
            ids = [doc.related_document_id]
        if not ids:
            return []
        rows = (
            self.db.query(ApprovalDocument)
            .outerjoin(ApprovalForm, ApprovalForm.id == ApprovalDocument.form_id)
            .filter(
                ApprovalDocument.id.in_(ids),
                ApprovalDocument.is_deleted.is_(False),
            )
            .all()
        )
        by_id = {r.id: r for r in rows}
        result: List[dict] = []
        for i in ids:
            r = by_id.get(i)
            if not r:
                continue
            form = getattr(r, "form", None)
            result.append({
                "id": r.id,
                "doc_number": r.doc_number,
                "title": r.title,
                "status": r.status,
                "form_name": form.name if form else None,
            })
        return result

    def pending_count(self, actor: User) -> int:
        """내 차례(line.status=PENDING & approver_id=actor.id) 건수. 읽기."""
        return (
            self.db.query(ApprovalLine)
            .join(ApprovalDocument, ApprovalDocument.id == ApprovalLine.document_id)
            .filter(
                ApprovalLine.approver_id == actor.id,
                ApprovalLine.status == LINE_PENDING,
                ApprovalDocument.status == STATUS_IN_PROGRESS,
                ApprovalDocument.is_deleted.is_(False),
            )
            .count()
        )

    def can_act(self, doc: ApprovalDocument, actor: User) -> bool:
        """현재 차례+본인 결재(승인) 가능 여부(라우터 응답 주입용)."""
        if doc.status != STATUS_IN_PROGRESS:
            return False
        line = self._current_line(doc)
        return bool(line and line.status == LINE_PENDING and line.approver_id == actor.id)

    def can_reject(self, doc: ApprovalDocument, actor: User) -> bool:
        """반려 가능 여부: 진행 중(IN_PROGRESS)이고, 결재선에서 본인이 현재 대기중(PENDING)
        이거나 이미 승인(APPROVED)한 경우. 승인 후에도 되돌릴 수 있게(v0.90.x)."""
        if doc.status != STATUS_IN_PROGRESS:
            return False
        return any(
            ln.approver_id == actor.id and ln.status in (LINE_PENDING, LINE_APPROVED)
            for ln in doc.lines
        )

    # ==================== 내부 헬퍼 ====================

    def _guard_turn(self, doc: ApprovalDocument, actor: User) -> ApprovalLine:
        """IN_PROGRESS + 현재 step line.approver_id==actor.id (ADMIN 예외 없음)."""
        if doc.status != STATUS_IN_PROGRESS:
            raise BusinessRuleException("결재중(IN_PROGRESS) 문서만 처리할 수 있습니다.", rule="IN_PROGRESS_ONLY")
        line = self._current_line(doc)
        if not line or line.status != LINE_PENDING:
            raise BusinessRuleException("현재 결재 대기 단계가 아닙니다.", rule="NOT_PENDING_STEP")
        if line.approver_id != actor.id:
            # ADMIN 도 대리 승인 불가
            raise BusinessRuleException("본인 차례가 아닙니다.", rule="NOT_YOUR_TURN")
        return line

    def _guard_reject(self, doc: ApprovalDocument, actor: User) -> ApprovalLine:
        """반려 가드: IN_PROGRESS 문서에서, 결재선에 포함된 결재자가 현재 대기중(PENDING)이거나
        이미 승인(APPROVED)한 경우 반려 가능. 반려자 본인의 line을 반환(현재 대기 단계 우선).
        승인 후에도 되돌릴 수 있게 하기 위해 _guard_turn과 분리(v0.90.x)."""
        if doc.status != STATUS_IN_PROGRESS:
            raise BusinessRuleException("결재중(IN_PROGRESS) 문서만 반려할 수 있습니다.", rule="IN_PROGRESS_ONLY")
        candidate: Optional[ApprovalLine] = None
        for ln in doc.lines:
            if ln.approver_id == actor.id and ln.status in (LINE_PENDING, LINE_APPROVED):
                candidate = ln
                if ln.status == LINE_PENDING:
                    break  # 현재 차례 단계 우선
        if not candidate:
            raise BusinessRuleException("반려할 수 있는 결재자가 아닙니다.", rule="NOT_REJECTABLE")
        return candidate

    def _snapshot_seal(self, line: ApprovalLine, actor: User) -> None:
        """승인/반려 시점 결재자 정보 스냅샷. seal_snapshot 에는 식별자만 저장(출력 시 재생성)."""
        line.approver_name = actor.name
        line.approver_position = actor.position
        if actor.seal_image_path:
            line.seal_snapshot = actor.seal_image_path
        else:
            seal_label = actor.seal_text or actor.name or ""
            line.seal_snapshot = f"자동:{seal_label}"

    def _record_action(
        self,
        doc: ApprovalDocument,
        actor: User,
        action: str,
        comment: Optional[str],
        ip: Optional[str],
    ) -> None:
        self.db.add(ApprovalAction(
            document_id=doc.id,
            actor_id=actor.id,
            action=action,
            comment=comment,
            ip_address=ip,
            # DB 기본값(now())은 초까지 들어가므로 분 단위로 맞춘 값을 명시한다
            acted_at=self._now(),
        ))

    def _resolve_correction_target(self, doc: ApprovalDocument, req: CorrectionRequest):
        """정정 대상 row 조회 (target_table 은 documents/lines/actions 만 허용)."""
        table = req.target_table
        if table == "documents":
            return doc if doc.id == req.target_id else None
        if table == "lines":
            return (
                self.db.query(ApprovalLine)
                .filter(ApprovalLine.id == req.target_id, ApprovalLine.document_id == doc.id)
                .first()
            )
        if table == "actions":
            return (
                self.db.query(ApprovalAction)
                .filter(ApprovalAction.id == req.target_id, ApprovalAction.document_id == doc.id)
                .first()
            )
        raise ValidationException(f"허용되지 않은 정정 대상 테이블입니다: {table}", field="target_table")

    def _coerce_correction_value(self, target, field_name: str, raw):
        """정정 값 타입 변환. DateTime 컬럼이면 문자열을 datetime 으로 파싱."""
        col = target.__table__.columns.get(field_name)
        if col is not None and isinstance(col.type, SADateTime):
            if raw is None or str(raw).strip() == "":
                return None
            from dateutil import parser as _dtp
            try:
                dt = _dtp.parse(str(raw))
            except (ValueError, OverflowError):
                raise ValidationException(
                    f"날짜 형식을 해석할 수 없습니다: {raw}", field=field_name
                )
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_KST)  # 입력값은 KST 벽시계 시각 그대로
            return dt
        return raw

    # ==================== 프로젝트 마스터 (v0.38.0 공용 ProjectService 위임) ====================
    # 프로젝트는 공용 도메인(app.services.project_service.ProjectService)으로 분리됨.
    # 기존 호출부(approval 라우터 하위호환)를 위해 위임 래퍼만 유지한다.

    def list_projects(self, active_only: bool = True) -> List[Project]:
        """프로젝트 목록. active_only=True 면 활성만. ProjectService 위임."""
        svc = ProjectService(self.db)
        return svc.list_active() if active_only else svc.list_all()

    def create_project(self, data: ProjectCreate) -> Project:
        """프로젝트 생성. ProjectService 위임 (단일 commit)."""
        return ProjectService(self.db).create(data)

    def update_project(self, project_id: int, data: ProjectUpdate) -> Project:
        """프로젝트 수정. ProjectService 위임 (단일 commit)."""
        return ProjectService(self.db).update(project_id, data)

    def search_all(self, keyword=None, status=None, drafter_id=None,
                   date_from=None, date_to=None, skip: int = 0, limit: int = 50):
        """[관리자] 전체 결재 문서 검색 (모든 사용자/상태)."""
        q = self.db.query(ApprovalDocument)
        if keyword:
            like = f"%{keyword}%"
            drafter_sub = self.db.query(User.id).filter(User.name.ilike(like))
            q = q.filter(or_(
                ApprovalDocument.title.ilike(like),
                ApprovalDocument.doc_number.ilike(like),
                ApprovalDocument.drafter_id.in_(drafter_sub),
            ))
        if status:
            q = q.filter(ApprovalDocument.status == status)
        if drafter_id:
            q = q.filter(ApprovalDocument.drafter_id == drafter_id)
        if date_from:
            q = q.filter(ApprovalDocument.created_at >= date_from)
        if date_to:
            q = q.filter(ApprovalDocument.created_at <= date_to)
        total = q.count()
        docs = (
            q.order_by(ApprovalDocument.id.desc())
            .offset(skip).limit(limit).all()
        )
        return docs, total

    def get_corrections(self, doc_id: int):
        """[관리자] 문서의 정정 이력 목록."""
        return (
            self.db.query(ApprovalCorrection)
            .filter(ApprovalCorrection.document_id == doc_id)
            .order_by(ApprovalCorrection.id.desc())
            .all()
        )

    def calendar_events(self, date_from: Optional[str] = None, date_to: Optional[str] = None):
        """휴가/출장(TRIP/LEAVE) 문서를 캘린더 이벤트로 반환.

        진행중(IN_PROGRESS) + 승인완료(APPROVED) 문서만, form_data 의 start_date~end_date 가
        조회 범위와 겹치는 것. (form_data 날짜는 문자열이라 파이썬에서 범위 필터)
        """
        forms = {
            f.id: f
            for f in self.db.query(ApprovalForm)
            .filter(ApprovalForm.code.in_(["TRIP", "LEAVE"]))
            .all()
        }
        if not forms:
            return []
        docs = (
            self.db.query(ApprovalDocument)
            .filter(
                ApprovalDocument.form_id.in_(list(forms.keys())),
                ApprovalDocument.status.in_([STATUS_IN_PROGRESS, STATUS_APPROVED]),
                ApprovalDocument.is_deleted.is_(False),
            )
            .all()
        )
        out = []
        for d in docs:
            fd = d.form_data or {}
            sd = fd.get("start_date")
            ed = fd.get("end_date") or sd
            if not sd:
                continue
            sd, ed = str(sd)[:10], str(ed)[:10]
            if date_from and ed < date_from:
                continue
            if date_to and sd > date_to:
                continue
            out.append({
                "id": d.id,
                "doc_number": d.doc_number,
                "title": d.title,
                "form_code": forms[d.form_id].code,
                "drafter_name": d.drafter.name if d.drafter else None,
                "start_date": sd,
                "end_date": ed,
                "status": d.status,
                "leave_type": fd.get("leave_type"),
            })
        return out
