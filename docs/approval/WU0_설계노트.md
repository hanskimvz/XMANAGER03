# WU0 설계노트 — 전자결재 모듈 Phase 1

- 기준 문서: `전자결재시스템_개발기획서_v0.2.md` (단독 기준)
- 대상 코드베이스: `X-MANAGER_R0.1 (2)/X-MANAGER_R0.1` (FastAPI 0.110 + SQLAlchemy 2.0 + Pydantic 2 + Vue3)
- 작성 목적: WU1(마이그레이션)~WU7 빌드 에이전트가 그대로 구현할 수 있는 설계 확정안.
- 본 문서는 **설계만** 담는다. 실제 코드(마이그레이션/모델/라우터)는 생성하지 않는다.

> 핵심 사전 확인 (코드 직접 확인 완료)
> - `users.position` = 마이그레이션 `w3x4y5z6a7b8`로 **이미 존재** → 추가 금지 (게이트 체크 항목).
> - `users.name_en` = 마이그레이션 `u1v2w3x4y5z6`로 **이미 존재** → 추가 금지.
> - Alembic 현재 head = **`h4i5j6k7l8m9`** (`add_tbd_text_to_sales_document_item`). 신규 리비전의 `down_revision`은 이 값.
> - PDF 파이프라인 = `services/pdf/quotation_pdf.py`가 Jinja2(`templates/pdf/*.html`) → WeasyPrint. 폰트는 `services/pdf/fonts.py` 경유(직접 `import weasyprint` 금지 원칙). 저장/해시 = `sales_document_pdf` + `services/pdf/storage.py` + `sales_document_pdf_service.py`.
> - `BaseService`(`services/base.py`)는 `create()`/`update()`/`bulk_create()`마다 `self.db.commit()`을 호출한다 → **다중 테이블 원자성이 깨진다**. 따라서 approval_service는 BaseService의 쓰기 메서드를 상속·사용하지 않고 자체 트랜잭션 경계로 구현한다(아래 4장).

---

## 1. 범위 / 비범위

### 1.1 Phase 1 범위 (이 설계노트 대상)
- 문서 종류: **자유 기안 1종만** (`form_id = NULL`)
- 결재 흐름: 상신(SUBMIT) / 승인(APPROVE) / 반려(REJECT) / 회수(CANCEL) / 재상신(RESUBMIT)
- 순차 결재 2~3단계, 차례 검증
- 자동 도장(SVG) 생성
- 문서 출력: 인쇄용 HTML(`/print`) + PDF(`/pdf`, WeasyPrint) — 단일 Jinja2 템플릿 공유
- 본문 SHA-256 해시 + 검증번호(앞 4자리 hex 대문자)를 출력 PDF 저장 시 기록
- 디폴트 결재자 설정(관리자) + 기안 시 자동 채움/자유 변경
- (1.5) 관리자 사후 정정 + `approval_corrections` 이력

### 1.2 비범위 (Phase 2 이후 — 설계에서 제외)
- 표준 양식 4종(휴가/출장/지출/회의록), `approval_forms` 테이블 **생성 안 함**
  - 단, `approval_documents`에 `form_id`(FK nullable) / `form_data`(JSONB nullable) 컬럼은 **미리 둔다**. FK 대상 테이블이 없으므로 Phase 1 마이그레이션에서는 `form_id`를 **FK 제약 없이 단순 Integer nullable**로 만들고, Phase 2에서 `approval_forms` 생성 후 FK 추가(주석으로 명시).
- 첨부파일, 알림(시스템/이메일), 대결/참조, 검색/필터 고도화, 기존 승인 통합

---

## 2. DB 설계 (실제 SQLAlchemy 모델 정의안)

### 2.1 파일 위치 권장안
- **단일 파일 `models/approval.py`** 에 결재 4종 + PDF 보관 테이블을 모두 정의한다.
  - 근거: 기존 관행상 `sales_document.py` 한 파일에 `SalesDocument`/`SalesDocumentItem`/`SalesDocumentLink`를 함께 둔다(연관 도메인 그룹핑). 결재 테이블은 모두 `approval_documents`를 중심으로 강결합되므로 한 파일이 자연스럽다.
  - 단, `ApprovalDocumentPdf`만은 `sales_document_pdf.py`와 동일하게 별 클래스로 같은 파일에 두되, 원하면 `models/approval_pdf.py`로 분리 가능(빌드 시 택1, 기본은 단일 파일).
- `models/__init__.py`에 신규 모델 import 추가(기존 모델 등록 방식 따름).
- `users` 확장은 **새 컬럼만** `models/user.py`의 `User` 클래스에 추가(2.2).

> 공통 컨벤션 (기존 모델과 동일)
> - `from app.core.database import Base`
> - `Column(..., comment="한글 설명")` 필수
> - 생성/수정 시각: `created_at = Column(DateTime(timezone=True), server_default=func.now())`, `updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())`
> - 타입: PostgreSQL `TIMESTAMPTZ` = `DateTime(timezone=True)`, `JSONB` = `from sqlalchemy.dialects.postgresql import JSONB`

### 2.2 users 테이블 확장 (ALTER — 신규 컬럼 3개만)

`models/user.py`의 `User` 클래스에 추가:

