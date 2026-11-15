"""
공급업체 관리 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from app.core.database import get_db
from app.models.supplier import Supplier
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierListItem,
    SupplierSearchParams,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=List[SupplierListItem])
def get_suppliers(
    keyword: str = None,
    is_active: bool = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    공급업체 목록 조회 (검색 및 필터링 지원)

    - **keyword**: 공급업체 코드 또는 업체명으로 검색
    - **is_active**: 활성 여부 필터 (True/False)
    - **skip**: 건너뛸 레코드 수 (페이지네이션)
    - **limit**: 최대 레코드 수 (기본 100, 최대 1000)
    """
    query = db.query(Supplier)

    # 키워드 검색
    if keyword:
        search_filter = or_(
            Supplier.supplier_code.ilike(f"%{keyword}%"),
            Supplier.supplier_name.ilike(f"%{keyword}%"),
        )
        query = query.filter(search_filter)

    # 활성 여부 필터
    if is_active is not None:
        query = query.filter(Supplier.is_active == is_active)

    # 정렬 및 페이지네이션
    suppliers = query.order_by(Supplier.supplier_code).offset(skip).limit(limit).all()

    return suppliers


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """
    공급업체 단건 조회

    - **supplier_id**: 공급업체 ID
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )

    return supplier


@router.get("/code/{supplier_code}", response_model=SupplierResponse)
def get_supplier_by_code(supplier_code: str, db: Session = Depends(get_db)):
    """
    공급업체 코드로 조회

    - **supplier_code**: 공급업체 코드
    """
    supplier = (
        db.query(Supplier).filter(Supplier.supplier_code == supplier_code).first()
    )

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )

    return supplier


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(supplier_data: SupplierCreate, db: Session = Depends(get_db)):
    """
    공급업체 생성

    - **supplier_code**: 공급업체 코드 (필수, 중복 불가)
    - **supplier_name**: 공급업체명 (필수)
    - 기타 정보는 선택적
    """
    # 중복 코드 확인
    existing = (
        db.query(Supplier)
        .filter(Supplier.supplier_code == supplier_data.supplier_code)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"공급업체 코드 '{supplier_data.supplier_code}'가 이미 존재합니다",
        )

    # 중복 업체명 확인
    existing_name = (
        db.query(Supplier)
        .filter(Supplier.supplier_name == supplier_data.supplier_name)
        .first()
    )
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"공급업체명 '{supplier_data.supplier_name}'이 이미 존재합니다",
        )

    # 공급업체 생성
    supplier = Supplier(**supplier_data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int, supplier_data: SupplierUpdate, db: Session = Depends(get_db)
):
    """
    공급업체 수정

    - **supplier_id**: 공급업체 ID
    - 수정할 필드만 전송 (부분 업데이트 지원)
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )

    # 코드 중복 확인 (변경 시)
    if supplier_data.supplier_code and supplier_data.supplier_code != supplier.supplier_code:
        existing = (
            db.query(Supplier)
            .filter(
                Supplier.supplier_code == supplier_data.supplier_code,
                Supplier.id != supplier_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"공급업체 코드 '{supplier_data.supplier_code}'가 이미 존재합니다",
            )

    # 업체명 중복 확인 (변경 시)
    if supplier_data.supplier_name and supplier_data.supplier_name != supplier.supplier_name:
        existing_name = (
            db.query(Supplier)
            .filter(
                Supplier.supplier_name == supplier_data.supplier_name,
                Supplier.id != supplier_id,
            )
            .first()
        )
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"공급업체명 '{supplier_data.supplier_name}'이 이미 존재합니다",
            )

    # 업데이트
    update_data = supplier_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)

    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """
    공급업체 삭제

    - **supplier_id**: 공급업체 ID
    - 주의: 부품 마스터에서 참조 중인 공급업체는 삭제할 수 없습니다
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )

    # 부품 참조 확인 (추후 구현)
    # TODO: parts 테이블에서 supplier_id 참조 확인

    db.delete(supplier)
    db.commit()

    return None


@router.patch("/{supplier_id}/activate", response_model=SupplierResponse)
def activate_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """
    공급업체 활성화

    - **supplier_id**: 공급업체 ID
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )

    supplier.is_active = True
    db.commit()
    db.refresh(supplier)

    return supplier


@router.patch("/{supplier_id}/deactivate", response_model=SupplierResponse)
def deactivate_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """
    공급업체 비활성화

    - **supplier_id**: 공급업체 ID
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )

    supplier.is_active = False
    db.commit()
    db.refresh(supplier)

    return supplier
