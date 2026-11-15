"""
부품 마스터 API
부품 마스터 CRUD API를 제공합니다.

Service Layer를 통해 비즈니스 로직을 처리합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional
from io import BytesIO
from datetime import datetime
from decimal import Decimal
import re

from app.api.v1.deps import get_part_service, handle_service_exception
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.services.part_service import PartService
from app.schemas.parts import (
    PartCreate,
    PartUpdate,
    PartResponse,
    PartListResponse,
    PartPaginatedResponse,
    AssemblyCreate,
)
from app.core.exceptions import AppException

router = APIRouter(prefix="/parts", tags=["부품 마스터"])


@router.get("/by-protected-customer/{customer_id}", response_model=List[PartListResponse])
def get_protected_parts_by_customer(customer_id: int, db: Session = Depends(get_db)):
    """해당 고객의 전속(독점) 계약 부품 목록 — 거래처 상세에서 확인용 (v0.79.0)"""
    from app.models.parts import Part
    return db.query(Part).filter(
        Part.is_protected == True,  # noqa: E712
        Part.protected_customer_id == customer_id,
    ).order_by(Part.part_number).all()


@router.get("", response_model=PartPaginatedResponse)
def get_parts(
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    # 신규 필터 (v0.10.0 품번구조)
    product_line_id: Optional[int] = Query(None, description="대분류/제품라인 필터"),
    part_group_id: Optional[int] = Query(None, description="소분류/품목군 필터"),
    # Legacy 필터 (하위 호환성)
    major_category_id: Optional[int] = Query(None, description="[Legacy] 대분류 필터"),
    middle_category_id: Optional[int] = Query(None, description="[Legacy] 중분류 필터"),
    minor_category_id: Optional[int] = Query(None, description="[Legacy] 소분류 필터"),
    # 공통 필터
    level_id: Optional[int] = Query(None, description="레벨 필터 (단일)"),
    level_ids: Optional[str] = Query(None, description="레벨 필터 (다중, 콤마 구분)"),
    material_id: Optional[int] = Query(None, description="재질 필터"),
    # v0.12.0: 추가 필터
    treatment_id: Optional[int] = Query(None, description="후처리 필터"),
    drawing_type_id: Optional[int] = Query(None, description="도면유형 필터"),
    procurement_type_id: Optional[int] = Query(None, description="조달유형 필터"),
    unit_id: Optional[int] = Query(None, description="단위 필터"),
    development_type_id: Optional[int] = Query(None, description="개발구분 필터 (단일)"),
    development_type_ids: Optional[str] = Query(None, description="개발구분 필터 (다중, 콤마 구분)"),
    part_status: Optional[str] = Query(None, alias="status", description="상태 필터"),
    is_active: Optional[bool] = Query(None, description="사용여부 필터"),
    classified: Optional[bool] = Query(None, description="분류상태: 미지정=전체, true=분류됨, false=미분류"),
    # 고급 필터: 미입력 필드 검색
    missing_fields: Optional[str] = Query(None, description="미입력 필드 검색 (콤마 구분: supplier_id,part_name_en,standard_price,specification 등)"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(20, ge=1, le=1000, description="조회 개수"),
    order_by: str = Query("created_at", description="정렬 기준 (part_number, part_name, status, created_at 등)"),
    order_desc: bool = Query(True, description="내림차순 정렬 여부"),
    service: PartService = Depends(get_part_service)
):
    """부품 목록 조회 (검색 및 필터링) - 페이지네이션 및 정렬 지원"""
    # level_ids 문자열을 리스트로 변환
    level_ids_list = None
    if level_ids:
        try:
            level_ids_list = [int(x.strip()) for x in level_ids.split(',') if x.strip()]
        except ValueError:
            pass

    # v0.12.0: development_type_ids 문자열을 리스트로 변환
    dev_type_ids_list = None
    if development_type_ids:
        try:
            dev_type_ids_list = [int(x.strip()) for x in development_type_ids.split(',') if x.strip()]
        except ValueError:
            pass

    # 고급 필터: missing_fields 문자열을 리스트로 변환
    missing_fields_list = None
    if missing_fields:
        missing_fields_list = [x.strip() for x in missing_fields.split(',') if x.strip()]

    items, total = service.search_parts_with_count(
        keyword=keyword,
        product_line_id=product_line_id,
        part_group_id=part_group_id,
        major_category_id=major_category_id,
        middle_category_id=middle_category_id,
        minor_category_id=minor_category_id,
        level_id=level_id,
        level_ids=level_ids_list,
        material_id=material_id,
        treatment_id=treatment_id,
        drawing_type_id=drawing_type_id,
        procurement_type_id=procurement_type_id,
        unit_id=unit_id,
        development_type_id=development_type_id,
        development_type_ids=dev_type_ids_list,
        status=part_status,
        is_active=is_active,
        classified=classified,
        missing_fields=missing_fields_list,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_desc=order_desc
    )
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }


@router.get("/export/excel")
def export_parts_excel(
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    # 신규 필터 (v0.10.0 품번구조)
    product_line_id: Optional[int] = Query(None, description="대분류/제품라인 필터"),
    part_group_id: Optional[int] = Query(None, description="소분류/품목군 필터"),
    # Legacy 필터 (하위 호환성)
    major_category_id: Optional[int] = Query(None, description="[Legacy] 대분류 필터"),
    middle_category_id: Optional[int] = Query(None, description="[Legacy] 중분류 필터"),
    minor_category_id: Optional[int] = Query(None, description="[Legacy] 소분류 필터"),
    # 공통 필터
    level_id: Optional[int] = Query(None, description="레벨 필터 (단일)"),
    level_ids: Optional[str] = Query(None, description="레벨 필터 (다중, 콤마 구분)"),
    material_id: Optional[int] = Query(None, description="재질 필터"),
    # v0.12.0: 추가 필터
    treatment_id: Optional[int] = Query(None, description="후처리 필터"),
    drawing_type_id: Optional[int] = Query(None, description="도면유형 필터"),
    procurement_type_id: Optional[int] = Query(None, description="조달유형 필터"),
    unit_id: Optional[int] = Query(None, description="단위 필터"),
    development_type_id: Optional[int] = Query(None, description="개발구분 필터 (단일)"),
    development_type_ids: Optional[str] = Query(None, description="개발구분 필터 (다중, 콤마 구분)"),
    part_status: Optional[str] = Query(None, alias="status", description="상태 필터"),
    is_active: Optional[bool] = Query(None, description="사용여부 필터"),
    order_by: str = Query("created_at", description="정렬 기준"),
    order_desc: bool = Query(True, description="내림차순 정렬 여부"),
    service: PartService = Depends(get_part_service)
):
    """부품 목록 엑셀 다운로드"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    # level_ids 문자열을 리스트로 변환
    level_ids_list = None
    if level_ids:
        try:
            level_ids_list = [int(x.strip()) for x in level_ids.split(',') if x.strip()]
        except ValueError:
            pass

    # development_type_ids 문자열을 리스트로 변환
    dev_type_ids_list = None
    if development_type_ids:
        try:
            dev_type_ids_list = [int(x.strip()) for x in development_type_ids.split(',') if x.strip()]
        except ValueError:
            pass

    # 모든 데이터 조회 (limit 없이)
    items, total = service.search_parts_with_count(
        keyword=keyword,
        product_line_id=product_line_id,
        part_group_id=part_group_id,
        major_category_id=major_category_id,
        middle_category_id=middle_category_id,
        minor_category_id=minor_category_id,
        level_id=level_id,
        level_ids=level_ids_list,
        material_id=material_id,
        treatment_id=treatment_id,
        drawing_type_id=drawing_type_id,
        procurement_type_id=procurement_type_id,
        unit_id=unit_id,
        development_type_id=development_type_id,
        development_type_ids=dev_type_ids_list,
        status=part_status,
        is_active=is_active,
        skip=0,
        limit=10000,  # 최대 10000건
        order_by=order_by,
        order_desc=order_desc
    )

    # 워크북 생성
    wb = Workbook()
    ws = wb.active
    ws.title = "부품목록"

    # 스타일 정의
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 헤더 정의 (업로드 포맷과 동일한 13컬럼, v0.23.0: 기준단가+통화 추가)
    headers = [
        "No", "전체품번", "품명", "설명",
        "코드1(대분류)", "코드2(소분류)", "코드3", "코드4",
        "코드5(재질)", "코드6(후처리)", "레벨",
        "기준단가", "통화"
    ]

    # 헤더 작성
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # 데이터 작성
    for row_idx, part in enumerate(items, 2):
        # 코드 값 추출 (관계 데이터에서 code 필드, NULL이면 빈 문자열)
        product_line_code = part.product_line.code if part.product_line else ""
        part_group_code = part.part_group.code if part.part_group else ""
        material_code = part.material.code if part.material else ""
        treatment_code = part.treatment.code if part.treatment else ""
        level_code = part.level.code if part.level else ""

        # item_code (5자리) → 코드3(앞3자리) + 코드4(뒤2자리) 분리
        item_code = part.item_code or ""
        item_code_prefix = item_code[:3] if len(item_code) >= 3 else item_code
        item_code_suffix = item_code[3:] if len(item_code) > 3 else ""

        # 전체품번: part_number_display 사용 (bracket suffix [S] 등 포함)
        full_part_number = part.part_number_display or part.part_number or ""

        ws.cell(row=row_idx, column=1, value=row_idx - 1).border = thin_border
        ws.cell(row=row_idx, column=2, value=full_part_number).border = thin_border
        ws.cell(row=row_idx, column=3, value=part.part_name or "").border = thin_border
        ws.cell(row=row_idx, column=4, value=part.description or "").border = thin_border
        ws.cell(row=row_idx, column=5, value=product_line_code).border = thin_border
        ws.cell(row=row_idx, column=6, value=part_group_code).border = thin_border
        ws.cell(row=row_idx, column=7, value=item_code_prefix).border = thin_border
        ws.cell(row=row_idx, column=8, value=item_code_suffix).border = thin_border
        ws.cell(row=row_idx, column=9, value=material_code).border = thin_border
        ws.cell(row=row_idx, column=10, value=treatment_code).border = thin_border
        ws.cell(row=row_idx, column=11, value=level_code).border = thin_border
        # v0.23.0: 기준단가, 통화 (통화별 천 단위 콤마 + 소수 자리)
        from app.utils.money import excel_money_format
        price_cell = ws.cell(row=row_idx, column=12, value=float(part.standard_price) if part.standard_price else 0)
        price_cell.border = thin_border
        price_cell.number_format = excel_money_format(part.standard_price_currency or "KRW")
        ws.cell(row=row_idx, column=13, value=part.standard_price_currency or "KRW").border = thin_border

    # 열 너비 조정
    column_widths = [6, 30, 30, 40, 14, 14, 8, 8, 12, 12, 8, 14, 8]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + col)].width = width

    # 파일 저장
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # 파일명 생성 (URL 인코딩)
    from urllib.parse import quote
    filename = f"부품목록_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"parts.xlsx\"; filename*=UTF-8''{encoded_filename}"
        }
    )