```python
# --- 전자결재 모듈 (v0.33.0) ---
approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="디폴트 결재자(관리자 설정, 기안 시 1차로 자동 채움)")
seal_text = Column(String(10), nullable=True, comment="도장에 새길 글자(미설정 시 name에서 추출)")
seal_image_path = Column(String(300), nullable=True, comment="업로드한 도장/서명 이미지 경로(선택). NULL이면 자동 생성 SVG 사용")

# self-참조 관계 (디폴트 결재자)
default_approver = relationship("User", remote_side=[id], foreign_keys=[approver_id])
```
- `position`, `name_en`은 **추가 금지**(이미 존재).
- `ForeignKey`/`relationship` import를 `user.py` 상단에 추가 필요(`from sqlalchemy import ..., ForeignKey`, `from sqlalchemy.orm import relationship`).

### 2.3 approval_documents (결재 문서)

```python
class ApprovalDocument(Base):
    """전자결재 문서 (Phase 1: 자유 기안 1종)

    status: DRAFT(임시저장) / IN_PROGRESS(결재중) / APPROVED(승인완료)
            / REJECTED(반려) / CANCELED(회수)
    """
    __tablename__ = "approval_documents"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    doc_number = Column(String(30), unique=True, nullable=False, index=True, comment="문서번호 AP-2026-0001")
    form_id = Column(Integer, nullable=True, comment="양식 ID (Phase 2, NULL=자유기안). FK는 approval_forms 생성 후 추가")
    form_data = Column(JSONB, nullable=True, comment="양식별 입력값 (Phase 2)")
    title = Column(String(200), nullable=False, comment="제목")
    content = Column(Text, nullable=True, comment="본문 HTML (TipTap 출력)")
    content_hash = Column(String(64), nullable=True, comment="본문 SHA-256 해시(상신/승인 시점 스냅샷, 위변조 대조용)")
    status = Column(String(20), nullable=False, default="DRAFT", server_default="DRAFT", index=True,
                    comment="상태 DRAFT/IN_PROGRESS/APPROVED/REJECTED/CANCELED")
    current_step = Column(Integer, nullable=False, default=0, server_default="0", comment="현재 결재 차례(1부터, 0=미상신)")
    drafter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="기안자")
    drafted_at = Column(DateTime(timezone=True), nullable=True, comment="상신 시각")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="최종 승인/반려 시각")
    is_corrected = Column(Boolean, nullable=False, default=False, server_default="false", comment="관리자 사후 정정 여부 표식(11장)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

    drafter = relationship("User", foreign_keys=[drafter_id])
    lines = relationship("ApprovalLine", back_populates="document",
                         cascade="all, delete-orphan", order_by="ApprovalLine.step_order")
    actions = relationship("ApprovalAction", back_populates="document", order_by="ApprovalAction.acted_at")
```
- `content_hash`는 v0.2 9.3/12 "본문 해시 Phase 1로 앞당김" 반영. 본문 텍스트 자체의 결정적 해시.
- `is_corrected`는 11.1 "관리자 정정됨" 표식용(출력에 노출).

### 2.4 approval_lines (결재선)

```python
class ApprovalLine(Base):
    """결재선 — 누가 몇 번째로 결재하는가. 상신 후 수정 금지(v0.2 부록A)."""
    __tablename__ = "approval_lines"
    __table_args__ = (
        UniqueConstraint("document_id", "step_order", name="uq_approval_lines_doc_step"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="문서 ID")
    step_order = Column(Integer, nullable=False, comment="결재 순서(1,2,3)")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="결재자")
    status = Column(String(20), nullable=False, default="WAITING", server_default="WAITING",
                    comment="WAITING/PENDING(내 차례)/APPROVED/REJECTED")
    acted_at = Column(DateTime(timezone=True), nullable=True, comment="처리 시각")
    comment = Column(Text, nullable=True, comment="승인/반려 의견")
    seal_snapshot = Column(String(300), nullable=True, comment="승인 시점 도장(자동 SVG 문자열 또는 업로드 경로) 스냅샷")
    approver_name = Column(String(100), nullable=True, comment="승인 시점 결재자 이름 스냅샷")
    approver_position = Column(String(20), nullable=True, comment="승인 시점 직급 스냅샷")

    document = relationship("ApprovalDocument", back_populates="lines")
    approver = relationship("User", foreign_keys=[approver_id])
```
- `seal_snapshot`은 SVG 문자열이 길 수 있어 v0.2 SQL은 VARCHAR(300)이나, 자동생성 SVG 전체를 담으면 초과 가능 → **빌드 시 결정 필요**(10장 열린항목): (a) SVG는 출력 시 `seal_service`로 재생성하고 snapshot에는 도장 글자/색만 저장, (b) 또는 `Text`로 확장. **권장: (a)** — snapshot에는 "자동:홍길동" 또는 업로드 경로만, 실제 SVG는 출력 시 결정적 재생성(검증번호/해시로 무결성 보장).

### 2.5 approval_actions (감사 이력 — INSERT 전용)

```python
class ApprovalAction(Base):
    """결재 행위 감사 이력. INSERT 전용 — UPDATE/DELETE API 없음(v0.2 13장)."""
    __tablename__ = "approval_actions"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id"),
                         nullable=False, index=True, comment="문서 ID")
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="행위자")
    action = Column(String(20), nullable=False, comment="SUBMIT/APPROVE/REJECT/CANCEL/RESUBMIT")
    comment = Column(Text, nullable=True, comment="의견")
    acted_at = Column(DateTime(timezone=True), server_default=func.now(), comment="행위 시각")
    ip_address = Column(String(45), nullable=True, comment="감사 추적용 요청 IP")

    document = relationship("ApprovalDocument", back_populates="actions")
    actor = relationship("User", foreign_keys=[actor_id])
```
- `ondelete` 없음(문서 삭제해도 감사 이력 보존 의도). 단 Phase 1엔 문서 삭제 API가 없으므로 무관.

