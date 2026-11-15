"""
영업 문서 서비스
Quotation / PI / CI CRUD + 번호 채번 + 문서 전환 로직
"""

from datetime import date
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, desc, case

from app.models.sales_document import SalesDocument, SalesDocumentItem
from app.models.business_partner import BusinessPartner
from app.schemas.sales_document import (
    SalesDocumentCreate,
    SalesDocumentUpdate,
    SalesDocumentItemCreate,
    ConvertToNextRequest,
)


def compute_pi_production_progress(prs) -> Optional[dict]:
    """PI에 연결된 생산요청 목록 → 진행 집계(집계 방식 A: 병목 = 가장 덜 진행된 열린 요청).

    각 생산요청을 3단계로 사상: 1=생산, 2=출고, 3=배송.
      · CANCELLED/REJECTED 는 분모에서 제외
      · DELIVERED/delivered_at → 3(배송), SHIPPED/production_shipped → 2(출고), 그 외(REQUESTED·
        APPROVED·IN_PROGRESS·COMPLETED·HOLD) → 1(생산)
    반환: {pr_total, stage(=min, 병목/현재), counts{prod,ship,deliv}} · 활성 요청 없으면 None.
    """
    stages = []
    for pr in prs:
        st = (getattr(pr, "status", "") or "").upper()
        if st in ("CANCELLED", "REJECTED"):
            continue
        if st == "DELIVERED" or getattr(pr, "delivered_at", None):
            stages.append(3)
        elif st == "SHIPPED" or getattr(pr, "production_shipped", False):
            stages.append(2)
        else:
            stages.append(1)
    if not stages:
        return None
    return {
        "pr_total": len(stages),
        "stage": min(stages),
        "counts": {
            "prod": stages.count(1),
            "ship": stages.count(2),
            "deliv": stages.count(3),
        },
    }


