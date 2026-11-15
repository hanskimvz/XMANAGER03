"""
생산 요청서 Service
비즈니스 로직을 처리합니다.

v0.20.0: 생산 요청서 기능 추가
- 생산 요청서 CRUD
- 상태 전이 (REQUESTED → APPROVED/REJECTED)
- 작업지시서 연동

v0.22.0: 다중 제품 지원
- ProductionRequestItem 관리
"""

from typing import Optional, List, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.repositories.production_request_repository import ProductionRequestRepository
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.schemas.production_request import (
    ProductionRequestCreate,
    ProductionRequestUpdate,
    ProductionRequestStatus,
    ProductionRequestApprove,
    ProductionRequestReject,
    ProductionRequestHold,
)
from app.utils.number_generator import generate_pr_number
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException,
)


class ProductionRequestService:
    """
    생산 요청서 서비스

    생산 요청서 관련 비즈니스 로직을 캡슐화합니다.
    - 요청서 CRUD
    - 상태 전이 (REQUESTED → APPROVED/REJECTED/HOLD)
    - 작업지시서 생성 연동
    """

    # 상태 전이 규칙 정의
    VALID_TRANSITIONS = {
        ProductionRequestStatus.REQUESTED: [
            ProductionRequestStatus.APPROVED,
            ProductionRequestStatus.IN_PROGRESS,  # 확인은 체크박스로 기록, 생산 시작은 요청에서 바로(v0.85.0)
            ProductionRequestStatus.REJECTED,
            ProductionRequestStatus.HOLD,
            ProductionRequestStatus.CANCELLED
        ],
        ProductionRequestStatus.HOLD: [
            ProductionRequestStatus.REQUESTED,  # 보류 해제
            ProductionRequestStatus.REJECTED,
            ProductionRequestStatus.CANCELLED
        ],
        ProductionRequestStatus.APPROVED: [
            ProductionRequestStatus.REQUESTED,   # 확인 취소(미확인으로 되돌리기)
            ProductionRequestStatus.IN_PROGRESS,
            ProductionRequestStatus.CANCELLED
        ],
        ProductionRequestStatus.IN_PROGRESS: [
            ProductionRequestStatus.COMPLETED,
            ProductionRequestStatus.SHIPPED,
            ProductionRequestStatus.CANCELLED
        ],
        ProductionRequestStatus.COMPLETED: [
            ProductionRequestStatus.SHIPPED,
        ],
        ProductionRequestStatus.SHIPPED: [
            ProductionRequestStatus.DELIVERED,
        ],
        ProductionRequestStatus.DELIVERED: [],  # 발송 완료 후 변경 불가
        ProductionRequestStatus.REJECTED: [
            ProductionRequestStatus.REQUESTED,  # 반려 → 수정 후 재요청
        ],
        ProductionRequestStatus.CANCELLED: [],  # 취소 후 변경 불가
    }

    def __init__(self, db: Session, actor_id: Optional[int] = None):
        self.db = db
        self.repository = ProductionRequestRepository(db)
        self.actor_id = actor_id  # 행위자(로그인 사용자) id — 생성/수정/승인자 기록용

    # ==================== 알림 ====================

    def _notify(self, build_fn) -> None:
        """커밋 후 알림 발송(best-effort — 실패해도 본 흐름에 영향 없음)."""
        try:
            from app.services.notification_service import NotificationService
            build_fn(NotificationService(self.db))
            self.db.commit()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("생산요청 알림 발송 실패")

    def _notify_stage_group(self, pr_full, event: str) -> None:
        """생산 단계별 지정 수신자(그룹)에게 알림. event ∈ requested/in_progress/shipped."""
        from app.services.production_notify import get_notify_recipient_ids
        recips = [r for r in get_notify_recipient_ids(self.db, event) if r != self.actor_id]
        if not recips:
            return
        if event == "requested":
            self._notify(lambda ns: ns.notify_production_requested(pr_full, recips, self.actor_id))
        elif event == "in_progress":
            self._notify(lambda ns: ns.notify_production_started(pr_full, recips, self.actor_id))
        elif event == "shipped":
            self._notify(lambda ns: ns.notify_production_shipped_group(pr_full, recips, self.actor_id))

    # ==================== 조회 ====================

    def get(self, id: int) -> Optional[ProductionRequest]:
        """ID로 생산 요청서 조회"""
        return self.repository.get_by_id_with_relations(id)

    def get_or_raise(self, id: int) -> ProductionRequest:
        """ID로 생산 요청서 조회 (없으면 예외)"""
        pr = self.repository.get_by_id_with_relations(id)
        if not pr:
            raise NotFoundException("생산 요청서", id)
        return pr

    def get_by_request_number(self, request_number: str) -> Optional[ProductionRequest]:
        """요청서 번호로 조회"""
        return self.repository.get_by_request_number_with_relations(request_number)

    def search_production_requests(
        self,
        keyword: Optional[str] = None,
        status: Optional[ProductionRequestStatus] = None,
        customer_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        priority: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[ProductionRequest]:
        """생산 요청서 검색"""
        # 콤마 구분 다중 상태 허용(예: "REQUESTED,APPROVED"). 단일도 그대로 동작.
        status_value = (status.value if hasattr(status, "value") else status) if status else None
        return self.repository.search_production_requests(
            keyword=keyword,
            status=status_value,
            customer_id=customer_id,
            from_date=from_date,
            to_date=to_date,
            priority=priority,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    def search_production_requests_with_count(
        self,
        keyword: Optional[str] = None,
        status: Optional[ProductionRequestStatus] = None,
        customer_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        priority: Optional[int] = None,
        is_draft: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[ProductionRequest], int]:
        """생산 요청서 검색 + 총 개수"""
        # 콤마 구분 다중 상태 허용(예: "REQUESTED,APPROVED"). 단일도 그대로 동작.
        status_value = (status.value if hasattr(status, "value") else status) if status else None
        return self.repository.search_production_requests_with_count(
            keyword=keyword,
            status=status_value,
            customer_id=customer_id,
            from_date=from_date,
            to_date=to_date,
            priority=priority,
            is_draft=is_draft,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    def get_pending_requests(self, skip: int = 0, limit: int = 50) -> List[ProductionRequest]:
        """대기 중인 요청서 조회"""
        return self.repository.get_pending_requests(skip, limit)

    def get_pending_requests_count(self) -> int:
        """대기 중인 요청서 개수"""
        return self.repository.get_pending_requests_count()

    # ==================== 생성 ====================

    def _check_protected_parts(self, items, customer_id, override: bool = False) -> None:
        """전속(독점) 계약 위반 검사 — 보호 부품을 전속 고객이 아닌 고객으로 생산요청 시 차단.

        override=True(관리자 확인) 또는 보호 부품이 없으면 통과. 비보호 부품은 전혀 영향 없음.
        """
        if override or not items:
            return
        from app.models.parts import Part
        part_ids = [getattr(it, "product_part_id", None) for it in items]
        part_ids = [pid for pid in part_ids if pid]
        if not part_ids:
            return
        protected = self.db.query(Part).filter(
            Part.id.in_(part_ids),
            Part.is_protected == True,  # noqa: E712
        ).all()
        for p in protected:
            if p.protected_customer_id and p.protected_customer_id != customer_id:
                cust = p.protected_customer
                name = cust.partner_name if cust else f"고객 #{p.protected_customer_id}"
                raise BusinessRuleException(
                    f"'{p.part_number}' 은(는) '{name}' 전속(독점) 계약 품목입니다. "
                    "다른 고객으로는 생산요청할 수 없습니다. (관리자 확인 필요)"
                )

    def create_production_request(
        self,
        pr_in: ProductionRequestCreate,
        created_by_name: Optional[str] = None,
        allow_protected_override: bool = False,
    ) -> ProductionRequest:
        """
        생산 요청서 생성 (v0.22.0 다중 제품 지원)

        Args:
            pr_in: 생산 요청서 생성 데이터
            created_by_name: 작성자명 (로그인 사용자 — 영업담당자로 기록)

        Returns:
            생성된 생산 요청서
        """
        # 전속(독점) 계약 위반 검사 (보호 부품 → 다른 고객 차단)
        if pr_in.items:
            self._check_protected_parts(pr_in.items, pr_in.customer_id, override=allow_protected_override)

        # 요청서 번호 자동 생성
        request_number = generate_pr_number(self.db)

        # 첫번째 항목을 deprecated 필드에 저장 (호환성)
        first_item = pr_in.items[0] if pr_in.items else None

        # 영업담당자(작성자명): 로그인 사용자 우선, 없으면 payload 값
        prepared_by_name = created_by_name or pr_in.prepared_by_name

        # 생산 요청서 생성
        pr = ProductionRequest(
            request_number=request_number,
            customer_id=pr_in.customer_id,
            customer_order_no=pr_in.customer_order_no,
            # deprecated 필드 (호환성용 - 첫번째 제품)
            product_part_id=first_item.product_part_id if first_item else pr_in.product_part_id,
            requested_quantity=first_item.requested_quantity if first_item else pr_in.requested_quantity,
            due_date=pr_in.due_date,
            priority=pr_in.priority,
            pi_number=pr_in.pi_number,
            payment_status=pr_in.payment_status or "UNPAID",
            prepared_by_name=prepared_by_name,
            remarks=pr_in.remarks,
            requested_by=pr_in.requested_by or self.actor_id,
            requested_at=datetime.now(),
            status=ProductionRequestStatus.REQUESTED.value,
            created_by=self.actor_id,
            updated_by=self.actor_id,
        )
        self.db.add(pr)
        self.db.flush()  # ID 생성을 위해 flush

        # v0.22.0: 제품 항목 생성
        if pr_in.items:
            for idx, item in enumerate(pr_in.items):
                pr_item = ProductionRequestItem(
                    production_request_id=pr.id,
                    product_part_id=item.product_part_id,
                    # v0.80.0: BOM 미등록(외주) 항목 — 직접 입력 품번/품명
                    custom_product_code=getattr(item, "custom_product_code", None),
                    custom_product_name=getattr(item, "custom_product_name", None),
                    requested_quantity=item.requested_quantity,
                    uom=item.uom,
                    line_remarks=item.line_remarks,
                    customer_requirements=item.customer_requirements,
                    sort_order=item.sort_order if item.sort_order else idx,
                )
                self.db.add(pr_item)

        self.db.commit()

        pr_full = self.repository.get_by_id_with_relations(pr.id)
        # #1 생산요청 등록 → '생산요청' 단계 지정 인원에게 알림(본인 제외)
        self._notify_stage_group(pr_full, "requested")
        return pr_full

    def submit_draft(self, pr_id: int) -> ProductionRequest:
        """초안(is_draft) 생산요청을 정식으로 전송 — 생산팀 노출 + '생산요청' 단계 알림.

        영업이 특이사항 입력 후 '생산팀에 요청'할 때 호출. 이미 정식이면 알림 재발송 안 함.
        """
        pr = self.get_or_raise(pr_id)
        was_draft = bool(getattr(pr, "is_draft", False))
        if was_draft:
            pr.is_draft = False
            pr.updated_by = self.actor_id
            self.db.commit()
        pr_full = self.repository.get_by_id_with_relations(pr_id)
        if was_draft:
            self._notify_stage_group(pr_full, "requested")
        return pr_full

    def withdraw_draft(self, pr_id: int) -> bool:
        """초안(is_draft) 생산요청을 영업이 회수(삭제).

        초안은 아직 생산팀에 전송·노출되지 않은 임시 상태라, 영업이 직접 회수할 수 있게 한다.
        정식 전송된(is_draft=False) 건은 이 경로로 삭제 불가 — 오회수 방지.
        """
        pr = self.get_or_raise(pr_id)
        if not bool(getattr(pr, "is_draft", False)):
            raise BusinessRuleException(
                "임시(초안) 상태의 생산요청만 회수할 수 있습니다. 이미 생산팀에 전송된 건은 회수할 수 없습니다.",
                rule="DRAFT_ONLY",
            )
        return self.repository.delete(pr)

    # ==================== 수정/삭제 ====================

    def update_production_request(self, pr_id: int, pr_in: ProductionRequestUpdate, allow_protected_override: bool = False) -> ProductionRequest:
        """
        생산 요청서 수정 (v0.22.0 다중 제품 지원)

        출고(SHIPPED) 이전 모든 상태에서 영업 수정 가능(v0.78.0 확장).
        수정 시 연결된 작업지시서에 source_request_modified 플래그 설정

        Args:
            pr_id: 생산 요청서 ID
            pr_in: 수정 데이터

        Returns:
            수정된 생산 요청서
        """
        pr = self.get_or_raise(pr_id)

        # 출고(SHIPPED) 이전 모든 상태에서 영업 수정 가능(요청/보류/승인/반려/진행중/완료).
        # 출고완료·발송완료·취소 건만 수정 불가.
        locked_statuses = [
            ProductionRequestStatus.SHIPPED.value,
            ProductionRequestStatus.DELIVERED.value,
            ProductionRequestStatus.CANCELLED.value,
        ]
        if pr.status in locked_statuses:
            raise BusinessRuleException(
                f"'{pr.status}' 상태의 요청서는 수정할 수 없습니다. "
                "출고 완료 이전 상태에서만 수정 가능합니다."
            )

        update_data = pr_in.model_dump(exclude_unset=True)
        if not update_data:
            return self.repository.get_by_id_with_relations(pr_id)

        # v0.22.0: items 업데이트 (v0.31.0: 작업지시서 연결 보호)
        # v0.67.0: id 있는 항목은 in-place 수정 → customer_requirements/pi_item_id/pi_document_id 보존
        #          (기존엔 스키마에 id가 없어 매번 삭제·재생성되며 고객요구사항·PI연결이 소실됐음)
        if pr_in.items is not None:
            # 전속(독점) 계약 위반 검사 — 고객이 바뀔 수 있으니 유효 고객 기준
            effective_customer = update_data.get("customer_id", pr.customer_id)
            self._check_protected_parts(pr_in.items, effective_customer, override=allow_protected_override)

            existing_items = {item.id: item for item in pr.items}
            new_items_data = list(pr_in.items)

            # 클라이언트가 유지하겠다고 보낸 기존 항목 id
            incoming_ids = {
                item.id for item in new_items_data
                if getattr(item, 'id', None) and item.id in existing_items
            }

            # 유지 목록에 없는 기존 항목 삭제 (작업지시서 연결 항목은 보호)
            for existing_item in list(pr.items):
                if existing_item.id not in incoming_ids:
                    if existing_item.work_order_id:
                        continue
                    self.db.delete(existing_item)

            # DELETE를 먼저 반영 (시퀀스 충돌 방지)
            self.db.flush()

            for idx, item in enumerate(new_items_data):
                item_id = getattr(item, 'id', None)
                if item_id and item_id in existing_items:
                    # 기존 항목 in-place 수정 — pi_item_id/pi_document_id는 건드리지 않아 PI 추적 유지
                    existing = existing_items[item_id]
                    existing.product_part_id = item.product_part_id
                    existing.custom_product_code = getattr(item, "custom_product_code", None)
                    existing.custom_product_name = getattr(item, "custom_product_name", None)
                    existing.requested_quantity = item.requested_quantity
                    existing.uom = item.uom
                    existing.line_remarks = item.line_remarks
                    existing.customer_requirements = item.customer_requirements
                    existing.sort_order = item.sort_order if item.sort_order else idx
                else:
                    # 신규 항목 (수동 추가) — PI 링크 없음. BOM 미등록(외주) 항목 포함
                    pr_item = ProductionRequestItem(
                        production_request_id=pr.id,
                        product_part_id=item.product_part_id,
                        custom_product_code=getattr(item, "custom_product_code", None),
                        custom_product_name=getattr(item, "custom_product_name", None),
                        requested_quantity=item.requested_quantity,
                        uom=item.uom,
                        line_remarks=item.line_remarks,
                        customer_requirements=item.customer_requirements,
                        sort_order=item.sort_order if item.sort_order else idx,
                    )
                    self.db.add(pr_item)

            # deprecated 필드 업데이트 (첫번째 제품)
            if new_items_data:
                first_item = new_items_data[0]
                pr.product_part_id = first_item.product_part_id
                pr.requested_quantity = first_item.requested_quantity

            # items는 update_from_dict에서 제외
            update_data.pop('items', None)

        # 나머지 필드 업데이트
        self.repository.update_from_dict(pr, update_data)
        pr.updated_by = self.actor_id

        # v0.21.0: 연결된 작업지시서에 수정 알림 플래그 설정
        if pr.work_orders:
            for wo in pr.work_orders:
                wo.source_request_modified = True

        self.db.commit()

        return self.repository.get_by_id_with_relations(pr_id)

    # 공정 확인표 표준 항목 (생산요청서 양식 기준) — 생산 시작 시 자동 시딩
    DEFAULT_PROCESS_CHECKS = [
        "각 구성품 자재 출고 확인 (고객 요구사항 포함)",
        "조립 전 도면 및 고객 요구사항 확인",
        "조립 절차에 따라 작업진행 확인",
        "특성검사 확인",
        "포장 상태 및 중량확인",
    ]

    @classmethod
    def _default_process_checks(cls) -> list:
        return [
            {"seq": i + 1, "content": c, "date": "", "checker": "", "note": "", "action": ""}
            for i, c in enumerate(cls.DEFAULT_PROCESS_CHECKS)
        ]

    def seed_process_checks_if_empty(self, pr) -> None:
        """생산 시작 시 공정 확인표가 비어 있으면 표준 5개 항목으로 시딩."""
        if not pr.process_checks:
            pr.process_checks = self._default_process_checks()

    def update_production_notes(self, pr_id: int, manager_memo=None, process_checks=None) -> "ProductionRequest":
        """생산 시작 단계 자료(총괄자 메모 / 공정 확인표) 저장.

        status 워크플로우와 무관 — IN_PROGRESS 등에서도 저장 가능(None 필드는 미변경).
        """
        pr = self.get_or_raise(pr_id)
        if manager_memo is not None:
            pr.manager_memo = manager_memo
        if process_checks is not None:
            pr.process_checks = process_checks
        pr.updated_by = self.actor_id
        self.db.commit()
        return self.repository.get_by_id_with_relations(pr_id)

    def update_flags(self, pr_id: int, **flags) -> "ProductionRequest":
        """진행 체크박스(insert_shipped / production_shipped / needs_review) 토글.

        status 워크플로우와 무관 — 어떤 상태에서도 가능. None인 플래그는 변경하지 않음.

        출고 완료시각(v0.84.0):
          - 켜기: 명시 날짜(_at)가 오면 그 날짜로, 없고 기존 시각이 있으면 보존(실수 재기록 방지),
                  둘 다 없으면 now().
          - 명시 날짜만 오고 플래그는 그대로면(켜진 상태) 날짜만 수정.
          - 끄기: 시각 NULL.
        """
        from datetime import date as _date
        pr = self.get_or_raise(pr_id)

        def _to_dt(v):
            if isinstance(v, _date) and not isinstance(v, datetime):
                return datetime.combine(v, datetime.min.time())
            return v

        # 검토 필요 플래그(시각 없음). 꺼짐→켜짐 전환 시 영업 담당자에게 알림.
        nr = flags.get("needs_review")
        review_turned_on = False
        if nr is not None:
            if bool(nr) and not pr.needs_review:
                review_turned_on = True
            pr.needs_review = bool(nr)

        # 인서트 해당없음(N/A) — 켜면 출고 상태 해제(상호배타)
        na = flags.get("insert_not_applicable")
        if na is not None:
            pr.insert_not_applicable = bool(na)
            if na:
                pr.insert_shipped = False
                pr.insert_shipped_at = None

        # 출고 플래그(완료시각 포함)
        for key in ("insert_shipped", "production_shipped"):
            val = flags.get(key)
            explicit_at = _to_dt(flags.get(f"{key}_at"))
            if val is not None:
                setattr(pr, key, bool(val))
                if val:
                    # 인서트 출고를 켜면 N/A 해제(상호배타)
                    if key == "insert_shipped":
                        pr.insert_not_applicable = False
                    if explicit_at is not None:
                        setattr(pr, f"{key}_at", explicit_at)
                    elif getattr(pr, f"{key}_at", None) is None:
                        setattr(pr, f"{key}_at", datetime.now())
                    # 기존 시각이 있으면 보존(재기록 안 함)
                else:
                    setattr(pr, f"{key}_at", None)
            elif explicit_at is not None and getattr(pr, key, False):
                # 플래그는 그대로(켜짐), 날짜만 수정
                setattr(pr, f"{key}_at", explicit_at)
        # 검토 필요 사유: 명시적으로 전달되면 저장. needs_review를 끄면 사유도 정리.
        if "review_note" in flags and flags.get("review_note") is not None:
            pr.review_note = flags.get("review_note") or None
        if flags.get("needs_review") is False:
            pr.review_note = None
        pr.updated_by = self.actor_id
        self.db.commit()
        pr_full = self.repository.get_by_id_with_relations(pr_id)
        # 생산팀 검토 요청 → 해당 건 영업 담당자(생성자)에게 알림
        if review_turned_on:
            self._notify(lambda ns: ns.notify_review_requested(pr_full, self.actor_id))
        return pr_full

    def ship_with_packing(self, pr_id: int, packing_list: Optional[list] = None) -> "ProductionRequest":
        """생산 출고 처리 — packing list 저장과 함께 SHIPPED로 전환.

        IN_PROGRESS(또는 COMPLETED) → SHIPPED. 출고시각·생산출고 플래그 자동 기록.
        packing_list(박스별 포장 명세)는 이후 영업 CI 발행에 승계된다.
        """
        pr = self.get_or_raise(pr_id)
        self._validate_transition(pr.status, ProductionRequestStatus.SHIPPED)
        now = datetime.now()
        if packing_list is not None:
            pr.packing_list = packing_list
        pr.status = ProductionRequestStatus.SHIPPED.value
        pr.shipped_at = pr.shipped_at or now
        pr.production_shipped = True
        pr.production_shipped_at = pr.production_shipped_at or now
        if not pr.due_date:  # 출고 시 납기일 자동 입력(비어있을 때 = 출고일)
            pr.due_date = pr.shipped_at.date()
        pr.updated_at = now
        pr.updated_by = self.actor_id
        self.db.commit()
        pr_full = self.repository.get_by_id_with_relations(pr_id)
        # #3 출고 완료 → 해당 건 영업 담당자(생성자)에게 알림 + '출고' 단계 지정 인원(그룹)에게 알림
        self._notify(lambda ns: ns.notify_production_shipped(pr_full, self.actor_id))
        self._notify_stage_group(pr_full, "shipped")
        return pr_full

    def update_packing_list(self, pr_id: int, packing_list: Optional[list]) -> "ProductionRequest":
        """출고 후 패킹 정보 수정 — 상태 전이 없이 packing_list 만 갱신.

        실제 포장이 출고 이후 바뀌는 경우(박스 재구성·중량 정정 등)를 반영한다.
        상태·출고시각은 건드리지 않으므로 출고 이력이 보존된다.
        이미 발행된 CI에는 자동 반영되지 않는다(CI는 발행 시점 승계).
        """
        pr = self.get_or_raise(pr_id)
        pr.packing_list = packing_list
        pr.updated_at = datetime.now()
        pr.updated_by = self.actor_id
        self.db.commit()
        return self.repository.get_by_id_with_relations(pr_id)

    def update_box_plan(self, pr_id: int, box_plan: Optional[list]) -> "ProductionRequest":
        """분할선적 박스 분할계획 저장 — 영업이 작성(자동생성 후 수기조정).

        box_plan: [{box_no, items:[{pr_item_id, product_code, quantity}], remarks}] 또는 None(해제).
        """
        pr = self.get_or_raise(pr_id)
        pr.box_plan = box_plan if box_plan else None
        pr.updated_at = datetime.now()
        pr.updated_by = self.actor_id
        self.db.commit()
        return self.repository.get_by_id_with_relations(pr_id)

    def update_due_date(self, pr_id: int, new_due: Optional[date]) -> "ProductionRequest":
        """납기일 변경(영업이 캘린더/현황에서 조정) — 변경 시 생산팀(요청 단계 그룹)에 알림."""
        from app.services.production_notify import get_notify_recipient_ids
        pr = self.get_or_raise(pr_id)
        old_due = pr.due_date
        if old_due == new_due:
            return self.repository.get_by_id_with_relations(pr_id)  # 변화 없으면 알림도 없음
        pr.due_date = new_due
        pr.updated_at = datetime.now()
        pr.updated_by = self.actor_id
        self.db.commit()
        pr_full = self.repository.get_by_id_with_relations(pr_id)
        recips = get_notify_recipient_ids(self.db, "requested")
        self._notify(lambda ns: ns.notify_due_date_changed(pr_full, recips, self.actor_id, old_due, new_due))
        return pr_full

    def delete_production_request(self, pr_id: int) -> bool:
        """
        생산 요청서 완전 삭제 (REQUESTED, CANCELLED, REJECTED 상태에서만)

        Args:
            pr_id: 생산 요청서 ID

        Returns:
            삭제 성공 여부
        """
        pr = self.get_or_raise(pr_id)

        # REQUESTED, CANCELLED, REJECTED 상태에서만 삭제 가능
        deletable_statuses = [
            ProductionRequestStatus.REQUESTED.value,
            ProductionRequestStatus.CANCELLED.value,
            ProductionRequestStatus.REJECTED.value,
        ]
        if pr.status not in deletable_statuses:
            raise BusinessRuleException(
                f"'{pr.status}' 상태의 요청서는 삭제할 수 없습니다. "
                "요청됨, 취소됨 또는 반려됨 상태에서만 삭제 가능합니다."
            )

        return self.repository.delete(pr)

    # ==================== 상태 전이 ====================

    def _validate_transition(self, current: str, target: ProductionRequestStatus) -> None:
        """상태 전이 유효성 검사"""
        current_status = ProductionRequestStatus(current)
        valid_targets = self.VALID_TRANSITIONS.get(current_status, [])

        if target not in valid_targets:
            raise BusinessRuleException(
                f"'{current}' 상태에서 '{target.value}' 상태로 변경할 수 없습니다. "
                f"가능한 상태: {[s.value for s in valid_targets]}"
            )

    def approve(self, pr_id: int, request: ProductionRequestApprove) -> ProductionRequest:
        """
        생산 요청서 승인 (REQUESTED → APPROVED)

        Args:
            pr_id: 생산 요청서 ID
            request: 승인 요청

        Returns:
            수정된 생산 요청서
        """
        pr = self.get_or_raise(pr_id)
        self._validate_transition(pr.status, ProductionRequestStatus.APPROVED)

        pr.status = ProductionRequestStatus.APPROVED.value
        # 승인자는 로그인 사용자(토큰)에서 취득 — 요청 본문 값보다 우선(위조 방지, ①-4)
        pr.approved_by = self.actor_id or request.approved_by
        pr.approved_at = datetime.now()
        if request.remarks:
            pr.remarks = (pr.remarks + "\n[승인] " if pr.remarks else "[승인] ") + request.remarks
        pr.updated_at = datetime.now()
        pr.updated_by = self.actor_id

        self.db.commit()

        return self.repository.get_by_id_with_relations(pr_id)

    def create_work_order_for_item(self, pr_id: int, item_id: int) -> dict:
        """
        생산요청 품목별 작업지시서 개별 생성 (v0.29.0)
        승인된 생산요청의 특정 품목에 대해 작업지시서를 생성합니다.
        """
        from app.models.work_order import WorkOrder
        from app.models.production_request import ProductionRequestItem
        from app.utils.number_generator import generate_wo_number

        pr = self.get_or_raise(pr_id)
        if pr.status not in ("APPROVED", "IN_PROGRESS"):
            raise ValidationException("승인된 생산요청만 작업지시서를 생성할 수 있습니다")

        # 해당 품목 조회
        item = self.db.query(ProductionRequestItem).filter(
            ProductionRequestItem.id == item_id,
            ProductionRequestItem.production_request_id == pr_id,
        ).first()
        if not item:
            raise NotFoundException("품목", item_id)
        if item.work_order_id:
            raise ValidationException(f"이미 작업지시서가 생성된 품목입니다 (WO ID: {item.work_order_id})")

        # 작업지시서 생성
        wo_number = generate_wo_number(self.db)
        wo = WorkOrder(
            wo_number=wo_number,
            production_request_id=pr.id,
            product_part_id=item.product_part_id,
            order_quantity=item.requested_quantity,
            customer_id=pr.customer_id,
            customer_order_no=pr.customer_order_no,
            priority=pr.priority,
            status="RECEIVED",
        )
        self.db.add(wo)
        self.db.flush()

        # 품목에 WO 연결
        item.work_order_id = wo.id

        # 생산요청 상태를 IN_PROGRESS로 변경 (첫 WO 생성 시)
        started = pr.status == "APPROVED"
        if started:
            pr.status = "IN_PROGRESS"
            self.seed_process_checks_if_empty(pr)

        # 모든 품목에 WO가 생성되었는지 확인
        all_items = self.db.query(ProductionRequestItem).filter(
            ProductionRequestItem.production_request_id == pr_id,
        ).all()
        all_assigned = all(i.work_order_id is not None for i in all_items)

        self.db.commit()

        # 생산 시작(진행중 진입) → '진행' 단계 지정 인원에게 알림
        if started:
            self._notify_stage_group(self.repository.get_by_id_with_relations(pr_id), "in_progress")

        return {
            "success": True,
            "work_order_id": wo.id,
            "wo_number": wo.wo_number,
            "all_items_assigned": all_assigned,
            "message": f"작업지시서 {wo.wo_number} 생성 완료" + (" (전체 품목 배정 완료)" if all_assigned else ""),
        }

    def reject(self, pr_id: int, request: ProductionRequestReject) -> ProductionRequest:
        """
        생산 요청서 반려 (REQUESTED/HOLD → REJECTED)

        Args:
            pr_id: 생산 요청서 ID
            request: 반려 요청

        Returns:
            수정된 생산 요청서
        """
        pr = self.get_or_raise(pr_id)
        self._validate_transition(pr.status, ProductionRequestStatus.REJECTED)

        pr.status = ProductionRequestStatus.REJECTED.value
        pr.rejection_reason = request.rejection_reason
        pr.updated_at = datetime.now()
        pr.updated_by = self.actor_id

        self.db.commit()

        pr_full = self.repository.get_by_id_with_relations(pr_id)
        # #2 반려 → 영업 담당자(생성자)에게 알림
        self._notify(lambda ns: ns.notify_production_rejected(pr_full, self.actor_id))
        return pr_full

    def hold(self, pr_id: int, request: ProductionRequestHold) -> ProductionRequest:
        """
        생산 요청서 보류 (REQUESTED → HOLD)

        Args:
            pr_id: 생산 요청서 ID
            request: 보류 요청

        Returns:
            수정된 생산 요청서
        """
        pr = self.get_or_raise(pr_id)
        self._validate_transition(pr.status, ProductionRequestStatus.HOLD)

        pr.status = ProductionRequestStatus.HOLD.value
        if request.remarks:
            pr.remarks = (pr.remarks + "\n[보류] " if pr.remarks else "[보류] ") + request.remarks
        pr.updated_at = datetime.now()
        pr.updated_by = self.actor_id

        self.db.commit()

        return self.repository.get_by_id_with_relations(pr_id)

    def release_hold(self, pr_id: int) -> ProductionRequest:
        """
        보류 해제 (HOLD → REQUESTED)

        Args:
            pr_id: 생산 요청서 ID

        Returns:
            수정된 생산 요청서
        """
        pr = self.get_or_raise(pr_id)
        self._validate_transition(pr.status, ProductionRequestStatus.REQUESTED)

        pr.status = ProductionRequestStatus.REQUESTED.value
        pr.updated_at = datetime.now()
        pr.updated_by = self.actor_id

        self.db.commit()

        return self.repository.get_by_id_with_relations(pr_id)

    def cancel(self, pr_id: int, reason: Optional[str] = None) -> ProductionRequest:
        """
        생산 요청서 취소

        Args:
            pr_id: 생산 요청서 ID
            reason: 취소 사유

        Returns:
            수정된 생산 요청서
        """
        pr = self.get_or_raise(pr_id)
        self._validate_transition(pr.status, ProductionRequestStatus.CANCELLED)

        pr.status = ProductionRequestStatus.CANCELLED.value
        if reason:
            pr.remarks = (pr.remarks + "\n[취소] " if pr.remarks else "[취소] ") + reason
        pr.updated_at = datetime.now()
        pr.updated_by = self.actor_id

        self.db.commit()

        return self.repository.get_by_id_with_relations(pr_id)

    def update_status_to_in_progress(self, pr_id: int) -> ProductionRequest:
        """
        진행중 상태로 변경 (APPROVED → IN_PROGRESS)
        작업지시서 생성 시 호출

        Args:
            pr_id: 생산 요청서 ID

        Returns:
            수정된 생산 요청서
        """
        pr = self.get_or_raise(pr_id)

        started = pr.status == ProductionRequestStatus.APPROVED.value
        if started:
            pr.status = ProductionRequestStatus.IN_PROGRESS.value
            pr.updated_at = datetime.now()
            self.seed_process_checks_if_empty(pr)
            self.db.commit()

        pr_full = self.repository.get_by_id_with_relations(pr_id)
        # 생산 시작(진행중 진입) → '진행' 단계 지정 인원에게 알림
        if started:
            self._notify_stage_group(pr_full, "in_progress")
        return pr_full

    def update_status_to_completed(self, pr_id: int) -> ProductionRequest:
        """
        완료 상태로 변경 (IN_PROGRESS → COMPLETED)
        모든 작업지시서 완료 시 호출

        Args:
            pr_id: 생산 요청서 ID

        Returns:
            수정된 생산 요청서
        """
        pr = self.get_or_raise(pr_id)

        if pr.status == ProductionRequestStatus.IN_PROGRESS.value:
            pr.status = ProductionRequestStatus.COMPLETED.value
            pr.updated_at = datetime.now()
            self.db.commit()

        return self.repository.get_by_id_with_relations(pr_id)