@router.get("/{part_id}", response_model=PartResponse)
def get_part(
    part_id: int,
    service: PartService = Depends(get_part_service)
):
    """부품 단건 조회"""
    try:
        return service.get_or_raise(part_id)
    except AppException as e:
        handle_service_exception(e)


@router.get("/by-number/{part_number}", response_model=PartResponse)
def get_part_by_number(
    part_number: str,
    service: PartService = Depends(get_part_service)
):
    """품번으로 부품 조회"""
    try:
        return service.get_by_part_number_or_raise(part_number)
    except AppException as e:
        handle_service_exception(e)


@router.get("/check-duplicate")
def check_part_number_duplicate(
    part_number: str = Query(..., description="중복 체크할 품번"),
    exclude_id: int = Query(None, description="제외할 부품 ID (수정 시)"),
    service: PartService = Depends(get_part_service)
):
    """
    품번 중복 체크

    Returns:
        - exists: 중복 여부
        - part: 중복된 부품 정보 (중복 시)
    """
    try:
        # 하이픈 제거한 내부 품번으로 검색
        internal_part_number = part_number.replace("-", "")
        part = service.get_by_part_number(internal_part_number)

        if part and (exclude_id is None or part.id != exclude_id):
            return {
                "exists": True,
                "part": {
                    "id": part.id,
                    "part_number": part.part_number,
                    "part_number_display": part.part_number_display,
                    "part_name": part.part_name
                }
            }
        return {"exists": False, "part": None}
    except Exception:
        return {"exists": False, "part": None}


