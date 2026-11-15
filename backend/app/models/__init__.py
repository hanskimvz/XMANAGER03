"""
모델 패키지
모든 SQLAlchemy 모델을 정의합니다.

v0.10.0: 품번 구조 변경 (부품코드 관리기준서 적용)
- 신규: ProductLine, PartGroup, DevelopmentType, PartType, DrawingType
- Legacy: MajorCategory, MiddleCategory, MinorCategory 유지 (하위 호환)
"""

from app.models.code_master import (
    # 신규 코드 테이블 (v0.10.0)
    ProductLine,
    PartGroup,
    DevelopmentType,
    PartType,
    DrawingType,
    part_part_type,  # M:N 관계 테이블
    # Legacy 코드 테이블 (하위 호환성)
    MajorCategory,
    MiddleCategory,
    MinorCategory,
    SubCategory,
    ItemCode,
    Material,
    Treatment,
    Level,
    ProcurementType,
    Unit,
)
from app.models.supplier import Supplier  # Legacy - 호환성 유지
from app.models.business_partner import BusinessPartner
from app.models.parts import Part
from app.models.bom import BOM
from app.models.warehouse import WarehouseLocation
from app.models.inventory import Inventory, InventoryTransaction
from app.models.inventory_lot import InventoryLot, WorkOrderItemIssue
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.production_request import ProductionRequest, ProductionRequestItem  # v0.22.0
from app.models.work_order import WorkOrder, WorkOrderItem, WorkOrderProduct
from app.models.work_order_task import WorkOrderTask  # v0.29.0
from app.models.price_history import PriceHistory, ExchangeRate
from app.models.product_description_code import ProductDescriptionCode  # v0.24.0
from app.models.sales_document import SalesDocument, SalesDocumentItem  # v0.24.0
from app.models.sales_document_pdf import SalesDocumentPdf  # Phase 3: PDF 보관 이력
from app.models.process_log import WorkOrderProcessLog  # v0.24.0
from app.models.project import Project  # v0.38.0 공용 프로젝트 마스터
from app.models.department import Department  # v0.43.0 부서 마스터
from app.models.approval import (  # 전자결재 (v0.33.0)
    ApprovalDocument,
    ApprovalLine,
    ApprovalAction,
    ApprovalCorrection,
    ApprovalDocumentPdf,
)
from app.models.approval_comment import ApprovalComment  # 결재 의견(댓글) (v0.65.0)  # noqa: F401
from app.models.rbac import (  # RBAC 토대 (v0.40.0)
    Role,
    Permission,
    RolePermission,
    UserRole,
    RbacModulePolicy,  # v0.47.0 모듈별 enforce 토글
)
from app.models.leave_ledger import LeaveLedger  # 연차 거래 원장 (v0.45.0)
from app.models.app_setting import AppSetting  # v0.49.0 앱 전역 설정(key-value)  # noqa: F401
from app.models.announcement import (  # 회사 공지사항 (v0.50.0)
    Announcement,
    AnnouncementAttachment,
    AnnouncementRead,
)
from app.models.free_board import FreeBoardPost, FreeBoardComment  # 자유게시판 (v1.02.0)
from app.models.schedule import Schedule  # 일정 등록 (v1.03.0)  # noqa: F401
from app.models.notification import Notification  # 인앱 알림 (v0.54.0)
from app.models.business_partner_shipping_address import BusinessPartnerShippingAddress  # 거래처 배송지 (v0.58.0)  # noqa: F401
from app.models.push_subscription import PushSubscription  # 웹푸시 구독 (v0.59.0)  # noqa: F401

__all__ = [
    # 신규 코드 테이블 (v0.10.0)
    "ProductLine",
    "PartGroup",
    "DevelopmentType",
    "PartType",
    "DrawingType",
    "part_part_type",
    # Legacy 코드 테이블
    "MajorCategory",
    "MiddleCategory",
    "MinorCategory",
    "SubCategory",
    "ItemCode",
    "Material",
    "Treatment",
    "Level",
    "ProcurementType",
    "Unit",
    "Supplier",  # Legacy
    "BusinessPartner",
    "Part",
    "BOM",
    # 재고관리 (v0.5.0)
    "WarehouseLocation",
    "Inventory",
    "InventoryTransaction",
    # 로트 추적 (v0.7.0)
    "InventoryLot",
    "WorkOrderItemIssue",
    # 입출고 관리 (v0.6.0)
    "PurchaseOrder",
    "PurchaseOrderItem",
    "ProductionRequest",  # v0.20.0
    "ProductionRequestItem",  # v0.22.0
    "WorkOrder",
    "WorkOrderItem",
    "WorkOrderProduct",
    # 원가관리 (v0.18.0)
    "PriceHistory",
    "ExchangeRate",
    # 제품 설명 코드 (v0.24.0)
    "ProductDescriptionCode",
    # 영업 문서 (v0.24.0)
    "SalesDocument",
    "SalesDocumentItem",
    # 공정 로그 (v0.24.0)
    "WorkOrderProcessLog",
    # 공용 프로젝트 마스터 (v0.38.0)
    "Project",
    # 부서 마스터 (v0.43.0)
    "Department",
    # 전자결재 (v0.33.0)
    "ApprovalDocument",
    "ApprovalLine",
    "ApprovalAction",
    "ApprovalCorrection",
    "ApprovalDocumentPdf",
    # RBAC 토대 (v0.40.0)
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "RbacModulePolicy",
    # 연차 거래 원장 (v0.45.0)
    "LeaveLedger",
    # 앱 전역 설정 (v0.49.0)
    "AppSetting",
    # 회사 공지사항 (v0.50.0)
    "Announcement",
    "AnnouncementAttachment",
    "AnnouncementRead",
    # 인앱 알림 (v0.54.0)
    "Notification",
    # 자유게시판 (v1.02.0)
    "FreeBoardPost",
    "FreeBoardComment",
]