### 2.6 approval_corrections (관리자 사후 정정 이력 — 11장, INSERT 전용)

```python
class ApprovalCorrection(Base):
    """관리자 사후 정정 이력. 원본 덮어쓰지 않고 변경분만 기록. INSERT 전용(삭제 불가)."""
    __tablename__ = "approval_corrections"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id"),
                         nullable=False, index=True, comment="문서 ID")
    target_table = Column(String(40), nullable=False, comment="대상 테이블(actions/lines/documents)")
    target_id = Column(Integer, nullable=False, comment="대상 row ID")
    field_name = Column(String(40), nullable=False, comment="고친 필드(acted_at, comment ...)")
    old_value = Column(Text, nullable=True, comment="원래 값")
    new_value = Column(Text, nullable=True, comment="새 값")
    reason = Column(Text, nullable=False, comment="수정 사유(필수 — 없으면 저장 실패)")
    corrected_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="정정 관리자")
    corrected_at = Column(DateTime(timezone=True), server_default=func.now(), comment="정정 시각")
    ip_address = Column(String(45), nullable=True, comment="요청 IP")

    document = relationship("ApprovalDocument")
    corrector = relationship("User", foreign_keys=[corrected_by])
```

### 2.7 approval_document_pdf (출력 PDF 보관 — `sales_document_pdf` 패턴 복제)

```python
class ApprovalDocumentPdf(Base):
    """결재 문서 PDF 보관 이력 (sales_document_pdf 패턴 복제 + 검증번호)."""
    __tablename__ = "approval_document_pdf"
    __table_args__ = (
        UniqueConstraint("document_id", "language", name="uq_approval_document_pdf_doc_lang"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="대상 결재 문서 ID")
    language = Column(String(10), nullable=False, default="ko", server_default="ko", comment="언어(ko)")
    file_path = Column(String(500), nullable=False, comment="storage root 기준 상대 경로")
    file_size = Column(BigInteger, nullable=False, comment="파일 크기(bytes)")
    file_hash = Column(String(64), nullable=False, comment="PDF 바이트 SHA-256")
    content_hash = Column(String(64), nullable=True, comment="본문(content) SHA-256 — 생성 시점 스냅샷")
    verify_code = Column(String(4), nullable=False, comment="검증번호 = SHA256(doc_number+content) 앞 4 hex 대문자")
    download_count = Column(Integer, nullable=False, default=1, server_default="1", comment="누적 다운로드")
    first_generated_at = Column(DateTime(timezone=True), nullable=False, comment="최초 생성 시각")
    last_downloaded_at = Column(DateTime(timezone=True), nullable=False, comment="최근 다운로드 시각")
    last_generated_by = Column(String(100), nullable=True, comment="최근 생성/다운로드 사용자")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document = relationship("ApprovalDocument", foreign_keys=[document_id])
```
- `sales_document_pdf`와 달리 결재 문서는 버전 개념이 없으므로 unique 키는 `(document_id, language)`. 문서가 진행되며 도장이 늘어나면 같은 row 덮어쓰기 + `download_count++`(원 패턴과 동일한 upsert).
- import 필요: `from sqlalchemy import BigInteger, UniqueConstraint, Boolean`.

### 2.8 WU1 Alembic 마이그레이션 명세
- 파일명: 기존 컨벤션(`{12자 hex-ish id}_{snake_설명}.py`) + v0.2 버전(v0.33.0) 표기. 예: `i2j3k4l5m6n7_v0_33_0_add_approval_tables.py`
- `revision = 'i2j3k4l5m6n7'`(빌드 시 신규 12자 생성), `down_revision = 'h4i5j6k7l8m9'`(현재 head).
- `Create Date` 주석 + 1줄 docstring(기존 스타일).
- `upgrade()`:
  1. `op.add_column('users', sa.Column('approver_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, comment=...))`, `seal_text` VARCHAR(10), `seal_image_path` VARCHAR(300) — **position/name_en 추가 금지**.
  2. `op.create_table('approval_documents', ...)` (2.3과 동일 컬럼/제약, `form_id`는 FK 없는 Integer).
  3. `op.create_table('approval_lines', ...)` + `UniqueConstraint(document_id, step_order)`.
  4. `op.create_table('approval_actions', ...)`.
  5. `op.create_table('approval_corrections', ...)`.
  6. `op.create_table('approval_document_pdf', ...)` + `UniqueConstraint(document_id, language)`.
- `downgrade()`: 역순 `drop_table` 후 `op.drop_column('users', ...)` 3개. (게이트: upgrade/downgrade 모두 성공)

---

## 3. Pydantic 스키마 안 (`schemas/approval.py`)

> 컨벤션: `BaseModel` + `Field(..., description=...)`, 응답은 `model_config = ConfigDict(from_attributes=True)`, 상태/액션은 `str, Enum`.

### 3.1 Enum
```python
class ApprovalStatus(str, Enum):  # DRAFT/IN_PROGRESS/APPROVED/REJECTED/CANCELED
class LineStatus(str, Enum):      # WAITING/PENDING/APPROVED/REJECTED
class ActionType(str, Enum):      # SUBMIT/APPROVE/REJECT/CANCEL/RESUBMIT
class BoxType(str, Enum):         # draft/pending/done  (in_progress는 done과 별도 탭이면 추가)
```

