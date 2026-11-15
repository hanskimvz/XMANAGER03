"""
생산 요청서 (Production Request) 모델
영업팀이 생산팀에 생산을 요청하는 문서입니다.

v0.20.0: 생산 요청서 기능 추가
- ProductionRequest: 생산 요청서 헤더
- 작업지시서(WorkOrder)와 1:N 관계 (하나의 요청에 여러 작업지시서 가능)

v0.22.0: 다중 제품 지원
- ProductionRequestItem: 생산 요청서 제품 항목
- 하나의 요청서에 여러 제품 등록 가능
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, ForeignKey, Date, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProductionRequest(Base):
    """
    생산 요청서 (Production Request)
    영업팀이 생산팀에 생산을 요청하는 문서

    상태(status):
    - REQUESTED: 요청됨 (영업팀 요청 완료)
    - HOLD: 보류 (추가 정보 필요)
    - REJECTED: 반려됨
    - APPROVED: 승인됨 (작업지시서 생성됨)
    - IN_PROGRESS: 진행중 (작업지시서 작업 중)
    - COMPLETED: 완료 (모든 작업지시서 완료)
    - CANCELLED: 취소됨
    """
    __tablename__ = "production_request"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 요청서 번호 (자동채번: PR-YYYYMMDD-001)
    request_number = Column(String(20), unique=True, nullable=False, index=True, comment="요청서번호")

    # 고객사 정보
    customer_id = Column(Integer, ForeignKey("business_partner.id"), comment="고객사 ID")
    customer_order_no = Column(String(50), comment="고객 주문번호")

    # [DEPRECATED] 단일 제품 필드 - 호환성 유지용 (v0.22.0)
    product_part_id = Column(Integer, ForeignKey("parts.id"), nullable=True, index=True, comment="제품 부품 ID (deprecated)")
    requested_quantity = Column(Numeric(15, 3), nullable=True, comment="요청 수량 (deprecated)")

    # 납기
    due_date = Column(Date, comment="희망 납기일")

    # 상태
    status = Column(String(20), default="REQUESTED", index=True, comment="상태")
    # v0.87.0 초안 여부 — PI 자동생성 초안은 True(생산팀 미노출·알림 X). 영업이 '생산팀에 요청'하면 False+알림
    is_draft = Column(Boolean, nullable=False, default=False, server_default="false", index=True, comment="초안(미전송) 여부")

    # 요청 정보
    requested_by = Column(Integer, comment="요청자 ID")
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), comment="요청일시")

    # 승인/반려 정보
    approved_by = Column(Integer, comment="승인자 ID")
    approved_at = Column(DateTime(timezone=True), comment="승인일시")
    rejection_reason = Column(Text, comment="반려 사유")

    # 우선순위: 0(보통), 1(높음), 2(긴급)
    priority = Column(Integer, default=0, comment="우선순위")

    # PI / PO (v0.23.0)
    pi_number = Column(String(50), comment="PI 번호 (Proforma Invoice)")
    payment_status = Column(String(20), default="UNPAID", comment="입금현황")  # UNPAID, PARTIAL, PAID

    # v0.28.0: 생산요청서 추가 필드
    country = Column(String(100), comment="국가")
    production_period = Column(String(50), comment="생산기간 (예: 5주)")
    shipping_mark = Column(Text, comment="SHIPPING MARK")
    consignee = Column(Text, comment="CONSIGNEE (수하인)")
    destination = Column(String(200), comment="DESTINATION (도착지 도시/국가)")
    prepared_by_name = Column(String(100), comment="작성자명")

    # 비고
    remarks = Column(Text, comment="비고")

    # 진행 체크박스 (노션 생산스케줄 양식 반영) — status 워크플로우와 독립적인 보조 플래그
    insert_shipped = Column(Boolean, nullable=False, default=False, server_default="false", comment="인서트출고 여부")
    # v0.84.0 인서트 해당없음(N/A) — 인서트 공정이 없는 건. True면 출고 대상에서 제외
    insert_not_applicable = Column(Boolean, nullable=False, default=False, server_default="false", comment="인서트 해당없음(N/A)")
    production_shipped = Column(Boolean, nullable=False, default=False, server_default="false", comment="생산출고 여부")
    needs_review = Column(Boolean, nullable=False, default=False, server_default="false", comment="검토필요 플래그")
    # v0.74.0 완료 시각 — 체크 시 기록(해제 시 NULL). 영업 현황 표시·출고일 조회용
    insert_shipped_at = Column(DateTime(timezone=True), nullable=True, comment="인서트출고 완료 시각")
    production_shipped_at = Column(DateTime(timezone=True), nullable=True, comment="생산출고 완료 시각")

    # v0.76.0 검토 필요 사유 — needs_review와 함께 영업에 표시(생산팀→영업 확인요청)
    review_note = Column(Text, comment="검토 필요 사유(생산팀이 영업에 확인 요청)")
    # v0.76.0 상태 전이 시각 — 출고(SHIPPED)/발송(DELIVERED). 발송은 영업이 처리
    shipped_at = Column(DateTime(timezone=True), nullable=True, comment="생산 출고(SHIPPED) 시각")
    delivered_at = Column(DateTime(timezone=True), nullable=True, comment="발송 완료(DELIVERED) 시각 — 영업 처리")
    # v0.77.0 출고 packing list — 생산팀이 출고 시 입력, 영업 CI 발행에 승계
    # [{box_type, quantity, gross_weight, net_weight, length, width, height, remarks}]
    packing_list = Column(JSON, comment="출고 포장 명세 박스 목록 (JSON)")
    # v0.86.0 포장사진 폴더(납품 베이스 기준 상대경로) — 최초 업로드 시 저장(번호 prefix 매칭/생성)
    packing_folder = Column(String(300), nullable=True, comment="포장사진 폴더 경로(납품 트리 기준)")
    # v0.90.0 분할선적 박스 분할계획 — 영업이 작성("N개씩 M박스"), 생산팀이 보고 포장. 박스별 CI 발행에 사용
    # [{box_no, items:[{pr_item_id, quantity}], remarks}]
    box_plan = Column(JSON, nullable=True, comment="분할선적 박스 분할계획 (영업 작성 → 생산 포장 → 박스별 CI)")

    # 첨부파일 (v0.22.0)
    attachment_files = Column(JSON, comment="첨부파일 목록 (JSON)")  # [{filename, filepath, mimetype}]

    # v0.69.0: 생산 시작 단계 자료
    manager_memo = Column(Text, comment="생산팀 총괄자 메모 (생산 시작 전 작성)")
    process_checks = Column(JSON, comment="공정 확인표 [{seq, content, date, checker, note, action}]")

    # 감사 필드
    created_by = Column(Integer, comment="생성자 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_by = Column(Integer, comment="수정자 ID")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

    # Relationships
    customer = relationship("BusinessPartner", foreign_keys=[customer_id])
    product_part = relationship("Part", foreign_keys=[product_part_id])  # deprecated
    work_orders = relationship("WorkOrder", back_populates="production_request")
    items = relationship("ProductionRequestItem", back_populates="production_request", cascade="all, delete-orphan", order_by="ProductionRequestItem.sort_order")  # v0.22.0 (sort_order=PI 품목 순서)

    def __repr__(self):
        return f"<ProductionRequest(id={self.id}, request_number={self.request_number}, status={self.status})>"


class ProductionRequestItem(Base):
    """
    생산 요청서 제품 항목 (v0.22.0)
    하나의 요청서에 여러 제품을 등록할 수 있습니다.
    """
    __tablename__ = "production_request_item"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 생산 요청서 참조
    production_request_id = Column(Integer, ForeignKey("production_request.id", ondelete="CASCADE"), nullable=False, index=True, comment="생산 요청서 ID")

    # 제품 정보
    # v0.80.0: BOM에 없는 제품(외주 부품 등)도 등록 가능 — product_part_id 없이 품번/품명 직접 입력
    product_part_id = Column(Integer, ForeignKey("parts.id"), nullable=True, index=True, comment="제품 부품 ID (없으면 커스텀/외주 항목)")
    custom_product_code = Column(String(100), nullable=True, comment="커스텀 품번 (BOM 미등록·외주 부품)")
    custom_product_name = Column(String(200), nullable=True, comment="커스텀 품명 (BOM 미등록·외주 부품)")
    requested_quantity = Column(Numeric(15, 3), nullable=False, comment="요청 수량")
    # v0.88.0 분할선적 — 누적 CI 발행(배송) 수량. 잔여 = requested_quantity - ci_quantity
    ci_quantity = Column(Numeric(15, 3), nullable=False, default=0, server_default="0", comment="누적 CI 발행 수량(분할선적)")
    uom = Column(String(20), comment="단위 (PI 품목에서 승계, 예: EA/SET/M)")

    # v0.75.0 품목별 도면/첨부 [{filename, filepath, mimetype, size}]
    attachment_files = Column(JSON, comment="품목별 도면/첨부 목록 (JSON)")

    # 항목 비고
    line_remarks = Column(Text, comment="항목 비고")

    # v0.28.0: 고객 요구사항
    customer_requirements = Column(Text, comment="고객 요구사항 (도면 참조, 특이사항 등)")

    # v0.29.0: 제품별 작업지시서 연결
    work_order_id = Column(Integer, ForeignKey("work_order.id"), comment="연결된 작업지시서 ID")

    # v0.30.0: PI 품목 연결 (분할 생산요청 추적)
    # v0.67.0: ondelete=SET NULL — DRAFT PI 수정 시 품목 삭제가 FK로 막히지 않도록(링크는 pi_number로 폴백)
    pi_document_id = Column(Integer, ForeignKey("sales_document.id", ondelete="SET NULL"), nullable=True, index=True, comment="원본 PI 문서 ID")
    pi_item_id = Column(Integer, ForeignKey("sales_document_item.id", ondelete="SET NULL"), nullable=True, comment="원본 PI 품목 ID")

    # 정렬 순서
    sort_order = Column(Integer, default=0, comment="정렬순서")

    # Relationships
    production_request = relationship("ProductionRequest", back_populates="items")
    product_part = relationship("Part", foreign_keys=[product_part_id])
    work_order = relationship("WorkOrder", foreign_keys=[work_order_id])

    def __repr__(self):
        return f"<ProductionRequestItem(id={self.id}, part_id={self.product_part_id}, qty={self.requested_quantity})>"
