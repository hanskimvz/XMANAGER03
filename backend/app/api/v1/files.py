"""
파일 업로드/다운로드 API
부품 및 거래처에 첨부되는 도면, 사진, 문서 파일을 관리합니다.

저장 구조:
  storage/uploads/parts/{part_id}/{file_type}/{uuid}_{원본파일명}.{확장자}
  storage/uploads/partners/{partner_id}/documents/{uuid}_{원본파일명}.{확장자}

파일 타입:
  - drawing: 도면 파일 (PDF, DWG, DXF, STEP, STP, IGS)
  - photo: 사진 파일 (JPG, PNG, GIF, WEBP)
  - document: 문서 파일 (PDF, DOC, DOCX, XLS, XLSX, HWP)
"""

import os
import uuid
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Literal

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.parts import Part
from app.models.business_partner import BusinessPartner

router = APIRouter(prefix="/parts", tags=["파일 관리"])

# 파일 타입 정의
FileType = Literal["drawing", "photo", "document"]

# 파일 타입별 디렉토리명
FILE_TYPE_DIRS = {
    "drawing": "drawings",
    "photo": "photos",
    "document": "documents",
}


# ================== Schemas ==================

class FileInfo(BaseModel):
    """파일 정보"""
    file_name: str
    original_name: str
    file_type: str
    file_size: int
    file_path: str
    uploaded_at: str
    download_url: str
    preview_url: str

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    """파일 업로드 응답"""
    success: bool
    message: str
    file_info: Optional[FileInfo] = None


class PartFilesResponse(BaseModel):
    """부품 첨부파일 목록 응답"""
    part_id: int
    part_number: str
    drawing: Optional[FileInfo] = None
    photo: Optional[FileInfo] = None
    documents: List[FileInfo] = []


class FileDeleteResponse(BaseModel):
    """파일 삭제 응답"""
    success: bool
    message: str


# ================== Helper Functions ==================

def get_part_upload_dir(part_id: int, file_type: str) -> Path:
    """부품별 파일 저장 디렉토리 반환"""
    dir_name = FILE_TYPE_DIRS.get(file_type)
    if not dir_name:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 파일 타입입니다. 허용: {list(FILE_TYPE_DIRS.keys())}"
        )
    return settings.uploads_path / "parts" / str(part_id) / dir_name


def generate_file_name(original_name: str) -> str:
    """
    고유 파일명 생성
    형식: {UUID}_{원본파일명}
    예: 550e8400-e29b-41d4-a716-446655440000_도면_rev2.pdf
    """
    file_uuid = str(uuid.uuid4())
    # 보안: 원본 파일명에서 디렉터리 성분 제거(경로 탈출 ../ 방지). basename 만 사용.
    safe_name = Path(original_name or "file").name.replace("\\", "_").replace("/", "_")
    safe_name = safe_name or "file"
    return f"{file_uuid}_{safe_name}"


def validate_file_extension(filename: str, file_type: str) -> bool:
    """파일 확장자 유효성 검사"""
    ext = Path(filename).suffix.lower()
    allowed = settings.get_allowed_extensions(file_type)
    return ext in allowed


def validate_file_size(file_size: int) -> bool:
    """파일 크기 유효성 검사"""
    return file_size <= settings.MAX_UPLOAD_SIZE


def get_relative_path(part_id: int, file_type: str, file_name: str) -> str:
    """DB 저장용 상대 경로 반환"""
    dir_name = FILE_TYPE_DIRS.get(file_type, file_type)
    return f"parts/{part_id}/{dir_name}/{file_name}"


def build_file_info(
    file_name: str,
    original_name: str,
    file_type: str,
    file_size: int,
    file_path: str,
    uploaded_at: Optional[str] = None
) -> FileInfo:
    """FileInfo 객체 생성"""
    return FileInfo(
        file_name=file_name,
        original_name=original_name,
        file_type=file_type,
        file_size=file_size,
        file_path=file_path,
        uploaded_at=uploaded_at or datetime.now().isoformat(),
        download_url=f"/api/v1/files/{file_path}",
        preview_url=f"/api/v1/files/{file_path}?preview=true"
    )


async def save_upload_file(
    file: UploadFile,
    part_id: int,
    file_type: str
) -> FileInfo:
    """파일 저장 및 정보 반환"""
    # 파일 확장자 검증
    if not validate_file_extension(file.filename, file_type):
        allowed = settings.get_allowed_extensions(file_type)
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(allowed)}"
        )

    # 파일 내용 읽기
    content = await file.read()

    # 파일 크기 검증
    if not validate_file_size(len(content)):
        max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. 최대 {max_mb}MB까지 허용됩니다."
        )

    # 저장 디렉토리 생성
    save_dir = get_part_upload_dir(part_id, file_type)
    save_dir.mkdir(parents=True, exist_ok=True)

    # 고유 파일명 생성
    new_file_name = generate_file_name(file.filename)
    file_path = save_dir / new_file_name

    # 파일 저장
    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")

    # 상대 경로 (DB 저장용)
    relative_path = get_relative_path(part_id, file_type, new_file_name)

    return build_file_info(
        file_name=new_file_name,
        original_name=file.filename,
        file_type=file_type,
        file_size=len(content),
        file_path=relative_path
    )