@router.post("", response_model=PartResponse, status_code=status.HTTP_201_CREATED)
def create_part(
    part: PartCreate,
    service: PartService = Depends(get_part_service)
):
    """부품 생성"""
    try:
        return service.create_part(part)
    except AppException as e:
        handle_service_exception(e)


@router.post("/assembly", response_model=PartResponse, status_code=status.HTTP_201_CREATED)
def create_assembly(
    assembly: AssemblyCreate,
    service: PartService = Depends(get_part_service)
):
    """
    조합/키트 생성 (자유형식 코드)

    BOM에서 사용할 조합(Assembly), 키트(Kit), 서브조합(Sub-Assembly) 등을 등록합니다.
    품번은 사용자가 직접 입력하며, 대분류/소분류/품목코드는 선택사항입니다.
    """
    try:
        return service.create_assembly(assembly)
    except AppException as e:
        handle_service_exception(e)


@router.put("/{part_id}", response_model=PartResponse)
def update_part(
    part_id: int,
    part: PartUpdate,
    service: PartService = Depends(get_part_service)
):
    """부품 수정"""
    try:
        return service.update_part(part_id, part)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{part_id}")
def delete_part(
    part_id: int,
    force: bool = Query(False, description="강제 삭제 여부 (True: 상태와 무관하게 즉시 삭제)"),
    service: PartService = Depends(get_part_service)
):
    """
    부품 삭제 (2단계 삭제)

    - 1단계: 상태가 ACTIVE/INACTIVE인 경우 → OBSOLETE(단종)으로 변경
    - 2단계: 상태가 이미 OBSOLETE인 경우 → DB에서 완전 삭제
    - force=True: 강제로 즉시 완전 삭제 (관리자용)

    Returns:
        dict: {"action": "obsoleted" | "deleted", "message": str}
    """
    try:
        result = service.delete_part(part_id, force=force)
        return result
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{part_id}/activate", response_model=PartResponse)
def activate_part(
    part_id: int,
    service: PartService = Depends(get_part_service)
):
    """부품 활성화"""
    try:
        return service.activate(part_id)
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{part_id}/deactivate", response_model=PartResponse)
def deactivate_part(
    part_id: int,
    service: PartService = Depends(get_part_service)
):
    """부품 비활성화"""
    try:
        return service.deactivate(part_id)
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{part_id}/status", response_model=PartResponse)
def update_part_status(
    part_id: int,
    new_status: str = Query(..., description="새로운 상태 (ACTIVE/INACTIVE/OBSOLETE)"),
    service: PartService = Depends(get_part_service)
):
    """부품 상태 변경"""
    try:
        return service.update_status(part_id, new_status)
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{part_id}/approval", response_model=PartResponse)
def update_approval_status(
    part_id: int,
    approval_status: str = Query(..., description="승인 상태 (DRAFT/PENDING/APPROVED/REJECTED)"),
    approved_by: Optional[int] = Query(None, description="승인자 ID"),
    service: PartService = Depends(get_part_service)
):
    """부품 승인 상태 변경"""
    try:
        return service.update_approval_status(part_id, approval_status, approved_by)
    except AppException as e:
        handle_service_exception(e)