### 3.2 결재선 입력/응답
- `ApprovalLineCreate`: `step_order:int(ge=1)`, `approver_id:int`
- `ApprovalLineResponse`: `id, step_order, approver_id, approver_name, approver_position, status, acted_at, comment` + (출력용) `seal_svg:Optional[str]`(서비스 주입) — `from_attributes`

### 3.3 문서 Create / Update / Response
- `ApprovalDocumentCreate`(임시저장 생성):
  - `title:str(max=200)`, `content:Optional[str]`, `lines:List[ApprovalLineCreate]`(빈 리스트 허용 — DRAFT 단계), `form_id:Optional[int]=None`, `form_data:Optional[dict]=None`
- `ApprovalDocumentUpdate`(DRAFT 수정):
  - `title:Optional[str]`, `content:Optional[str]`, `lines:Optional[List[ApprovalLineCreate]]` (전체 교체)
- `ApprovalActionRequest`(승인/반려/회수/재상신 공용):
  - `comment:Optional[str]` (반려 시 서비스에서 필수 검증)
- `ApprovalDocumentResponse`(상세):
  - `id, doc_number, form_id, title, content, status, current_step, drafter_id, drafter_name, drafted_at, completed_at, is_corrected, created_at, updated_at`, `lines:List[ApprovalLineResponse]`, `actions:List[ApprovalActionResponse]`, `verify_code:Optional[str]`, `can_act:bool`(내 차례 여부, 서비스 주입)
- `ApprovalDocumentListItem`(목록): `id, doc_number, title, drafter_name, current_approver_name, status, current_step, drafted_at, created_at`
- `ApprovalActionResponse`: `id, actor_id, actor_name, action, comment, acted_at` (ip_address는 ADMIN 전용 응답에만)

### 3.4 box 조회 쿼리 파라미터
- `box: BoxType = Query(...)`, `keyword: Optional[str]=Query(None)`, `skip:int=Query(0,ge=0)`, `limit:int=Query(50,ge=1,le=200)`
  - `draft` = 내가 기안한 DRAFT, `pending` = 내가 현재 차례 결재자(line.status=PENDING), `done` = 내가 관련된 APPROVED/REJECTED/CANCELED. (in_progress 탭이 필요하면 box 값 추가)

### 3.5 관리자/정정 스키마
- `DefaultApproverUpdate`: `approver_id:Optional[int]`
- `CorrectionRequest`: `target_table:str`, `target_id:int`, `field_name:str`, `new_value:str`, `reason:str(min_length=1)` (reason 빈값이면 422)

### 3.6 응답 포맷 (deps.create_response 사용 여부)
- 기존 코드가 혼재(sales_document는 `response_model` 직접 반환, deps.create_response는 일부만). **권장: 신규 결재 라우터는 `response_model`로 Pydantic 스키마 직접 반환**(sales_document 패턴과 일치, OpenAPI 깔끔). 목록은 `{items, total, skip, limit}` 래퍼 스키마(`ApprovalListResponse`) 사용 — sales_document의 `SalesDocumentListResponse`와 동일 형태.

---

## 4. approval_service 설계 (`services/approval_service.py`)

### 4.1 트랜잭션/상속 방침 (확정)
- `class ApprovalService:` — **BaseService를 상속하지 않는다**(BaseService의 create/update가 메서드마다 commit하여 다중 테이블 원자성을 깨므로).
- 생성자: `def __init__(self, db: Session): self.db = db` (sales_document_service 스타일).
- 상태 전이 메서드(submit/approve/reject/cancel/resubmit/admin_correct)는 **여러 row(document+lines+actions[+corrections])를 변경한 뒤 메서드 끝에서 단 한 번 `self.db.commit()`** 한다. 예외 발생 시 `self.db.rollback()` 후 도메인 예외 재발생 → 전체 롤백.
- 읽기 메서드(get_box/get_detail/pending_count)는 commit 없음.
- 영향받는 메서드(자체 트랜잭션 경계 필수): **create_draft, update_draft, submit, approve, reject, cancel, resubmit, admin_correct**.
- 예외: `app/core/exceptions.py`의 `NotFoundException / ValidationException / BusinessRuleException` 사용(라우터에서 `handle_service_exception` 또는 직접 매핑). 권한 위반은 라우터에서 403으로 변환(아래 6장).

### 4.2 동시성 (확정)
- 승인/반려/회수/상신 처리 시 대상 문서 행을 **`with_for_update()` 로 잠금** 후 상태 재검증:
  ```python
  doc = self.db.query(ApprovalDocument).filter(ApprovalDocument.id == doc_id).with_for_update().first()
  ```
- 추가 안전장치: 승인 처리에서 `current_step`을 잠근 상태에서 검증(`doc.current_step == expected_step`)하고 갱신 → 이중 클릭/이중 승인 방지. (조건부 UPDATE 대신 SELECT FOR UPDATE 방식 채택 — ORM 흐름과 일관.)

### 4.3 문서번호 채번 (AP-YYYY-NNNN, 동시성 안전)
- 형식: `AP-{YYYY}-{NNNN}` (4자리 zero-pad, 연도별 리셋). 연 2,500건 이내이므로 4자리 충분.
- **채번은 상신(submit) 시점이 아니라 create_draft 시점에 부여**(임시저장도 문서번호를 가짐 — v0.2 출력 예시가 DRAFT에도 번호 표기). 단 빌드 시 "상신 시 채번"으로 바꿔도 무방(열린항목 후보 아님, create 시 채번 권장).
- 동시성 안전 채번:
  - 같은 트랜잭션 안에서 `SELECT max(doc_number)`는 경합 위험 → **해당 연도 prefix에 대해 `SELECT ... FOR UPDATE`로 카운터 행을 잠그는 방식이 가장 안전**하나 별도 카운터 테이블이 없다.
  - Phase 1 권장(단순/충분): `doc_number`에 **UNIQUE 제약**(이미 있음)을 두고, `max+1`로 생성 → INSERT 시 `IntegrityError` 나면 1회 재시도(최대 N회 루프). 30명/저빈도 환경에서 충분.
  - 대안(빌드 선택): Postgres 시퀀스 또는 advisory lock(`pg_advisory_xact_lock`). 권장은 재시도 방식.

