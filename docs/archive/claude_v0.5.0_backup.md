# Claude 개발 가이드 - X-Manager 프로젝트

**작성일**: 2026-01-08
**최종 업데이트**: 2026-01-09
**프로젝트**: X-Manager v0.5.0
**목적**: 개발 일관성 유지 및 AI 어시스턴트 협업 가이드

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [아키텍처 패턴](#아키텍처-패턴)
3. [코딩 규칙](#코딩-규칙)
4. [데이터베이스 설계 원칙](#데이터베이스-설계-원칙)
5. [API 설계 패턴](#api-설계-패턴)
6. [파일 업로드 패턴](#파일-업로드-패턴)
7. [프론트엔드 패턴](#프론트엔드-패턴)
8. [개발 워크플로우](#개발-워크플로우)
9. [문제 해결 가이드](#문제-해결-가이드)

---

## 프로젝트 개요

### 목적
X-Manager는 제조업 ERP 시스템으로, 부품 관리, BOM 관리, 원가 계산, 승인 프로세스를 통합 관리하는 웹 기반 애플리케이션입니다.

### 기술 스택

**백엔드**
- Python 3.12.10
- FastAPI 0.110.0 (비동기 REST API)
- SQLAlchemy 2.0.27 (ORM)
- Pydantic 2.6.1 (데이터 검증)
- Alembic 1.13.1 (마이그레이션)
- PostgreSQL 17.7 (데이터베이스)
- aiofiles (비동기 파일 처리)

**프론트엔드**
- TypeScript (타입 안정성)
- Vue.js 3.4+ (Composition API)
- Vite 7.3.1 (빌드 도구)
- Tailwind CSS 3.4.0 (스타일링)
- Pinia 2.1+ (상태 관리)
- Vue Router 4+ (라우팅)
- Axios (HTTP 클라이언트)

### 프로젝트 구조
```
X-MANAGER_R0.1/
├── backend/                # FastAPI 백엔드
│   ├── app/
│   │   ├── api/v1/        # API 라우터
│   │   │   ├── code_master.py
│   │   │   ├── parts.py
│   │   │   ├── business_partner.py
│   │   │   └── files.py   # 파일 업로드 API
│   │   ├── core/          # 설정, DB 연결
│   │   ├── models/        # SQLAlchemy 모델
│   │   └── schemas/       # Pydantic 스키마
│   ├── alembic/           # DB 마이그레이션
│   └── seeds/             # 초기 데이터
├── frontend/              # Vue.js 프론트엔드
│   └── src/
│       ├── api/           # API 서비스
│       ├── components/    # 재사용 컴포넌트
│       │   ├── FileUpload.vue
│       │   ├── FileList.vue
│       │   └── PartnerDetailModal.vue
│       ├── views/         # 페이지 컴포넌트
│       ├── router/        # 라우팅
│       └── stores/        # Pinia 스토어
├── storage/               # 파일 저장소 (NEW)
│   └── uploads/
│       ├── parts/
│       └── partners/
└── docs/                  # 문서
```

---

## 아키텍처 패턴

### 백엔드 아키텍처

#### 1. 레이어 분리
```
Controller (API Router)
    ↓
Service (비즈니스 로직 - 추후 구현)
    ↓
Repository (데이터 접근 - 현재 직접 구현)
    ↓
Model (SQLAlchemy)
```

**현재 상태**: 간단한 CRUD이므로 Service 레이어 없이 API Router에서 직접 DB 접근

**향후 계획**: 복잡한 비즈니스 로직 발생 시 Service 레이어 도입

#### 2. 의존성 주입
```python
from fastapi import Depends
from app.core.database import get_db

@router.get("/items")
def get_items(db: Session = Depends(get_db)):
    # db 세션은 FastAPI가 자동 관리
    return db.query(Model).all()
```

#### 3. 설정 관리
```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
```

### 프론트엔드 아키텍처

#### 1. 컴포넌트 구조
```
Pages (views/)
    ↓
Feature Components (components/)
    ↓
Base Components (공통 UI - 추후 구현)
```

#### 2. API 서비스 분리
```typescript
// src/api/codeMaster.ts
export const majorCategoryApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/major-categories'),
  create: (data: CodeMasterCreate) => apiClient.post('/codes/major-categories', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put(`/codes/major-categories/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/major-categories/${id}`)
}
```

#### 3. 상태 관리 (Pinia)
**현재**: 아직 사용하지 않음 (컴포넌트 로컬 상태 사용)
**향후**: 전역 상태 필요 시 Pinia 스토어 구현

---

## 코딩 규칙

### 백엔드 규칙

#### 1. 파일 및 모듈 명명
```
models/code_master.py     # 스네이크 케이스
schemas/code_master.py
api/v1/code_master.py
```

#### 2. 클래스 및 함수 명명
```python
# 클래스: PascalCase
class MajorCategory(Base):
    pass

# 함수: 스네이크 케이스
def get_major_categories(db: Session):
    pass

# 상수: 대문자 스네이크 케이스
MAX_PAGE_SIZE = 100
```

#### 3. 모델 정의 패턴
```python
class BaseCodeMaster(Base):
    """모든 코드 마스터 테이블의 공통 구조"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name_ko = Column(String(50), nullable=False)
    name_en = Column(String(50))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### 4. 스키마 정의 패턴
```python
# Base: 공통 필드
class MajorCategoryBase(BaseModel):
    code: str = Field(..., max_length=10)
    name_ko: str = Field(..., max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

# Create: 생성 시 필요한 필드
class MajorCategoryCreate(MajorCategoryBase):
    pass

# Update: 수정 시 모든 필드 선택적
class MajorCategoryUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

# Response: 응답 시 반환되는 필드 (DB 필드 포함)
class MajorCategoryResponse(MajorCategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # SQLAlchemy 모델 → Pydantic
```

#### 5. API 엔드포인트 패턴
```python
router = APIRouter(prefix="/codes", tags=["Code Master"])

# 목록 조회: GET /codes/major-categories
@router.get("/major-categories", response_model=List[MajorCategoryResponse])
def get_major_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    categories = db.query(MajorCategory)\
        .order_by(MajorCategory.sort_order)\
        .offset(skip)\
        .limit(limit)\
        .all()
    return categories

# 단건 조회: GET /codes/major-categories/{id}
@router.get("/major-categories/{id}", response_model=MajorCategoryResponse)
def get_major_category(id: int, db: Session = Depends(get_db)):
    category = db.query(MajorCategory).filter(MajorCategory.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다")
    return category

# 생성: POST /codes/major-categories
@router.post("/major-categories", response_model=MajorCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_major_category(category: MajorCategoryCreate, db: Session = Depends(get_db)):
    # 중복 체크
    existing = db.query(MajorCategory).filter(MajorCategory.code == category.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 코드입니다")

    db_category = MajorCategory(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# 수정: PUT /codes/major-categories/{id}
@router.put("/major-categories/{id}", response_model=MajorCategoryResponse)
def update_major_category(
    id: int,
    category: MajorCategoryUpdate,
    db: Session = Depends(get_db)
):
    db_category = db.query(MajorCategory).filter(MajorCategory.id == id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다")

    # 제공된 필드만 업데이트
    for key, value in category.model_dump(exclude_unset=True).items():
        setattr(db_category, key, value)

    db.commit()
    db.refresh(db_category)
    return db_category

# 삭제: DELETE /codes/major-categories/{id}
@router.delete("/major-categories/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_major_category(id: int, db: Session = Depends(get_db)):
    db_category = db.query(MajorCategory).filter(MajorCategory.id == id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다")

    db.delete(db_category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

### 프론트엔드 규칙

#### 1. 파일 명명
```
components/CodeMasterModal.vue    # PascalCase
views/CodeMasterView.vue
api/codeMaster.ts                # camelCase
```

#### 2. TypeScript 인터페이스
```typescript
export interface CodeMaster {
  id: number
  code: string
  name_ko: string
  name_en?: string
  description?: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface CodeMasterCreate {
  code: string
  name_ko: string
  name_en?: string
  description?: string
  sort_order?: number
  is_active?: boolean
}
```

#### 3. Vue 컴포넌트 패턴 (Composition API)
```vue
<template>
  <!-- 템플릿 -->
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { CodeMaster } from '@/api/codeMaster'

// Props 정의
interface Props {
  show: boolean
  isEdit?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isEdit: false
})

// Emits 정의
const emit = defineEmits<{
  close: []
  submit: [data: CodeMasterCreate]
}>()

// 반응형 상태
const items = ref<CodeMaster[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Computed
const filteredItems = computed(() => {
  return items.value.filter(item => item.is_active)
})

// Methods
const loadData = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await majorCategoryApi.getAll()
    items.value = response.data
  } catch (err) {
    error.value = '데이터를 불러오는데 실패했습니다'
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* 스타일 */
</style>
```

#### 4. API 서비스 패턴
```typescript
import apiClient from './client'

export const majorCategoryApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/major-categories'),

  getById: (id: number) =>
    apiClient.get<CodeMaster>(`/codes/major-categories/${id}`),

  create: (data: CodeMasterCreate) =>
    apiClient.post<CodeMaster>('/codes/major-categories', data),

  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/major-categories/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/codes/major-categories/${id}`)
}
```

---

## 데이터베이스 설계 원칙

### 1. 코드 마스터 테이블 패턴

모든 코드 마스터 테이블은 동일한 구조를 따릅니다:

```python
class BaseCodeMaster(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name_ko = Column(String(50), nullable=False)
    name_en = Column(String(50))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**코드 마스터 테이블 (10개)**:
- `major_category` (대분류)
- `middle_category` (중분류)
- `minor_category` (소분류)
- `sub_category` (세분류)
- `item_code` (품목코드)
- `material` (재질)
- `treatment` (후처리)
- `level` (레벨)
- `procurement_type` (조달구분)
- `unit` (단위)

### 2. 마스터 데이터 테이블 패턴

```python
class Part(Base):
    __tablename__ = "parts"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # 고유 식별자
    part_number = Column(String(20), unique=True, nullable=False, index=True)

    # 기본 정보
    part_name = Column(String(200), nullable=False)
    description = Column(Text)

    # 코드 마스터 외래키
    major_category_id = Column(Integer, ForeignKey("major_category.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("material.id"))
    # ... 기타 FK

    # 관계 정의
    major_category = relationship("MajorCategory")
    material = relationship("Material")
    # ... 기타 관계

    # 감사 필드
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 3. 마이그레이션 규칙

```bash
# 1. 모델 변경 후 마이그레이션 생성
cd backend
.\venv\Scripts\alembic revision --autogenerate -m "설명적인 메시지"

# 2. 마이그레이션 검토
# alembic/versions/xxx_설명.py 파일 확인

# 3. 마이그레이션 적용
.\venv\Scripts\alembic upgrade head

# 4. 롤백 (필요시)
.\venv\Scripts\alembic downgrade -1
```

### 4. 초기 데이터 관리

```sql
-- seeds/01_initial_codes.sql
INSERT INTO major_category (code, name_ko, name_en, description, sort_order, is_active)
VALUES
  ('D', '개발품', 'Developed Part', '자체 개발 부품', 1, true),
  ('S', '표준품', 'Standard Part', '표준 규격 부품', 2, true);
```

실행:
```bash
psql -U postgres -d xmanager -f seeds/01_initial_codes.sql
```

---

## API 설계 패턴

### REST API 규칙

#### 1. URL 구조
```
/api/v1/{resource}/{action}

예시:
GET    /api/v1/codes/major-categories        # 목록
GET    /api/v1/codes/major-categories/{id}   # 단건
POST   /api/v1/codes/major-categories        # 생성
PUT    /api/v1/codes/major-categories/{id}   # 수정
DELETE /api/v1/codes/major-categories/{id}   # 삭제
```

#### 2. HTTP 상태 코드
```python
200 OK                    # 조회, 수정 성공
201 Created               # 생성 성공
204 No Content            # 삭제 성공
400 Bad Request           # 잘못된 요청
404 Not Found             # 리소스 없음
500 Internal Server Error # 서버 오류
```

#### 3. 에러 응답 형식
```python
raise HTTPException(
    status_code=400,
    detail="이미 존재하는 코드입니다"
)

# 응답:
{
  "detail": "이미 존재하는 코드입니다"
}
```

#### 4. 페이지네이션
```python
@router.get("/items")
def get_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(Model).offset(skip).limit(limit).all()
    return items
```

---

## 파일 업로드 패턴

### 백엔드 파일 처리

#### 1. 파일 저장 구조
```
storage/uploads/
├── parts/{part_id}/
│   ├── drawings/       # 도면 파일
│   ├── photos/         # 사진 파일
│   └── documents/      # 문서 파일
└── partners/{partner_id}/
    └── documents/      # 거래처 문서
```

#### 2. 파일 정보 모델
```python
from pydantic import BaseModel
from datetime import datetime

class FileInfo(BaseModel):
    file_name: str          # UUID 포함 저장 파일명
    original_name: str      # 원본 파일명
    file_type: str          # drawing, photo, document
    file_size: int          # 바이트 단위
    file_path: str          # 상대 경로
    uploaded_at: str        # ISO 8601 형식
    download_url: str       # 다운로드 URL
    preview_url: str        # 미리보기 URL
```

#### 3. 파일 업로드 API 패턴
```python
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException
from uuid import uuid4

router = APIRouter(prefix="/parts", tags=["파일 관리"])

@router.post("/{part_id}/upload/{file_type}")
async def upload_file(
    part_id: int,
    file_type: str,  # drawing, photo, document
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. 부품 존재 확인
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="부품을 찾을 수 없습니다")

    # 2. 파일 확장자 검증
    allowed_extensions = {"drawing": ["pdf", "dwg", "dxf"],
                         "photo": ["jpg", "png", "gif"],
                         "document": ["pdf", "doc", "docx", "xls", "xlsx"]}

    ext = file.filename.split(".")[-1].lower()
    if ext not in allowed_extensions.get(file_type, []):
        raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다")

    # 3. 고유 파일명 생성
    unique_name = f"{uuid4().hex[:8]}_{file.filename}"

    # 4. 저장 경로 생성
    save_dir = Path(f"storage/uploads/parts/{part_id}/{file_type}s")
    save_dir.mkdir(parents=True, exist_ok=True)

    # 5. 비동기 파일 저장
    content = await file.read()
    async with aiofiles.open(save_dir / unique_name, "wb") as f:
        await f.write(content)

    # 6. DB 업데이트 (JSON 필드)
    file_info = {
        "file_name": unique_name,
        "original_name": file.filename,
        "file_path": f"parts/{part_id}/{file_type}s/{unique_name}",
        "file_size": len(content),
        "uploaded_at": datetime.now().isoformat()
    }

    # JSON 필드 업데이트 (flag_modified 필수!)
    from sqlalchemy.orm.attributes import flag_modified

    files_field = f"{file_type}_files"  # drawing_files, photo_files, document_files
    existing = getattr(part, files_field) or []
    existing.append(file_info)
    setattr(part, files_field, existing)
    flag_modified(part, files_field)  # 중요: JSON 변경 감지용

    db.commit()
    return {"success": True, "file_info": file_info}
```

#### 4. SQLAlchemy JSON 필드 변경 감지
```python
# 중요: JSON/ARRAY 필드 업데이트 시 반드시 필요
from sqlalchemy.orm.attributes import flag_modified

# JSON 필드 업데이트 후
part.document_files = new_files_list
flag_modified(part, "document_files")  # 변경 감지를 위해 필수
db.commit()
```

#### 5. 파일 다운로드/미리보기 패턴
```python
from fastapi.responses import FileResponse

@router.get("/files/{file_path:path}")
async def download_file(file_path: str, preview: bool = False):
    full_path = Path("storage/uploads") / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    # MIME 타입 결정
    ext = full_path.suffix.lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".png": "image/png",
        # ...
    }
    media_type = mime_types.get(ext, "application/octet-stream")

    if preview:
        # 미리보기: Content-Disposition 없이 반환
        return FileResponse(path=full_path, media_type=media_type)
    else:
        # 다운로드: 파일명 포함
        original_name = full_path.name.split("_", 1)[-1]  # UUID 제거
        return FileResponse(
            path=full_path,
            media_type=media_type,
            filename=original_name
        )
```

### 프론트엔드 파일 처리

#### 1. 파일 업로드 컴포넌트 패턴
```vue
<template>
  <div
    class="border-2 border-dashed rounded-lg p-6"
    @dragover.prevent="isDragging = true"
    @dragleave="isDragging = false"
    @drop.prevent="handleDrop"
    :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'"
  >
    <input
      type="file"
      ref="fileInput"
      class="hidden"
      :accept="acceptTypes"
      @change="handleFileSelect"
    />
    <button @click="$refs.fileInput.click()">파일 선택</button>

    <div v-if="isUploading">
      <div class="h-2 bg-gray-200 rounded">
        <div class="h-full bg-blue-500 rounded" :style="{width: progress + '%'}"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  acceptTypes?: string
  maxSize?: number  // MB
}>()

const emit = defineEmits<{
  upload: [file: File]
  error: [message: string]
}>()

const isDragging = ref(false)
const isUploading = ref(false)
const progress = ref(0)

const handleDrop = (e: DragEvent) => {
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files?.length) {
    validateAndUpload(files[0])
  }
}

const validateAndUpload = (file: File) => {
  // 크기 검증
  if (props.maxSize && file.size > props.maxSize * 1024 * 1024) {
    emit('error', `파일 크기는 ${props.maxSize}MB 이하여야 합니다`)
    return
  }
  emit('upload', file)
}
</script>
```

#### 2. 파일 목록 표시 패턴
```vue
<template>
  <div class="space-y-2">
    <div
      v-for="(file, index) in files"
      :key="index"
      class="flex items-center justify-between p-3 bg-gray-50 rounded"
    >
      <div class="flex items-center gap-3">
        <!-- 파일 아이콘 (타입별) -->
        <svg v-if="isPdf(file.original_name)" class="w-8 h-8 text-red-500">...</svg>
        <svg v-else-if="isImage(file.original_name)" class="w-8 h-8 text-green-500">...</svg>

        <div>
          <p class="font-medium">{{ file.original_name }}</p>
          <p class="text-xs text-gray-500">
            {{ formatFileSize(file.file_size) }} · {{ formatDate(file.uploaded_at) }}
          </p>
        </div>
      </div>

      <div class="flex gap-2">
        <a :href="getPreviewUrl(file.file_path)" target="_blank" title="미리보기">👁</a>
        <a :href="getDownloadUrl(file.file_path)" download title="다운로드">⬇</a>
        <button @click="$emit('delete', index)" title="삭제">🗑</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const API_BASE = 'http://localhost:8000/api/v1'

const getDownloadUrl = (path: string) => `${API_BASE}/files/${path}`
const getPreviewUrl = (path: string) => `${API_BASE}/files/${path}?preview=true`

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const isPdf = (name: string) => name.toLowerCase().endsWith('.pdf')
const isImage = (name: string) => /\.(jpg|jpeg|png|gif|webp)$/i.test(name)
</script>
```

#### 3. API 서비스 파일 업로드 패턴
```typescript
// src/api/files.ts
import apiClient from './client'

export const fileApi = {
  // 부품 파일 업로드
  uploadPartFile: (partId: number, fileType: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/parts/${partId}/upload/${fileType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        const percent = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))
        console.log(`Upload: ${percent}%`)
      }
    })
  },

  // 거래처 문서 업로드
  uploadPartnerDocument: (partnerId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/partners/${partnerId}/upload/document`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 파일 삭제
  deletePartFile: (partId: number, fileType: string, fileIndex: number) => {
    return apiClient.delete(`/parts/${partId}/files/${fileType}/${fileIndex}`)
  }
}
```

---

## 프론트엔드 패턴

### 1. 토스트 알림 패턴

```typescript
const toast = ref<{
  show: boolean
  message: string
  type: 'success' | 'error'
}>({
  show: false,
  message: '',
  type: 'success'
})

const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 3000)
}
```

### 2. 모달 패턴

```vue
<!-- 모달 컴포넌트 -->
<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="show" @click.self="$emit('close')">
        <!-- 모달 내용 -->
      </div>
    </Transition>
  </Teleport>
</template>

<!-- 사용하는 곳 -->
<CodeMasterModal
  :show="showModal"
  :isEdit="isEditMode"
  :initialData="selectedItem"
  @close="closeModal"
  @submit="handleSubmit"
/>
```

### 3. 로딩/에러 처리

```vue
<template>
  <div v-if="loading">로딩 중...</div>
  <div v-else-if="error">{{ error }}</div>
  <div v-else>
    <!-- 데이터 표시 -->
  </div>
</template>

<script setup lang="ts">
const loading = ref(false)
const error = ref<string | null>(null)

const loadData = async () => {
  loading.value = true
  error.value = null
  try {
    // API 호출
  } catch (err) {
    error.value = '오류 메시지'
  } finally {
    loading.value = false
  }
}
</script>
```

---

## 개발 워크플로우

### 새로운 기능 추가 시 워크플로우

#### 1단계: 데이터베이스 모델 정의
```python
# backend/app/models/new_feature.py
from app.core.database import Base

class NewFeature(Base):
    __tablename__ = "new_features"
    # 필드 정의
```

#### 2단계: 마이그레이션
```bash
cd backend
.\venv\Scripts\alembic revision --autogenerate -m "Add new_features table"
.\venv\Scripts\alembic upgrade head
```

#### 3단계: Pydantic 스키마
```python
# backend/app/schemas/new_feature.py
from pydantic import BaseModel

class NewFeatureBase(BaseModel):
    # 필드 정의

class NewFeatureCreate(NewFeatureBase):
    pass

class NewFeatureResponse(NewFeatureBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
```

#### 4단계: API 라우터
```python
# backend/app/api/v1/new_feature.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/new-features", tags=["New Feature"])

@router.get("/", response_model=List[NewFeatureResponse])
def get_new_features(db: Session = Depends(get_db)):
    # 구현
```

#### 5단계: 라우터 등록
```python
# backend/app/main.py
from app.api.v1 import new_feature

app.include_router(new_feature.router, prefix="/api/v1")
```

#### 6단계: 프론트엔드 API 서비스
```typescript
// frontend/src/api/newFeature.ts
export interface NewFeature {
  // 인터페이스 정의
}

export const newFeatureApi = {
  getAll: () => apiClient.get<NewFeature[]>('/new-features'),
  // CRUD 메서드
}
```

#### 7단계: Vue 컴포넌트
```vue
<!-- frontend/src/views/NewFeatureView.vue -->
<template>
  <!-- UI 구현 -->
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { newFeatureApi } from '@/api/newFeature'
// 구현
</script>
```

#### 8단계: 라우터 등록
```typescript
// frontend/src/router/index.ts
{
  path: '/new-features',
  name: 'new-features',
  component: () => import('../views/NewFeatureView.vue')
}
```

---

## 문제 해결 가이드

### 백엔드 문제

#### 1. Alembic 마이그레이션 오류
```
문제: UnicodeDecodeError 발생
원인: alembic.ini나 env.py에 한글 주석
해결: 주석을 영문으로 변경
```

#### 2. SQLAlchemy 관계 오류
```
문제: relationship backref 충돌
원인: 양방향 관계 설정 시 중복
해결: back_populates 사용
```

#### 3. Pydantic 검증 오류
```
문제: from_attributes 에러
원인: SQLAlchemy 모델 → Pydantic 변환 설정 누락
해결: Config 클래스에 from_attributes = True 추가
```

### 프론트엔드 문제

#### 1. Tailwind CSS 디렉티브 오류
```
문제: @tailwind 디렉티브 인식 안 됨
원인: Tailwind v4 자동 설치
해결: v3.4로 다운그레이드
```

#### 2. CORS 오류
```
문제: 브라우저에서 API 호출 차단
원인: FastAPI CORS 미설정
해결: main.py에 CORSMiddleware 추가
```

#### 3. Axios 401 오류
```
문제: 인증 토큰 없음
원인: 헤더에 토큰 미포함
해결: client.ts 인터셉터에서 토큰 자동 추가 (추후 구현)
```

### 환경 문제

#### 1. 가상환경 활성화 안 됨
```bash
# PowerShell 실행 정책 오류
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 활성화
.\venv\Scripts\activate
```

#### 2. PostgreSQL 연결 실패
```
문제: psycopg2.OperationalError
원인: 잘못된 비밀번호 또는 DB 없음
해결: .env 확인, DB 생성 확인
```

#### 3. Node.js 패키지 설치 실패
```bash
# 캐시 정리
npm cache clean --force

# 재설치
rm -rf node_modules package-lock.json
npm install
```

---

## 개발 프롬프트 예시

### 새 기능 추가
```
"부품 마스터 관리 기능을 추가해줘. 다음 순서로 작업해줘:
1. parts 테이블에 대한 전체 CRUD API 구현
2. 품번 자동생성 로직 추가
3. 프론트엔드에 부품 등록 및 목록 화면 구현
4. 검색 및 필터링 기능 추가"
```

### 버그 수정
```
"코드 마스터 수정 시 code 필드가 변경되는 문제가 있어.
수정 시에는 code를 변경할 수 없도록 막아줘."
```

### 기능 개선
```
"코드 마스터 목록에 검색 기능을 추가해줘.
- 백엔드: name_ko, name_en에 대한 LIKE 검색
- 프론트엔드: 검색 입력창 추가"
```

---

## 체크리스트

### 새 기능 개발 체크리스트

**백엔드**
- [ ] 모델 정의 (models/)
- [ ] 마이그레이션 생성 및 적용
- [ ] 스키마 정의 (schemas/)
- [ ] API 라우터 구현 (api/v1/)
- [ ] 라우터 등록 (main.py)
- [ ] Swagger 문서 확인 (http://localhost:8000/docs)

**프론트엔드**
- [ ] TypeScript 인터페이스 정의
- [ ] API 서비스 모듈 작성 (api/)
- [ ] 컴포넌트 구현 (components/ 또는 views/)
- [ ] 라우터 등록 (router/index.ts)
- [ ] 브라우저 테스트

**문서화**
- [ ] 개발진행상황.md 업데이트
- [ ] API 변경사항 문서화
- [ ] 주요 결정사항 기록

---

## 참고 자료

### 공식 문서
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
- [Vue.js 3 문서](https://vuejs.org/)
- [Pinia 문서](https://pinia.vuejs.org/)
- [Tailwind CSS 문서](https://tailwindcss.com/)

### 프로젝트 문서
- [개발기획서 v1.3](./X-Manager_개발기획서_v1.3.md)
- [프로젝트 지침](./X-Manager_프로젝트_지침.md)
- [개발진행상황](./00_개발진행상황.md)

---

**최종 업데이트**: 2026-01-09