@router.post("/generate-missing-uids")
def generate_missing_uids(
    service: PartService = Depends(get_part_service)
):
    """
    UID가 없는 부품에 대해 일괄 UID 생성

    기존에 등록된 부품 중 part_uid가 없는 부품을 찾아서 일괄 생성합니다.

    Returns:
        dict: {
            "total_without_uid": UID 없는 총 부품 수,
            "generated_count": 생성된 UID 수,
            "failed_count": 실패한 수,
            "parts": 처리된 부품 목록
        }
    """
    try:
        return service.generate_missing_uids()
    except AppException as e:
        handle_service_exception(e)


@router.post("/upload-excel")
async def upload_excel(
    file: UploadFile = File(...),
    service: PartService = Depends(get_part_service)
):
    """
    엑셀 파일을 업로드하여 부품 일괄 등록 (v0.23.0)

    엑셀 파일 컬럼 형식 (13개):
    - No: 순번 (무시됨)
    - 전체품번: 품번 (예: HB05-RCP-FSO-01-A6-HB [S])
    - 품명: 부품명 (예: HXB15 리셉터클 프론트쉘 기본 AL6061)
    - 설명: 부품 설명 (예: HXB15 / 리셉터클 / 프론트쉘 / 기본 / AL6061 / ...)
    - 코드1: 대분류/제품라인 코드 (예: HB05)
    - 코드2: 소분류/품목군 코드 (예: RCP)
    - 코드3: 품목코드 앞 3자리 (예: FSO)
    - 코드4: 품목코드 뒤 2자리 (예: 01)
    - 코드5: 재질 코드 (예: A6)
    - 코드6: 후처리 코드 (예: HB)
    - 레벨: 레벨 코드 (예: S)
    - 기준단가: 숫자 (빈칸이면 미입력)
    - 통화: KRW/USD/EUR/JPY/CNY/GBP (빈칸이면 KRW)

    기존 부품(중복 품번)의 경우:
    - 기준단가 값이 있으면 → 가격만 업데이트 (status: price_updated)
    - 기준단가 값이 없으면 → 건너뜀 (status: skipped)

    Returns:
        dict: {
            "total": 총 행 수,
            "success_count": 성공 수,
            "price_updated_count": 가격 업데이트 수,
            "failed_count": 실패 수,
            "results": 처리 결과 목록
        }
    """
    import openpyxl
    from app.utils.part_number_parser import parse_excel_part_number
    from app.core.database import SessionLocal

    # 파일 확장자 검증
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다."
        )

    try:
        # 엑셀 파일 읽기
        contents = await file.read()
        workbook = openpyxl.load_workbook(BytesIO(contents))
        sheet = workbook.active

        results = []
        success_count = 0
        price_updated_count = 0
        failed_count = 0

        # 헤더 행 건너뛰고 데이터 행 처리
        rows = list(sheet.iter_rows(min_row=2, values_only=True))

        for row_idx, row in enumerate(rows, start=2):
            if not row or not row[1]:  # 빈 행 또는 품번 없는 행 건너뛰기
                continue

            try:
                # v0.22.0 컬럼 매핑 (0-indexed, 11개 컬럼)
                # No(0), 전체품번(1), 품명(2), 설명(3), 코드1(4), 코드2(5),
                # 코드3(6), 코드4(7), 코드5(8), 코드6(9), 레벨(10)
                full_part_number = str(row[1]).strip() if row[1] else ""
                part_name = str(row[2]).strip() if row[2] else ""          # 품명
                description = str(row[3]).strip() if row[3] else ""        # 설명
                product_line_code = str(row[4]).strip() if row[4] else ""  # 코드1: 대분류
                part_group_code = str(row[5]).strip() if row[5] else ""    # 코드2: 소분류
                item_code_prefix = str(row[6]).strip() if row[6] else ""   # 코드3: 품목코드 앞
                item_code_suffix = str(row[7]).strip() if row[7] else ""   # 코드4: 품목코드 뒤
                material_code = str(row[8]).strip() if row[8] else ""      # 코드5: 재질
                treatment_code = str(row[9]).strip() if row[9] else ""     # 코드6: 후처리
                level_code = str(row[10]).strip() if len(row) > 10 and row[10] else ""  # 레벨

                # v0.23.0: 기준단가, 통화 파싱
                raw_price = row[11] if len(row) > 11 and row[11] is not None else None
                raw_currency = str(row[12]).strip().upper() if len(row) > 12 and row[12] else "KRW"

                # 기준단가 숫자 변환
                standard_price_value = None
                if raw_price is not None and str(raw_price).strip() != "":
                    try:
                        standard_price_value = Decimal(str(raw_price).strip())
                    except Exception:
                        standard_price_value = None

                # 통화 유효성 검증
                valid_currencies = {"KRW", "USD", "EUR", "JPY", "CNY", "GBP"}
                if raw_currency not in valid_currencies:
                    raw_currency = "KRW"

                # 품번에서 레벨 부분 제거하여 기본 품번 추출
                base_part_number = re.sub(r'\s*\[[A-Za-z0-9]+\]', '', full_part_number).strip()
                base_system_number = base_part_number.replace("-", "")

                # 시스템용 품번 생성 (하이픈 제거 + 레벨코드)
                system_part_number = base_system_number + level_code.upper() if level_code else base_system_number

                # v0.24.0: 중복 체크 - 레벨 포함한 최종 품번으로 검사
                existing = service.repository.get_by_part_number(system_part_number)

                # 레벨이 다른 경우: 기본 품번(레벨 없음)이 존재하는지 추가 확인
                existing_base = None
                if not existing and level_code:
                    existing_base = service.repository.get_by_part_number(base_system_number)
                    # 기본 품번이 있고 레벨이 없으면 → 레벨 추가 대상
                    if existing_base and not existing_base.level_id:
                        existing = existing_base

                if existing:
                    # v0.24.0: 가격 또는 레벨 업데이트
                    updates = []
                    from app.models.code_master import Level

                    # 레벨 업데이트 (기존에 없고, 엑셀에 있으면)
                    level_updated = False
                    if level_code and not existing.level_id:
                        level = service.db.query(Level).filter(
                            Level.code == level_code.strip().upper(),
                            Level.is_active == True
                        ).first()
                        if level:
                            existing.level_id = level.id
                            # 품번도 레벨 포함으로 업데이트
                            existing.part_number = system_part_number
                            existing.part_number_display = f"{base_part_number} [{level_code.upper()}]"
                            level_updated = True
                            updates.append(f"레벨 추가: [{level_code.upper()}]")

                    # 가격 업데이트
                    price_updated = False
                    if standard_price_value is not None:
                        from app.services.price_service import PriceService
                        old_price = existing.standard_price or Decimal("0")
                        old_currency = existing.standard_price_currency or "KRW"

                        existing.standard_price = standard_price_value
                        existing.standard_price_currency = raw_currency
                        existing.price_updated_at = datetime.now()
                        price_updated = True
                        updates.append(f"기준단가 변경 ({old_price} {old_currency} → {standard_price_value} {raw_currency})")

                    if updates:
                        service.db.commit()

                        # PriceHistory 기록 (가격 변경 시)
                        if price_updated:
                            try:
                                price_service = PriceService(service.db)
                                price_service.record_price_history(
                                    part_id=existing.id,
                                    unit_price=standard_price_value,
                                    currency=raw_currency,
                                    price_type="STANDARD",
                                    reference_type="EXCEL_UPLOAD",
                                    remarks=f"엑셀 업로드: {', '.join(updates)}"
                                )
                            except Exception:
                                pass

                        results.append({
                            "row": row_idx,
                            "part_number": full_part_number,
                            "part_id": existing.id,
                            "status": "updated" if level_updated else "price_updated",
                            "message": ", ".join(updates)
                        })
                        if price_updated:
                            price_updated_count += 1
                        else:
                            success_count += 1  # 레벨만 업데이트된 경우
                    else:
                        results.append({
                            "row": row_idx,
                            "part_number": full_part_number,
                            "status": "skipped",
                            "message": "이미 존재하는 품번입니다."
                        })
                        failed_count += 1
                    continue

                # v0.22.0: 코드 컬럼 중 하나라도 비어있으면 직접입력 모드로 처리
                # 코드1~코드6 중 하나라도 비어있으면 직접입력 형태로 간주
                is_direct_input = not all([
                    product_line_code, part_group_code,
                    item_code_prefix, item_code_suffix,
                    material_code, treatment_code
                ])

                db = service.db

                if is_direct_input:
                    # 직접입력 모드: 레벨만 파싱하고 나머지는 NULL
                    from app.models.code_master import Level
                    level_id = None
                    level_warning = None
                    if level_code:
                        level = db.query(Level).filter(
                            Level.code == level_code.strip().upper(),
                            Level.is_active == True
                        ).first()
                        if level:
                            level_id = level.id
                        else:
                            level_warning = f"레벨 코드 '{level_code.upper()}' 없음"

                    # 부품 데이터 생성 (직접입력 모드)
                    part_data = PartCreate(
                        part_number=base_part_number,
                        part_name=part_name if part_name else None,
                        description=description,
                        product_line_id=None,
                        part_group_id=None,
                        material_id=None,
                        treatment_id=None,
                        level_id=level_id,
                        # v0.23.0: 기준단가
                        standard_price=standard_price_value if standard_price_value is not None else Decimal("0"),
                        standard_price_currency=raw_currency,
                    )

                    # 부품 생성
                    new_part = service.create_part(part_data)

                    # v0.23.0: 기준단가 이력 기록
                    if standard_price_value is not None and standard_price_value > 0:
                        try:
                            from app.services.price_service import PriceService
                            price_service = PriceService(service.db)
                            price_service.record_price_history(
                                part_id=new_part.id,
                                unit_price=standard_price_value,
                                currency=raw_currency,
                                price_type="STANDARD",
                                reference_type="EXCEL_UPLOAD",
                                remarks=f"엑셀 업로드: 신규 등록 기준단가 {standard_price_value} {raw_currency}"
                            )
                        except Exception:
                            pass

                    msg = "등록 완료 (직접입력)"
                    if level_warning:
                        msg += f" - 경고: {level_warning}"
                    results.append({
                        "row": row_idx,
                        "part_number": full_part_number,
                        "part_id": new_part.id,
                        "status": "success" if not level_warning else "warning",
                        "message": msg,
                        "input_mode": "direct"
                    })
                    success_count += 1

                else:
                    # 코드 매핑 모드: 모든 코드 → ID 변환
                    parsed = parse_excel_part_number(
                        db=db,
                        product_line_code=product_line_code,
                        part_group_code=part_group_code,
                        item_code_prefix=item_code_prefix,
                        item_code_suffix=item_code_suffix,
                        material_code=material_code,
                        treatment_code=treatment_code,
                        level_code=level_code
                    )

                    # v0.22.0: 엑셀에서 품명이 제공되면 해당 값 사용, 없으면 서비스에서 description 기반 자동 생성
                    # 자동 생성 예: "HXB11 / 리셉터클 / 벡쉘L/로우 / ..." → "HXB11 리셉터클 벡쉘L/로우"

                    # 부품 데이터 생성 (코드 매핑 모드)
                    part_data = PartCreate(
                        part_number=base_part_number,
                        part_name=part_name if part_name else None,
                        description=description,
                        product_line_id=parsed.get('product_line_id'),
                        part_group_id=parsed.get('part_group_id'),
                        material_id=parsed.get('material_id'),
                        treatment_id=parsed.get('treatment_id'),
                        level_id=parsed.get('level_id'),
                        # v0.23.0: 기준단가
                        standard_price=standard_price_value if standard_price_value is not None else Decimal("0"),
                        standard_price_currency=raw_currency,
                    )

                    # 부품 생성
                    new_part = service.create_part(part_data)

                    # item_code 업데이트 (파싱된 값이 있으면)
                    if parsed.get('item_code'):
                        service.repository.update_from_dict(new_part, {'item_code': parsed['item_code']})

                    # v0.23.0: 기준단가 이력 기록
                    if standard_price_value is not None and standard_price_value > 0:
                        try:
                            from app.services.price_service import PriceService
                            price_service = PriceService(service.db)
                            price_service.record_price_history(
                                part_id=new_part.id,
                                unit_price=standard_price_value,
                                currency=raw_currency,
                                price_type="STANDARD",
                                reference_type="EXCEL_UPLOAD",
                                remarks=f"엑셀 업로드: 신규 등록 기준단가 {standard_price_value} {raw_currency}"
                            )
                        except Exception:
                            pass

                    results.append({
                        "row": row_idx,
                        "part_number": full_part_number,
                        "part_id": new_part.id,
                        "status": "success",
                        "message": "등록 완료 (코드매핑)",
                        "input_mode": "code_mapping",
                        "parsed_errors": parsed.get('errors', [])
                    })
                    success_count += 1

            except Exception as e:
                results.append({
                    "row": row_idx,
                    "part_number": str(row[1]) if row[1] else "",
                    "status": "failed",
                    "message": str(e)
                })
                failed_count += 1

        return {
            "total": len(rows),
            "success_count": success_count,
            "price_updated_count": price_updated_count,
            "failed_count": failed_count,
            "results": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"엑셀 파일 처리 중 오류가 발생했습니다: {str(e)}"
        )