### 4.4 메서드 시그니처 + 상태머신 규칙

모든 쓰기 메서드는 `actor: User`, `ip: Optional[str]`(actions 기록용)을 받는다.

| 메서드 | 시그니처 | 전이/검증 (6장·12장) |
|---|---|---|
| `create_draft` | `(self, data: ApprovalDocumentCreate, actor: User) -> ApprovalDocument` | 상태 DRAFT 생성. drafter_id=actor.id. lines 입력 시 step_order 1..n 연속 검증. 디폴트 결재자 자동채움은 라우터/프론트가 기본값 주입(서비스는 들어온 lines 저장). doc_number 채번. **단일 commit**. |
| `update_draft` | `(self, doc_id, data: ApprovalDocumentUpdate, actor) -> ApprovalDocument` | **DRAFT 상태에서만** 허용(아니면 BusinessRule). actor==drafter 검증. lines 전체 교체(delete-orphan). **단일 commit**. |
| `submit` | `(self, doc_id, actor, ip) -> ApprovalDocument` | DRAFT→IN_PROGRESS. actor==drafter. lines ≥1 검증. `current_step=1`, line1.status=PENDING(나머지 WAITING), `drafted_at=now`, `content_hash` 계산·저장. action=SUBMIT 기록. with_for_update. **단일 commit**. |
| `approve` | `(self, doc_id, req: ApprovalActionRequest, actor, ip) -> ApprovalDocument` | IN_PROGRESS만. with_for_update. **현재 step의 line.approver_id==actor.id**(차례+본인, ADMIN도 예외 없음). 해당 line APPROVED+acted_at+comment+스냅샷(approver_name/position, seal_snapshot). 마지막 step이면 doc APPROVED+completed_at, 아니면 current_step++ 및 다음 line PENDING. action=APPROVE. **단일 commit**. |
| `reject` | `(self, doc_id, req, actor, ip) -> ApprovalDocument` | IN_PROGRESS만. 차례+본인 검증. **comment 필수**(없으면 Validation). 현재 line REJECTED, doc REJECTED+completed_at(**즉시 종료, 뒤로 안 감**). action=REJECT. **단일 commit**. |
| `cancel` | `(self, doc_id, actor, ip) -> ApprovalDocument` | **회수는 1차 결재자 처리 전에만**: status==IN_PROGRESS AND current_step==1 AND line1.status==PENDING(아직 미처리). actor==drafter. doc CANCELED. action=CANCEL. 이후엔 BusinessRule 거부. **단일 commit**. |
| `resubmit` | `(self, doc_id, data: Optional[ApprovalDocumentUpdate], actor, ip) -> ApprovalDocument` | **REJECTED 문서만**(이력 유지). actor==drafter. 본문/제목 수정 허용(결재선은 v0.2 "상신 후 수정 금지"이나 재상신은 새 사이클 → 결재선 재지정 허용 여부는 열린항목; 기본은 동일 결재선 재사용). lines 전부 WAITING 리셋, current_step=1, line1 PENDING, status=IN_PROGRESS, content_hash 재계산. action=RESUBMIT. **단일 commit**. |
| `get_box` | `(self, box: BoxType, actor, keyword, skip, limit) -> tuple[list, int]` | draft/pending/done 필터(3.4). 읽기. |
| `get_detail` | `(self, doc_id, actor) -> ApprovalDocument` | 열람권한 검증(기안자|결재선 포함자|ADMIN). can_act/verify_code 주입은 라우터/스키마 단에서. |
| `pending_count` | `(self, actor) -> int` | 내 차례(line.status=PENDING & approver_id=actor.id) 건수. |
| `admin_correct` | `(self, doc_id, req: CorrectionRequest, actor(ADMIN), ip) -> ApprovalCorrection` | reason 필수(없으면 Validation). 대상 row 현재값을 old_value로, new_value 적용, `approval_corrections` INSERT, 문서 `is_corrected=True`. **원본 actions/corrections는 UPDATE/DELETE API 없음**. **단일 commit**. |

- 차례검증/권한검증 위치: **서비스 계층에서 강제**(16.3 불변식). 라우터는 require_auth만 통과시키고 본인/차례 검증은 서비스가 도메인 예외로 던진 뒤 403/422 매핑.
- 도장 스냅샷 생성: approve 시 `seal_service.make_seal_svg`를 호출하거나(또는 출력 시 재생성 — 2.4 권장 (a)), snapshot에는 식별자만 저장.

---

## 5. seal_service 설계 (`services/seal_service.py`)

- 라이브러리 불필요(순수 문자열 SVG). v0.2 9.1 기준.
- 시그니처: `def make_seal_svg(name: str, approved_date: str, color: str = "#C00000") -> str:`
  - `name`: 도장 글자(우선순위 `user.seal_text` → 없으면 `user.name`)
  - `approved_date`: `YYYY-MM-DD`(또는 `YY.MM.DD`) 문자열
  - `color`: 기본 빨강 `#C00000`(v0.2 9.1). 출력 예시 호환을 위해 인자로 분리(열린항목 10장).
