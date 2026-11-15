"""
RBAC(역할 기반 접근 제어) 모델 (v0.40.0)

가산적(additive) 토대:
- Role / Permission / RolePermission / UserRole 4개 테이블만 추가한다.
- 기존 User.role('ADMIN'/'USER') 컬럼은 그대로 유지(하위 호환). ADMIN 은 와일드카드.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Role(Base):
    """역할. is_admin=True 이면 전체 권한 와일드카드."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True, comment="역할 코드")
    name = Column(String(100), nullable=False, comment="역할 이름(한글)")
    is_system = Column(Boolean, nullable=False, default=False, server_default="false", comment="시스템 기본 역할(삭제/코드변경 금지)")
    is_admin = Column(Boolean, nullable=False, default=False, server_default="false", comment="전체 권한 와일드카드 역할")
    description = Column(Text, nullable=True, comment="설명")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0", comment="정렬 순서")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

    role_permissions = relationship(
        "RolePermission",
        back_populates="role",
        foreign_keys="RolePermission.role_id",
        cascade="all, delete-orphan",
    )
    user_roles = relationship(
        "UserRole",
        back_populates="role",
        foreign_keys="UserRole.role_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Role(code={self.code}, is_admin={self.is_admin})>"


class Permission(Base):
    """권한 (module:action). 레지스트리(app.core.permissions)가 단일 진실원천."""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True, comment="권한 코드 module:action")
    module = Column(String(50), nullable=False, comment="모듈 코드")
    action = Column(String(30), nullable=False, comment="동작 코드")
    label = Column(String(100), nullable=False, comment="한글 라벨")

    role_permissions = relationship(
        "RolePermission",
        back_populates="permission",
        foreign_keys="RolePermission.permission_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Permission(code={self.code})>"


class RolePermission(Base):
    """역할-권한 연결."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)

    role = relationship("Role", back_populates="role_permissions", foreign_keys=[role_id])
    permission = relationship("Permission", back_populates="role_permissions", foreign_keys=[permission_id])


class UserRole(Base):
    """사용자-역할 연결."""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)

    role = relationship("Role", back_populates="user_roles", foreign_keys=[role_id])


class RbacModulePolicy(Base):
    """모듈별 권한 강제(enforce) 토글 (v0.47.0).

    전역 RBAC_MODE 와 별개로 '모듈 단위'로 권한 강제를 켜고 끈다(관리자 UI).
    - enforced=True → 그 모듈은 전역 모드와 무관하게 항상 권한 강제(로그인+권한).
    - 민감 모듈(leave 등)은 코드 상수로 항상 enforce(이 표와 무관, 끌 수 없음).
    """

    __tablename__ = "rbac_module_policy"

    module = Column(String(30), primary_key=True)
    enforced = Column(Boolean, nullable=False, server_default="false")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