# ==================== 부품 첨부파일 (도면/스펙/사진/기타) v0.96.0 ====================
import os as _os
from pathlib import Path as _Path
from fastapi import Form as _Form
from fastapi.responses import FileResponse as _FileResponse
from app.core.auth import require_auth as _require_auth
from app.models.parts import Part as _Part, PartAttachment as _PartAttachment
from app.schemas.parts import PartAttachmentResponse as _PartAttachmentResponse

from app.core.config import settings as _settings
from app.core.storage_paths import resolve_stored_path as _resolve_stored_path

# 업로드 폴더(config.json storage.upload) 아래에 저장 — 과거 경로는 _resolve_stored_path 가 맞춰 준다
_ATT_DIR = _settings.uploads_path / "part_attachments"
_ATT_ALLOWED = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf", ".xlsx", ".xls",
                ".csv", ".doc", ".docx", ".hwp", ".hwpx", ".ppt", ".pptx", ".txt", ".zip",
                ".step", ".stp", ".dwg", ".dxf", ".igs", ".iges"}
_ATT_KINDS = {"DRAWING", "SPEC", "PHOTO", "OTHER"}


@router.get("/{part_id}/attachments", response_model=List[_PartAttachmentResponse])
def list_part_attachments(part_id: int, db: Session = Depends(get_db)):
    """부품 첨부파일 목록."""
    return db.query(_PartAttachment).filter(_PartAttachment.part_id == part_id)\
        .order_by(_PartAttachment.created_at.desc()).all()