# ================== API Endpoints ==================

@router.post("/{part_id}/upload/drawing", response_model=FileUploadResponse)
async def upload_drawing(
    part_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    도면 파일 업로드

    - **part_id**: 부품 ID
    - **file**: 도면 파일 (PDF, DWG, DXF, STEP, STP, IGS)
    """
    # 부품 확인
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="부품을 찾을 수 없습니다")

    # 기존 파일 삭제 (있으면)
    if part.drawing_file:
        old_path = settings.uploads_path / part.drawing_file
        if old_path.exists():
            os.remove(old_path)

    # 파일 저장
    file_info = await save_upload_file(file, part_id, "drawing")

    # DB 업데이트
    part.file_name = file_info.original_name
    part.drawing_file = file_info.file_path
    db.commit()

    return FileUploadResponse(
        success=True,
        message=f"도면 파일이 업로드되었습니다: {file_info.original_name}",
        file_info=file_info
    )


@router.post("/{part_id}/upload/photo", response_model=FileUploadResponse)
async def upload_photo(
    part_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    사진 파일 업로드

    - **part_id**: 부품 ID
    - **file**: 이미지 파일 (JPG, PNG, GIF, WEBP)
    """
    # 부품 확인
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="부품을 찾을 수 없습니다")

    # 기존 파일 삭제 (있으면)
    if part.photo_file:
        old_path = settings.uploads_path / part.photo_file
        if old_path.exists():
            os.remove(old_path)

    # 파일 저장
    file_info = await save_upload_file(file, part_id, "photo")

    # DB 업데이트
    part.photo_file = file_info.file_path
    db.commit()

    return FileUploadResponse(
        success=True,
        message=f"사진 파일이 업로드되었습니다: {file_info.original_name}",
        file_info=file_info
    )


@router.post("/{part_id}/upload/document", response_model=FileUploadResponse)
async def upload_document(
    part_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    문서 파일 업로드 (다중 파일 지원)

    - **part_id**: 부품 ID
    - **file**: 문서 파일 (PDF, DOC, DOCX, XLS, XLSX, HWP)
    """
    # 부품 확인
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="부품을 찾을 수 없습니다")

    # 파일 저장
    file_info = await save_upload_file(file, part_id, "document")

    # DB 업데이트 (JSON 배열에 추가)
    # SQLAlchemy는 JSON 필드의 in-place 변경을 감지하지 못하므로 새 리스트를 할당
    existing_docs = list(part.document_files or [])
    existing_docs.append({
        "file_name": file_info.file_name,
        "original_name": file_info.original_name,
        "file_path": file_info.file_path,
        "file_size": file_info.file_size,
        "uploaded_at": file_info.uploaded_at
    })
    part.document_files = existing_docs  # 새 리스트 할당으로 변경 감지

    # 변경 감지를 위해 명시적으로 표시
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(part, "document_files")

    db.commit()

    return FileUploadResponse(
        success=True,
        message=f"문서 파일이 업로드되었습니다: {file_info.original_name}",
        file_info=file_info
    )


@router.get("/{part_id}/files", response_model=PartFilesResponse)
async def get_part_files(part_id: int, db: Session = Depends(get_db)):
    """
    부품 첨부파일 목록 조회

    - **part_id**: 부품 ID
    """
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="부품을 찾을 수 없습니다")

    response = PartFilesResponse(
        part_id=part.id,
        part_number=part.part_number_display or part.part_number,
        drawing=None,
        photo=None,
        documents=[]
    )

    # 도면 파일
    if part.drawing_file:
        full_path = settings.uploads_path / part.drawing_file
        if full_path.exists():
            response.drawing = build_file_info(
                file_name=full_path.name,
                original_name=part.file_name or full_path.name,
                file_type="drawing",
                file_size=full_path.stat().st_size,
                file_path=part.drawing_file
            )

    # 사진 파일
    if part.photo_file:
        full_path = settings.uploads_path / part.photo_file
        if full_path.exists():
            response.photo = build_file_info(
                file_name=full_path.name,
                original_name=full_path.name.split("_", 1)[1] if "_" in full_path.name else full_path.name,
                file_type="photo",
                file_size=full_path.stat().st_size,
                file_path=part.photo_file
            )

    # 문서 파일들
    if part.document_files:
        for doc in part.document_files:
            full_path = settings.uploads_path / doc.get("file_path", "")
            if full_path.exists():
                response.documents.append(build_file_info(
                    file_name=doc.get("file_name", ""),
                    original_name=doc.get("original_name", ""),
                    file_type="document",
                    file_size=doc.get("file_size", 0),
                    file_path=doc.get("file_path", ""),
                    uploaded_at=doc.get("uploaded_at")
                ))

    return response


@router.delete("/{part_id}/files/{file_type}", response_model=FileDeleteResponse)
async def delete_part_file(
    part_id: int,
    file_type: str,
    file_index: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    부품 파일 삭제

    - **part_id**: 부품 ID
    - **file_type**: 파일 타입 (drawing, photo, document)
    - **file_index**: document 타입일 때 삭제할 파일 인덱스 (0부터 시작)
    """
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="부품을 찾을 수 없습니다")

    file_path_to_delete = None

    if file_type == "drawing":
        if part.drawing_file:
            file_path_to_delete = settings.uploads_path / part.drawing_file
            part.file_name = None
            part.drawing_file = None

    elif file_type == "photo":
        if part.photo_file:
            file_path_to_delete = settings.uploads_path / part.photo_file
            part.photo_file = None

    elif file_type == "document":
        if file_index is None:
            raise HTTPException(status_code=400, detail="document 타입은 file_index가 필요합니다")

        docs = list(part.document_files or [])
        if 0 <= file_index < len(docs):
            doc = docs.pop(file_index)
            file_path_to_delete = settings.uploads_path / doc.get("file_path", "")
            part.document_files = docs
            # 변경 감지를 위해 명시적으로 표시
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(part, "document_files")
        else:
            raise HTTPException(status_code=404, detail="해당 인덱스의 문서를 찾을 수 없습니다")

    else:
        raise HTTPException(status_code=400, detail="잘못된 파일 타입입니다")

    # 실제 파일 삭제
    if file_path_to_delete and file_path_to_delete.exists():
        try:
            os.remove(file_path_to_delete)
        except Exception:
            pass  # 파일 삭제 실패해도 DB는 업데이트

    db.commit()

    return FileDeleteResponse(success=True, message="파일이 삭제되었습니다")


