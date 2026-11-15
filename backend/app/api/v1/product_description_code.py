"""
제품 설명 코드 API 라우터
오더코드 세그먼트별 Description 매핑 CRUD + 자동 조합
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.product_description_code import ProductDescriptionCode
from app.schemas.product_description_code import (
    ProductDescriptionCodeCreate,
    ProductDescriptionCodeUpdate,
    ProductDescriptionCodeResponse,
    ProductDescriptionCodeListResponse,
    DescriptionComposeRequest,
    DescriptionComposeResponse,
)

router = APIRouter(prefix="/product-description-codes", tags=["제품 설명 코드"])

# 읽기 전용 조합(compose) 전용 라우터.
# CRUD 라우터는 code 모듈 RBAC(enforce 시 create 권한 요구)로 보호되지만,
# compose 는 오더코드→Description 문자열을 계산만 하는 읽기 헬퍼라
# 견적 작성 등에서 모든 로그인 사용자가 써야 한다. → 로그인만 요구(main.py 에서 부착).
compose_router = APIRouter(prefix="/product-description-codes", tags=["제품 설명 코드"])


@router.get("", response_model=ProductDescriptionCodeListResponse)
@router.get("/", response_model=ProductDescriptionCodeListResponse, include_in_schema=False)
def get_all(
    segment_type: Optional[str] = Query(None, description="세그먼트 유형 필터"),
    is_active: Optional[bool] = Query(None, description="활성 여부"),
    db: Session = Depends(get_db),
):
    """제품 설명 코드 목록 조회"""
    query = db.query(ProductDescriptionCode)
    if segment_type:
        query = query.filter(ProductDescriptionCode.segment_type == segment_type)
    if is_active is not None:
        query = query.filter(ProductDescriptionCode.is_active == is_active)
    query = query.order_by(ProductDescriptionCode.segment_type, ProductDescriptionCode.sort_order)
    items = query.all()
    return ProductDescriptionCodeListResponse(items=items, total=len(items))


@router.get("/{code_id}", response_model=ProductDescriptionCodeResponse)
def get_by_id(code_id: int, db: Session = Depends(get_db)):
    """제품 설명 코드 상세 조회"""
    item = db.query(ProductDescriptionCode).filter(ProductDescriptionCode.id == code_id).first()
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="코드를 찾을 수 없습니다")
    return item


@router.post("", response_model=ProductDescriptionCodeResponse, status_code=201)
@router.post("/", response_model=ProductDescriptionCodeResponse, status_code=201, include_in_schema=False)
def create(data: ProductDescriptionCodeCreate, db: Session = Depends(get_db)):
    """제품 설명 코드 생성"""
    item = ProductDescriptionCode(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{code_id}", response_model=ProductDescriptionCodeResponse)
def update(code_id: int, data: ProductDescriptionCodeUpdate, db: Session = Depends(get_db)):
    """제품 설명 코드 수정"""
    item = db.query(ProductDescriptionCode).filter(ProductDescriptionCode.id == code_id).first()
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="코드를 찾을 수 없습니다")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{code_id}", status_code=204)
def delete(code_id: int, db: Session = Depends(get_db)):
    """제품 설명 코드 삭제"""
    item = db.query(ProductDescriptionCode).filter(ProductDescriptionCode.id == code_id).first()
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="코드를 찾을 수 없습니다")
    db.delete(item)
    db.commit()


@compose_router.post("/compose", response_model=DescriptionComposeResponse)
def compose_description(data: DescriptionComposeRequest, db: Session = Depends(get_db)):
    """
    오더코드에서 Description 자동 조합

    예시 입력: HXB13-PSD-B-O4-S1-D55
    출력: 각 세그먼트의 description_en을 조합한 문자열

    특수 규칙:
    - D + 2자리 숫자 (예: D55) = 케이블 외경 → "for out diameter 5.5mm Outdoor cable"
      매칭 순위: 1) DB 등록된 정확 매칭 코드  2) 자동 파싱 fallback
    """
    import re

    order_code = data.order_code.strip()
    # 레벨 접미사 제거 (예: "HXB13-PSD-B-O4-S1-D85 [U]" → "HXB13-PSD-B-O4-S1-D85")
    cleaned_code = re.sub(r"\s*\[[A-Z]\]\s*$", "", order_code).strip()
    segments = cleaned_code.replace("-", " ").split()

    # DB에서 모든 활성 코드 로드 (캐시 활용 가능)
    all_codes = db.query(ProductDescriptionCode).filter(
        ProductDescriptionCode.is_active == True
    ).all()
    code_map = {c.code.upper(): c for c in all_codes}

    use_ko = data.language == "ko"

    # D접두사 외경 자동 파싱 (예: D55 → 5.5mm, D125 → 12.5mm)
    # 규칙: D 다음 숫자를 10으로 나눔 (마지막 자리가 소수점)
    diameter_pattern = re.compile(r"^D(\d{2,3})$")

    def auto_parse_diameter(seg_upper: str) -> Optional[str]:
        m = diameter_pattern.match(seg_upper)
        if not m:
            return None
        digits = m.group(1)
        # D55 → 5.5mm, D125 → 12.5mm
        diameter_mm = int(digits) / 10.0
        if use_ko:
            return f"-외경 {diameter_mm}mm Outdoor 케이블용"
        return f"-for out diameter {diameter_mm}mm Outdoor cable"

    # 케이블 조립체 길이 표기 자동 파싱
    # 규칙:
    #   - "L1/L2" (예: 1.5/30, 020/30) → 하이브리드 케이블 (LC/SC/ST 등). L1=전체길이 m, L2=분기부 cm.
    #   - "L1"    (예: 1.5, 500)       → SA(양쪽 HXB) 케이블. 단일 전체길이 m.
    # 소수 미터 허용(예: 1.5m). 슬래시 유무로 듀얼/단일 구분(슬래시가 있어 오탐 위험 없음).
    # 표기 일관성을 위해 두 케이스 모두 "L1 : N m" 라벨 사용 (듀얼은 L2도 추가).
    length_pattern = re.compile(r"^(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)$")
    single_length_pattern = re.compile(r"^(\d+(?:\.\d+)?)$")

    def auto_parse_length(seg: str) -> Optional[list]:
        """길이 표기 → ['-L1 : NNN m', '-L2 : NN cm'] (듀얼) 또는 ['-L1 : NNN m'] (단일)."""
        m = length_pattern.match(seg)
        if m:
            l1, l2 = m.group(1), m.group(2)
            return [f"-L1 : {l1} m", f"-L2 : {l2} cm"]
        m = single_length_pattern.match(seg)
        if m:
            l1 = m.group(1)
            return [f"-L1 : {l1} m"]
        return None

    matched = []
    unmatched = []
    descriptions = []

    for seg in segments:
        seg_upper = seg.upper()
        if seg_upper in code_map:
            code_obj = code_map[seg_upper]
            matched.append({
                "code": seg,
                "segment_type": code_obj.segment_type,
                "description_en": code_obj.description_en,
            })
            # 한글 요청 시 description_ko 우선, 없으면 영문 fallback
            desc = (code_obj.description_ko if use_ko and code_obj.description_ko else code_obj.description_en) or ""
            if desc:
                descriptions.append(desc)
        else:
            # D접두사 외경 자동 파싱 시도
            auto_desc = auto_parse_diameter(seg_upper)
            if auto_desc:
                matched.append({
                    "code": seg,
                    "segment_type": "CABLE",
                    "description_en": auto_desc,
                })
                descriptions.append(auto_desc)
                continue

            # 길이 표기 자동 파싱 시도 (예: 020/30 → L1/L2)
            length_lines = auto_parse_length(seg)
            if length_lines:
                matched.append({
                    "code": seg,
                    "segment_type": "LENGTH",
                    "description_en": " / ".join(length_lines),
                })
                descriptions.extend(length_lines)
                continue

            unmatched.append(seg)

    # Description 조합: CHANNEL+FIBER는 같은 줄로 연결
    # FIBER description이 ', '로 시작하므로 이전 줄에 이어붙임
    lines = []
    for desc in descriptions:
        if desc.startswith(",") and lines:
            # 이전 줄에 이어붙임 (예: "-4 CH" + ", 62.5 μm core Multimode fiber")
            lines[-1] += desc
        else:
            lines.append(desc)

    return DescriptionComposeResponse(
        order_code=order_code,
        description="\n".join(lines),
        segments=matched,
        unmatched=unmatched,
    )
