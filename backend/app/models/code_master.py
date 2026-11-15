"""
코드 마스터 테이블 모델
부품 분류, 재질, 후처리 등 기본 코드를 관리합니다.

변경이력:
- v0.10.0: 품번 구조 변경 (부품코드 관리기준서 적용)
  - ProductLine: 대분류/제품라인 (HB1, BI3, TF1 등)
  - PartGroup: 소분류/품목군 (DCP, PLP, OCP 등)
  - DevelopmentType: 개발구분 (D, S, M, R, C, P)
  - PartType: 부품유형 (P, E, O, M, G, I, W, A, C, H, X, T) - 다중선택
  - DrawingType: 도면여부 (D, S, N)
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# Part-PartType 다대다 관계 테이블 (부품유형 다중선택용)
part_part_type = Table(
    'part_part_type',
    Base.metadata,
    Column('part_id', Integer, ForeignKey('parts.id', ondelete='CASCADE'), primary_key=True),
    Column('part_type_id', Integer, ForeignKey('part_type.id', ondelete='CASCADE'), primary_key=True)
)


class ProductLine(Base):
    """
    대분류 코드 (제품라인)
    품번 구성요소 - 4자리
    예: HB01(HXB11), HB03(HXB13), BI01(XBI11), TF01(TFOCA), COM0(공용)
    """
    __tablename__ = "product_line"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드 (4자리)")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class PartGroup(Base):
    """
    소분류 코드 (품목군)
    품번 구성요소 - 3자리
    예: DCP(더스트캡), PLP(플러그), RCP(리셉터클), OCP(광학), JIG(지그)
    """
    __tablename__ = "part_group"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드 (3자리)")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class DevelopmentType(Base):
    """
    개발구분 (분류1) - 검색/필터용
    품번에 포함되지 않음, 단일선택
    예: D(개발품), S(규격품), M(상용품), R(원소재), C(주문품), P(공정)
    """
    __tablename__ = "development_type"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드 (1자리)")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class PartType(Base):
    """
    부품유형 (분류2) - 검색/필터용
    품번에 포함되지 않음, 다중선택 가능 (M:N 관계)
    예: P(가공품), E(고무품), O(광학품), M(금형품), G(기계류), I(사출품)
    """
    __tablename__ = "part_type"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드 (1자리)")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class DrawingType(Base):
    """
    도면여부 (분류3) - 검색/필터용
    품번에 포함되지 않음, 단일선택
    예: D(도면), S(표준품번), N(없음)
    """
    __tablename__ = "drawing_type"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드 (1자리)")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


# ============================================================================
# Legacy 코드 테이블 (하위 호환성 유지, 향후 삭제 예정)
# ============================================================================

class MajorCategory(Base):
    """
    대분류 코드 (개발구분)
    예: D(개발품), S(규격품), M(상용품), R(원소재), C(주문품), P(공정)
    """
    __tablename__ = "major_category"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class MiddleCategory(Base):
    """
    중분류 코드 (부품유형)
    예: P(가공품), E(고무품), O(광학품), M(금형품), G(기계류),
        C(다이캐스트품), B(베어링), I(사출품), W(와이어류),
        A(조립품), F(체결품), H(하드웨어), X(화학품), T(수축튜브)
    """
    __tablename__ = "middle_category"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class MinorCategory(Base):
    """
    소분류 코드 (제품라인)
    예: HB1(HXB11), HB3(HXB13), HB5(HXB15), TF1(TFOCA),
        IS1(XBI11), CRP(케이블류), COM(상용품)
    """
    __tablename__ = "minor_category"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class SubCategory(Base):
    """
    세분류 코드 (부품군)
    예: DC(더스트캡), BI(바디/인서트), PP(플러그), RP(리셉터클),
        CH(커넥터홀더), CM(커넥터), PS(광학부품), HP(하우징/플러그)
    """
    __tablename__ = "sub_category"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class ItemCode(Base):
    """
    품목 코드 (세부품목)
    예: CB00(커넥터바디), GP00(글래스 플레이트), LN00(렌즈), SF00(스페이서 필름)
    """
    __tablename__ = "item_code"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class Material(Base):
    """
    재질 코드
    예: A6(AL6061), S4(STS304/AISI304), S3(SUS303), S6(SUS316),
        NB(NBR), EP(EPDM), SI(Silicone), AB(ABS), BR(Brass),
        L1(LAK-10), XX(미지정)
    """
    __tablename__ = "material"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class Treatment(Base):
    """
    후처리 코드
    예: NK(니켈), ZK(징크-니켈), CD(카드뮴), HB(하드 블랙),
        WA(백색 아노다이징), A0(AR코팅), NN(없음)
    """
    __tablename__ = "treatment"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class Level(Base):
    """
    레벨 코드 (BOM 단계) - v0.12.0 확장

    단품 레벨 (부품관리 페이지, 단가 직접 입력):
    - M: 내부공정 (Manufacturing)
    - O: 외주공정 (Outsourcing)
    - R: Row Component (원자재/단품)

    조립품 레벨 (BOM관리 페이지, 단가 = 하위품목 합산):
    - C: 조합부품 (R+O 등의 조합)
    - S: 서브어셈블리 (C 레벨 조합)
    - P: 패키지 (포장단위)
    - K: 키트 (Kit 단위)
    - F: 최종품 (Finished Good)
    """
    __tablename__ = "level"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    bom_level = Column(Integer, comment="BOM 레벨 (0~5)")
    default_unit = Column(String(10), comment="기본 단위 (FP, PKG, KIT, SET, EA)")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")

    # v0.12.0: 레벨별 관리 구분
    is_assembly = Column(Boolean, default=False, comment="조립품 여부 (True: BOM관리, False: 부품관리)")
    cost_calculation = Column(String(10), default="MANUAL", comment="단가계산방식 (MANUAL: 직접입력, BOM: 하위합산)")

    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class ProcurementType(Base):
    """
    조달 구분 코드
    MFG(가공품/Manufactured), PUR(구매품/Purchased), INJ(사출품/Injection),
    SEM(반제품/Semi-finished), FIN(완제품/Finished)
    """
    __tablename__ = "procurement_type"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class SupplierType(Base):
    """
    공급업체 구분 코드
    공급업체를 분류하기 위한 관리 데이터 (예: 원자재/외주가공/상사/COTS 등).
    """
    __tablename__ = "supplier_type"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")


class Unit(Base):
    """
    단위 코드
    EA(개/Each), SET(세트/Set), KIT(키트/Kit), PKG(패키지/Package),
    FP(완제품/Finished Product), M(미터/Meter), MM(밀리미터/Millimeter),
    G(그램/Gram), ML(밀리리터/Milliliter)
    """
    __tablename__ = "unit"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(10), unique=True, nullable=False, index=True, comment="코드")
    name_ko = Column(String(50), nullable=False, comment="한글명")
    name_en = Column(String(50), comment="영문명")
    description = Column(Text, comment="설명")
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")