# ================== 파일 다운로드/미리보기 API ==================
# 별도 라우터로 분리 (prefix 없음)

files_router = APIRouter(prefix="/files", tags=["파일 다운로드"])


@files_router.get("/{file_path:path}")
async def download_or_preview_file(file_path: str, preview: bool = False):
    """
    파일 다운로드 또는 미리보기

    - **file_path**: 파일 경로 (예: parts/1/drawings/uuid_filename.pdf)
    - **preview**: true이면 브라우저에서 직접 표시, false이면 다운로드
    """
    full_path = settings.uploads_path / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    # 보안: 상위 디렉토리 접근 방지
    try:
        full_path.resolve().relative_to(settings.uploads_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="접근이 거부되었습니다")

    # MIME 타입 결정
    ext = full_path.suffix.lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".dwg": "application/acad",
        ".dxf": "application/dxf",
        ".step": "application/step",
        ".stp": "application/step",
        ".igs": "application/iges",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".hwp": "application/x-hwp",
    }
    media_type = mime_types.get(ext, "application/octet-stream")

    # 원본 파일명 추출 (UUID_ 이후 부분)
    original_name = full_path.name
    if "_" in original_name:
        original_name = original_name.split("_", 1)[1]

    # 보안 헤더: MIME 스니핑 차단 + 인라인 실행 방지(sandbox)
    safe_headers = {"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"}
    # 보안: SVG 는 <script> 내장 가능 → 인라인 제공 금지(저장형 XSS 방지). PDF/이미지만 인라인 허용.
    if preview and ext in [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        # 미리보기 모드: 브라우저에서 직접 표시
        return FileResponse(path=full_path, media_type=media_type, headers=safe_headers)
    else:
        # 다운로드 모드(SVG·기타 모두 첨부 다운로드로 강제)
        return FileResponse(
            path=full_path,
            media_type=media_type,
            filename=original_name,
            headers=safe_headers,
        )


# ================== 거래처 파일 업로드 API ==================

partner_files_router = APIRouter(prefix="/partners", tags=["거래처 파일 관리"])


class PartnerFilesResponse(BaseModel):
    """거래처 첨부파일 목록 응답"""
    partner_id: int
    partner_code: str
    documents: List[FileInfo] = []


def get_partner_upload_dir(partner_id: int) -> Path:
    """거래처별 파일 저장 디렉토리 반환"""
    return settings.uploads_path / "partners" / str(partner_id) / "documents"


def get_partner_relative_path(partner_id: int, file_name: str) -> str:
    """거래처 파일 DB 저장용 상대 경로 반환"""
    return f"partners/{partner_id}/documents/{file_name}"


async def save_partner_upload_file(
    file: UploadFile,
    partner_id: int
) -> FileInfo:
    """거래처 파일 저장 및 정보 반환"""
    # 파일 확장자 검증 (document 타입)
    if not validate_file_extension(file.filename, "document"):
        allowed = settings.get_allowed_extensions("document")
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(allowed)}"
        )

    # 파일 내용 읽기
    content = await file.read()

    # 파일 크기 검증
    if not validate_file_size(len(content)):
        max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. 최대 {max_mb}MB까지 허용됩니다."
        )

    # 저장 디렉토리 생성
    save_dir = get_partner_upload_dir(partner_id)
    save_dir.mkdir(parents=True, exist_ok=True)

    # 고유 파일명 생성
    new_file_name = generate_file_name(file.filename)
    file_path = save_dir / new_file_name

    # 파일 저장
    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")

    # 상대 경로 (DB 저장용)
    relative_path = get_partner_relative_path(partner_id, new_file_name)

    return build_file_info(
        file_name=new_file_name,
        original_name=file.filename,
        file_type="document",
        file_size=len(content),
        file_path=relative_path
    )


