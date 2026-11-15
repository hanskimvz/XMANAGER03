"""v0.40.0 RBAC foundation (roles/permissions/role_permissions/user_roles)

Revision ID: p9q0r1s2t3u4
Revises: o8p9q0r1s2t3
Create Date: 2026-06-21

RBAC v0.40.0 (가산적):
- roles / permissions / role_permissions / user_roles 4개 테이블 신규 생성.
- 기본 역할 시드: ADMIN_SYS(시스템관리자, is_system=True, is_admin=True),
                  EMPLOYEE(일반사원, is_system=True, is_admin=False).
- 기존 사용자 자동 배정: users.role=='ADMIN' -> ADMIN_SYS, 그 외 -> EMPLOYEE.
- permissions 행과 EMPLOYEE 기본 권한(role_permissions)은 앱 부팅 동기화에서 부여.
  ADMIN_SYS 는 is_admin=True 와일드카드라 권한행 불필요.
- 기존 350개 업무 엔드포인트에는 어떤 변경도 가하지 않는다(차단 미적용).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p9q0r1s2t3u4'
down_revision: Union[str, None] = 'o8p9q0r1s2t3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- roles ----
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(50), nullable=False, comment="역할 코드"),
        sa.Column('name', sa.String(100), nullable=False, comment="역할 이름(한글)"),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false', comment="시스템 기본 역할"),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false', comment="전체 권한 와일드카드"),
        sa.Column('description', sa.Text(), nullable=True, comment="설명"),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment="정렬 순서"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('code', name='uq_roles_code'),
    )
    op.create_index('ix_roles_code', 'roles', ['code'])

    # ---- permissions ----
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(100), nullable=False, comment="권한 코드 module:action"),
        sa.Column('module', sa.String(50), nullable=False, comment="모듈 코드"),
        sa.Column('action', sa.String(30), nullable=False, comment="동작 코드"),
        sa.Column('label', sa.String(100), nullable=False, comment="한글 라벨"),
        sa.UniqueConstraint('code', name='uq_permissions_code'),
    )
    op.create_index('ix_permissions_code', 'permissions', ['code'])

    # ---- role_permissions ----
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )
    op.create_index('ix_role_permissions_role_id', 'role_permissions', ['role_id'])
    op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'])

    # ---- user_roles ----
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])

    # ---- 기본 역할 시드 ----
    op.execute("""
        INSERT INTO roles (code, name, is_system, is_admin, description, sort_order, created_at)
        VALUES
            ('ADMIN_SYS', '시스템관리자', true, true, '전체 권한(와일드카드) 시스템 관리자', 0, NOW()),
            ('EMPLOYEE', '일반사원', true, false, '일반 사원 기본 역할', 10, NOW())
    """)

    # ---- 기존 사용자 자동 배정 ----
    # ADMIN -> ADMIN_SYS
    op.execute("""
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE u.role = 'ADMIN' AND r.code = 'ADMIN_SYS'
    """)
    # 그 외 -> EMPLOYEE
    op.execute("""
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE u.role <> 'ADMIN' AND r.code = 'EMPLOYEE'
    """)


def downgrade() -> None:
    op.drop_index('ix_user_roles_role_id', table_name='user_roles')
    op.drop_index('ix_user_roles_user_id', table_name='user_roles')
    op.drop_table('user_roles')

    op.drop_index('ix_role_permissions_permission_id', table_name='role_permissions')
    op.drop_index('ix_role_permissions_role_id', table_name='role_permissions')
    op.drop_table('role_permissions')

    op.drop_index('ix_permissions_code', table_name='permissions')
    op.drop_table('permissions')

    op.drop_index('ix_roles_code', table_name='roles')
    op.drop_table('roles')
