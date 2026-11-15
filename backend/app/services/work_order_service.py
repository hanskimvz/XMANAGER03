"""
Work Order Service (v0.6.0)
작업지시서 관련 비즈니스 로직을 처리합니다.

Repository Pattern을 통해 데이터 접근 로직과 분리됩니다.

v0.6.0: 입출고 관리 기능 추가
- 작업지시서 CRUD
- BOM 자동 전개
- 상태 전이 관리 (7단계)
- 부품 출고 → 재고 감소

v0.19.0: 다중 제품 지원
- WorkOrderProduct를 통해 작업지시서당 여러 제품 지원
- products 파라미터로 다중 제품 생성
"""

from typing import Optional, List, Tuple
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.work_order_repository import WorkOrderRepository, WorkOrderItemRepository
from app.models.work_order import WorkOrder, WorkOrderItem, WorkOrderProduct
from app.models.bom import BOM
from app.models.parts import Part
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderItemCreate,
    WorkOrderStatus,
    IssueRequest,
    IssueItemRequest,
    AdditionalIssueRequest,
    ReturnRequest,
    ProductionCompleteRequest,
    BOMPreviewItem,
    BOMPreviewResponse,
)
from app.schemas.inventory import TransactionType, InventoryAdjust
from app.schemas.inventory_lot import (
    WorkOrderIssueRequest,
    WorkOrderItemIssueRequest,
    ProductionAvailabilityResponse,
)
from app.services.inventory_service import InventoryService
from app.services.inventory_lot_service import InventoryLotService
from app.utils.number_generator import generate_wo_number
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException,
)
from app.models.process_log import WorkOrderProcessLog