- 글자수별 배치 규칙(9.1):
  - 사용 글자: `chars = list(name[-3:])` (성 포함 최대 3글자)
  - 2글자: 좌우 2칸 배치
  - 3글자: 위 1 / 아래 2 (전통 인장)
  - 4글자(seal_text가 4자일 때): 2x2
  - 공통: `viewBox="0 0 100 100"`, 외곽 `<circle r=46 stroke=color stroke-width=3 fill=none>`, 가운데 이름 `<text>`(색=color), 하단 `y≈88 font-size≈9`에 날짜.
- 보조 함수(선택): `make_seal_css(name, date, color)` → WeasyPrint용 CSS 원(border-radius)+텍스트 버전(v0.2 10.1 "둘 다 동일 모양" 요구). 인쇄 HTML=인라인 SVG, PDF=호환 안전한 버전을 택할 수 있게 둘 다 제공.
- 단위 테스트 대상(WU 검증): 글자수 2/3/4 분기 좌표, 색 인자 반영, 결정성(같은 입력=같은 출력).

---

## 6. 라우터 설계 (`api/v1/approval.py`) — 7장 1:1 매핑

- `router = APIRouter(prefix="/approvals", tags=["전자결재"])`
- 관리자/도장은 별 router 또는 같은 파일 내 별도 prefix 사용. 권장: 결재 본문 = `/approvals`, 도장 = `auth.py`의 users 라우터에 `/users/seal/{user_id}.svg` 추가(또는 같은 파일), 관리자 = `admin` 라우터 또는 `/admin/...` prefix.
- 서비스 주입: `def get_approval_service(db=Depends(get_db)) -> ApprovalService` 를 `deps.py`에 추가(기존 패턴). 단 require_auth로 받은 `User`를 서비스에 넘김.
- IP 추출: 라우터에서 `request: Request` 받아 `request.client.host`(또는 `X-Forwarded-For` 헤더 우선 — 열린항목 10장)를 서비스에 전달.

| 메서드 | 경로 | 의존성 | 요청 | 응답 |
|---|---|---|---|---|
| POST | `/approvals` | require_auth | `ApprovalDocumentCreate` | `ApprovalDocumentResponse`(DRAFT) |
| PUT | `/approvals/{id}` | require_auth + (서비스)기안자검증 + DRAFT만 | `ApprovalDocumentUpdate` | `ApprovalDocumentResponse` |
| POST | `/approvals/{id}/submit` | require_auth + 기안자검증 | — | `ApprovalDocumentResponse`(IN_PROGRESS) |
| POST | `/approvals/{id}/approve` | require_auth + 차례검증(서비스) | `ApprovalActionRequest` | `ApprovalDocumentResponse` |
| POST | `/approvals/{id}/reject` | require_auth + 차례검증 | `ApprovalActionRequest`(comment 필수) | `ApprovalDocumentResponse` |
| POST | `/approvals/{id}/cancel` | require_auth + 기안자검증 | — | `ApprovalDocumentResponse`(CANCELED) |
| POST | `/approvals/{id}/resubmit` | require_auth + 기안자검증 | `ApprovalDocumentUpdate`(optional) | `ApprovalDocumentResponse` |
| GET | `/approvals?box=draft\|pending\|done` | require_auth | query(3.4) | `ApprovalListResponse` |
| GET | `/approvals/{id}` | require_auth + 열람권한(서비스) | — | `ApprovalDocumentResponse` |
| GET | `/approvals/pending-count` | require_auth | — | `{count:int}` (라우트 등록 순서: `{id}`보다 **먼저** 선언) |
| GET | `/approvals/{id}/print` | require_auth + 열람권한 | — | `HTMLResponse` |
| GET | `/approvals/{id}/pdf` | require_auth + 열람권한 | — | `Response(media_type=application/pdf)` (+PDF 저장/해시/검증번호) |
| GET | `/users/seal/{user_id}.svg` | require_auth | — | `Response(media_type=image/svg+xml)` |
| GET | `/admin/users/{id}/default-approver` | require_admin | — | `{approver_id, approver_name}` |
| PUT | `/admin/users/{id}/default-approver` | require_admin | `DefaultApproverUpdate` | 동일 |
| GET | `/admin/approvals/{id}/actions` | require_admin | — | actions 원본(ip 포함) |
| PUT | `/admin/approvals/{id}/actions/{action_id}` | require_admin | `CorrectionRequest` | `ApprovalCorrection`(+is_corrected=True) |

> 주의: `/approvals/pending-count`, `/approvals` 고정경로는 `/approvals/{id}` 동적경로보다 **위에 선언**해야 매칭 충돌이 없다(FastAPI 선언 순서). sales_document.py가 `/payment-counts`를 `/{doc_id}`보다 먼저 둔 패턴과 동일.

> **불변식 13.x / 16.3 준수**: actions·corrections에 대한 DELETE/일반 UPDATE 엔드포인트는 **만들지 않는다**. 관리자 정정도 actions를 직접 UPDATE하지 않고 corrections에 기록 + (정정값 반영)만.

### 6.1 main.py 등록 라인
```python
from app.api.v1 import (..., approval)   # 기존 import 목록 끝에 추가
# 전자결재 API (v0.33.0)
app.include_router(approval.router, prefix=settings.API_V1_PREFIX)
```
- 관리자/도장 엔드포인트를 별 router 객체로 분리했다면 함께 `include_router` 추가.

---

