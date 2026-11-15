"""v0.28.0 add users table

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h9
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6g7h8i9'
down_revision: str = 'c3d4e5f6g7h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(200), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(200)),
        sa.Column('role', sa.String(20), nullable=False, server_default='USER'),
        sa.Column('department', sa.String(50)),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # 초기 관리자 계정 (비밀번호: admin123)
    import bcrypt
    password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")
    op.execute(
        sa.text(
            "INSERT INTO users (username, password_hash, name, role, department) "
            "VALUES (:u, :p, :n, :r, :d)"
        ).bindparams(
            u="admin",
            p=password_hash,
            n="관리자",
            r="ADMIN",
            d="MANAGEMENT",
        )
    )


def downgrade() -> None:
    op.drop_table('users')
