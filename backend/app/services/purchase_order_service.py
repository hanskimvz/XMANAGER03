"""
Purchase Order Service (v0.6.0)
발주서 관련 비즈니스 로직을 처리합니다.

Repository Pattern을 통해 데이터 접근 로직과 분리됩니다.

v0.6.0: 입출고 관리 기능 추가
- 발주서 CRUD
- 상태 전이 관리
- 입고 처리 → 재고 증가
"""

from typing import Optional, List, Tuple
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.purchase_order_repository import PurchaseOrderRepository, PurchaseOrderItemRepository
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderItemCreate,
    PurchaseOrderItemUpdate,
    PurchaseOrderStatus,
    ReceiveRequest,
    ReceiveItemRequest,
    ConfirmDeliveryRequest,
    PaymentRequest,
)
from app.schemas.inventory import TransactionType, InventoryAdjust
from app.schemas.inventory_lot import InventoryLotCreate
from app.services.inventory_service import InventoryService
from app.services.inventory_lot_service import InventoryLotService
from app.services.price_service import PriceService
from app.utils.number_generator import generate_po_number
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException,
)


class PurchaseOrderService:
    """
    발주서 서비스

    발주서 관련 비즈니스 로직을 캡슐화합니다.
    - 발주서 CRUD
    - 상태 전이 (DRAFT → ORDERED → CONFIRMED → RECEIVED)
    - 결재는 is_paid 필드로 별도 관리
    - 입고 처리 시 재고 자동 증가
    """

    # 상태 전이 규칙 정의 (COMPLETED는 기존 데이터 호환용)
    VALID_TRANSITIONS = {
        PurchaseOrderStatus.DRAFT: [PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.CANCELLED],
        PurchaseOrderStatus.ORDERED: [PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED],
        PurchaseOrderStatus.CONFIRMED: [PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED],
        PurchaseOrderStatus.RECEIVED: [PurchaseOrderStatus.CANCELLED],  # 입고완료가 최종 상태
        PurchaseOrderStatus.COMPLETED: [],  # 기존 데이터 호환용 - 상태 변경 불가
        PurchaseOrderStatus.CANCELLED: [],
    }

    # 상태 롤백 규칙 정의 (이전 상태로 되돌리기)
    VALID_ROLLBACKS = {
        PurchaseOrderStatus.ORDERED: PurchaseOrderStatus.DRAFT,       # 주문완료 -> 작성중
        PurchaseOrderStatus.CONFIRMED: PurchaseOrderStatus.ORDERED,   # 납기확정 -> 주문완료
        PurchaseOrderStatus.RECEIVED: PurchaseOrderStatus.CONFIRMED,  # 입고완료 -> 납기확정 (재고 차감)
        PurchaseOrderStatus.COMPLETED: PurchaseOrderStatus.RECEIVED,  # 기존 데이터: 완료 -> 입고완료
        # DRAFT, CANCELLED는 롤백 불가
    }

    def __init__(self, db: Session):
        self.db = db
        self.repository = PurchaseOrderRepository(db)
        self.item_repository = PurchaseOrderItemRepository(db)
        self.inventory_service = InventoryService(db)
        self.lot_service = InventoryLotService(db)
        self.price_service = PriceService(db)

    # ==================== 조회 ====================

    def get(self, id: int) -> Optional[PurchaseOrder]:
        """ID로 발주서 조회"""
        return self.repository.get_by_id_with_relations(id)

    def get_or_raise(self, id: int) -> PurchaseOrder:
        """ID로 발주서 조회 (없으면 예외)"""
        po = self.repository.get_by_id_with_relations(id)
        if not po:
            raise NotFoundException("발주서", id)
        return po

    def get_by_po_number(self, po_number: str) -> Optional[PurchaseOrder]:
        """발주서 번호로 조회"""
        return self.repository.get_by_po_number_with_relations(po_number)

    def search_purchase_orders(
        self,
        keyword: Optional[str] = None,
        status: Optional[PurchaseOrderStatus] = None,
        supplier_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[PurchaseOrder]:
        """발주서 검색"""
        return self.repository.search_purchase_orders(
            keyword=keyword,
            status=status,
            supplier_id=supplier_id,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    def search_purchase_orders_with_count(
        self,
        keyword: Optional[str] = None,
        status: Optional[PurchaseOrderStatus] = None,
        supplier_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[PurchaseOrder], int]:
        """발주서 검색 + 총 개수"""
        return self.repository.search_purchase_orders_with_count(
            keyword=keyword,
            status=status,
            supplier_id=supplier_id,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    # ==================== 생성 ====================

    def create_purchase_order(self, po_in: PurchaseOrderCreate) -> PurchaseOrder:
        """
        발주서 생성

        Args:
            po_in: 발주서 생성 데이터

        Returns:
            생성된 발주서
        """
        # 발주서 번호 자동 생성
        po_number = generate_po_number(self.db, po_in.order_date)

        # 발주서 생성
        po = PurchaseOrder(
            po_number=po_number,
            supplier_id=po_in.supplier_id,
            order_date=po_in.order_date,
            expected_delivery_date=po_in.expected_delivery_date,
            currency=po_in.currency,
            payment_terms=po_in.payment_terms,
            delivery_terms=po_in.delivery_terms,
            remarks=po_in.remarks,
            status=PurchaseOrderStatus.DRAFT.value,
            total_amount=Decimal(0),
            tax_amount=Decimal(0),
            discount_amount=Decimal(0),
        )
        self.db.add(po)
        self.db.flush()

        # 항목 추가
        total_amount = Decimal(0)
        if po_in.items:
            for idx, item_in in enumerate(po_in.items):
                line_total = item_in.ordered_quantity * item_in.unit_price
                total_amount += line_total

                item = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    part_id=item_in.part_id,
                    custom_product_code=getattr(item_in, "custom_product_code", None),
                    custom_product_name=getattr(item_in, "custom_product_name", None),
                    ordered_quantity=item_in.ordered_quantity,
                    unit_price=item_in.unit_price,
                    line_total=line_total,
                    unit_id=item_in.unit_id,
                    line_remarks=item_in.line_remarks,
                    sort_order=item_in.sort_order if item_in.sort_order else idx,
                )
                self.db.add(item)

        # 총 금액 업데이트
        po.total_amount = total_amount
        self.db.commit()

        return self.repository.get_by_id_with_relations(po.id)

    # ==================== 항목 관리 ====================

    def add_item(self, po_id: int, item_in: PurchaseOrderItemCreate) -> PurchaseOrder:
        """
        발주서에 항목 추가

        Args:
            po_id: 발주서 ID
            item_in: 항목 데이터

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)

        # DRAFT 상태에서만 수정 가능
        if po.status != PurchaseOrderStatus.DRAFT.value:
            raise BusinessRuleException("작성중 상태의 발주서만 항목을 추가할 수 있습니다.")

        # 항목 생성
        line_total = item_in.ordered_quantity * item_in.unit_price
        item = PurchaseOrderItem(
            purchase_order_id=po_id,
            part_id=item_in.part_id,
            custom_product_code=getattr(item_in, "custom_product_code", None),
            custom_product_name=getattr(item_in, "custom_product_name", None),
            ordered_quantity=item_in.ordered_quantity,
            unit_price=item_in.unit_price,
            line_total=line_total,
            unit_id=item_in.unit_id,
            line_remarks=item_in.line_remarks,
            sort_order=item_in.sort_order,
        )
        self.db.add(item)

        # 총 금액 재계산
        po.total_amount = (po.total_amount or Decimal(0)) + line_total
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    def update_item(self, po_id: int, item_id: int, item_in: PurchaseOrderItemUpdate) -> PurchaseOrder:
        """
        발주서 항목 수정

        취소 상태를 제외한 모든 상태에서 수정 가능합니다.
        (불량/초과생산 등으로 인한 단가 변경 대응)

        Args:
            po_id: 발주서 ID
            item_id: 항목 ID
            item_in: 수정 데이터

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)

        # 취소 상태에서만 수정 불가
        if po.status == PurchaseOrderStatus.CANCELLED.value:
            raise BusinessRuleException("취소된 발주서의 항목은 수정할 수 없습니다.")

        # 항목 조회
        item = self.item_repository.get_by_id(item_id)
        if not item or item.purchase_order_id != po_id:
            raise NotFoundException("발주서 항목", item_id)

        # 수정
        update_data = item_in.model_dump(exclude_unset=True)

        # 수량 또는 단가 변경 시 금액 재계산
        qty = update_data.get("ordered_quantity", item.ordered_quantity)
        price = update_data.get("unit_price", item.unit_price)
        old_line_total = item.line_total or Decimal(0)
        new_line_total = qty * price
        update_data["line_total"] = new_line_total

        self.item_repository.update_from_dict(item, update_data)

        # 총 금액 재계산
        po.total_amount = (po.total_amount or Decimal(0)) - old_line_total + new_line_total
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    def delete_item(self, po_id: int, item_id: int) -> PurchaseOrder:
        """
        발주서 항목 삭제

        Args:
            po_id: 발주서 ID
            item_id: 항목 ID

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)

        # DRAFT 상태에서만 삭제 가능
        if po.status != PurchaseOrderStatus.DRAFT.value:
            raise BusinessRuleException("작성중 상태의 발주서만 항목을 삭제할 수 있습니다.")

        # 항목 조회
        item = self.item_repository.get_by_id(item_id)
        if not item or item.purchase_order_id != po_id:
            raise NotFoundException("발주서 항목", item_id)

        # 총 금액 차감
        po.total_amount = (po.total_amount or Decimal(0)) - (item.line_total or Decimal(0))

        # 삭제
        self.item_repository.delete(item)
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    # ==================== 수정/삭제 ====================

    def update_purchase_order(self, po_id: int, po_in: PurchaseOrderUpdate) -> PurchaseOrder:
        """
        발주서 수정

        모든 상태에서 수정 가능합니다 (취소 상태 제외).
        단, 이미 입고 처리된 항목의 수량은 변경할 수 없습니다.

        Args:
            po_id: 발주서 ID
            po_in: 수정 데이터

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)
        update_data = po_in.model_dump(exclude_unset=True)

        # 취소된 발주서만 수정 불가
        if po.status == PurchaseOrderStatus.CANCELLED.value:
            raise BusinessRuleException("취소된 발주서는 수정할 수 없습니다.")

        if not update_data:
            return self.repository.get_by_id_with_relations(po_id)

        self.repository.update_from_dict(po, update_data)

        return self.repository.get_by_id_with_relations(po_id)

    def delete_purchase_order(self, po_id: int) -> bool:
        """
        발주서 삭제 (DRAFT 상태에서만)

        Args:
            po_id: 발주서 ID

        Returns:
            삭제 성공 여부
        """
        po = self.get_or_raise(po_id)

        # DRAFT 상태에서만 삭제 가능
        if po.status != PurchaseOrderStatus.DRAFT.value:
            raise BusinessRuleException("작성중 상태의 발주서만 삭제할 수 있습니다.")

        return self.repository.delete(po)

    # ==================== 상태 전이 ====================

    def _validate_transition(self, current: str, target: PurchaseOrderStatus) -> None:
        """상태 전이 유효성 검사"""
        current_status = PurchaseOrderStatus(current)
        valid_targets = self.VALID_TRANSITIONS.get(current_status, [])

        if target not in valid_targets:
            raise BusinessRuleException(
                f"'{current}' 상태에서 '{target.value}' 상태로 변경할 수 없습니다. "
                f"가능한 상태: {[s.value for s in valid_targets]}"
            )

    def order(self, po_id: int) -> PurchaseOrder:
        """
        주문 확정 (DRAFT → ORDERED)

        Args:
            po_id: 발주서 ID

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)
        self._validate_transition(po.status, PurchaseOrderStatus.ORDERED)

        # 항목 존재 확인
        if not po.items or len(po.items) == 0:
            raise BusinessRuleException("발주 항목이 없습니다. 항목을 추가한 후 주문을 확정하세요.")

        po.status = PurchaseOrderStatus.ORDERED.value
        po.updated_at = datetime.now()
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    def confirm_delivery(self, po_id: int, request: ConfirmDeliveryRequest) -> PurchaseOrder:
        """
        납기 확정 (ORDERED → CONFIRMED)

        Args:
            po_id: 발주서 ID
            request: 납기 확정 요청

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)
        self._validate_transition(po.status, PurchaseOrderStatus.CONFIRMED)

        po.status = PurchaseOrderStatus.CONFIRMED.value
        po.expected_delivery_date = request.expected_delivery_date
        if request.remarks:
            po.remarks = (po.remarks + "\n" if po.remarks else "") + request.remarks
        po.updated_at = datetime.now()
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    def receive(self, po_id: int, request: ReceiveRequest) -> PurchaseOrder:
        """
        입고 처리 (CONFIRMED → RECEIVED)

        입고된 수량만큼 재고가 자동으로 증가합니다.
        불량 수량은 재고에서 제외됩니다.

        Args:
            po_id: 발주서 ID
            request: 입고 요청

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)

        # CONFIRMED 또는 RECEIVED 상태에서 입고 가능 (부분 입고 지원)
        if po.status not in [PurchaseOrderStatus.CONFIRMED.value, PurchaseOrderStatus.RECEIVED.value]:
            if po.status == PurchaseOrderStatus.ORDERED.value:
                # ORDERED 상태에서도 입고 허용 (납기 확정 없이 바로 입고)
                pass
            else:
                raise BusinessRuleException(
                    f"'{po.status}' 상태에서는 입고 처리할 수 없습니다. "
                    "주문완료, 납기확정 또는 입고완료 상태에서만 가능합니다."
                )

        # 입고 처리
        for item_data in request.items:
            # 항목 조회
            item = self.item_repository.get_by_id(item_data.item_id)
            if not item or item.purchase_order_id != po_id:
                raise NotFoundException("발주서 항목", item_data.item_id)

            # 입고 수량 검증 (경고만 로깅, 초과 입고 허용)
            remaining = item.ordered_quantity - (item.received_quantity or Decimal(0))
            if item_data.received_quantity > remaining:
                # 경고만 기록하고 초과 입고 허용 (불량/초과생산 대응)
                import logging
                logging.warning(
                    f"입고 수량({item_data.received_quantity})이 미입고 수량({remaining})을 초과합니다. "
                    f"발주서: {po.po_number}, 항목 ID: {item.id}"
                )

            # 항목 업데이트
            item.received_quantity = (item.received_quantity or Decimal(0)) + item_data.received_quantity
            item.defective_quantity = (item.defective_quantity or Decimal(0)) + item_data.defective_quantity

            # 최종 입고 시 가격 조정 처리
            old_line_total = item.line_total or Decimal(0)
            price_adjusted = False

            if request.is_final_receive:
                # 최종 단가 또는 총액 조정
                if item_data.final_line_total is not None:
                    # 총액 입력 → 단가 역계산
                    item.line_total = item_data.final_line_total
                    if item.received_quantity > 0:
                        item.unit_price = item_data.final_line_total / item.received_quantity
                    price_adjusted = True
                elif item_data.final_unit_price is not None:
                    # 단가 입력 → 총액 계산 (실제 입고수량 기준)
                    item.unit_price = item_data.final_unit_price
                    item.line_total = item_data.final_unit_price * item.received_quantity
                    price_adjusted = True

                # 가격 조정 시 발주서 총액 재계산
                if price_adjusted:
                    po.total_amount = (po.total_amount or Decimal(0)) - old_line_total + item.line_total

            # 실제 입고량 = 입고수량 - 불량수량
            actual_received = item_data.received_quantity - item_data.defective_quantity

            # 가격 정보 (조정된 단가 또는 기존 단가 사용)
            final_unit_price = item.unit_price

            # 재고 증가 및 로트 생성
            if actual_received > 0:
                # 1. 로트 생성 (v0.7.0)
                lot_number = self.lot_service.generate_lot_number(
                    part_id=item.part_id,
                    po_number=po.po_number,
                    item_seq=item.sort_order or 1
                )

                lot = self.lot_service.create_lot(InventoryLotCreate(
                    part_id=item.part_id,
                    lot_number=lot_number,
                    quantity_received=actual_received,
                    received_date=datetime.now(),
                    purchase_order_id=po.id,
                    supplier_id=po.supplier_id,
                    unit_cost=final_unit_price,  # 조정된 단가 또는 기존 단가
                    remarks=f"발주 입고: {po.po_number}"
                ))

                # 2. 재고 증가
                inventory = self.inventory_service.get_by_part_id(item.part_id)
                if inventory:
                    self.inventory_service.adjust_inventory(
                        inventory.id,
                        InventoryAdjust(
                            quantity=actual_received,
                            transaction_type=TransactionType.IN,
                            reference_type="PO",
                            reference_id=po.po_number,
                            reason=f"발주 입고: {po.po_number} (로트: {lot_number})"
                        )
                    )
                else:
                    # 재고가 없으면 생성
                    from app.schemas.inventory import InventoryCreate
                    new_inventory = self.inventory_service.create_inventory(
                        InventoryCreate(
                            part_id=item.part_id,
                            quantity_on_hand=Decimal(0)
                        )
                    )
                    self.inventory_service.adjust_inventory(
                        new_inventory.id,
                        InventoryAdjust(
                            quantity=actual_received,
                            transaction_type=TransactionType.IN,
                            reference_type="PO",
                            reference_id=po.po_number,
                            reason=f"발주 입고: {po.po_number} (로트: {lot_number})"
                        )
                    )

                # 3. 부품 가격 정보 업데이트 (v0.18.0 원가관리)
                # - 재고단가 (이동평균)
                # - 최근단가
                # - 가격 이력 기록
                self.price_service.update_part_prices_on_receive(
                    part_id=item.part_id,
                    received_quantity=actual_received,
                    unit_price=final_unit_price,  # 조정된 단가 또는 기존 단가
                    currency=po.currency or "KRW",
                    supplier_id=po.supplier_id,
                    po_number=po.po_number
                )

                # 4. 평균단가 캐시 업데이트
                self.price_service.update_avg_price_cache(item.part_id)

        # 전체 입고 완료 체크
        all_received = all(
            (item.received_quantity or Decimal(0)) >= item.ordered_quantity
            for item in po.items
        )

        if all_received:
            po.status = PurchaseOrderStatus.RECEIVED.value
        else:
            # 부분 입고 상태 유지 (이미 RECEIVED가 아닌 경우)
            if po.status != PurchaseOrderStatus.RECEIVED.value:
                po.status = PurchaseOrderStatus.RECEIVED.value  # 부분 입고도 RECEIVED로 처리

        # 실제 입고일 설정
        if request.actual_delivery_date:
            po.actual_delivery_date = request.actual_delivery_date
        else:
            po.actual_delivery_date = date.today()

        po.updated_at = datetime.now()
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    # complete 메서드는 더 이상 사용하지 않음 - 결재는 is_paid 필드로 별도 관리
    # def complete(self, po_id: int) -> PurchaseOrder: ...

    def cancel(self, po_id: int, reason: Optional[str] = None) -> PurchaseOrder:
        """
        발주 취소

        Args:
            po_id: 발주서 ID
            reason: 취소 사유

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)
        self._validate_transition(po.status, PurchaseOrderStatus.CANCELLED)

        po.status = PurchaseOrderStatus.CANCELLED.value
        if reason:
            po.remarks = (po.remarks + "\n[취소사유] " if po.remarks else "[취소사유] ") + reason
        po.updated_at = datetime.now()
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    # ==================== 파일 첨부 ====================

    def add_document_file(self, po_id: int, file_info: dict) -> PurchaseOrder:
        """
        문서 파일 첨부

        Args:
            po_id: 발주서 ID
            file_info: 파일 정보 (file_name, file_path, file_size 등)

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)

        files = po.document_files or []
        files.append(file_info)
        po.document_files = files
        po.updated_at = datetime.now()
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    def remove_document_file(self, po_id: int, file_index: int) -> PurchaseOrder:
        """
        문서 파일 삭제

        Args:
            po_id: 발주서 ID
            file_index: 파일 인덱스

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)

        files = po.document_files or []
        if file_index < 0 or file_index >= len(files):
            raise ValidationException(f"유효하지 않은 파일 인덱스: {file_index}")

        files.pop(file_index)
        po.document_files = files
        po.updated_at = datetime.now()
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    # ==================== 부품 가격 이력 ====================

    def get_part_price_history(self, part_id: int, limit: int = 5) -> List[dict]:
        """
        부품별 이전 구매 가격 이력 조회

        Args:
            part_id: 부품 ID
            limit: 조회 개수

        Returns:
            가격 이력 목록 [{ unit_price, order_date, supplier_name }]
        """
        return self.repository.get_part_price_history(part_id, limit)

    # ==================== 결제 처리 ====================

    def mark_sent(self, po_id: int, sent: bool, actor_id: Optional[int] = None) -> PurchaseOrder:
        """발주서 발송 완료/취소 — 발송 완료 시 발송일자 기록(생산요청 인서트출고와 동일 방식)."""
        po = self.get_or_raise(po_id)
        if sent:
            po.sent_at = datetime.now()
            po.sent_by = actor_id
        else:
            po.sent_at = None
            po.sent_by = None
        self.db.commit()
        self.db.refresh(po)
        return po

    def update_payment(self, po_id: int, request: PaymentRequest) -> PurchaseOrder:
        """
        결제 상태 업데이트

        발주서의 결제 여부를 업데이트합니다.
        결제는 발주 프로세스 상태와 별도로 관리됩니다.

        Args:
            po_id: 발주서 ID
            request: 결제 요청

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)

        po.is_paid = request.is_paid

        if request.is_paid:
            # 결제 완료 처리
            po.paid_date = request.paid_date or date.today()
            po.paid_amount = request.paid_amount or po.total_amount
        else:
            # 결제 취소 처리
            po.paid_date = None
            po.paid_amount = None

        po.updated_at = datetime.now()
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)

    # ==================== 상태 롤백 (v0.6.1) ====================

    def rollback(self, po_id: int, reason: Optional[str] = None) -> PurchaseOrder:
        """
        상태 롤백 (이전 상태로 되돌리기)

        입고완료 상태에서 롤백 시 재고가 차감됩니다.

        Args:
            po_id: 발주서 ID
            reason: 롤백 사유

        Returns:
            수정된 발주서
        """
        po = self.get_or_raise(po_id)
        current_status = PurchaseOrderStatus(po.status)

        # 롤백 가능 여부 확인
        if current_status not in self.VALID_ROLLBACKS:
            raise BusinessRuleException(
                f"'{current_status.value}' 상태에서는 롤백할 수 없습니다."
            )

        previous_status = self.VALID_ROLLBACKS[current_status]

        # RECEIVED -> CONFIRMED 롤백 시 재고 차감
        if current_status == PurchaseOrderStatus.RECEIVED:
            for item in po.items:
                # 입고된 수량만큼 재고 차감
                received = item.received_quantity or Decimal(0)
                defective = item.defective_quantity or Decimal(0)
                actual_received = received - defective

                if actual_received > 0:
                    inventory = self.inventory_service.get_by_part_id(item.part_id)
                    if inventory:
                        self.inventory_service.adjust_inventory(
                            inventory.id,
                            InventoryAdjust(
                                quantity=actual_received,
                                transaction_type=TransactionType.OUT,
                                reference_type="PO",
                                reference_id=po.po_number,
                                reason=f"상태 롤백 재고 차감: {po.po_number}"
                            )
                        )

                # 입고 수량 초기화
                item.received_quantity = Decimal(0)
                item.defective_quantity = Decimal(0)

            # 입고일 초기화
            po.actual_delivery_date = None

        # 상태 변경
        po.status = previous_status.value

        # 비고에 롤백 사유 추가
        if reason:
            po.remarks = (po.remarks + "\n[롤백] " if po.remarks else "[롤백] ") + reason

        po.updated_at = datetime.now()
        self.db.commit()

        return self.repository.get_by_id_with_relations(po_id)