## 7. 출력 / PDF 설계

### 7.1 템플릿 (`templates/pdf/approval_ko.html`, Jinja2)
- 기존 `templates/pdf/quotation_ko.html` + `base.html` 구조 따름(`{% extends "base.html" %}` 가능 — 폰트/A4 CSS 재사용). 한글 폰트는 base가 `assets/fonts` 참조.
- 블록 구조(v0.2 10.2 레이아웃):
  - 헤더: 회사 로고 + 회사명 / 우측 **결재란 표**(`{% for line in lines %}` 칸 자동 생성: 직급/명칭 행 + 도장 행). 미결재 칸은 빈칸.
  - 문서번호(`doc_number`), 구분선
  - 제목, 기안자(이름/부서), 기안일
  - 본문(`content` — TipTap HTML, `| safe`). autoescape 환경이므로 본문만 안전 출력 필터.
  - 하단: **검증번호 `{{ doc_number }}-{{ verify_code }}`**, `is_corrected`면 "관리자 정정됨(YYYY-MM-DD)" 표식.
- 도장 렌더: 변수 `seal_svg`(인라인) 또는 CSS 원(`make_seal_css`). v0.2 10.1대로 **두 방식 헬퍼 제공** — 인쇄 HTML은 SVG, PDF는 호환 안전 버전을 컨텍스트 플래그로 선택.
- `@media print` CSS로 인쇄 최적화(브라우저 인쇄 = 같은 HTML).

### 7.2 렌더 서비스 (`services/pdf/approval_pdf.py`)
- `quotation_pdf.py`의 `QuotationPdfService` 구조 복제: `__init__`에서 `verify_fonts` + Jinja2 `Environment(FileSystemLoader(templates/pdf), autoescape)`, `render(data, lang="ko") -> bytes` (`weasyprint`는 이 모듈 내부에서만 import, 단 `services/pdf/__init__`(=fonts 로드)가 먼저 import되도록 import 순서 유지).
- 입력 데이터: 결재 문서 + lines(도장 SVG 주입) + verify_code + content_hash.

### 7.3 저장 + 해시 + 검증번호 흐름 (`services/approval_pdf_service.py`)
- `sales_document_pdf_service.py` 복제:
  - `verify_code = sha256((doc_number + (content or "")).encode("utf-8")).hexdigest()[:4].upper()` — **앞 4자리 hex, 대문자**(확정 결정 3).
  - `content_hash = sha256((content or "").encode("utf-8")).hexdigest()` — `approval_documents.content_hash`/`approval_document_pdf.content_hash`에 기록.
  - PDF bytes → `storage.save(relative_path, bytes)`, `file_hash = sha256(pdf_bytes)`, upsert `approval_document_pdf`(unique `(document_id, language)`), `download_count++`.
  - `build_pdf_relative_path` = `"{document_id}/{doc_number}_ko.pdf"`(sanitize).
- 검증번호는 결정적(같은 doc_number+content면 항상 동일) → 출력본 대조 가능. 본문 변조 시 검증번호 불일치로 탐지.
- 라우터 `/print`와 `/pdf`는 **같은 템플릿** 사용. `/print`는 HTML 반환(저장 안 함), `/pdf`는 렌더+저장+해시 후 PDF 반환.

---

## 8. 프론트 설계

> 패턴(확인됨): axios 싱글턴 `api/client.ts`(요청 인터셉터가 `Authorization: Bearer` + 토큰 자동, 401 시 refresh). api 모듈 = `xxxApi` 객체(`getList/getById/create/update...`). 라우터 `router/index.ts` 글로벌 `beforeEach`가 `meta.public` 아니면 `access_token` 요구. 인증 = `useAuth()`(`isLoggedIn/isAdmin/user.value.{id,role,name}`). 본문 = `components/common/MarkupEditor.vue`(`v-model`=`modelValue:string`, emit `update:modelValue`). 공통 컴포넌트 = `components/Pagination.vue`(props `total/pageSize/currentPage`, emit `update:currentPage/update:pageSize`), `components/SearchableSelect.vue`(props `modelValue:number/options:{id,code,name_ko,name_en?}`, emit `update:modelValue`). 메뉴 = `App.vue`(PC/모바일 `RouterLink`). 인쇄 = `meta:{layout:'print'}` + `window.print()`(`PurchaseOrderPrintView.vue`).

### 8.1 라우트 추가 (`router/index.ts`)
- `/approvals` → `ApprovalListView.vue` (탭: 기안함/결재대기/진행중/완료함, query `?box=`)
- `/approvals/write` 및 `/approvals/:id/edit` → `ApprovalWriteView.vue`
- `/approvals/:id` → `ApprovalDetailView.vue`
- `/approvals/:id/print` → `ApprovalPrintView.vue` (`meta:{layout:'print'}`)
- 모두 비-public(로그인 필요). 관리자 디폴트결재자/정정 화면은 기존 `AdminView.vue`에 탭/섹션 추가.

### 8.2 api 모듈 (`api/approval.ts`) — `approvalApi` 객체
- `getBox(params:{box,keyword?,skip?,limit?})`
- `getById(id)`
- `create(data)` / `update(id,data)`
- `submit(id)` / `approve(id,{comment?})` / `reject(id,{comment})` / `cancel(id)` / `resubmit(id,data?)`
- `pendingCount()`
- `printHtmlUrl(id)` / `downloadPdf(id)` (PurchaseOrder PDF 다운로드 패턴: blob 응답)
- `sealSvgUrl(userId)`
- 관리자: `getDefaultApprover(userId)` / `setDefaultApprover(userId,{approver_id})` / `getActions(id)` / `correctAction(id,actionId,payload)`
- 타입 인터페이스(`ApprovalDocument`, `ApprovalLine`, `ApprovalListResponse`) export — salesDocument.ts 컨벤션.