@partner_files_router.post("/{partner_id}/upload/document", response_model=FileUploadResponse)
async def upload_partner_document(
    partner_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    거래처 문서 파일 업로드 (다중 파일 지원)

    - **partner_id**: 거래처 ID
    - **file**: 문서 파일 (PDF, DOC, DOCX, XLS, XLSX, HWP, JPG, PNG)

    사업자등록증, 계약서, 협약서 등을 업로드할 수 있습니다.
    """
    # 거래처 확인
    partner = db.query(BusinessPartner).filter(BusinessPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다")

    # 파일 저장
    file_info = await save_partner_upload_file(file, partner_id)

    # DB 업데이트 (JSON 배열에 추가)
    existing_docs = list(partner.document_files or [])
    existing_docs.append({
        "file_name": file_info.file_name,
        "original_name": file_info.original_name,
        "file_path": file_info.file_path,
        "file_size": file_info.file_size,
        "uploaded_at": file_info.uploaded_at
    })
    partner.document_files = existing_docs

    # 변경 감지를 위해 명시적으로 표시
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(partner, "document_files")

    db.commit()

    return FileUploadResponse(
        success=True,
        message=f"문서 파일이 업로드되었습니다: {file_info.original_name}",
        file_info=file_info
    )


@partner_files_router.get("/{partner_id}/files", response_model=PartnerFilesResponse)
async def get_partner_files(partner_id: int, db: Session = Depends(get_db)):
    """
    거래처 첨부파일 목록 조회

    - **partner_id**: 거래처 ID
    """
    partner = db.query(BusinessPartner).filter(BusinessPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다")

    response = PartnerFilesResponse(
        partner_id=partner.id,
        partner_code=partner.partner_code,
        documents=[]
    )

    # 문서 파일들
    if partner.document_files:
        for doc in partner.document_files:
            full_path = settings.uploads_path / doc.get("file_path", "")
            if full_path.exists():
                response.documents.append(build_file_info(
                    file_name=doc.get("file_name", ""),
                    original_name=doc.get("original_name", ""),
                    file_type="document",
                    file_size=doc.get("file_size", 0),
                    file_path=doc.get("file_path", ""),
                    uploaded_at=doc.get("uploaded_at")
                ))

    return response


@partner_files_router.delete("/{partner_id}/files/{file_index}", response_model=FileDeleteResponse)
async def delete_partner_file(
    partner_id: int,
    file_index: int,
    db: Session = Depends(get_db)
):
    """
    거래처 파일 삭제

    - **partner_id**: 거래처 ID
    - **file_index**: 삭제할 파일 인덱스 (0부터 시작)
    """
    partner = db.query(BusinessPartner).filter(BusinessPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다")

    docs = list(partner.document_files or [])
    if not (0 <= file_index < len(docs)):
        raise HTTPException(status_code=404, detail="해당 인덱스의 문서를 찾을 수 없습니다")

    doc = docs.pop(file_index)
    file_path_to_delete = settings.uploads_path / doc.get("file_path", "")

    partner.document_files = docs

    # 변경 감지를 위해 명시적으로 표시
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(partner, "document_files")

    # 실제 파일 삭제
    if file_path_to_delete.exists():
        try:
            os.remove(file_path_to_delete)
        except Exception:
            pass  # 파일 삭제 실패해도 DB는 업데이트

    db.commit()

    return FileDeleteResponse(success=True, message="파일이 삭제되었습니다")