@router.post("/{part_id}/attachments", response_model=_PartAttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_part_attachment(
    part_id: int,
    file: UploadFile = File(...),
    kind: str = _Form("OTHER"),
    db: Session = Depends(get_db),
    user=Depends(_require_auth),
):
    """부품 첨부 업로드(도면/스펙/사진/기타). 허용 형식만, 30MB 제한."""
    part = db.query(_Part).filter(_Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="부품을 찾을 수 없습니다.")
    kind = (kind or "OTHER").upper()
    if kind not in _ATT_KINDS:
        kind = "OTHER"
    ext = _os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ATT_ALLOWED:
        raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다: {ext or '확장자 없음'}")
    contents = await file.read()
    if len(contents) > 30 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다. 최대 30MB")
    _ATT_DIR.mkdir(parents=True, exist_ok=True)
    import uuid as _uuid
    safe = f"{part_id}_{_uuid.uuid4().hex}{ext}"
    dest = _ATT_DIR / safe
    with open(dest, "wb") as f:
        f.write(contents)
    att = _PartAttachment(
        part_id=part_id, kind=kind, filename=(file.filename or safe),
        filepath=str(dest).replace("\\", "/"), mime_type=file.content_type,
        size=len(contents), uploaded_by=getattr(user, "id", None),
    )
    db.add(att); db.commit(); db.refresh(att)
    return att


@router.get("/attachments/{att_id}/preview")
def preview_part_attachment(att_id: int, db: Session = Depends(get_db)):
    """첨부 인라인 미리보기(이미지/PDF)."""
    att = db.query(_PartAttachment).filter(_PartAttachment.id == att_id).first()
    path = _resolve_stored_path(att.filepath) if att else None
    if not att or not path.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return _FileResponse(path=str(path), media_type=att.mime_type or "application/octet-stream",
                         headers={"Content-Disposition": "inline"})


@router.get("/attachments/{att_id}/download")
def download_part_attachment(att_id: int, db: Session = Depends(get_db)):
    """첨부 다운로드."""
    att = db.query(_PartAttachment).filter(_PartAttachment.id == att_id).first()
    path = _resolve_stored_path(att.filepath) if att else None
    if not att or not path.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return _FileResponse(path=str(path), filename=att.filename,
                         headers={"Content-Disposition": f'attachment; filename="{att.filename}"'})


@router.delete("/attachments/{att_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part_attachment(att_id: int, db: Session = Depends(get_db), user=Depends(_require_auth)):
    """첨부 삭제(파일+행)."""
    att = db.query(_PartAttachment).filter(_PartAttachment.id == att_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="첨부를 찾을 수 없습니다.")
    try:
        path = _resolve_stored_path(att.filepath)
        if path.is_file():
            path.unlink()
    except OSError:
        pass
    db.delete(att); db.commit()
    return None


# ==================== BOM 개편 P4: 미분류→정식 분류 승격 · 부품 병합 ====================
from pydantic import BaseModel as _BaseModelP


class _ClassifyRequest(_BaseModelP):
    product_line_id: int
    part_group_id: int
    item_code_prefix: str
    level_id: int
    material_id: Optional[int] = None
    treatment_id: Optional[int] = None
    item_code_suffix: Optional[str] = None
    part_name: Optional[str] = None


class _MergeRequest(_BaseModelP):
    source_id: int
    target_id: int


@router.post("/{part_id}/classify", response_model=PartResponse)
def classify_part(part_id: int, req: _ClassifyRequest, service: PartService = Depends(get_part_service)):
    """미분류 부품을 정식 분류/채번으로 승격 (품번 생성). id·UID 유지."""
    try:
        return service.classify_part(part_id, req.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.post("/merge")
def merge_parts(req: _MergeRequest, service: PartService = Depends(get_part_service), user=Depends(_require_auth)):
    """중복 부품 병합: source의 BOM 참조를 target으로 이관 후 source 비활성화."""
    try:
        return service.merge_parts(req.source_id, req.target_id, actor_id=getattr(user, "id", None))
    except AppException as e:
        handle_service_exception(e)