class WorkOrderService:
    """
    작업지시서 서비스

    작업지시서 관련 비즈니스 로직을 캡슐화합니다.
    - 작업지시서 CRUD
    - BOM 자동 전개
    - 상태 전이 (7단계)
    - 부품 출고 시 재고 자동 감소
    """

    # 상태 전이 규칙 정의
    VALID_TRANSITIONS = {
        WorkOrderStatus.RECEIVED: [WorkOrderStatus.APPROVED, WorkOrderStatus.CANCELLED],
        WorkOrderStatus.APPROVED: [WorkOrderStatus.ISSUED, WorkOrderStatus.CANCELLED],
        WorkOrderStatus.ISSUED: [WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED],
        WorkOrderStatus.IN_PROGRESS: [WorkOrderStatus.INSPECTION],
        WorkOrderStatus.INSPECTION: [WorkOrderStatus.PACKED],
        WorkOrderStatus.PACKED: [WorkOrderStatus.SHIPPED],
        WorkOrderStatus.SHIPPED: [],
        WorkOrderStatus.CANCELLED: [],
    }

    # 상태 롤백 규칙 정의 (이전 상태로 되돌리기)
    VALID_ROLLBACKS = {
        WorkOrderStatus.APPROVED: WorkOrderStatus.RECEIVED,      # 승인 -> 접수
        WorkOrderStatus.ISSUED: WorkOrderStatus.APPROVED,        # 출고 -> 승인 (재고 복구)
        WorkOrderStatus.IN_PROGRESS: WorkOrderStatus.ISSUED,     # 작업중 -> 출고
        WorkOrderStatus.INSPECTION: WorkOrderStatus.IN_PROGRESS, # 검사 -> 작업중
        WorkOrderStatus.PACKED: WorkOrderStatus.INSPECTION,      # 포장 -> 검사
        # SHIPPED, CANCELLED는 롤백 불가
    }

    def __init__(self, db: Session):
        self.db = db
        self.repository = WorkOrderRepository(db)
        self.item_repository = WorkOrderItemRepository(db)
        self.inventory_service = InventoryService(db)
        self.lot_service = InventoryLotService(db)

    # ==================== 조회 ====================

    def get(self, id: int) -> Optional[WorkOrder]:
        """ID로 작업지시서 조회"""
        return self.repository.get_by_id_with_relations(id)

    def get_or_raise(self, id: int) -> WorkOrder:
        """ID로 작업지시서 조회 (없으면 예외)"""
        wo = self.repository.get_by_id_with_relations(id)
        if not wo:
            raise NotFoundException("작업지시서", id)
        return wo

    def get_by_wo_number(self, wo_number: str) -> Optional[WorkOrder]:
        """작업지시서 번호로 조회"""
        return self.repository.get_by_wo_number_with_relations(wo_number)

    def search_work_orders(
        self,
        keyword: Optional[str] = None,
        status: Optional[WorkOrderStatus] = None,
        customer_id: Optional[int] = None,
        product_part_id: Optional[int] = None,
        priority: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[WorkOrder]:
        """작업지시서 검색"""
        return self.repository.search_work_orders(
            keyword=keyword,
            status=status,
            customer_id=customer_id,
            product_part_id=product_part_id,
            priority=priority,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    def search_work_orders_with_count(
        self,
        keyword: Optional[str] = None,
        status: Optional[WorkOrderStatus] = None,
        customer_id: Optional[int] = None,
        product_part_id: Optional[int] = None,
        priority: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[WorkOrder], int]:
        """작업지시서 검색 + 총 개수"""
        return self.repository.search_work_orders_with_count(
            keyword=keyword,
            status=status,
            customer_id=customer_id,
            product_part_id=product_part_id,
            priority=priority,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    # ==================== BOM 전개 ====================

    def _expand_bom(self, parent_part_id: int, multiplier: Decimal = Decimal(1), level: int = 1) -> List[dict]:
        """
        BOM 재귀 전개 (내부 메서드)

        Args:
            parent_part_id: 상위 부품 ID
            multiplier: 수량 배수
            level: 현재 BOM 레벨

        Returns:
            전개된 항목 목록
        """
        items = []

        # 하위 BOM 조회
        bom_entries = self.db.query(BOM).filter(
            BOM.parent_part_id == parent_part_id,
            BOM.is_active == True
        ).order_by(BOM.sort_order).all()

        for bom in bom_entries:
            child_part = self.db.query(Part).filter(Part.id == bom.child_part_id).first()
            if not child_part:
                continue

            quantity = Decimal(str(bom.quantity)) * multiplier

            items.append({
                "part_id": bom.child_part_id,
                "bom_id": bom.id,
                "bom_level": level,
                "quantity": quantity,
                "unit_id": bom.unit_id,
                "part": child_part,
            })

            # 하위 BOM이 있으면 재귀 전개 (최대 5레벨)
            if level < 5:
                child_items = self._expand_bom(bom.child_part_id, quantity, level + 1)
                items.extend(child_items)

        return items

    def _expand_bom_for_work_order(self, wo: WorkOrder) -> None:
        """
        작업지시서에 BOM 항목 전개 (내부 메서드)

        이미 존재하는 작업지시서에 BOM을 기반으로 WorkOrderItem을 생성합니다.
        v0.19.0: 다중 제품 지원 - products가 있으면 각 제품별로 전개

        Args:
            wo: 작업지시서 객체
        """
        global_sort_order = 0

        # v0.19.0: 다중 제품이 있으면 각 제품별로 전개
        if wo.products:
            for wo_product in wo.products:
                expanded_items = self._expand_bom(wo_product.product_part_id, wo_product.order_quantity)

                for idx, item_data in enumerate(expanded_items):
                    item = WorkOrderItem(
                        work_order_id=wo.id,
                        work_order_product_id=wo_product.id,
                        part_id=item_data["part_id"],
                        bom_id=item_data["bom_id"],
                        required_quantity=item_data["quantity"],
                        issued_quantity=Decimal(0),
                        additional_quantity=Decimal(0),
                        returned_quantity=Decimal(0),
                        unit_id=item_data.get("unit_id"),
                        bom_level=item_data["bom_level"],
                        sort_order=global_sort_order,
                    )
                    self.db.add(item)
                    global_sort_order += 1
        else:
            # 기존 호환성: product_part_id 사용
            expanded_items = self._expand_bom(wo.product_part_id, wo.order_quantity)

            for idx, item_data in enumerate(expanded_items):
                item = WorkOrderItem(
                    work_order_id=wo.id,
                    work_order_product_id=None,
                    part_id=item_data["part_id"],
                    bom_id=item_data["bom_id"],
                    required_quantity=item_data["quantity"],
                    issued_quantity=Decimal(0),
                    additional_quantity=Decimal(0),
                    returned_quantity=Decimal(0),
                    unit_id=item_data.get("unit_id"),
                    bom_level=item_data["bom_level"],
                    sort_order=idx,
                )
                self.db.add(item)

    def get_bom_preview(self, product_part_id: int, order_quantity: Decimal) -> BOMPreviewResponse:
        """
        BOM 전개 미리보기

        Args:
            product_part_id: 완제품 부품 ID
            order_quantity: 지시 수량

        Returns:
            BOM 전개 결과
        """
        # 완제품 정보
        product_part = self.db.query(Part).filter(Part.id == product_part_id).first()
        if not product_part:
            raise NotFoundException("부품", product_part_id)

        # BOM 전개
        expanded_items = self._expand_bom(product_part_id, order_quantity)

        # 재고 정보 추가
        preview_items = []
        has_insufficient = False

        for item in expanded_items:
            part = item["part"]
            inventory = self.inventory_service.get_by_part_id(part.id)
            current_stock = inventory.quantity_on_hand if inventory else Decimal(0)
            stock_status = "SUFFICIENT" if current_stock >= item["quantity"] else "INSUFFICIENT"

            if stock_status == "INSUFFICIENT":
                has_insufficient = True

            preview_items.append(BOMPreviewItem(
                part_id=part.id,
                part_number=part.part_number,
                part_number_display=part.part_number_display,
                part_name=part.part_name,
                bom_id=item["bom_id"],
                bom_level=item["bom_level"],
                unit_quantity=item["quantity"] / order_quantity if order_quantity else Decimal(0),
                total_quantity=item["quantity"],
                current_stock=current_stock,
                stock_status=stock_status,
            ))

        return BOMPreviewResponse(
            product_part_id=product_part_id,
            product_part_name=product_part.part_name,
            order_quantity=order_quantity,
            items=preview_items,
            has_insufficient_stock=has_insufficient,
        )

    # ==================== 생성 ====================

    def create_work_order(self, wo_in: WorkOrderCreate) -> WorkOrder:
        """
        작업지시서 생성 (v0.19.0 다중 제품 지원)

        BOM이 있으면 자동으로 전개하여 항목을 생성합니다.

        Args:
            wo_in: 작업지시서 생성 데이터

        Returns:
            생성된 작업지시서
        """
        # 제품 목록 확인 (v0.19.0)
        if not wo_in.products:
            raise ValidationException("제품 목록이 필요합니다.")

        # 각 제품의 부품 확인
        for product in wo_in.products:
            part = self.db.query(Part).filter(Part.id == product.product_part_id).first()
            if not part:
                raise NotFoundException("부품", product.product_part_id)

        # 작업지시서 번호 자동 생성
        wo_number = generate_wo_number(self.db)

        # 작업지시서 생성 (v0.19.0: product_part_id, order_quantity는 deprecated)
        # 호환성을 위해 첫 번째 제품의 정보로 설정
        first_product = wo_in.products[0]
        wo = WorkOrder(
            wo_number=wo_number,
            product_part_id=first_product.product_part_id,  # deprecated - 호환성용
            production_request_id=wo_in.production_request_id,  # v0.20.0: 생산요청 연결
            parent_wo_id=wo_in.parent_wo_id,  # v0.31.0: 상위 WO 체인
            target_part_id=wo_in.target_part_id,  # v0.31.0: 목적 부품
            customer_id=wo_in.customer_id,
            customer_order_no=wo_in.customer_order_no,
            order_quantity=first_product.order_quantity,  # deprecated - 호환성용
            completed_quantity=Decimal(0),
            defective_quantity=Decimal(0),
            status=WorkOrderStatus.RECEIVED.value,
            priority=wo_in.priority,
            remarks=wo_in.remarks,
            issue_scheduled_date=wo_in.issue_scheduled_date,
            production_scheduled_date=wo_in.production_scheduled_date,
            inspection_scheduled_date=wo_in.inspection_scheduled_date,
            packing_scheduled_date=wo_in.packing_scheduled_date,
            shipping_scheduled_date=wo_in.shipping_scheduled_date,
        )
        self.db.add(wo)
        self.db.flush()

        # v0.20.0: 생산요청 상태 업데이트 (IN_PROGRESS)
        if wo_in.production_request_id:
            from app.models.production_request import ProductionRequest
            pr = self.db.query(ProductionRequest).filter(
                ProductionRequest.id == wo_in.production_request_id
            ).first()
            if pr and pr.status == "APPROVED":
                pr.status = "IN_PROGRESS"

        # v0.19.0: 각 제품별로 WorkOrderProduct 생성 및 BOM 전개
        global_sort_order = 0
        for prod_idx, product_in in enumerate(wo_in.products):
            # WorkOrderProduct 생성
            wo_product = WorkOrderProduct(
                work_order_id=wo.id,
                product_part_id=product_in.product_part_id,
                order_quantity=product_in.order_quantity,
                completed_quantity=Decimal(0),
                defective_quantity=Decimal(0),
                sort_order=product_in.sort_order if product_in.sort_order else prod_idx,
                line_remarks=product_in.line_remarks,
            )
            self.db.add(wo_product)
            self.db.flush()

            # BOM 자동 전개
            if wo_in.auto_expand_bom:
                expanded_items = self._expand_bom(product_in.product_part_id, product_in.order_quantity)

                for idx, item_data in enumerate(expanded_items):
                    item = WorkOrderItem(
                        work_order_id=wo.id,
                        work_order_product_id=wo_product.id,  # v0.19.0
                        part_id=item_data["part_id"],
                        bom_id=item_data["bom_id"],
                        required_quantity=item_data["quantity"],
                        issued_quantity=Decimal(0),
                        additional_quantity=Decimal(0),
                        returned_quantity=Decimal(0),
                        unit_id=item_data.get("unit_id"),
                        bom_level=item_data["bom_level"],
                        sort_order=global_sort_order,
                    )
                    self.db.add(item)
                    global_sort_order += 1

        # 수동 항목 추가 (제품과 연결되지 않은 항목)
        if wo_in.items:
            for idx, item_in in enumerate(wo_in.items):
                item = WorkOrderItem(
                    work_order_id=wo.id,
                    work_order_product_id=None,  # 수동 추가 항목은 제품 연결 없음
                    part_id=item_in.part_id,
                    bom_id=item_in.bom_id,
                    required_quantity=item_in.required_quantity,
                    issued_quantity=Decimal(0),
                    additional_quantity=Decimal(0),
                    returned_quantity=Decimal(0),
                    unit_id=item_in.unit_id,
                    bom_level=item_in.bom_level,
                    line_remarks=item_in.line_remarks,
                    sort_order=item_in.sort_order if item_in.sort_order else global_sort_order + idx,
                )
                self.db.add(item)

        self.db.commit()

        return self.repository.get_by_id_with_relations(wo.id)

    # ==================== 수정/삭제 ====================

    def update_work_order(self, wo_id: int, wo_in: WorkOrderUpdate) -> WorkOrder:
        """
        작업지시서 수정

        상태에 따라 수정 가능한 필드가 다릅니다:
        - RECEIVED: 모든 필드 수정 가능 (수량, 고객사, 예정일 등)
        - APPROVED ~ IN_PROGRESS: 예정일, 우선순위, 비고 수정 가능
        - INSPECTION ~ SHIPPED: 비고만 수정 가능
        - CANCELLED: 수정 불가

        Args:
            wo_id: 작업지시서 ID
            wo_in: 수정 데이터

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        update_data = wo_in.model_dump(exclude_unset=True)

        # 상태별 수정 가능 필드 제한
        if wo.status == WorkOrderStatus.CANCELLED.value:
            raise BusinessRuleException("취소된 작업지시서는 수정할 수 없습니다.")

        if wo.status in [WorkOrderStatus.INSPECTION.value, WorkOrderStatus.PACKED.value, WorkOrderStatus.SHIPPED.value]:
            # 검사 이후 상태: 비고만 수정 가능
            allowed_fields = {'remarks'}
            update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        elif wo.status in [WorkOrderStatus.APPROVED.value, WorkOrderStatus.ISSUED.value, WorkOrderStatus.IN_PROGRESS.value]:
            # 승인~작업중: 예정일, 우선순위, 비고 수정 가능
            allowed_fields = {
                'priority', 'remarks',
                'issue_scheduled_date', 'production_scheduled_date',
                'inspection_scheduled_date', 'packing_scheduled_date', 'shipping_scheduled_date'
            }
            update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        # RECEIVED 상태: 모든 필드 수정 가능

        if not update_data:
            return self.repository.get_by_id_with_relations(wo_id)

        # RECEIVED 상태에서 수량 변경 시 항목의 필요수량도 비례 조정
        if wo.status == WorkOrderStatus.RECEIVED.value:
            if "order_quantity" in update_data and update_data["order_quantity"] != wo.order_quantity:
                old_qty = wo.order_quantity
                new_qty = update_data["order_quantity"]
                ratio = new_qty / old_qty if old_qty else Decimal(1)

                for item in wo.items:
                    item.required_quantity = item.required_quantity * ratio

        self.repository.update_from_dict(wo, update_data)

        return self.repository.get_by_id_with_relations(wo_id)

    def delete_work_order(self, wo_id: int) -> bool:
        """
        작업지시서 삭제 (취소 상태에서만)

        취소된 작업지시서만 완전 삭제가 가능합니다.
        진행 중인 작업지시서는 먼저 취소 처리 후 삭제해야 합니다.

        Args:
            wo_id: 작업지시서 ID

        Returns:
            삭제 성공 여부
        """
        wo = self.get_or_raise(wo_id)

        # 취소 상태에서만 삭제 가능
        if wo.status != WorkOrderStatus.CANCELLED.value:
            raise BusinessRuleException("취소된 작업지시서만 삭제할 수 있습니다. 먼저 취소 처리를 해주세요.")

        return self.repository.delete(wo)

    # ==================== 상태 전이 ====================

    def _validate_transition(self, current: str, target: WorkOrderStatus) -> None:
        """상태 전이 유효성 검사"""
        current_status = WorkOrderStatus(current)
        valid_targets = self.VALID_TRANSITIONS.get(current_status, [])

        if target not in valid_targets:
            raise BusinessRuleException(
                f"'{current}' 상태에서 '{target.value}' 상태로 변경할 수 없습니다. "
                f"가능한 상태: {[s.value for s in valid_targets]}"
            )

    def approve(self, wo_id: int, approved_by: Optional[int] = None, worker_name: Optional[str] = None) -> WorkOrder:
        """
        승인 (RECEIVED → APPROVED)

        Args:
            wo_id: 작업지시서 ID
            approved_by: 승인자 ID

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        self._validate_transition(wo.status, WorkOrderStatus.APPROVED)

        # 항목이 없으면 BOM에서 자동 전개 시도
        if not wo.items or len(wo.items) == 0:
            # BOM 전개 시도
            self._expand_bom_for_work_order(wo)
            self.db.flush()

            # 그래도 없으면 BOM 미등록 안내
            if not wo.items or len(wo.items) == 0:
                raise BusinessRuleException(
                    "해당 완제품에 등록된 BOM이 없습니다. BOM 관리에서 먼저 BOM을 등록해주세요."
                )

        wo.status = WorkOrderStatus.APPROVED.value
        wo.approved_date = datetime.now(timezone.utc)
        wo.approved_by = approved_by
        wo.updated_at = datetime.now(timezone.utc)

        # 공정 로그: 접수→승인 (작업지시서 생성~승인까지 소요시간)
        self._log_process(wo, "APPROVAL", "승인", started=wo.received_date, completed=wo.approved_date, worker_name=worker_name)

        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def issue_parts(self, wo_id: int, request: Optional[IssueRequest] = None, worker_name: Optional[str] = None) -> WorkOrder:
        """
        부품 출고 (APPROVED → ISSUED)

        출고된 수량만큼 재고가 자동으로 감소합니다.

        Args:
            wo_id: 작업지시서 ID
            request: 출고 요청 (None이면 전체 출고)

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        self._validate_transition(wo.status, WorkOrderStatus.ISSUED)

        # 재고 부족 체크
        insufficient_items = []
        for item in wo.items:
            inventory = self.inventory_service.get_by_part_id(item.part_id)
            available = inventory.quantity_on_hand if inventory else Decimal(0)
            needed = item.required_quantity - (item.issued_quantity or Decimal(0))

            if needed > available:
                insufficient_items.append({
                    "part_id": item.part_id,
                    "part_name": item.part.part_name if item.part else "",
                    "needed": needed,
                    "available": available,
                })

        if insufficient_items:
            items_str = ", ".join([
                f"{i['part_name']}(필요:{i['needed']}/가용:{i['available']})"
                for i in insufficient_items[:3]
            ])
            raise BusinessRuleException(f"재고 부족: {items_str}")

        # 출고 처리
        for item in wo.items:
            issue_qty = item.required_quantity - (item.issued_quantity or Decimal(0))

            if issue_qty > 0:
                # 재고 감소
                inventory = self.inventory_service.get_by_part_id(item.part_id)
                if inventory:
                    self.inventory_service.adjust_inventory(
                        inventory.id,
                        InventoryAdjust(
                            quantity=issue_qty,
                            transaction_type=TransactionType.OUT,
                            reference_type="WO",
                            reference_id=wo.wo_number,
                            reason=f"작업지시 출고: {wo.wo_number}"
                        )
                    )

                # 항목 업데이트
                item.issued_quantity = item.required_quantity

        wo.status = WorkOrderStatus.ISSUED.value
        wo.issue_completed_date = datetime.now(timezone.utc)
        wo.updated_at = datetime.now(timezone.utc)

        # 공정 로그: 승인→출고 (부품 출고 소요시간)
        self._log_process(wo, "PARTS_ISSUE", "부품 출고", started=wo.approved_date, completed=wo.issue_completed_date, worker_name=worker_name)

        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def issue_additional(self, wo_id: int, item_id: int, request: AdditionalIssueRequest) -> WorkOrder:
        """
        추가 출고 (불량 대응 등)

        Args:
            wo_id: 작업지시서 ID
            item_id: 항목 ID
            request: 추가 출고 요청

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)

        # ISSUED 또는 IN_PROGRESS 상태에서만 추가 출고 가능
        if wo.status not in [WorkOrderStatus.ISSUED.value, WorkOrderStatus.IN_PROGRESS.value]:
            raise BusinessRuleException("부품출고 또는 작업중 상태에서만 추가 출고가 가능합니다.")

        # 항목 조회
        item = self.item_repository.get_by_id(item_id)
        if not item or item.work_order_id != wo_id:
            raise NotFoundException("작업지시서 항목", item_id)

        # 재고 확인
        inventory = self.inventory_service.get_by_part_id(item.part_id)
        available = inventory.quantity_on_hand if inventory else Decimal(0)

        if request.quantity > available:
            raise BusinessRuleException(
                f"재고 부족: 필요 {request.quantity}, 가용 {available}"
            )

        # 재고 감소
        if inventory:
            self.inventory_service.adjust_inventory(
                inventory.id,
                InventoryAdjust(
                    quantity=request.quantity,
                    transaction_type=TransactionType.OUT,
                    reference_type="WO",
                    reference_id=wo.wo_number,
                    reason=request.reason or f"추가 출고: {wo.wo_number}"
                )
            )

        # 항목 업데이트
        item.additional_quantity = (item.additional_quantity or Decimal(0)) + request.quantity
        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def return_parts(self, wo_id: int, item_id: int, request: ReturnRequest) -> WorkOrder:
        """
        부품 반납

        Args:
            wo_id: 작업지시서 ID
            item_id: 항목 ID
            request: 반납 요청

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)

        # 항목 조회
        item = self.item_repository.get_by_id(item_id)
        if not item or item.work_order_id != wo_id:
            raise NotFoundException("작업지시서 항목", item_id)

        # 총 출고량 계산
        total_issued = (item.issued_quantity or Decimal(0)) + (item.additional_quantity or Decimal(0))
        already_returned = item.returned_quantity or Decimal(0)
        max_returnable = total_issued - already_returned

        if request.quantity > max_returnable:
            raise ValidationException(
                f"반납 가능 수량({max_returnable})을 초과합니다."
            )

        # 재고 증가
        inventory = self.inventory_service.get_by_part_id(item.part_id)
        if inventory:
            self.inventory_service.adjust_inventory(
                inventory.id,
                InventoryAdjust(
                    quantity=request.quantity,
                    transaction_type=TransactionType.RETURN,
                    reference_type="WO",
                    reference_id=wo.wo_number,
                    reason=request.reason or f"부품 반납: {wo.wo_number}"
                )
            )

        # 항목 업데이트
        item.returned_quantity = already_returned + request.quantity
        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def start_production(self, wo_id: int, worker_name: Optional[str] = None) -> WorkOrder:
        """
        작업 시작 (ISSUED → IN_PROGRESS)

        Args:
            wo_id: 작업지시서 ID

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        self._validate_transition(wo.status, WorkOrderStatus.IN_PROGRESS)

        wo.status = WorkOrderStatus.IN_PROGRESS.value
        wo.production_start_date = datetime.now(timezone.utc)
        wo.updated_at = datetime.now(timezone.utc)

        # 공정 로그: 출고→작업시작 (조립 준비 소요시간)
        self._log_process(wo, "PRODUCTION_START", "작업 시작", started=wo.issue_completed_date, completed=wo.production_start_date, worker_name=worker_name)

        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def complete_production(self, wo_id: int, request: ProductionCompleteRequest, worker_name: Optional[str] = None) -> WorkOrder:
        """
        작업 완료 (IN_PROGRESS → INSPECTION)

        Args:
            wo_id: 작업지시서 ID
            request: 생산 완료 요청

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        self._validate_transition(wo.status, WorkOrderStatus.INSPECTION)

        # 완료 수량 검증
        total_completed = request.completed_quantity + request.defective_quantity
        if total_completed > wo.order_quantity:
            raise ValidationException(
                f"완료 수량({total_completed})이 지시 수량({wo.order_quantity})을 초과합니다."
            )

        wo.status = WorkOrderStatus.INSPECTION.value
        wo.completed_quantity = request.completed_quantity
        wo.defective_quantity = request.defective_quantity
        wo.production_end_date = datetime.now(timezone.utc)
        if request.remarks:
            wo.remarks = (wo.remarks + "\n" if wo.remarks else "") + request.remarks
        wo.updated_at = datetime.now(timezone.utc)

        # 공정 로그: 작업시작→작업완료 (생산/조립 소요시간)
        self._log_process(wo, "PRODUCTION", "생산/조립", started=wo.production_start_date, completed=wo.production_end_date, worker_name=worker_name)

        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def complete_inspection(self, wo_id: int, worker_name: Optional[str] = None) -> WorkOrder:
        """
        검사 완료 (INSPECTION → PACKED)

        Args:
            wo_id: 작업지시서 ID

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        self._validate_transition(wo.status, WorkOrderStatus.PACKED)

        wo.status = WorkOrderStatus.PACKED.value
        wo.inspection_completed_date = datetime.now(timezone.utc)
        wo.packing_completed_date = datetime.now(timezone.utc)  # 검사 완료 시 포장 완료로 처리
        wo.updated_at = datetime.now(timezone.utc)

        # 공정 로그: 작업완료→검사/포장 완료
        self._log_process(wo, "INSPECTION_PACKING", "검사/포장", started=wo.production_end_date, completed=wo.inspection_completed_date, worker_name=worker_name)

        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def ship(self, wo_id: int, worker_name: Optional[str] = None) -> WorkOrder:
        """
        출하 (PACKED → SHIPPED)

        Args:
            wo_id: 작업지시서 ID

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        self._validate_transition(wo.status, WorkOrderStatus.SHIPPED)

        wo.status = WorkOrderStatus.SHIPPED.value
        wo.shipping_completed_date = datetime.now(timezone.utc)
        wo.updated_at = datetime.now(timezone.utc)

        # 공정 로그: 포장→출하 완료
        self._log_process(wo, "SHIPPING", "출하", started=wo.packing_completed_date, completed=wo.shipping_completed_date, worker_name=worker_name)

        # 공정 로그: 전체 리드타임 (접수→출하)
        self._log_process(wo, "TOTAL_LEAD_TIME", "전체 리드타임", started=wo.received_date, completed=wo.shipping_completed_date, worker_name=worker_name)

        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    # ==================== 공정 로그 자동 기록 (v0.24.0) ====================

    def _log_process(self, wo: WorkOrder, process_type: str, process_name: str,
                     started=None, completed=None, worker_name=None):
        """상태 변경 시 공정 로그 자동 기록"""
        if not started or not completed:
            return

        delta = completed - started
        duration_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))

        log = WorkOrderProcessLog(
            work_order_id=wo.id,
            process_type=process_type,
            process_name=process_name,
            started_at=started,
            completed_at=completed,
            duration_hours=duration_hours,
            worker_name=worker_name,
        )
        self.db.add(log)

    def cancel(self, wo_id: int, reason: Optional[str] = None) -> WorkOrder:
        """
        작업지시 취소

        출고된 부품은 재고로 복구합니다.
        취소 전 상태는 비고에 저장되어 복원 시 사용됩니다.

        Args:
            wo_id: 작업지시서 ID
            reason: 취소 사유

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        self._validate_transition(wo.status, WorkOrderStatus.CANCELLED)

        # 취소 전 상태 저장 (복원용)
        previous_status = wo.status

        # 출고된 부품 재고 복구
        if wo.status in [WorkOrderStatus.ISSUED.value, WorkOrderStatus.IN_PROGRESS.value]:
            for item in wo.items:
                total_issued = (item.issued_quantity or Decimal(0)) + (item.additional_quantity or Decimal(0))
                returned = item.returned_quantity or Decimal(0)
                to_return = total_issued - returned

                if to_return > 0:
                    inventory = self.inventory_service.get_by_part_id(item.part_id)
                    if inventory:
                        self.inventory_service.adjust_inventory(
                            inventory.id,
                            InventoryAdjust(
                                quantity=to_return,
                                transaction_type=TransactionType.RETURN,
                                reference_type="WO",
                                reference_id=wo.wo_number,
                                reason=f"작업지시 취소 복구: {wo.wo_number}"
                            )
                        )

        wo.status = WorkOrderStatus.CANCELLED.value
        # 취소 전 상태와 사유를 비고에 저장
        cancel_info = f"[취소:FROM={previous_status}]"
        if reason:
            cancel_info += f" {reason}"
        wo.remarks = (wo.remarks + "\n" if wo.remarks else "") + cancel_info
        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def restore(self, wo_id: int, reason: Optional[str] = None) -> WorkOrder:
        """
        취소된 작업지시서 복원

        취소 전 상태로 되돌립니다.
        단, 출고 상태였던 경우 재고가 다시 차감되지 않고 APPROVED 상태로 복원됩니다.

        Args:
            wo_id: 작업지시서 ID
            reason: 복원 사유

        Returns:
            복원된 작업지시서
        """
        wo = self.get_or_raise(wo_id)

        # 취소 상태인지 확인
        if wo.status != WorkOrderStatus.CANCELLED.value:
            raise BusinessRuleException("취소된 작업지시서만 복원할 수 있습니다.")

        # 비고에서 취소 전 상태 파싱
        restore_to_status = WorkOrderStatus.RECEIVED.value  # 기본값
        if wo.remarks:
            import re
            match = re.search(r'\[취소:FROM=(\w+)\]', wo.remarks)
            if match:
                restore_to_status = match.group(1)

        # 출고 상태였던 경우 APPROVED로 복원 (재고 재차감 방지)
        if restore_to_status in [WorkOrderStatus.ISSUED.value, WorkOrderStatus.IN_PROGRESS.value]:
            restore_to_status = WorkOrderStatus.APPROVED.value
            # 출고 수량 초기화
            for item in wo.items:
                item.issued_quantity = Decimal(0)
                item.additional_quantity = Decimal(0)
                item.returned_quantity = Decimal(0)
            wo.issue_completed_date = None

        wo.status = restore_to_status

        # 복원 정보를 비고에 추가
        restore_info = f"[복원:{restore_to_status}]"
        if reason:
            restore_info += f" {reason}"
        wo.remarks = (wo.remarks + "\n" if wo.remarks else "") + restore_info
        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    # ==================== 원본 요청서 수정 알림 (v0.21.0) ====================

    def get_modified_work_orders(self, skip: int = 0, limit: int = 20) -> list[WorkOrder]:
        """
        원본 요청서가 수정된 작업지시서 목록 조회

        source_request_modified=True인 작업지시서를 반환합니다.
        """
        return (
            self.db.query(WorkOrder)
            .filter(WorkOrder.source_request_modified == True)
            .filter(WorkOrder.status != "SHIPPED")
            .filter(WorkOrder.status != "CANCELLED")
            .order_by(WorkOrder.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def acknowledge_source_modification(self, wo_id: int) -> WorkOrder:
        """
        원본 요청서 수정 알림 확인

        source_request_modified 플래그를 False로 리셋합니다.

        Args:
            wo_id: 작업지시서 ID

        Returns:
            작업지시서
        """
        wo = self.get_or_raise(wo_id)
        wo.source_request_modified = False
        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    # ==================== 파일 첨부 ====================

    def add_document_file(self, wo_id: int, file_info: dict) -> WorkOrder:
        """문서 파일 첨부"""
        wo = self.get_or_raise(wo_id)

        files = wo.document_files or []
        files.append(file_info)
        wo.document_files = files
        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def remove_document_file(self, wo_id: int, file_index: int) -> WorkOrder:
        """문서 파일 삭제"""
        wo = self.get_or_raise(wo_id)

        files = wo.document_files or []
        if file_index < 0 or file_index >= len(files):
            raise ValidationException(f"유효하지 않은 파일 인덱스: {file_index}")

        files.pop(file_index)
        wo.document_files = files
        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    # ==================== 생산 가용수량 체크 (v0.7.0) ====================

    def check_production_availability(
        self,
        product_part_id: int,
        quantity: Decimal
    ) -> ProductionAvailabilityResponse:
        """
        BOM 기준 생산 가용수량 체크

        Args:
            product_part_id: 완제품 부품 ID
            quantity: 생산 수량

        Returns:
            생산 가용수량 응답
        """
        return self.lot_service.check_production_availability(product_part_id, quantity)

    # ==================== 로트 선택 출고 (v0.7.0) ====================

    def issue_parts_with_lots(
        self,
        wo_id: int,
        request: WorkOrderIssueRequest
    ) -> WorkOrder:
        """
        로트 선택 부품 출고 (APPROVED → ISSUED)

        FIFO 자동 또는 수동 로트 선택으로 출고합니다.

        Args:
            wo_id: 작업지시서 ID
            request: 출고 요청 (항목별 출고수량 및 로트 선택)

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        self._validate_transition(wo.status, WorkOrderStatus.ISSUED)

        # 각 항목별 출고 처리
        for item_request in request.items:
            # 항목 조회
            item = self.item_repository.get_by_id(item_request.item_id)
            if not item or item.work_order_id != wo_id:
                raise NotFoundException("작업지시서 항목", item_request.item_id)

            issue_qty = item_request.issue_quantity

            # FIFO 또는 수동 로트 선택
            issue_records = []
            if item_request.use_fifo:
                # FIFO 자동 출고 (로트가 없으면 빈 리스트 반환)
                issue_records = self.lot_service.issue_with_fifo(
                    work_order_item_id=item.id,
                    part_id=item.part_id,
                    quantity=issue_qty
                )
            elif item_request.lot_selections:
                # 수동 로트 선택 (로트가 지정된 경우에만)
                total_selected = sum(s.quantity for s in item_request.lot_selections)
                if total_selected != issue_qty:
                    raise ValidationException(
                        f"선택된 로트 수량 합계({total_selected})가 출고 수량({issue_qty})과 일치하지 않습니다."
                    )

                lot_selections = [
                    {"lot_id": s.lot_id, "quantity": s.quantity}
                    for s in item_request.lot_selections
                ]
                issue_records = self.lot_service.issue_from_lots(
                    work_order_item_id=item.id,
                    lot_selections=lot_selections
                )
            # else: 로트 없이 재고에서만 차감 (기존 재고 호환)

            # 재고 총량 감소 (Inventory 테이블)
            # 로트가 있으면 로트에서 이미 차감, 로트가 없으면 Inventory에서만 차감
            inventory = self.inventory_service.get_by_part_id(item.part_id)
            if inventory:
                if issue_records:
                    # 로트에서 차감한 경우 - Inventory 동기화 (이미 로트에서 차감됨)
                    reason = f"작업지시 출고: {wo.wo_number} (로트)"
                else:
                    # 로트 없이 출고 - Inventory에서만 차감
                    reason = f"작업지시 출고: {wo.wo_number}"
                self.inventory_service.adjust_inventory(
                    inventory.id,
                    InventoryAdjust(
                        quantity=issue_qty,
                        transaction_type=TransactionType.OUT,
                        reference_type="WO",
                        reference_id=wo.wo_number,
                        reason=reason
                    )
                )

            # 항목 출고수량 업데이트
            item.issued_quantity = (item.issued_quantity or Decimal(0)) + issue_qty

        wo.status = WorkOrderStatus.ISSUED.value
        wo.issue_completed_date = datetime.now(timezone.utc)
        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)

    def get_issue_records(self, wo_id: int, item_id: int) -> list:
        """
        작업지시서 항목별 출고 기록 조회

        Args:
            wo_id: 작업지시서 ID
            item_id: 항목 ID

        Returns:
            출고 기록 목록
        """
        wo = self.get_or_raise(wo_id)

        # 항목 확인
        item = self.item_repository.get_by_id(item_id)
        if not item or item.work_order_id != wo_id:
            raise NotFoundException("작업지시서 항목", item_id)

        return self.lot_service.get_issue_records(item_id)

    # ==================== 상태 롤백 (v0.6.1) ====================

    def rollback(self, wo_id: int, reason: Optional[str] = None) -> WorkOrder:
        """
        상태 롤백 (이전 상태로 되돌리기)

        출고 상태에서 롤백 시 재고가 자동 복구됩니다.

        Args:
            wo_id: 작업지시서 ID
            reason: 롤백 사유

        Returns:
            수정된 작업지시서
        """
        wo = self.get_or_raise(wo_id)
        current_status = WorkOrderStatus(wo.status)

        # 롤백 가능 여부 확인
        if current_status not in self.VALID_ROLLBACKS:
            raise BusinessRuleException(
                f"'{current_status.value}' 상태에서는 롤백할 수 없습니다."
            )

        previous_status = self.VALID_ROLLBACKS[current_status]

        # ISSUED -> APPROVED 롤백 시 재고 복구
        if current_status == WorkOrderStatus.ISSUED:
            for item in wo.items:
                total_issued = (item.issued_quantity or Decimal(0)) + (item.additional_quantity or Decimal(0))
                returned = item.returned_quantity or Decimal(0)
                to_return = total_issued - returned

                if to_return > 0:
                    inventory = self.inventory_service.get_by_part_id(item.part_id)
                    if inventory:
                        self.inventory_service.adjust_inventory(
                            inventory.id,
                            InventoryAdjust(
                                quantity=to_return,
                                transaction_type=TransactionType.RETURN,
                                reference_type="WO",
                                reference_id=wo.wo_number,
                                reason=f"상태 롤백 재고 복구: {wo.wo_number}"
                            )
                        )

                    # 출고 수량 초기화
                    item.issued_quantity = Decimal(0)
                    item.additional_quantity = Decimal(0)
                    item.returned_quantity = Decimal(0)

            # 출고 완료일 초기화
            wo.issue_completed_date = None

        # 상태 변경
        wo.status = previous_status.value

        # 해당 단계의 완료일 초기화
        if previous_status == WorkOrderStatus.RECEIVED:
            wo.approved_date = None
            wo.approved_by = None
        elif previous_status == WorkOrderStatus.ISSUED:
            wo.production_start_date = None
        elif previous_status == WorkOrderStatus.IN_PROGRESS:
            wo.production_end_date = None
        elif previous_status == WorkOrderStatus.INSPECTION:
            wo.inspection_completed_date = None
            wo.packing_completed_date = None

        # 비고에 롤백 사유 추가
        if reason:
            wo.remarks = (wo.remarks + "\n[롤백] " if wo.remarks else "[롤백] ") + reason

        wo.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return self.repository.get_by_id_with_relations(wo_id)