class SalesDocumentService:
    """영업 문서 서비스"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _apply_charges(subtotal: Decimal, discount, shipping) -> Decimal:
        """소계에 할인 차감·배송비 가산을 반영한 최종 총액 (음수면 0)."""
        total = Decimal(str(subtotal)) - (discount or Decimal("0")) + (shipping or Decimal("0"))
        return total if total > 0 else Decimal("0")

    # ==================== 번호 채번 ====================

    def _generate_document_number(self, document_type: str, customer_id: int, document_date: date) -> str:
        """
        문서 번호 자동 생성
        형식: {PREFIX}-{업체코드}{날짜6자리}
        예: Q-BI260306, PI-IH260108, CI-CL250408

        같은 날짜+업체에 중복 시: Q-BI260306-B, Q-BI260306-C ...
        """
        prefix_map = {"QUOTATION": "Q", "PI": "PI", "CI": "CI", "INVOICE": "INV"}
        prefix = prefix_map.get(document_type, "Q")

        # 업체 코드 조회 (partner_code 우선, short_code fallback)
        customer = self.db.query(BusinessPartner).filter(BusinessPartner.id == customer_id).first()
        short_code = (customer.partner_code or customer.short_code or "XX").upper() if customer else "XX"

        # 날짜 포맷: YYMMDD
        date_str = document_date.strftime("%y%m%d")

        base_number = f"{prefix}-{short_code}{date_str}"

        # 중복 확인: 같은 base 로 시작하는 기존 번호 전부 조회
        existing_numbers = [
            n for (n,) in self.db.query(SalesDocument.document_number).filter(
                SalesDocument.document_number.like(f"{base_number}%")
            ).all()
        ]
        if not existing_numbers:
            return base_number

        # 이미 쓰인 접미사 수집(맨 번호=접미사 없음, base-B/-C… 만 인식; 레거시 -v2 등은 무시)
        used = set()
        for n in existing_numbers:
            if n == base_number:
                used.add("")           # 접미사 없는 원본
            elif n.startswith(base_number + "-"):
                suf = n[len(base_number) + 1:]
                if len(suf) == 1 and suf.isalpha():
                    used.add(suf.upper())
        # B, C, D … 중 비어있는 첫 글자 사용(삭제로 생긴 공백에도 충돌 없음)
        for c in "BCDEFGHIJKLMNOPQRSTUVWXYZ":
            if c not in used:
                return f"{base_number}-{c}"
        # 26개 초과(사실상 없음): 개수 기반 fallback
        return f"{base_number}-{len(existing_numbers) + 1}"

    # ==================== CRUD ====================

    def get_list(
        self,
        document_type: Optional[str] = None,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: Optional[str] = None,
        order_desc: bool = True,
        include_old_versions: bool = False,
    ) -> Tuple[List[SalesDocument], int]:
        """문서 목록 조회 (대표 제품 포함)"""
        query = self.db.query(SalesDocument).options(
            joinedload(SalesDocument.customer),
            joinedload(SalesDocument.items),  # v0.31.0: 대표 제품 표시용
        )

        # 이전 버전 포함 여부
        if not include_old_versions:
            query = query.filter(SalesDocument.is_latest == True)

        if document_type:
            query = query.filter(SalesDocument.document_type == document_type)
        if customer_id:
            query = query.filter(SalesDocument.customer_id == customer_id)
        if status:
            query = query.filter(SalesDocument.status == status)
        if payment_status:
            # 미입금(UNPAID)은 NULL/빈값도 포함
            if payment_status == "UNPAID":
                query = query.filter(
                    (SalesDocument.payment_status == "UNPAID")
                    | (SalesDocument.payment_status.is_(None))
                    | (SalesDocument.payment_status == "")
                )
                # 견적대용 PI는 실제 매출/미수가 아니므로 미입금 목록에서 제외
                query = query.filter(SalesDocument.is_quote_only.is_(False))
            else:
                query = query.filter(SalesDocument.payment_status == payment_status)
        if keyword:
            keyword_filter = f"%{keyword}%"
            query = query.filter(
                (SalesDocument.document_number.ilike(keyword_filter)) |
                (SalesDocument.customer_po_number.ilike(keyword_filter))
            )

        total = query.count()

        # 정렬
        sort_column_map = {
            'document_number': SalesDocument.document_number,
            'document_date': SalesDocument.document_date,
            'total_amount': SalesDocument.total_amount,
            'status': SalesDocument.status,
            'created_at': SalesDocument.created_at,
            'document_type': SalesDocument.document_type,
        }
        sort_col = sort_column_map.get(order_by, SalesDocument.created_at)
        primary = desc(sort_col) if order_desc else sort_col
        # PI 목록은 입금상태 우선(미입금→부분→완납)으로 전역 정렬 → 미입금이 항상 앞페이지에 모임.
        #   (NULL/빈값은 미입금으로 취급, 프론트 정렬 기준과 일치)
        if document_type == "PI":
            payment_priority = case(
                (SalesDocument.payment_status == "PARTIAL", 1),
                (SalesDocument.payment_status == "PAID", 2),
                else_=0,
            )
            items = query.order_by(payment_priority.asc(), primary).offset(skip).limit(limit).all()
        else:
            items = query.order_by(primary).offset(skip).limit(limit).all()

        # 대표 제품 정보 주입 (line_no 정렬 후 첫 번째 품목)
        for doc in items:
            doc_items = sorted(doc.items or [], key=lambda i: i.line_no or 0)
            if doc_items:
                first = doc_items[0]
                # product_code 우선, 없으면 description 첫 줄
                doc._representative_product = first.product_code or (first.description or '').split('\n')[0] or ''
                doc._item_count = len(doc_items)
            else:
                doc._representative_product = None
                doc._item_count = 0

        return items, total

    def get_by_id(self, doc_id: int) -> Optional[SalesDocument]:
        """문서 상세 조회"""
        return self.db.query(SalesDocument).options(
            joinedload(SalesDocument.customer),
            joinedload(SalesDocument.items),
            joinedload(SalesDocument.source_document),
        ).filter(SalesDocument.id == doc_id).first()

    def _log_document_created(self, doc: SalesDocument) -> None:
        """문서 생성 시, 연결된 영업활동(sales_activity)이 있으면 히스토리에 자동 기록.
        커밋은 호출측 트랜잭션에 편승(같은 트랜잭션에서 add만)."""
        if not getattr(doc, "sales_activity_id", None):
            return
        from app.models.sales_activity import SalesActivityLog
        labels = {"QUOTATION": "견적서(Q)", "PI": "PI", "CI": "CI", "INVOICE": "INVOICE"}
        label = labels.get(doc.document_type, doc.document_type)
        amt = ""
        if doc.total_amount is not None:
            try:
                amt = f" · {(doc.currency or '').strip()} {float(doc.total_amount):,.2f}".rstrip()
            except (TypeError, ValueError):
                amt = ""
        content = f"{label} 생성: {doc.document_number}{amt}"
        self.db.add(SalesActivityLog(
            activity_id=doc.sales_activity_id,
            log_type="DOCUMENT",
            content=content,
            logged_by=getattr(doc, "prepared_by", None),
        ))

    def create(self, data: SalesDocumentCreate) -> SalesDocument:
        """문서 생성"""
        # 번호 채번
        doc_number = self._generate_document_number(
            data.document_type.value, data.customer_id, data.document_date
        )

        # 문서 생성
        items_data = data.items
        doc_dict = data.model_dump(exclude={"items"})
        doc_dict["document_type"] = data.document_type.value
        doc_dict["document_number"] = doc_number

        doc = SalesDocument(**doc_dict)
        self.db.add(doc)
        self.db.flush()

        # 해외 문서 은행정보는 현재 회사 계좌 설정을 권위로 반영(프론트 값/구버전 캐시 무관하게 최신 계좌)
        self._apply_company_bank(doc)

        # 품목 생성
        total = Decimal("0")
        for item_data in items_data:
            item = SalesDocumentItem(
                document_id=doc.id,
                **item_data.model_dump()
            )
            self.db.add(item)
            total += item.amount

        doc.total_amount = self._apply_charges(total, doc.discount_amount, doc.shipping_fee)
        self._log_document_created(doc)  # 연결된 영업활동 히스토리에 자동 기록
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update(self, doc_id: int, data: SalesDocumentUpdate) -> Optional[SalesDocument]:
        """
        문서 수정 (버전 복사 방식, v0.32.0)
        - 기존 문서를 이전 버전으로 보관 (is_latest=false)
        - 새 버전 생성 (version+1, is_latest=true)
        - DRAFT 상태에서만 수정 가능 (v1 초기 작성 중일 때는 인플레이스 수정)
        """
        doc = self.db.query(SalesDocument).options(
            joinedload(SalesDocument.items)
        ).filter(SalesDocument.id == doc_id).first()
        if not doc:
            return None

        # DRAFT 상태: 인플레이스 수정 + 날짜 변경 시 번호 재생성
        if doc.status == "DRAFT":
            update_data = data.model_dump(exclude_unset=True, exclude={"items"})
            old_date = doc.document_date

            for key, value in update_data.items():
                setattr(doc, key, value)

            # 날짜가 변경되었으면 문서번호 재생성
            if 'document_date' in update_data and doc.document_date != old_date and doc.customer_id:
                new_number = self._generate_document_number(doc.document_type, doc.customer_id, doc.document_date)
                # 생산요청의 pi_number도 업데이트
                from app.models.production_request import ProductionRequest
                self.db.query(ProductionRequest).filter(
                    ProductionRequest.pi_number == doc.document_number
                ).update({"pi_number": new_number})
                doc.document_number = new_number
                doc.version_group = new_number

            if data.items is not None:
                self.db.query(SalesDocumentItem).filter(
                    SalesDocumentItem.document_id == doc_id
                ).delete()
                total = Decimal("0")
                for item_data in data.items:
                    item = SalesDocumentItem(document_id=doc_id, **item_data.model_dump())
                    self.db.add(item)
                    total += item.amount
                doc.total_amount = self._apply_charges(total, doc.discount_amount, doc.shipping_fee)
            else:
                # 품목 변경 없이 할인/배송비만 바뀐 경우도 총액 재계산
                self.db.flush()
                subtotal = sum((i.amount for i in doc.items), Decimal("0"))
                doc.total_amount = self._apply_charges(subtotal, doc.discount_amount, doc.shipping_fee)

            if not doc.version_group:
                doc.version_group = doc.document_number

            self.db.commit()
            self.db.refresh(doc)
            return doc

        # SENT/CONFIRMED: 새 버전 생성 (이전 버전 보존)
        version_group = doc.version_group or doc.document_number
        new_version = doc.version + 1
        old_number = doc.document_number

        # 수정본은 '수정 날짜' 기준 새 문서번호로 생성(-v{n} 폐기).
        # 같은 날 수정이면 _generate_document_number 가 -B/-C 접미사로 중복 방지.
        pre = data.model_dump(exclude_unset=True, exclude={"items"})
        effective_date = pre.get("document_date") or doc.document_date
        new_number = self._generate_document_number(doc.document_type, doc.customer_id, effective_date)

        # 기존 문서를 이전 버전으로
        doc.is_latest = False

        # 생산요청(pi_number)이 옛 번호를 참조하면 새 번호로 승계 → 항상 최신본을 가리키게
        if new_number != old_number:
            from app.models.production_request import ProductionRequest
            self.db.query(ProductionRequest).filter(
                ProductionRequest.pi_number == old_number
            ).update({"pi_number": new_number})

        # 새 버전 문서 생성
        new_doc = SalesDocument(
            document_type=doc.document_type,
            document_number=new_number,
            document_date=effective_date,
            version=new_version,
            is_latest=True,
            version_group=version_group,
            source_document_id=doc.source_document_id,
            sales_activity_id=doc.sales_activity_id,
            customer_id=doc.customer_id,
            customer_contact_id=doc.customer_contact_id,
            is_quote_only=doc.is_quote_only,
            prepared_by=doc.prepared_by,
            prepared_email=doc.prepared_email,
            customer_po_number=doc.customer_po_number,
            customer_po_date=doc.customer_po_date,
            po_attachment_files=doc.po_attachment_files,
            payment_terms=doc.payment_terms,
            delivery_terms=doc.delivery_terms,
            incoterms=getattr(doc, "incoterms", None),
            freight_per_box=getattr(doc, "freight_per_box", None),
            show_customer_tax_id=getattr(doc, "show_customer_tax_id", False),
            show_statement_of_origin=getattr(doc, "show_statement_of_origin", False),
            hs_code=doc.hs_code,
            country_of_origin=doc.country_of_origin,
            valid_until=doc.valid_until,
            bank_name=doc.bank_name,
            bank_address=doc.bank_address,
            swift_code=doc.swift_code,
            account_name=doc.account_name,
            account_number=doc.account_number,
            ship_to_address_id=doc.ship_to_address_id,
            ship_to_name=doc.ship_to_name,
            ship_to_address=doc.ship_to_address,
            ship_to_contact=doc.ship_to_contact,
            ship_to_phone=doc.ship_to_phone,
            ship_to_email=doc.ship_to_email,
            total_amount=doc.total_amount,
            discount_amount=doc.discount_amount,
            discount_reason=doc.discount_reason,
            shipping_fee=doc.shipping_fee,
            currency=doc.currency,
            payment_status=doc.payment_status,
            paid_amount=doc.paid_amount,
            paid_date=doc.paid_date,
            remarks=doc.remarks,
            status="DRAFT",
        )

        # 수정 데이터 적용
        update_data = data.model_dump(exclude_unset=True, exclude={"items"})
        for key, value in update_data.items():
            setattr(new_doc, key, value)

        self.db.add(new_doc)
        self.db.flush()

        # 품목 복사 (수정 데이터가 있으면 교체, 없으면 기존 복사)
        if data.items is not None:
            total = Decimal("0")
            for item_data in data.items:
                item = SalesDocumentItem(document_id=new_doc.id, **item_data.model_dump())
                self.db.add(item)
                total += item.amount
            new_doc.total_amount = self._apply_charges(total, new_doc.discount_amount, new_doc.shipping_fee)
        else:
            total = Decimal("0")
            for src_item in doc.items:
                new_item = SalesDocumentItem(
                    document_id=new_doc.id,
                    line_no=src_item.line_no,
                    product_code=src_item.product_code,
                    description=src_item.description,
                    quantity=src_item.quantity,
                    uom=src_item.uom,
                    unit_price=src_item.unit_price,
                    amount=src_item.amount,
                    currency=src_item.currency,
                    line_remarks=src_item.line_remarks,
                )
                self.db.add(new_item)
                total += new_item.amount
            new_doc.total_amount = self._apply_charges(total, new_doc.discount_amount, new_doc.shipping_fee)

        # N:M 링크도 복사
        from app.models.sales_document import SalesDocumentLink
        old_links = self.db.query(SalesDocumentLink).filter(
            (SalesDocumentLink.source_id == doc.id) | (SalesDocumentLink.target_id == doc.id)
        ).all()
        for link in old_links:
            if link.source_id == doc.id:
                self.db.add(SalesDocumentLink(source_id=new_doc.id, target_id=link.target_id))
            if link.target_id == doc.id:
                self.db.add(SalesDocumentLink(source_id=link.source_id, target_id=new_doc.id))

        # v0.67.0: 기존 생산요청의 PI 링크를 새 버전 품목으로 승계 (잔여수량 리셋/전량 중복요청 방지)
        self.db.flush()  # new_doc.items 의 id 확보
        self._remap_production_request_links(list(doc.items), list(new_doc.items), doc.id, new_doc.id)

        self.db.commit()
        self.db.refresh(new_doc)
        return new_doc

    def _remap_production_request_links(self, old_items, new_items, old_doc_id: int, new_doc_id: int) -> None:
        """PI 수정(새 버전) 시 기존 생산요청 품목의 PI 링크를 새 버전 품목으로 승계.

        기존엔 pi_number 문자열만 새 번호로 갱신하고 pi_document_id/pi_item_id 는 옛 버전을
        계속 가리켜, 잔여수량 계산(pi_item_id 기준)이 옛 요청을 못 찾아 잔여가 전량으로 리셋됐음.
        old→new 매칭은 오더코드(마크업 제거) 기준, 동일코드 중복이면 등장 순서로 대응.
        """
        from app.models.production_request import ProductionRequestItem
        from app.services.pdf.highlight import strip_markup

        old_ids = [it.id for it in old_items]
        if not old_ids:
            return

        def _code(v):
            return strip_markup(v or "").strip()

        # 새 품목: 코드 -> id 리스트(순서 유지)
        new_by_code: dict = {}
        for it in new_items:
            new_by_code.setdefault(_code(it.product_code), []).append(it.id)
        old_code = {it.id: _code(it.product_code) for it in old_items}

        pr_items = self.db.query(ProductionRequestItem).filter(
            ProductionRequestItem.pi_item_id.in_(old_ids)
        ).all()

        used: dict = {}
        for pr_it in pr_items:
            code = old_code.get(pr_it.pi_item_id)
            candidates = new_by_code.get(code, [])
            idx = used.get(code, 0)
            if candidates:
                pr_it.pi_item_id = candidates[idx] if idx < len(candidates) else candidates[-1]
                used[code] = idx + 1
            pr_it.pi_document_id = new_doc_id

        # pi_document_id 만 옛 문서를 가리키던 항목도 최신 문서로 정렬
        self.db.query(ProductionRequestItem).filter(
            ProductionRequestItem.pi_document_id == old_doc_id
        ).update({"pi_document_id": new_doc_id}, synchronize_session=False)

    def delete(self, doc_id: int, force: bool = False) -> bool:
        """문서 삭제 (기본: DRAFT만, force=True: 모든 상태)"""
        doc = self.db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
        if not doc:
            return False
        if not force and doc.status != "DRAFT":
            return False
        from app.models.sales_document import SalesDocumentLink
        # CI 삭제 → 생산요청 품목의 누적 CI 발행 수량 복원(링크 삭제 전에 소스 PI 를 찾아야 함)
        if doc.document_type == "CI":
            self._release_production_ci_quantity(doc)
        # 이 문서의 원본(소스) 문서들 — 삭제 후 상태 롤백 판단용
        source_ids = [l.source_id for l in self.db.query(SalesDocumentLink).filter(
            SalesDocumentLink.target_id == doc_id).all()]
        # 연결된 link 삭제
        self.db.query(SalesDocumentLink).filter(
            (SalesDocumentLink.source_id == doc_id) | (SalesDocumentLink.target_id == doc_id)
        ).delete()
        self.db.delete(doc)
        self.db.flush()
        # 원본 문서: 남은 전방(forward) 링크가 없으면 확정(CONFIRMED)→작성중(DRAFT) 롤백
        # (Q→PI 전환 시 Q가 확정되는데, PI를 삭제하면 다시 작성중으로 되돌린다)
        self._rollback_orphan_sources(source_ids)
        self.db.commit()
        return True

    def _release_production_ci_quantity(self, ci: SalesDocument) -> None:
        """CI 삭제 시 생산요청 품목의 누적 CI 발행 수량(ci_quantity)을 되돌린다 — 분할선적 잔여 복원.

        - 박스 CI: box_plan 에 기록된 박스 품목·수량만큼 정확히 차감하고 박스 발행 표시를 지운다.
        - 그 외: 소스 PI 에 이 CI 말고 남은 CI 가 없으면 그 PI 의 생산요청 품목을 0 으로,
          남은 CI 가 있으면 이 CI 품목 수량을 품번이 같은 생산요청 품목에서 차감한다.
        (CI 품목에는 생산요청 품목 id 가 없어 PI 연결 + 품번으로 찾는다 — 발송완료 처리와 같은 방식)
        """
        from app.models.sales_document import SalesDocumentLink
        from app.models.production_request import ProductionRequest, ProductionRequestItem

        # 1) 소스 PI 와, 그 PI 에 연결된 생산요청
        pi_ids = {l.source_id for l in self.db.query(SalesDocumentLink).filter(
            SalesDocumentLink.target_id == ci.id).all()}
        if ci.source_document_id:
            pi_ids.add(ci.source_document_id)
        if not pi_ids:
            return
        pi_by_number = {d.document_number: d.id for d in self.db.query(SalesDocument).filter(
            SalesDocument.id.in_(pi_ids)).all() if d.document_number}
        pr_ids = {r for (r,) in self.db.query(ProductionRequestItem.production_request_id).filter(
            ProductionRequestItem.pi_document_id.in_(pi_ids))}
        if pi_by_number:
            pr_ids |= {r for (r,) in self.db.query(ProductionRequest.id).filter(
                ProductionRequest.pi_number.in_(list(pi_by_number)))}
        if not pr_ids:
            return
        prs = self.db.query(ProductionRequest).filter(ProductionRequest.id.in_(pr_ids)).all()

        def _minus(it, qty) -> Decimal:
            """품목 ci_quantity 에서 qty 만큼 차감(0 미만 방지). 실제 차감량 반환."""
            cur = Decimal(str(it.ci_quantity or 0))
            take = min(cur, Decimal(str(qty or 0)))
            if take > 0:
                it.ci_quantity = cur - take
            return take

        # 2) 박스 CI — 박스 품목·수량이 정확하므로 그것만 되돌린다
        released_box = False
        for pr in prs:
            boxes = list(pr.box_plan or [])
            hit = False
            for i, b in enumerate(boxes):
                if b.get("ci_document_id") != ci.id:
                    continue
                items = {it.id: it for it in (pr.items or [])}
                for ln in (b.get("items") or []):
                    it = items.get(ln.get("pr_item_id"))
                    if it:
                        _minus(it, ln.get("quantity"))
                nb = dict(b)
                nb.pop("ci_document_id", None)
                nb.pop("ci_number", None)
                boxes[i] = nb
                hit = True
            if hit:
                pr.box_plan = boxes  # JSON 재할당으로 변경 감지
                released_box = True
        if released_box:
            return

        # 3) 일반·합배송·분할 CI — 소스 PI 별로 판단
        def _other_ci_exists(pid) -> bool:
            linked = self.db.query(SalesDocumentLink).join(
                SalesDocument, SalesDocument.id == SalesDocumentLink.target_id
            ).filter(
                SalesDocumentLink.source_id == pid,
                SalesDocument.document_type == "CI", SalesDocument.id != ci.id,
            ).count()
            if linked:
                return True
            return self.db.query(SalesDocument).filter(
                SalesDocument.source_document_id == pid,
                SalesDocument.document_type == "CI", SalesDocument.id != ci.id,
            ).count() > 0

        items_by_pi = {}
        for pr in prs:
            fallback = pi_by_number.get(pr.pi_number)
            for it in (pr.items or []):
                pid = it.pi_document_id if it.pi_document_id else fallback
                if pid in pi_ids:
                    items_by_pi.setdefault(pid, []).append(it)

        shared = []  # 다른 CI 가 남은 PI 의 품목 → 이 CI 수량만큼만 차감
        for pid, its in items_by_pi.items():
            if _other_ci_exists(pid):
                shared.extend(its)
            else:
                for it in its:
                    it.ci_quantity = 0
        if not shared:
            return
        for line in (ci.items or []):
            need = Decimal(str(line.quantity or 0))
            code = (line.product_code or "").strip()
            for it in shared:
                if need <= 0:
                    break
                if self._production_item_code(it) == code:
                    need -= _minus(it, need)

    def _production_item_code(self, it) -> str:
        """생산요청 품목의 CI 품번 — CI 발행 시(_line_product_info)와 같은 규칙: PI 품목 우선, 없으면 부품/커스텀."""
        if getattr(it, "pi_item_id", None):
            pi_item = self.db.query(SalesDocumentItem).filter(SalesDocumentItem.id == it.pi_item_id).first()
            if pi_item and pi_item.product_code:
                return pi_item.product_code.strip()
        p = getattr(it, "product_part", None)
        if p:
            return (p.part_number_display or p.part_number or "").strip()
        return (getattr(it, "custom_product_code", None) or "-").strip()

    def _rollback_orphan_sources(self, source_ids) -> None:
        """전방 링크가 하나도 안 남은 확정 원본을 작성중으로 롤백. PI는 생산요청 있으면 유지."""
        from app.models.sales_document import SalesDocumentLink
        from app.models.production_request import ProductionRequest, ProductionRequestItem
        for sid in set(source_ids or []):
            src = self.db.query(SalesDocument).filter(SalesDocument.id == sid).first()
            if not src or src.status != "CONFIRMED":
                continue
            remaining = self.db.query(SalesDocumentLink).filter(SalesDocumentLink.source_id == sid).count()
            if remaining > 0:
                continue
            # PI 원본이 생산요청을 갖고 있으면 롤백 안 함(생산 진행중)
            if src.document_type == "PI":
                has_pr = self.db.query(ProductionRequestItem).filter(
                    ProductionRequestItem.pi_document_id == sid).first()
                if not has_pr and src.document_number:
                    has_pr = self.db.query(ProductionRequest).filter(
                        ProductionRequest.pi_number == src.document_number).first()
                if has_pr:
                    continue
            src.status = "DRAFT"

    # ==================== 상태 변경 ====================

    def update_status(self, doc_id: int, new_status: str) -> Optional[SalesDocument]:
        """문서 상태 변경.

        CI를 '발송(SENT)' 처리하면, 그 CI에 연결된 생산요청(출고 완료건)을
        자동으로 '발송 완료(DELIVERED)'로 전환한다. (출고→CI 발송→발송완료 프로세스 연결)
        """
        doc = self.db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
        if not doc:
            return None
        prev_status = doc.status
        doc.status = new_status
        self.db.commit()
        self.db.refresh(doc)
        # CI 발송 시 연결된 생산요청 발송완료 자동 처리
        if doc.document_type == "CI" and new_status == "SENT" and prev_status != "SENT":
            self._deliver_production_requests_for_ci(doc)
        return doc

    def _deliver_production_requests_for_ci(self, ci: SalesDocument) -> None:
        """CI 발송 시, 연결된 PI로부터 생산요청을 찾아 출고완료(SHIPPED) 건을 발송완료(DELIVERED)로 전환."""
        from app.models.sales_document import SalesDocumentLink
        from app.models.production_request import ProductionRequest, ProductionRequestItem
        from datetime import datetime

        # 1) CI의 소스 PI id 수집: source_document_id + N:M 링크
        pi_ids = set()
        if ci.source_document_id:
            pi_ids.add(ci.source_document_id)
        for link in self.db.query(SalesDocumentLink).filter(SalesDocumentLink.target_id == ci.id).all():
            pi_ids.add(link.source_id)
        if not pi_ids:
            return

        # 소스 문서번호(pi_number 폴백 매칭용)
        pi_docs = self.db.query(SalesDocument).filter(SalesDocument.id.in_(pi_ids)).all()
        pi_numbers = {d.document_number for d in pi_docs if d.document_number}

        # 2) 연결된 생산요청 id 수집: 품목 pi_document_id ∈ pi_ids  OR  pr.pi_number ∈ pi_numbers
        pr_ids = set()
        for (rid,) in self.db.query(ProductionRequestItem.production_request_id).filter(
            ProductionRequestItem.pi_document_id.in_(pi_ids)
        ).distinct():
            pr_ids.add(rid)
        if pi_numbers:
            for (rid,) in self.db.query(ProductionRequest.id).filter(
                ProductionRequest.pi_number.in_(pi_numbers)
            ):
                pr_ids.add(rid)
        if not pr_ids:
            return

        # 3) 출고완료(SHIPPED) 건만 발송완료로 전환(다른 상태는 건너뜀 — 상태머신 보호)
        now = datetime.now()
        changed = False
        for pr in self.db.query(ProductionRequest).filter(ProductionRequest.id.in_(pr_ids)).all():
            if pr.status == "SHIPPED":
                pr.status = "DELIVERED"
                pr.delivered_at = pr.delivered_at or now
                changed = True
        if changed:
            self.db.commit()

    # ==================== 문서 전환 (Q→PI, PI→CI) ====================

    def convert_to_next(self, doc_id: int, data: ConvertToNextRequest) -> Optional[SalesDocument]:
        """단일 소스 문서 전환 (하위호환)"""
        return self.convert_multiple_to_next([doc_id], data)

    def _build_next_doc_header(self, primary: SalesDocument, next_type: str, data: ConvertToNextRequest) -> SalesDocument:
        """전환 대상 문서의 헤더(품목 제외) 생성 — primary 소스에서 조건/수령자/은행 등 승계."""
        # 전환 문서 날짜: 지정하면 그 날짜, 없으면 오늘. CI는 이 날짜가 출고/매출 인식일.
        doc_date = data.document_date or date.today()
        new_number = self._generate_document_number(next_type, primary.customer_id, doc_date)
        new_doc = SalesDocument(
            document_type=next_type,
            document_number=new_number,
            document_date=doc_date,
            source_document_id=primary.id,
            customer_id=primary.customer_id,
            prepared_by=primary.prepared_by,
            prepared_email=primary.prepared_email,
            customer_po_number=data.customer_po_number or primary.customer_po_number,
            customer_po_date=data.customer_po_date or primary.customer_po_date,
            po_attachment_files=data.po_attachment_files or primary.po_attachment_files,
            sales_activity_id=primary.sales_activity_id,
            payment_terms=primary.payment_terms,
            delivery_terms=primary.delivery_terms,
            incoterms=getattr(primary, "incoterms", None),
            freight_per_box=getattr(primary, "freight_per_box", None),
            show_customer_tax_id=getattr(primary, "show_customer_tax_id", False),
            # 원산지 신고문: PI→CI 변환 시 거래처 기본값을 이어받음(없으면 원본 문서값)
            show_statement_of_origin=bool(
                getattr(getattr(primary, "customer", None), "show_statement_of_origin", False)
                or getattr(primary, "show_statement_of_origin", False)
            ),
            hs_code=primary.hs_code,
            country_of_origin=primary.country_of_origin,
            bank_name=primary.bank_name,
            bank_address=primary.bank_address,
            swift_code=primary.swift_code,
            account_name=primary.account_name,
            account_number=primary.account_number,
            ship_to_address_id=primary.ship_to_address_id,
            ship_to_name=primary.ship_to_name,
            ship_to_address=primary.ship_to_address,
            ship_to_contact=primary.ship_to_contact,
            ship_to_phone=primary.ship_to_phone,
            ship_to_email=primary.ship_to_email,
            currency=primary.currency,
            discount_amount=primary.discount_amount,
            discount_reason=primary.discount_reason,
            shipping_fee=primary.shipping_fee,
            remarks=primary.remarks,
            is_quote_only=(bool(data.is_quote_only) if next_type == "PI" else False),
            status="DRAFT",
        )
        # 변환 문서도 현재 회사 계좌(통화별 설정)로 은행정보 갱신 — 소스의 옛 계좌 복사 방지
        self._apply_company_bank(new_doc)
        return new_doc

    def _company_bank_for(self, currency: Optional[str]) -> Optional[dict]:
        """관리자 설정(company_bank_accounts)에서 통화에 맞는 회사 계좌 반환. 미설정이면 None."""
        from app.models.app_setting import AppSetting
        row = self.db.query(AppSetting).filter(AppSetting.key == "company_bank_accounts").first()
        accounts = row.value if (row and isinstance(row.value, list) and row.value) else None
        if not accounts:
            return None
        cur = (currency or "").strip().upper()
        return (
            next((a for a in accounts if (a.get("currency") or "").upper() == cur), None)
            or next((a for a in accounts if a.get("is_default")), None)
            or accounts[0]
        )

    def _apply_company_bank(self, doc: SalesDocument) -> None:
        """해외(비KRW) 문서의 은행정보를 현재 회사 계좌 설정으로 세팅(권위 소스).
        국내(KRW)는 문서에 은행정보를 표기하지 않으므로 손대지 않음."""
        cur = (getattr(doc, "currency", None) or "").upper()
        if cur == "KRW":
            return
        acct = self._company_bank_for(cur)
        if not acct:
            return
        doc.bank_name = acct.get("bank_name")
        doc.bank_address = acct.get("bank_address")
        doc.swift_code = acct.get("swift_code")
        doc.account_name = acct.get("account_name")
        doc.account_number = acct.get("account_number")

    def create_ci_from_lines(self, source_pi_ids: list, lines: list, data: ConvertToNextRequest,
                             shipping_fee_override: Optional[Decimal] = None) -> Optional[SalesDocument]:
        """지정 품목·수량으로 CI 발행(분할선적). lines=[{product_code, description, quantity, uom, unit_price, currency, line_remarks}].

        헤더는 소스 PI(primary)에서 승계, 품목은 전달된 lines만 사용. 소스 PI에 문서 링크.
        shipping_fee_override: 지정 시 이 CI의 배송비를 강제(박스당 운임=freight_per_box 등). None이면 PI 승계값 사용.
        """
        from app.models.sales_document import SalesDocumentLink
        sources = self.db.query(SalesDocument).filter(SalesDocument.id.in_(source_pi_ids)).all()
        if not sources:
            return None
        primary = sources[0]
        new_doc = self._build_next_doc_header(primary, "CI", data)
        if shipping_fee_override is not None:
            new_doc.shipping_fee = shipping_fee_override
        self.db.add(new_doc)
        self.db.flush()

        line_no = 1
        total_amount = 0.0
        for ln in lines:
            qty = float(ln.get("quantity") or 0)
            price = float(ln.get("unit_price") or 0)
            amount = round(qty * price, 2)
            self.db.add(SalesDocumentItem(
                document_id=new_doc.id,
                line_no=line_no,
                product_code=ln.get("product_code") or "-",
                description=ln.get("description"),
                quantity=ln.get("quantity") or 0,
                uom=ln.get("uom"),
                unit_price=ln.get("unit_price"),
                amount=amount,
                currency=ln.get("currency") or primary.currency,
                line_remarks=ln.get("line_remarks"),
            ))
            total_amount += amount
            line_no += 1

        new_doc.total_amount = self._apply_charges(Decimal(str(total_amount)), new_doc.discount_amount, new_doc.shipping_fee)

        for source in sources:
            self.db.add(SalesDocumentLink(source_id=source.id, target_id=new_doc.id))
            source.status = "CONFIRMED"

        self._log_document_created(new_doc)
        self.db.commit()
        self.db.refresh(new_doc)

        # 연결 영업활동 COMPLETED (convert와 동일)
        from app.models.sales_activity import SalesActivity
        activity_ids = set(s.sales_activity_id for s in sources if s.sales_activity_id)
        for aid in activity_ids:
            act = self.db.query(SalesActivity).filter(SalesActivity.id == aid).first()
            if act and act.status != "COMPLETED":
                act.status = "COMPLETED"
        if activity_ids:
            self.db.commit()
        return new_doc

    def convert_multiple_to_next(self, source_ids: list, data: ConvertToNextRequest) -> Optional[SalesDocument]:
        """
        문서 전환 (N:M 지원, v0.32.0)
        - 여러 QUOTATION → 1 PI (통합)
        - 여러 PI → 1 CI (합배송)
        - 1개만 선택해도 정상 동작
        """
        from app.models.sales_document import SalesDocumentLink

        sources = self.db.query(SalesDocument).options(
            joinedload(SalesDocument.items)
        ).filter(SalesDocument.id.in_(source_ids)).all()

        if not sources:
            return None

        # 모든 소스가 같은 문서 유형인지 확인
        doc_types = set(s.document_type for s in sources)
        if len(doc_types) != 1:
            return None

        source_type = doc_types.pop()
        # 허용 전이: Q→PI, PI→CI(기본) / PI→INVOICE(명시). INVOICE는 PI와 동일 양식, 제목만 다름.
        allowed = {"QUOTATION": {"PI"}, "PI": {"CI", "INVOICE"}}
        default_next = {"QUOTATION": "PI", "PI": "CI"}
        requested = getattr(data, "target_type", None)
        if requested:
            if requested not in allowed.get(source_type, set()):
                return None
            next_type = requested
        else:
            next_type = default_next.get(source_type)
        if not next_type:
            return None

        # 첫 번째 소스를 기준 문서로 사용 (고객, 조건 등)
        primary = sources[0]
        new_doc = self._build_next_doc_header(primary, next_type, data)
        self.db.add(new_doc)
        self.db.flush()

        # 모든 소스의 품목을 합쳐서 복사
        line_no = 1
        total_amount = 0
        for source in sources:
            for src_item in sorted(source.items, key=lambda x: x.line_no):
                new_item = SalesDocumentItem(
                    document_id=new_doc.id,
                    line_no=line_no,
                    product_code=src_item.product_code,
                    description=src_item.description,
                    quantity=src_item.quantity,
                    uom=src_item.uom,
                    unit_price=src_item.unit_price,
                    amount=src_item.amount,
                    currency=src_item.currency,
                    line_remarks=src_item.line_remarks,
                )
                self.db.add(new_item)
                total_amount += float(src_item.amount or 0)
                line_no += 1

        new_doc.total_amount = self._apply_charges(Decimal(str(total_amount)), new_doc.discount_amount, new_doc.shipping_fee)

        # N:M 연결 생성 + 원본 상태 CONFIRMED
        for source in sources:
            self.db.add(SalesDocumentLink(source_id=source.id, target_id=new_doc.id))
            source.status = "CONFIRMED"

        self._log_document_created(new_doc)  # 전환 생성도 영업활동 히스토리에 자동 기록

        self.db.commit()
        self.db.refresh(new_doc)

        # CI 발행 시 연결된 영업활동을 자동 COMPLETED로 전환
        if new_doc.document_type == "CI":
            from app.models.sales_activity import SalesActivity
            activity_ids = set(s.sales_activity_id for s in sources if s.sales_activity_id)
            for aid in activity_ids:
                activity = self.db.query(SalesActivity).filter(SalesActivity.id == aid).first()
                if activity and activity.status != "COMPLETED":
                    activity.status = "COMPLETED"
            if activity_ids:
                self.db.commit()

        return new_doc

    # ==================== 고객 정보 자동 로드 ====================

    def get_customer_defaults(self, customer_id: int) -> Optional[dict]:
        """고객사에서 문서 기본값 자동 로드"""
        customer = self.db.query(BusinessPartner).filter(
            BusinessPartner.id == customer_id
        ).first()
        if not customer:
            return None

        return {
            "customer_id": customer.id,
            "partner_name": customer.partner_name,
            "partner_name_en": customer.partner_name_en,
            "short_code": customer.short_code,
            "payment_terms": customer.payment_terms,
            "delivery_terms": customer.delivery_terms,
            "hs_code": customer.hs_code,
            "show_statement_of_origin": bool(getattr(customer, "show_statement_of_origin", False)),
            "default_margin_rate": float(customer.default_margin_rate) if customer.default_margin_rate else None,
            "bank_name": customer.bank_name,
            "bank_address": customer.bank_address,
            "swift_code": customer.swift_code,
            "account_name": customer.bank_holder,
            "account_number": customer.bank_account,
            "address": customer.address,
            "address_detail": customer.address_detail,
            "manager_name": customer.manager_name,
            "manager_email": customer.manager_email,
            "tel": customer.tel,
            "country_name": customer.country_name,
            "trade_type": customer.trade_type or "EXPORT",
            "default_shipping_mark": customer.default_shipping_mark,
            "default_consignee": customer.default_consignee,
            "default_destination": customer.default_destination,
        }

    # ==================== 수금 관리 ====================

    def update_payment(self, doc_id: int, payment_status: str, paid_amount=None, paid_date=None, payment_remarks=None):
        """입금 상태 변경 (영업 담당자 수동 입력)"""
        doc = self.db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
        if not doc:
            return None

        doc.payment_status = payment_status
        if paid_amount is not None:
            doc.paid_amount = paid_amount
        if paid_date is not None:
            doc.paid_date = paid_date
        if payment_remarks is not None:
            doc.payment_remarks = payment_remarks

        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update_po_number(self, doc_id: int, customer_po_number=None,
                         customer_po_date=None, cascade: bool = True):
        """고객 PO 번호·날짜 정정 — **버전 생성 없이 제자리 수정**.

        고객사가 잘못 준 PO 번호를 바로잡는 용도. PO 번호는 우리 문서의
        상거래 내용이 아니라 고객측 참조값이므로, update() 처럼 새 버전을
        만들면(문서번호 재발행 + 상태 DRAFT 복귀) 오히려 혼선이 생긴다.
        문서번호·상태·금액·품목은 전혀 건드리지 않는다.

        반영 범위:
        - 같은 문서의 모든 버전(version_group) — 이전 버전만 옛 번호로 남는 것 방지
        - cascade=True 면 이 문서에서 파생된 후속 문서(PI→CI 등)가 **같은(잘못된)
          PO 를 승계한 경우**에만 함께 정정. 따로 입력된 PO 는 보존한다.

        반환: (대상 문서, 정정된 문서 수)
        """
        doc = self.db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
        if not doc:
            return None, 0

        old_po = doc.customer_po_number or None

        group = doc.version_group or doc.document_number
        targets = self.db.query(SalesDocument).filter(
            SalesDocument.version_group == group
        ).all()
        if all(t.id != doc.id for t in targets):
            targets.append(doc)

        if cascade:
            seen = {t.id for t in targets}
            frontier = list(seen)
            while frontier:
                children = self.db.query(SalesDocument).filter(
                    SalesDocument.source_document_id.in_(frontier)
                ).all()
                frontier = []
                for c in children:
                    if c.id in seen:
                        continue
                    seen.add(c.id)
                    frontier.append(c.id)
                    # 승계값이 그대로인 문서만 정정(개별 입력된 PO 는 손대지 않음)
                    if (c.customer_po_number or None) == old_po:
                        targets.append(c)

        for t in targets:
            t.customer_po_number = customer_po_number
            t.customer_po_date = customer_po_date

        self.db.commit()
        self.db.refresh(doc)
        return doc, len(targets)

    def get_collection_summary(self) -> dict:
        """수금 현황 요약 (PI 문서 기준)"""
        from sqlalchemy import func as sa_func
        from decimal import Decimal

        pis = self.db.query(SalesDocument).filter(
            SalesDocument.document_type == "PI",
            SalesDocument.status != "CANCELLED",
            SalesDocument.is_quote_only == False,  # 견적 대용 PI 제외(허수 방지)  # noqa: E712
            SalesDocument.is_latest == True,  # 최신본만(버전 중복 합산 방지)  # noqa: E712
        ).all()

        total_amount = sum(float(d.total_amount or 0) for d in pis)
        paid_amount = sum(float(d.paid_amount or 0) for d in pis)
        unpaid_count = sum(1 for d in pis if d.payment_status == "UNPAID")
        partial_count = sum(1 for d in pis if d.payment_status == "PARTIAL")
        paid_count = sum(1 for d in pis if d.payment_status == "PAID")

        return {
            "total_documents": len(pis),
            "total_amount": Decimal(str(total_amount)),
            "paid_amount": Decimal(str(paid_amount)),
            "unpaid_amount": Decimal(str(total_amount - paid_amount)),
            "unpaid_count": unpaid_count,
            "partial_count": partial_count,
            "paid_count": paid_count,
        }

    def get_collection_documents(self) -> list:
        """수금 현황 목록 (PI 기준) + 배송완료 여부.

        배송완료 판정: 연결된 CI가 발송/확정(SENT/CONFIRMED)이거나, 연결 생산요청이 DELIVERED.
        → '배송완료인데 미수금'(제품 수령 후 입금 예정) 예외 건을 식별하기 위함.
        """
        from app.models.production_request import ProductionRequest
        from app.models.sales_document import SalesDocumentLink

        pis = self.db.query(SalesDocument).options(
            joinedload(SalesDocument.customer)
        ).filter(
            SalesDocument.document_type == "PI",
            SalesDocument.status != "CANCELLED",
            SalesDocument.is_quote_only == False,  # noqa: E712
            SalesDocument.is_latest == True,  # noqa: E712
        ).order_by(SalesDocument.document_date.desc().nullslast()).all()
        if not pis:
            return []

        pi_ids = [p.id for p in pis]
        pi_numbers = [p.document_number for p in pis if p.document_number]

        delivered_pi_ids = set()
        # CI 발송/확정 — 직접 source
        for (sid,) in self.db.query(SalesDocument.source_document_id).filter(
            SalesDocument.document_type == "CI",
            SalesDocument.status.in_(["SENT", "CONFIRMED"]),
            SalesDocument.source_document_id.in_(pi_ids),
        ):
            if sid:
                delivered_pi_ids.add(sid)
        # CI 발송/확정 — 합배송 링크
        for (src,) in self.db.query(SalesDocumentLink.source_id).join(
            SalesDocument, SalesDocumentLink.target_id == SalesDocument.id
        ).filter(
            SalesDocument.document_type == "CI",
            SalesDocument.status.in_(["SENT", "CONFIRMED"]),
            SalesDocumentLink.source_id.in_(pi_ids),
        ):
            delivered_pi_ids.add(src)
        # 생산요청 발송완료
        delivered_numbers = set()
        for (num,) in self.db.query(ProductionRequest.pi_number).filter(
            ProductionRequest.pi_number.in_(pi_numbers),
            ProductionRequest.status == "DELIVERED",
        ):
            if num:
                delivered_numbers.add(num)

        out = []
        for p in pis:
            delivered = (p.id in delivered_pi_ids) or (p.document_number in delivered_numbers)
            out.append({
                "id": p.id,
                "document_number": p.document_number,
                "customer_id": p.customer_id,
                "customer": {"partner_name": p.customer.partner_name} if p.customer else None,
                "customer_po_number": p.customer_po_number,
                "currency": p.currency or "USD",
                "total_amount": float(p.total_amount or 0),
                "paid_amount": float(p.paid_amount or 0),
                "payment_status": p.payment_status or "UNPAID",
                "paid_date": p.paid_date.isoformat() if p.paid_date else None,
                "delivered": delivered,
            })
        return out

    # ==================== 고객별 가격 이력 ====================

    def get_customer_price_history(self, customer_id: int, product_code: Optional[str] = None) -> List[dict]:
        """
        고객별 제품 가격 이력 조회
        SalesDocumentItem에서 해당 고객에게 보낸 모든 제품의 가격을 추출
        """
        query = self.db.query(
            SalesDocumentItem.product_code,
            SalesDocumentItem.unit_price,
            SalesDocumentItem.currency,
            SalesDocumentItem.quantity,
            SalesDocument.id.label("document_id"),
            SalesDocument.document_number,
            SalesDocument.document_type,
            SalesDocument.document_date,
            SalesDocument.status,
        ).join(
            SalesDocument, SalesDocumentItem.document_id == SalesDocument.id
        ).filter(
            SalesDocument.customer_id == customer_id,
            SalesDocument.status != "CANCELLED",
        )

        if product_code:
            query = query.filter(SalesDocumentItem.product_code.ilike(f"%{product_code}%"))

        query = query.order_by(
            SalesDocumentItem.product_code,
            desc(SalesDocument.document_date),
        )

        results = query.all()

        return [
            {
                "product_code": r.product_code,
                "unit_price": float(r.unit_price),
                "currency": r.currency,
                "quantity": float(r.quantity),
                "document_id": r.document_id,
                "document_number": r.document_number,
                "document_type": r.document_type,
                "document_date": r.document_date.isoformat() if r.document_date else None,
                "status": r.status,
            }
            for r in results
        ]

    def get_last_quoted_price(self, customer_id: int, product_code: str) -> Optional[dict]:
        """
        특정 고객에게 특정 제품의 마지막 견적 가격 조회
        견적 작성 시 이전 가격 비교용
        """
        result = self.db.query(
            SalesDocumentItem.unit_price,
            SalesDocumentItem.quantity,
            SalesDocumentItem.uom,
            SalesDocumentItem.currency,
            SalesDocument.document_number,
            SalesDocument.document_date,
            SalesDocument.document_type,
        ).join(
            SalesDocument, SalesDocumentItem.document_id == SalesDocument.id
        ).filter(
            SalesDocument.customer_id == customer_id,
            SalesDocumentItem.product_code == product_code,
            SalesDocument.status != "CANCELLED",
        ).order_by(
            desc(SalesDocument.document_date),
        ).first()

        if not result:
            return None

        return {
            "unit_price": float(result.unit_price),
            "quantity": float(result.quantity) if result.quantity is not None else None,
            "uom": result.uom,
            "currency": result.currency,
            "document_number": result.document_number,
            "document_date": result.document_date.isoformat() if result.document_date else None,
            "document_type": result.document_type,
        }

    # ==================== PI → 생산요청 초안 생성 ====================

    def get_pi_remaining_quantities(self, pi_id: int) -> dict:
        """
        PI 품목별 잔여 생산요청 수량 조회
        - 1차: pi_item_id로 정확 매칭
        - 2차: (fallback) pi_number + product_code로 매칭 (기존 데이터 호환)
        """
        from app.models.production_request import ProductionRequest, ProductionRequestItem
        from app.models.parts import Part
        from sqlalchemy import func as sa_func

        # 취소/반려된 생산요청은 실제 생산에서 빠지므로 잔여수량 집계에서 제외 (①-3)
        _EXCLUDED_PR_STATUS = ("CANCELLED", "REJECTED")

        pi = self.db.query(SalesDocument).options(
            joinedload(SalesDocument.items)
        ).filter(SalesDocument.id == pi_id).first()

        if not pi:
            return {"error": "문서를 찾을 수 없습니다"}

        # 1차: pi_item_id 정확 매칭으로 합계 (취소/반려 PR 제외)
        requested_map = {}
        if pi.items:
            pi_item_ids = [i.id for i in pi.items]
            results = self.db.query(
                ProductionRequestItem.pi_item_id,
                sa_func.coalesce(sa_func.sum(ProductionRequestItem.requested_quantity), 0).label("total"),
            ).join(
                ProductionRequest, ProductionRequestItem.production_request_id == ProductionRequest.id
            ).filter(
                ProductionRequestItem.pi_item_id.in_(pi_item_ids),
                ProductionRequest.status.notin_(_EXCLUDED_PR_STATUS),
            ).group_by(ProductionRequestItem.pi_item_id).all()
            requested_map = {r.pi_item_id: float(r.total) for r in results}

        # 2차: pi_item_id가 없는 레거시 PR 항목도 pi_number + product_code로 매칭
        # (pi_item_id가 NULL인데 pi_number는 같은 PR들)
        legacy_prs = self.db.query(ProductionRequest).filter(
            ProductionRequest.pi_number == pi.document_number,
            ProductionRequest.status.notin_(_EXCLUDED_PR_STATUS),
        ).all()
        legacy_pr_ids = [pr.id for pr in legacy_prs]

        legacy_items = []
        if legacy_pr_ids:
            legacy_items = self.db.query(ProductionRequestItem).filter(
                ProductionRequestItem.production_request_id.in_(legacy_pr_ids),
                ProductionRequestItem.pi_item_id.is_(None),
            ).all()

        # product_code → pi_item 매핑 준비
        pi_item_by_code = {i.product_code: i for i in (pi.items or [])}

        for pr_item in legacy_items:
            # product_part_id → Part.part_number_display로 매칭
            part = self.db.query(Part).filter(Part.id == pr_item.product_part_id).first()
            if not part:
                continue
            candidate_codes = [part.part_number_display, part.part_number]
            matched_pi_item = None
            for code in candidate_codes:
                if code and code in pi_item_by_code:
                    matched_pi_item = pi_item_by_code[code]
                    break
            if matched_pi_item:
                requested_map[matched_pi_item.id] = requested_map.get(matched_pi_item.id, 0) + float(pr_item.requested_quantity or 0)

        items_data = []
        for pi_item in pi.items:
            total = float(pi_item.quantity or 0)
            requested = requested_map.get(pi_item.id, 0)
            remaining = max(0, total - requested)
            items_data.append({
                "pi_item_id": pi_item.id,
                "product_code": pi_item.product_code,
                "description": pi_item.description,
                "total_qty": total,
                "requested_qty": requested,
                "remaining_qty": remaining,
            })

        return {
            "pi_id": pi.id,
            "pi_number": pi.document_number,
            "document_type": pi.document_type,
            "items": items_data,
        }

    def create_production_request_draft(self, doc_id: int, actor_id: Optional[int] = None) -> dict:
        """
        PI 문서에서 생산요청 초안을 자동 생성 (v0.30.0)
        - 잔여 수량 기반 분할 생산요청 지원
        - PI당 여러 생산요청 가능
        """
        from app.models.production_request import ProductionRequest, ProductionRequestItem
        from app.models.parts import Part
        from app.utils.number_generator import generate_pr_number

        from app.models.business_partner import BusinessPartner

        # PI 문서 로드
        pi = self.db.query(SalesDocument).options(
            joinedload(SalesDocument.items)
        ).filter(SalesDocument.id == doc_id).first()

        if not pi or pi.document_type != "PI":
            return {"success": False, "message": "PI 문서가 아닙니다"}

        # 거래처 정보 (국가 자동 매핑용)
        customer = (
            self.db.query(BusinessPartner).filter(BusinessPartner.id == pi.customer_id).first()
            if pi.customer_id else None
        )

        # 잔여 수량 조회
        remaining_info = self.get_pi_remaining_quantities(doc_id)
        remaining_map = {item["pi_item_id"]: item["remaining_qty"] for item in remaining_info["items"]}

        # 잔여 수량이 있는 품목만 추출 (PI 품목 순서=line_no 유지 → 생산요청 품목 순서 동일)
        items_with_remaining = [
            pi_item for pi_item in sorted(pi.items, key=lambda i: (i.line_no or 0, i.id))
            if remaining_map.get(pi_item.id, 0) > 0
        ]

        if not items_with_remaining:
            existing_count = self.db.query(ProductionRequest).filter(
                ProductionRequest.pi_number == pi.document_number
            ).count()
            return {
                "success": False,
                "message": f"잔여 수량이 없습니다. 모든 품목이 이미 생산요청됨 (기존 {existing_count}건)",
            }

        # 생산요청 번호 채번
        pr_number = generate_pr_number(self.db)

        # 기존 PR 개수 확인 (메모용)
        existing_count = self.db.query(ProductionRequest).filter(
            ProductionRequest.pi_number == pi.document_number
        ).count()
        memo_suffix = f" (분할 #{existing_count + 1})" if existing_count > 0 else ""

        # 생산요청 생성
        pr = ProductionRequest(
            request_number=pr_number,
            customer_id=pi.customer_id,
            customer_order_no=pi.customer_po_number,
            pi_number=pi.document_number,
            due_date=None,
            priority=0,
            payment_status=pi.payment_status or "UNPAID",
            country=(customer.country_name if customer and customer.country_name else None),
            prepared_by_name=pi.prepared_by,  # PI 작성자를 영업담당자 기본값으로 (대부분 PR 작성자와 동일)
            requested_by=actor_id,  # 생산요청 올린 영업 담당자(반려/출고 알림 수신자)
            created_by=actor_id,
            status="REQUESTED",
            is_draft=True,  # v0.87.0 초안 — 생산팀 미노출·알림 X. 영업이 '생산팀에 요청' 시 전환+알림
            remarks=f"[PI 자동생성{memo_suffix}] {pi.document_number}에서 생성된 초안입니다. 특이사항/도면을 추가해주세요.",
        )
        self.db.add(pr)
        self.db.flush()

        # PI 품목 → 생산요청 품목 매핑 (잔여 수량만)
        items_created = 0
        custom_created = []  # BOM 미매칭 → 커스텀 품목으로 등록된 코드(PI 원본 보존)
        for idx, pi_item in enumerate(items_with_remaining):
            remaining_qty = remaining_map.get(pi_item.id, 0)

            # product_code(오더코드)로 Part 검색 — 정확 매칭 우선(광범위 prefix로 인한 오연결 방지)
            import re
            from app.services.pdf.highlight import strip_markup
            # 강조 마크업 제거 후 레벨 접미사 [X] 제거 → 순수 품번으로 매칭
            clean_code = strip_markup(pi_item.product_code or '')
            clean_code = re.sub(r'\s*\[[A-Z]\]\s*$', '', clean_code).strip()

            part = None
            if clean_code:
                # 1) 정확 매칭 (표시품번 == 또는 품번 ==) — 결정적 정렬
                part = self.db.query(Part).filter(
                    (Part.part_number_display == clean_code) | (Part.part_number == clean_code)
                ).order_by(Part.id).first()
                # 2) 레벨 접미사만 붙은 정확 변형만 허용 (예: "CODE" → "CODE [U]"). 광범위 'CODE %'는 사용 안 함
                if not part:
                    part = self.db.query(Part).filter(
                        Part.part_number_display.like(clean_code + ' [%')
                    ).order_by(Part.id).first()

            if part:
                # BOM 등록 부품에 연결
                pr_item = ProductionRequestItem(
                    production_request_id=pr.id,
                    product_part_id=part.id,
                    requested_quantity=remaining_qty,  # 잔여 수량만
                    uom=pi_item.uom,  # PI 품목 단위 승계 (EA/SET/M 등)
                    line_remarks=pi_item.line_remarks or "",
                    customer_requirements="",  # 특이사항은 생산팀이 직접 입력 (PI description 자동복사 안 함)
                    sort_order=idx,
                    pi_document_id=pi.id,
                    pi_item_id=pi_item.id,
                )
                self.db.add(pr_item)
                items_created += 1
                # deprecated 호환: 첫번째 항목을 단일 필드에도 복사
                if idx == 0:
                    pr.product_part_id = part.id
                    pr.requested_quantity = remaining_qty
            else:
                # 매칭 실패 → stub 부품 생성 대신 PI 원본 텍스트를 커스텀 품목으로 보존
                # (parts 테이블 오염·다음 PI의 stub 재사용 오연결 방지 — 생산요청은 PI와 100% 동일 표시)
                desc_first_line = (pi_item.description or '').strip().split('\n')[0].strip() if pi_item.description else ''
                pr_item = ProductionRequestItem(
                    production_request_id=pr.id,
                    product_part_id=None,
                    custom_product_code=(strip_markup(pi_item.product_code or clean_code) or None),
                    custom_product_name=(strip_markup(desc_first_line) or None),
                    requested_quantity=remaining_qty,
                    uom=pi_item.uom,
                    line_remarks=pi_item.line_remarks or "",
                    customer_requirements="",
                    sort_order=idx,
                    pi_document_id=pi.id,
                    pi_item_id=pi_item.id,
                )
                self.db.add(pr_item)
                items_created += 1
                if idx == 0:
                    pr.requested_quantity = remaining_qty
                custom_created.append(clean_code or (strip_markup(pi_item.product_code or '') or '품목'))

        self.db.commit()
        self.db.refresh(pr)

        # v0.87.0: 초안은 알림을 보내지 않음. 영업이 특이사항 입력 후 '생산팀에 요청'(submit)할 때 발송.

        msg = f"생산요청 초안이 생성되었습니다 ({pr.request_number})."
        if custom_created:
            msg += f" BOM 미등록 품목 {len(custom_created)}건은 PI 원본 그대로 커스텀 품목으로 등록되었습니다."

        return {
            "success": True,
            "production_request_id": pr.id,
            "request_number": pr.request_number,
            "items_created": items_created,
            "items_skipped": [],  # 더 이상 스킵 없음 (호환성 유지)
            "stub_created": custom_created,  # 호환 키 유지(의미: 커스텀 등록 코드)
            "message": msg,
        }

    # ==================== PI 프로세스 현황 ====================

    def get_pi_process_status(self, doc_id: int) -> Optional[dict]:
        """
        PI 기준 영업 프로세스 진행 상태 조회
        단계: PI발송 → 입금확인 → 생산요청 → 생산완료 → CI발행 → 출하
        """
        from app.models.production_request import ProductionRequest
        from app.models.work_order import WorkOrder

        pi = self.db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
        if not pi or pi.document_type != "PI":
            return None

        # 1. PI발송
        pi_sent = pi.status in ("SENT", "CONFIRMED")

        # 2. 입금확인
        payment_done = pi.payment_status in ("PARTIAL", "PAID")
        payment_label = {"UNPAID": "미입금", "PARTIAL": "부분입금", "PAID": "완납"}.get(pi.payment_status or "UNPAID", "미입금")

        # 3. 생산요청
        pr = self.db.query(ProductionRequest).filter(
            ProductionRequest.pi_number == pi.document_number
        ).first()
        pr_exists = pr is not None
        pr_number = pr.request_number if pr else None

        # 4. 생산완료 (PR이 출고/발송됐거나, 연결 WorkOrder 중 SHIPPED 있는지)
        production_done = False
        if pr:
            if pr.status in ("SHIPPED", "DELIVERED"):
                production_done = True
            else:
                shipped_wo = self.db.query(WorkOrder).filter(
                    WorkOrder.production_request_id == pr.id,
                    WorkOrder.status == "SHIPPED",
                ).first()
                production_done = shipped_wo is not None

        # 5. CI발행 (PI에서 전환된 CI) — 직접 source + 합배송(N:M 링크) 모두 확인
        from app.models.sales_document import SalesDocumentLink
        ci = self.db.query(SalesDocument).filter(
            SalesDocument.source_document_id == pi.id,
            SalesDocument.document_type == "CI",
        ).first()
        if not ci:
            ci = (
                self.db.query(SalesDocument)
                .join(SalesDocumentLink, SalesDocumentLink.target_id == SalesDocument.id)
                .filter(SalesDocumentLink.source_id == pi.id, SalesDocument.document_type == "CI")
                .first()
            )
        ci_exists = ci is not None
        ci_number = ci.document_number if ci else None

        # 6. 출하 (CI가 CONFIRMED 또는 SENT)
        shipped = ci is not None and ci.status in ("SENT", "CONFIRMED")

        # 거래유형에 따른 라벨 분기
        customer = pi.customer if hasattr(pi, 'customer') and pi.customer else None
        is_domestic = False
        if customer and hasattr(customer, 'trade_type'):
            is_domestic = customer.trade_type == "DOMESTIC"
        elif pi.customer_id:
            bp = self.db.query(BusinessPartner).filter(BusinessPartner.id == pi.customer_id).first()
            is_domestic = bp.trade_type == "DOMESTIC" if bp and bp.trade_type else False

        if is_domestic:
            labels = {"sent": "발송", "payment": "입금확인", "pr": "생산요청", "prod": "생산완료", "ci": "명세서발행", "ship": "납품"}
        else:
            labels = {"sent": "PI발송", "payment": "입금확인", "pr": "생산요청", "prod": "생산완료", "ci": "CI발행", "ship": "출하"}

        return {
            "steps": [
                {"key": "pi_sent", "label": labels["sent"], "done": pi_sent},
                {"key": "payment", "label": labels["payment"], "done": payment_done, "detail": payment_label},
                {"key": "production_request", "label": labels["pr"], "done": pr_exists, "detail": pr_number},
                {"key": "production_done", "label": labels["prod"], "done": production_done},
                {"key": "ci_issued", "label": labels["ci"], "done": ci_exists, "detail": ci_number},
                {"key": "shipped", "label": labels["ship"], "done": shipped},
            ]
        }

    def generate_management_no(self) -> str:
        """관리번호 자동 생성 (연도-순번: 26-001)"""
        from datetime import date
        year_prefix = date.today().strftime("%y")

        last = self.db.query(SalesDocument).filter(
            SalesDocument.management_no.like(f"{year_prefix}-%")
        ).order_by(desc(SalesDocument.management_no)).first()

        if last and last.management_no:
            try:
                last_seq = int(last.management_no.split("-")[1])
                return f"{year_prefix}-{last_seq + 1:03d}"
            except (IndexError, ValueError):
                pass

        return f"{year_prefix}-001"
