"""v0.33.0 add electronic approval tables

Revision ID: i2j3k4l5m6n7
Revises: h4i5j6k7l8m9
Create Date: 2026-06-18

전자결재 모듈 Phase 1 (자유 기안 1종):
- users 확장: approver_id(self FK) / seal_text / seal_image_path
- approval_documents / approval_lines / approval_actions
  / approval_corrections / approval_document_pdf 생성
- form_id 는 Phase 2(approval_forms) 전까지 FK 없는 Integer
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'i2j3k4l5m6n7'
down_revision: Union[str, None] = 'h4i5j6k7l8m9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- 1. users 확장 (신규 컬럼 3개만, position/name_en 추가 금지) ----
    op.add_column('users',
        sa.Column('approver_id', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=True,
                  comment='디폴트 결재자(관리자 설정, 기안 시 1차로 자동 채움)'))
    op.add_column('users',
        sa.Column('seal_text', sa.String(length=10), nullable=True,
                  comment='도장에 새길 글자(미설정 시 name에서 추출)'))
    op.add_column('users',
        sa.Column('seal_image_path', sa.String(length=300), nullable=True,
                  comment='업로드한 도장/서명 이미지 경로(선택). NULL이면 자동 생성 SVG 사용'))

    # ---- 2. approval_documents ----
    op.create_table(
        'approval_documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('doc_number', sa.String(length=30), nullable=False, comment='문서번호 AP-2026-0001'),
        # Phase 1: FK 없는 Integer. Phase 2에서 approval_forms 생성 후 FK 추가
        sa.Column('form_id', sa.Integer(), nullable=True,
                  comment='양식 ID (Phase 2, NULL=자유기안). FK는 approval_forms 생성 후 추가'),
        sa.Column('form_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='양식별 입력값 (Phase 2)'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='제목'),
        sa.Column('content', sa.Text(), nullable=True, comment='본문 HTML (TipTap 출력)'),
        sa.Column('content_hash', sa.String(length=64), nullable=True,
                  comment='본문 SHA-256 해시(상신/승인 시점 스냅샷, 위변조 대조용)'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT',
                  comment='상태 DRAFT/IN_PROGRESS/APPROVED/REJECTED/CANCELED'),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='0',
                  comment='현재 결재 차례(1부터, 0=미상신)'),
        sa.Column('drafter_id', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=False, comment='기안자'),
        sa.Column('drafted_at', sa.DateTime(timezone=True), nullable=True, comment='상신 시각'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='최종 승인/반려 시각'),
        sa.Column('is_corrected', sa.Boolean(), nullable=False, server_default='false',
                  comment='관리자 사후 정정 여부 표식'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='수정일시'),
        sa.UniqueConstraint('doc_number', name='uq_approval_documents_doc_number'),
    )
    op.create_index('ix_approval_documents_doc_number', 'approval_documents', ['doc_number'])
    op.create_index('ix_approval_documents_status', 'approval_documents', ['status'])
    op.create_index('ix_approval_documents_drafter_id', 'approval_documents', ['drafter_id'])

    # ---- 3. approval_lines ----
    op.create_table(
        'approval_lines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('approval_documents.id', ondelete='CASCADE'),
                  nullable=False, comment='문서 ID'),
        sa.Column('step_order', sa.Integer(), nullable=False, comment='결재 순서(1,2,3)'),
        sa.Column('approver_id', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=False, comment='결재자'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='WAITING',
                  comment='WAITING/PENDING(내 차례)/APPROVED/REJECTED'),
        sa.Column('acted_at', sa.DateTime(timezone=True), nullable=True, comment='처리 시각'),
        sa.Column('comment', sa.Text(), nullable=True, comment='승인/반려 의견'),
        sa.Column('seal_snapshot', sa.String(length=300), nullable=True,
                  comment='승인 시점 도장(자동 SVG 식별자 또는 업로드 경로) 스냅샷'),
        sa.Column('approver_name', sa.String(length=100), nullable=True, comment='승인 시점 결재자 이름 스냅샷'),
        sa.Column('approver_position', sa.String(length=20), nullable=True, comment='승인 시점 직급 스냅샷'),
        sa.UniqueConstraint('document_id', 'step_order', name='uq_approval_lines_doc_step'),
    )
    op.create_index('ix_approval_lines_document_id', 'approval_lines', ['document_id'])
    op.create_index('ix_approval_lines_approver_id', 'approval_lines', ['approver_id'])

    # ---- 4. approval_actions (감사 이력, INSERT 전용) ----
    op.create_table(
        'approval_actions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('approval_documents.id'), nullable=False, comment='문서 ID'),
        sa.Column('actor_id', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=False, comment='행위자'),
        sa.Column('action', sa.String(length=20), nullable=False,
                  comment='SUBMIT/APPROVE/REJECT/CANCEL/RESUBMIT'),
        sa.Column('comment', sa.Text(), nullable=True, comment='의견'),
        sa.Column('acted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='행위 시각'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='감사 추적용 요청 IP'),
    )
    op.create_index('ix_approval_actions_document_id', 'approval_actions', ['document_id'])

    # ---- 5. approval_corrections (관리자 사후 정정 이력, INSERT 전용) ----
    op.create_table(
        'approval_corrections',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('approval_documents.id'), nullable=False, comment='문서 ID'),
        sa.Column('target_table', sa.String(length=40), nullable=False, comment='대상 테이블(actions/lines/documents)'),
        sa.Column('target_id', sa.Integer(), nullable=False, comment='대상 row ID'),
        sa.Column('field_name', sa.String(length=40), nullable=False, comment='고친 필드(acted_at, comment ...)'),
        sa.Column('old_value', sa.Text(), nullable=True, comment='원래 값'),
        sa.Column('new_value', sa.Text(), nullable=True, comment='새 값'),
        sa.Column('reason', sa.Text(), nullable=False, comment='수정 사유(필수 — 없으면 저장 실패)'),
        sa.Column('corrected_by', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=False, comment='정정 관리자'),
        sa.Column('corrected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='정정 시각'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='요청 IP'),
    )
    op.create_index('ix_approval_corrections_document_id', 'approval_corrections', ['document_id'])

    # ---- 6. approval_document_pdf (출력 PDF 보관) ----
    op.create_table(
        'approval_document_pdf',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('approval_documents.id', ondelete='CASCADE'),
                  nullable=False, comment='대상 결재 문서 ID'),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='ko', comment='언어(ko)'),
        sa.Column('file_path', sa.String(length=500), nullable=False, comment='storage root 기준 상대 경로'),
        sa.Column('file_size', sa.BigInteger(), nullable=False, comment='파일 크기(bytes)'),
        sa.Column('file_hash', sa.String(length=64), nullable=False, comment='PDF 바이트 SHA-256'),
        sa.Column('content_hash', sa.String(length=64), nullable=True,
                  comment='본문(content) SHA-256 — 생성 시점 스냅샷'),
        sa.Column('verify_code', sa.String(length=4), nullable=False,
                  comment='검증번호 = SHA256(doc_number+content) 앞 4 hex 대문자'),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='1', comment='누적 다운로드'),
        sa.Column('first_generated_at', sa.DateTime(timezone=True), nullable=False, comment='최초 생성 시각'),
        sa.Column('last_downloaded_at', sa.DateTime(timezone=True), nullable=False, comment='최근 다운로드 시각'),
        sa.Column('last_generated_by', sa.String(length=100), nullable=True, comment='최근 생성/다운로드 사용자'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('document_id', 'language', name='uq_approval_document_pdf_doc_lang'),
    )
    op.create_index('ix_approval_document_pdf_document_id', 'approval_document_pdf', ['document_id'])


def downgrade() -> None:
    # 역순 drop
    op.drop_index('ix_approval_document_pdf_document_id', table_name='approval_document_pdf')
    op.drop_table('approval_document_pdf')

    op.drop_index('ix_approval_corrections_document_id', table_name='approval_corrections')
    op.drop_table('approval_corrections')

    op.drop_index('ix_approval_actions_document_id', table_name='approval_actions')
    op.drop_table('approval_actions')

    op.drop_index('ix_approval_lines_approver_id', table_name='approval_lines')
    op.drop_index('ix_approval_lines_document_id', table_name='approval_lines')
    op.drop_table('approval_lines')

    op.drop_index('ix_approval_documents_drafter_id', table_name='approval_documents')
    op.drop_index('ix_approval_documents_status', table_name='approval_documents')
    op.drop_index('ix_approval_documents_doc_number', table_name='approval_documents')
    op.drop_table('approval_documents')

    # users 컬럼 3개 drop (역순)
    op.drop_column('users', 'seal_image_path')
    op.drop_column('users', 'seal_text')
    op.drop_column('users', 'approver_id')