### 8.3 View 3종 구성 + 재사용
- **ApprovalListView**: 탭 + 표(문서번호/제목/기안자/현재결재자/상태배지/상신일) + `Pagination` + 우상단 `[+ 기안 작성]`. `approvalApi.getBox`로 로드.
- **ApprovalWriteView**: 제목 input, 본문 `<MarkupEditor v-model="content"/>`(TipTap 재사용), 결재선 지정(사용자 `SearchableSelect`로 추가 + 순서 정렬). 기본값: `useAuth().user.approver_id`(또는 별도 조회)를 1차로 자동 입력. `[임시저장]`(create/update), `[상신]`(submit).
- **ApprovalDetailView**: 상단 결재란(이름/상태/일시), 본문, 이력 타임라인(actions). `can_act` true일 때만 `[승인]`/`[반려(의견)]` 버튼. `[인쇄]`/`[PDF]` 버튼.
- **ApprovalPrintView**: `PurchaseOrderPrintView` 패턴(`window.print()` + 서버 `/print` HTML 또는 클라 렌더).

### 8.4 대시보드 배지 + 메뉴
- 대시보드: `approvalApi.pendingCount()` 호출 → "결재 대기 N건" 배지(기존 dashboard 화면/스토어에 추가).
- 메뉴: `App.vue` PC(약 43~51행 영역) + 모바일(약 78~86행 영역)에 `<RouterLink to="/approvals" ...>전자결재</RouterLink>` 추가(전 직원 노출).

---

## 9. WU0 게이트 자가체크표

| 항목 | 기준 | 결과 |
|---|---|---|
| 5.1 users 확장 | approver_id/seal_text/seal_image_path만, position/name_en 제외 | 충족(2.2). position·name_en 이미 존재 확인됨 |
| 5.2 approval_documents | 컬럼/상태값/current_step/drafter/타임스탬프 일치 | 충족(2.3) + content_hash/is_corrected 보강(9.3/11) |
| 5.3 approval_lines | step_order, status값, 스냅샷 3종, unique(doc,step) | 충족(2.4) |
| 5.4 approval_actions | action값(SUBMIT/APPROVE/REJECT/CANCEL/RESUBMIT), ip, INSERT전용 | 충족(2.5) |
| 11.2 approval_corrections | 필드 전체 + reason 필수 | 충족(2.6) |
| PDF 보관 | sales_document_pdf 패턴 복제 + 해시/다운로드 | 충족(2.7) |
| 7장 API 14행 | 메서드/경로/권한 1:1 | 충족(6장) |
| 6·12장 상태머신/권한 | 차례·본인·즉시종료·회수범위·APPROVED잠금 서비스 강제 | 충족(4.4) |
| 16.3 불변식 | 차례 본인만, ADMIN 대리불가, APPROVED 불변, 반려 즉시종료, 회수 1차 전, actions/corrections UPDATE/DELETE API 없음, 정정 사유필수, weasyprint 직접 import 금지 | 설계 반영(4·6·7장) |
| 기존 명명규칙 | Base/comment/타임스탬프/services 3계층/deps 주입/response_model | 충족 |
| alembic 명명 | down_revision=h4i5j6k7l8m9, 파일명 컨벤션, upgrade/downgrade 쌍 | 충족(2.8) |
| position 중복추가 없음 | — | **명시적으로 추가 안 함** |

---

## 10. 열린 결정 / 리스크 (사람 결정 필요)

1. **도장 색**: v0.2 9.1 = **빨강 `#C00000`**(기본 채택). 그러나 루트 예시 `출력문서_예시_출장신청서.html`은 일부 **파랑 `#1456b8`** 사용(파일 내 두 색 혼재 확인됨). → 최종 도장/검증라인 색 1개 확정 필요(설계 기본값은 빨강).
2. **문서 열람권한 구현 방식**: "결재선 포함자|기안자|ADMIN" 판정을 (a) 매 조회 시 lines join 검사 vs (b) 별도 권한 헬퍼. 권장 (a). ADMIN 감사 열람 범위 확인 필요.
3. **IP 추출 방법**: `request.client.host` vs `X-Forwarded-For`(Nginx 프록시 뒤). 운영이 Nginx이므로 `X-Forwarded-For` 우선 파싱 여부 결정 필요.
4. **seal_snapshot 저장 형태**: VARCHAR(300)에 SVG 전체는 초과 위험 → (a)식별자만 저장+출력 시 재생성(권장) vs (b)컬럼을 Text로. 결정 필요.
5. **doc_number 채번 시점**: create_draft(권장) vs submit. 임시저장 출력에 번호 노출 여부와 연동.
6. **재상신 시 결재선 변경 허용 여부**: v0.2 "상신 후 수정 금지" vs 재상신은 새 사이클. 기본=동일 결재선 재사용. 변경 허용할지 결정 필요.
7. **box 탭 'in_progress' 분리 여부**: 화면 8.1은 4탭(기안/대기/진행중/완료), API box는 3값. 진행중 탭을 별 box 값으로 둘지.
8. **회사 정보(부록B)**: 직급명, 결재란 칸 명칭(담당/팀장/이사/대표), 회사 로고 파일, AP-YYYY-NNNN 확정 — 출력 템플릿/도장에 필요.
