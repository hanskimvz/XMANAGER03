"""
Business Partner Service
거래처(공급업체/고객사) 관련 비즈니스 로직을 처리합니다.

Repository Pattern을 통해 데이터 접근 로직과 분리됩니다.
"""

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.repositories.partner_repository import BusinessPartnerRepository
from app.models.business_partner import BusinessPartner
from app.schemas.business_partner import (
    BusinessPartnerCreate,
    BusinessPartnerUpdate,
)
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException,
    BusinessRuleException,
)


class BusinessPartnerService:
    """
    거래처 서비스

    공급업체와 고객사를 통합 관리합니다.
    Repository를 통해 데이터 접근 로직과 분리됩니다.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = BusinessPartnerRepository(db)

    # ==================== 조회 ====================

    def get(self, id: int) -> Optional[BusinessPartner]:
        """ID로 거래처 조회"""
        return self.repository.get_by_id(id)

    def get_or_raise(self, id: int) -> BusinessPartner:
        """ID로 거래처 조회 (없으면 예외)"""
        partner = self.repository.get_by_id(id)
        if not partner:
            raise NotFoundException("거래처", id)
        return partner

    def get_by_code(self, partner_code: str) -> Optional[BusinessPartner]:
        """
        거래처 코드로 조회

        Args:
            partner_code: 거래처 코드

        Returns:
            BusinessPartner 또는 None
        """
        return self.repository.get_by_code(partner_code)

    def get_by_code_or_raise(self, partner_code: str) -> BusinessPartner:
        """거래처 코드로 조회 (없으면 예외)"""
        partner = self.repository.get_by_code(partner_code)
        if not partner:
            raise NotFoundException("거래처", partner_code)
        return partner

    def search_partners(
        self,
        keyword: Optional[str] = None,
        is_supplier: Optional[bool] = None,
        is_customer: Optional[bool] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[BusinessPartner]:
        """
        거래처 검색

        Args:
            keyword: 검색 키워드 (코드, 거래처명)
            is_supplier: 공급업체 필터
            is_customer: 고객사 필터
            is_active: 활성 여부 필터
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            BusinessPartner 리스트
        """
        return self.repository.search_partners(
            keyword=keyword,
            is_supplier=is_supplier,
            is_customer=is_customer,
            is_active=is_active,
            skip=skip,
            limit=limit
        )

    def search_partners_with_count(
        self,
        keyword: Optional[str] = None,
        is_supplier: Optional[bool] = None,
        is_customer: Optional[bool] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[BusinessPartner], int]:
        """
        거래처 검색 + 총 개수 반환 (페이지네이션)

        Returns:
            (BusinessPartner 리스트, 총 개수) 튜플
        """
        return self.repository.search_partners_with_count(
            keyword=keyword,
            is_supplier=is_supplier,
            is_customer=is_customer,
            is_active=is_active,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    def count_partners(
        self,
        keyword: Optional[str] = None,
        is_supplier: Optional[bool] = None,
        is_customer: Optional[bool] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """거래처 수 조회 (검색 조건 적용)"""
        return self.repository.count_partners(
            keyword=keyword,
            is_supplier=is_supplier,
            is_customer=is_customer,
            is_active=is_active
        )

    def get_suppliers(
        self,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[BusinessPartner]:
        """공급업체 목록 조회"""
        return self.repository.get_suppliers(is_active, skip, limit)

    def get_customers(
        self,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[BusinessPartner]:
        """고객사 목록 조회"""
        return self.repository.get_customers(is_active, skip, limit)

    # ==================== 생성 ====================

    def create_partner(self, partner_in: BusinessPartnerCreate) -> BusinessPartner:
        """
        거래처 생성

        Args:
            partner_in: 거래처 생성 데이터

        Returns:
            생성된 BusinessPartner

        Raises:
            AlreadyExistsException: 동일한 코드가 이미 존재하는 경우
            ValidationException: 공급업체/고객사 중 하나 이상 선택되지 않은 경우
        """
        # 코드 중복 검사
        if self.repository.exists_by_code(partner_in.partner_code):
            raise AlreadyExistsException("거래처", "partner_code", partner_in.partner_code)

        # 유형 검증 (공급업체 또는 고객사 중 하나는 선택해야 함)
        if not partner_in.is_supplier and not partner_in.is_customer:
            raise ValidationException(
                "공급업체 또는 고객사 중 하나 이상을 선택해야 합니다.",
                field="is_supplier/is_customer"
            )

        partner = self.repository.create(partner_in)

        # v0.31.0: manager_* 데이터가 있으면 contacts 테이블에도 자동 생성
        self._sync_manager_to_contact(partner)

        return partner

    def _sync_manager_to_contact(self, partner):
        """manager_* 필드를 business_partner_contact 테이블에 동기화"""
        from app.models.business_partner_contact import BusinessPartnerContact

        if not partner.manager_name:
            return

        # 이미 같은 이름의 contact가 있는지 확인
        existing = self.db.query(BusinessPartnerContact).filter(
            BusinessPartnerContact.partner_id == partner.id,
            BusinessPartnerContact.name == partner.manager_name,
        ).first()

        if existing:
            # 기존 contact 업데이트
            existing.position = partner.manager_position or existing.position
            existing.email = partner.manager_email or existing.email
            existing.tel_mobile = partner.manager_mobile or existing.tel_mobile
            existing.tel_office = partner.manager_tel or existing.tel_office
        else:
            # 새 contact 생성
            contact = BusinessPartnerContact(
                partner_id=partner.id,
                name=partner.manager_name,
                position=partner.manager_position,
                email=partner.manager_email,
                tel_office=getattr(partner, 'manager_tel', None),
                tel_mobile=partner.manager_mobile,
                is_primary=True,
                sort_order=0,
            )
            self.db.add(contact)

        self.db.commit()

    # ==================== 수정 ====================

    def update_partner(self, partner_id: int, partner_in: BusinessPartnerUpdate) -> BusinessPartner:
        """
        거래처 수정

        Args:
            partner_id: 거래처 ID
            partner_in: 수정 데이터

        Returns:
            수정된 BusinessPartner

        Raises:
            NotFoundException: 거래처를 찾을 수 없는 경우
            AlreadyExistsException: 변경하려는 코드가 이미 존재하는 경우
        """
        db_partner = self.get_or_raise(partner_id)

        update_data = partner_in.model_dump(exclude_unset=True)

        # 코드 변경 시 중복 검사
        if 'partner_code' in update_data:
            new_code = update_data['partner_code']
            if new_code != db_partner.partner_code:
                if self.repository.exists_by_code(new_code):
                    raise AlreadyExistsException("거래처", "partner_code", new_code)

        # 유형 검증
        is_supplier = update_data.get('is_supplier', db_partner.is_supplier)
        is_customer = update_data.get('is_customer', db_partner.is_customer)
        if not is_supplier and not is_customer:
            raise ValidationException(
                "공급업체 또는 고객사 중 하나 이상을 선택해야 합니다.",
                field="is_supplier/is_customer"
            )

        result = self.repository.update_from_dict(db_partner, update_data)

        # v0.31.0: manager_* 변경 시 contacts 동기화
        manager_fields = ['manager_name', 'manager_position', 'manager_email', 'manager_mobile', 'manager_tel']
        if any(f in update_data for f in manager_fields):
            self._sync_manager_to_contact(result)

        return result

    # ==================== 상태 관리 ====================

    def activate(self, partner_id: int) -> BusinessPartner:
        """거래처 활성화"""
        db_partner = self.get_or_raise(partner_id)
        return self.repository.update_from_dict(db_partner, {"is_active": True})

    def deactivate(self, partner_id: int) -> BusinessPartner:
        """거래처 비활성화"""
        db_partner = self.get_or_raise(partner_id)
        return self.repository.update_from_dict(db_partner, {"is_active": False})

    # ==================== 삭제 ====================

    def delete_partner(self, partner_id: int) -> bool:
        """
        거래처 삭제 (사용 중인 경우 안내 메시지 포함)
        """
        db_partner = self.get_or_raise(partner_id)

        # 사용 중인 곳 체크
        usages = self._check_partner_usage(partner_id)
        if usages:
            usage_msg = ", ".join(usages)
            raise BusinessRuleException(
                f"이 거래처는 다음에서 사용 중이어서 삭제할 수 없습니다: {usage_msg}. "
                f"삭제 대신 '비활성화'를 사용하세요."
            )

        return self.repository.delete(db_partner)

    def _check_partner_usage(self, partner_id: int) -> list:
        """거래처가 사용 중인 곳 목록 반환"""
        usages = []

        # 영업 문서 (견적서/PI/CI)
        from app.models.sales_document import SalesDocument
        doc_count = self.db.query(SalesDocument).filter(
            SalesDocument.customer_id == partner_id
        ).count()
        if doc_count > 0:
            usages.append(f"영업 문서 {doc_count}건")

        # 영업활동
        from app.models.sales_activity import SalesActivity
        activity_count = self.db.query(SalesActivity).filter(
            SalesActivity.customer_id == partner_id
        ).count()
        if activity_count > 0:
            usages.append(f"영업활동 {activity_count}건")

        # 생산요청
        from app.models.production_request import ProductionRequest
        pr_count = self.db.query(ProductionRequest).filter(
            ProductionRequest.customer_id == partner_id
        ).count()
        if pr_count > 0:
            usages.append(f"생산요청 {pr_count}건")

        # 작업지시서
        from app.models.work_order import WorkOrder
        wo_count = self.db.query(WorkOrder).filter(
            WorkOrder.customer_id == partner_id
        ).count()
        if wo_count > 0:
            usages.append(f"작업지시서 {wo_count}건")

        # 발주서
        from app.models.purchase_order import PurchaseOrder
        po_count = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.supplier_id == partner_id
        ).count()
        if po_count > 0:
            usages.append(f"발주서 {po_count}건")

        return usages

    # ==================== 파일 관련 ====================

    def update_document_files(
        self,
        partner_id: int,
        document_files: List[Dict[str, Any]]
    ) -> BusinessPartner:
        """
        거래처 첨부파일 업데이트

        Args:
            partner_id: 거래처 ID
            document_files: 문서 파일 목록

        Returns:
            수정된 BusinessPartner
        """
        db_partner = self.get_or_raise(partner_id)
        return self.repository.update_from_dict(db_partner, {"document_files": document_files})

    def add_document_file(
        self,
        partner_id: int,
        file_info: Dict[str, Any]
    ) -> BusinessPartner:
        """
        거래처에 첨부파일 추가

        Args:
            partner_id: 거래처 ID
            file_info: 파일 정보 딕셔너리

        Returns:
            수정된 BusinessPartner
        """
        db_partner = self.get_or_raise(partner_id)

        current_files = db_partner.document_files or []
        current_files.append(file_info)

        return self.repository.update_from_dict(db_partner, {"document_files": current_files})

    def remove_document_file(
        self,
        partner_id: int,
        file_path: str
    ) -> BusinessPartner:
        """
        거래처에서 첨부파일 제거

        Args:
            partner_id: 거래처 ID
            file_path: 제거할 파일 경로

        Returns:
            수정된 BusinessPartner
        """
        db_partner = self.get_or_raise(partner_id)

        current_files = db_partner.document_files or []
        new_files = [f for f in current_files if f.get('file_path') != file_path]

        return self.repository.update_from_dict(db_partner, {"document_files": new_files})
