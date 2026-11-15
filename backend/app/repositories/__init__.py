"""
Repository Layer
데이터 접근 로직을 캡슐화하여 Service Layer와 데이터베이스 간의 추상화를 제공합니다.
"""

from app.repositories.base import BaseRepository
from app.repositories.part_repository import PartRepository
from app.repositories.partner_repository import BusinessPartnerRepository
from app.repositories.code_master_repository import CodeMasterRepository

__all__ = [
    "BaseRepository",
    "PartRepository",
    "BusinessPartnerRepository",
    "CodeMasterRepository",
]
