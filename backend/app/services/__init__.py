"""
Service Layer
비즈니스 로직을 캡슐화하는 서비스 계층입니다.

API 라우터는 Service를 호출하고, Service는 비즈니스 로직을 처리합니다.
이를 통해:
1. 코드 재사용성 향상
2. 테스트 용이성 향상
3. 관심사 분리 (API는 요청/응답, Service는 비즈니스 로직)
4. 유지보수성 향상
"""

from app.services.base import BaseService
from app.services.part_service import PartService
from app.services.partner_service import BusinessPartnerService
from app.services.code_master_service import CodeMasterService

__all__ = [
    "BaseService",
    "PartService",
    "BusinessPartnerService",
    "CodeMasterService",
]
