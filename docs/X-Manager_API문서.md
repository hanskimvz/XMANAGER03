# X-Manager API 문서

**작성일**: 2026-01-08
**최종 업데이트**: 2026-01-16
**버전**: 0.15.0
**Base URL**: `http://localhost:8000/api/v1`

---

## 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [인증](#인증)
4. [공통 사양](#공통-사양)
5. [코드 마스터 API](#코드-마스터-api)
6. [부품 마스터 API](#부품-마스터-api)
7. [거래처 API](#거래처-api)
8. [파일 관리 API](#파일-관리-api)
9. [에러 코드](#에러-코드)
10. [예제 코드](#예제-코드)

---

## 개요

X-Manager REST API는 제조업 ERP 시스템의 백엔드 서비스를 제공합니다.

### 기술 스택
- **프레임워크**: FastAPI 0.110.0
- **데이터베이스**: PostgreSQL 17.7
- **인증**: JWT (추후 구현)
- **문서**: OpenAPI 3.0 (Swagger)

### API 문서 접속
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 아키텍처

### Service Layer 패턴 (v0.6.0)

X-Manager API는 **Service Layer 패턴**을 적용하여 비즈니스 로직을 분리합니다.

```
┌─────────────────────────────────────────────────┐
│                 API Router Layer                │
│   (parts.py, business_partner.py, code_master.py)│
├─────────────────────────────────────────────────┤
│                 Service Layer                   │
│   (PartService, BusinessPartnerService,         │
│    CodeMasterService)                           │
├─────────────────────────────────────────────────┤
│              Database (SQLAlchemy)              │
└─────────────────────────────────────────────────┘
```

### 서비스 클래스

| 서비스 | 설명 | 주요 기능 |
|--------|------|----------|
| `BaseService` | 제네릭 기본 서비스 | CRUD, 검색, 페이지네이션 |
| `PartService` | 부품 비즈니스 로직 | 품번 자동생성, 승인 상태 관리 |
| `BusinessPartnerService` | 거래처 비즈니스 로직 | 공급업체/고객사 필터링 |
| `CodeMasterService` | 코드 마스터 통합 서비스 | 10개 테이블 동적 라우팅 |

### 커스텀 예외 시스템

| 예외 클래스 | HTTP 코드 | 용도 |
|-------------|-----------|------|
| `AppException` | 400 | 기본 애플리케이션 예외 |
| `NotFoundException` | 404 | 리소스 없음 |
| `AlreadyExistsException` | 400 | 중복 리소스 |
| `ValidationException` | 400 | 유효성 검증 실패 |
| `BusinessRuleException` | 422 | 비즈니스 규칙 위반 |
| `FileException` | 400 | 파일 처리 오류 |

### 의존성 주입

```python
from app.api.v1.deps import get_part_service, handle_service_exception
from app.services.part_service import PartService

@router.get("/{part_id}")
def get_part(
    part_id: int,
    service: PartService = Depends(get_part_service)
):
    try:
        return service.get_or_raise(part_id)
    except AppException as e:
        handle_service_exception(e)
```

---

## 인증

### 현재 상태
**인증 없음** - 개발 초기 단계로 인증이 구현되지 않았습니다.

### 향후 구현 예정
```http
Authorization: Bearer <JWT_TOKEN>
```

---

## 공통 사양

### 요청 헤더
```http
Content-Type: application/json
Accept: application/json
```

### HTTP 상태 코드

| 코드 | 설명 | 사용 예 |
|------|------|---------|
| 200 | OK | 조회, 수정 성공 |
| 201 | Created | 생성 성공 |
| 204 | No Content | 삭제 성공 |
| 400 | Bad Request | 잘못된 요청 (유효성 검증 실패) |
| 401 | Unauthorized | 인증 실패 (추후) |
| 403 | Forbidden | 권한 없음 (추후) |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 422 | Unprocessable Entity | Pydantic 검증 실패 |
| 500 | Internal Server Error | 서버 오류 |

### 페이지네이션

**쿼리 파라미터**:
```
skip: 건너뛸 항목 수 (기본값: 0)
limit: 최대 항목 수 (기본값: 100)
```

---

## 코드 마스터 API

### 공통 데이터 모델

```typescript
interface CodeMaster {
  id: number
  code: string                  // 코드 (최대 10자, 고유값)
  name_ko: string               // 한글명 (최대 50자, 필수)
  name_en?: string              // 영문명 (최대 50자, 선택)
  description?: string          // 설명 (선택)
  sort_order: number            // 정렬순서 (기본값: 0)
  is_active: boolean            // 사용여부 (기본값: true)
  created_at: string            // 생성일시 (ISO 8601)
  updated_at?: string           // 수정일시 (ISO 8601)
}
```

### 엔드포인트 목록

모든 코드 마스터 유형에 대해 동일한 CRUD 패턴이 적용됩니다.

| 유형 | 엔드포인트 프리픽스 |
|------|---------------------|
| 대분류 | `/api/v1/codes/major-categories` |
| 중분류 | `/api/v1/codes/middle-categories` |
| 소분류 | `/api/v1/codes/minor-categories` |
| 세분류 | `/api/v1/codes/sub-categories` |
| 품목코드 | `/api/v1/codes/item-codes` |
| 재질 | `/api/v1/codes/materials` |
| 후처리 | `/api/v1/codes/treatments` |
| 레벨 | `/api/v1/codes/levels` |
| 조달구분 | `/api/v1/codes/procurement-types` |
| 단위 | `/api/v1/codes/units` |

### CRUD 작업

```http
GET    /{prefix}           # 목록 조회
GET    /{prefix}/{id}      # 단건 조회
POST   /{prefix}           # 생성
PUT    /{prefix}/{id}      # 수정
DELETE /{prefix}/{id}      # 삭제
```

---

## 부품 마스터 API

### 데이터 모델

```typescript
interface Part {
  id: number
  part_number: string           // 품번 (자동생성)
  part_number_display: string   // 표시용 품번
  part_name: string             // 부품명
  part_name_en?: string         // 영문 부품명
  description?: string          // 설명

  // 분류 정보 (코드 마스터 참조)
  major_category_id?: number
  middle_category_id?: number
  minor_category_id?: number
  sub_category_id?: number
  item_code_id?: number
  level_id?: number
  material_id?: number
  treatment_id?: number
  procurement_type_id?: number
  unit_id?: number
  supplier_id?: number

  // 사양
  specification?: string

  // 상태
  status: string                // draft, active, obsolete
  approval_status: string       // pending, approved, rejected
  is_active: boolean

  // 파일 (JSON)
  drawing_files?: FileInfo[]
  photo_files?: FileInfo[]
  document_files?: FileInfo[]

  // 감사 필드
  created_at: string
  updated_at?: string
}
```

### 엔드포인트

#### 목록 조회
```http
GET /api/v1/parts
```

**쿼리 파라미터**:
- `keyword` (string): 검색어 (품번, 부품명)
- `level_id` (integer): 레벨 필터
- `status` (string): 상태 필터
- `is_active` (boolean): 활성 상태 필터
- `skip` (integer): 건너뛸 항목 수
- `limit` (integer): 최대 항목 수

#### 단건 조회
```http
GET /api/v1/parts/{id}
```

#### 품번으로 조회
```http
GET /api/v1/parts/by-number/{part_number}
```

#### 생성 (품번 자동생성)
```http
POST /api/v1/parts
```

**요청 본문**:
```json
{
  "part_name": "테스트 부품",
  "major_category_id": 1,
  "middle_category_id": 1,
  "minor_category_id": 1,
  "level_id": 1,
  "material_id": 1,
  "procurement_type_id": 1,
  "unit_id": 1
}
```

#### 수정
```http
PUT /api/v1/parts/{id}
```

#### 삭제
```http
DELETE /api/v1/parts/{id}
```

#### 상태 변경
```http
PATCH /api/v1/parts/{id}/activate      # 활성화
PATCH /api/v1/parts/{id}/deactivate    # 비활성화
PATCH /api/v1/parts/{id}/status        # 상태 변경 (body: {"status": "active"})
PATCH /api/v1/parts/{id}/approval      # 승인 상태 변경 (body: {"approval_status": "approved"})
```

---

## 거래처 API

### 데이터 모델

```typescript
interface BusinessPartner {
  id: number
  partner_code: string          // 거래처 코드 (고유)
  partner_name: string          // 거래처명
  partner_name_en?: string      // 영문 거래처명

  // 사업자 정보
  business_number?: string      // 사업자등록번호
  representative?: string       // 대표자명
  business_type?: string        // 업태
  business_item?: string        // 종목

  // 거래처 유형
  is_supplier: boolean          // 공급업체 여부
  is_customer: boolean          // 고객사 여부

  // 주소
  address?: string
  address_detail?: string
  postal_code?: string

  // 연락처
  tel?: string
  fax?: string
  email?: string
  website?: string

  // 담당자 정보
  manager_name?: string
  manager_position?: string
  manager_tel?: string
  manager_mobile?: string
  manager_email?: string

  // 공급업체용 필드
  payment_terms?: string        // 결제 조건
  delivery_terms?: string       // 납품 조건
  lead_time_days?: number       // 리드타임(일)

  // 고객사용 필드
  credit_limit?: number         // 신용한도
  discount_rate?: number        // 할인율(%)
  sales_rep?: string            // 영업담당자

  // 공통 평가 필드
  credit_rating?: string        // 신용등급
  grade?: string                // 거래처 등급

  // 은행 정보
  bank_name?: string
  bank_account?: string
  bank_holder?: string

  // 기타
  remark?: string               // 비고
  document_files?: FileInfo[]   // 첨부 문서 (JSON)
  is_active: boolean

  // 감사 필드
  created_at: string
  updated_at?: string
}
```

### 엔드포인트

#### 목록 조회
```http
GET /api/v1/partners
```

**쿼리 파라미터**:
- `keyword` (string): 검색어 (코드, 거래처명)
- `is_supplier` (boolean): 공급업체 필터
- `is_customer` (boolean): 고객사 필터
- `is_active` (boolean): 활성 상태 필터
- `skip` (integer): 건너뛸 항목 수
- `limit` (integer): 최대 항목 수

#### 공급업체 목록 조회 (v0.6.0)
```http
GET /api/v1/partners/suppliers
```

**쿼리 파라미터**:
- `is_active` (boolean): 활성 상태 필터 (기본값: true)
- `skip` (integer): 건너뛸 항목 수
- `limit` (integer): 최대 항목 수

#### 고객사 목록 조회 (v0.6.0)
```http
GET /api/v1/partners/customers
```

**쿼리 파라미터**:
- `is_active` (boolean): 활성 상태 필터 (기본값: true)
- `skip` (integer): 건너뛸 항목 수
- `limit` (integer): 최대 항목 수

**응답 예시**:
```json
[
  {
    "id": 1,
    "partner_code": "SUP-001",
    "partner_name": "삼성전자",
    "is_supplier": true,
    "is_customer": false,
    "tel": "02-1234-5678",
    "manager_name": "김철수",
    "is_active": true,
    "created_at": "2026-01-09T10:00:00+09:00"
  }
]
```

#### 단건 조회
```http
GET /api/v1/partners/{id}
```

#### 코드로 조회
```http
GET /api/v1/partners/code/{code}
```

#### 생성
```http
POST /api/v1/partners
```

**요청 본문**:
```json
{
  "partner_code": "SUP-001",
  "partner_name": "삼성전자",
  "partner_name_en": "Samsung Electronics",
  "is_supplier": true,
  "is_customer": false,
  "business_number": "123-45-67890",
  "representative": "이재용",
  "business_type": "제조업",
  "business_item": "전자부품",
  "tel": "02-1234-5678",
  "payment_terms": "월말 30일",
  "delivery_terms": "공장 도착",
  "lead_time_days": 7
}
```

#### 수정
```http
PUT /api/v1/partners/{id}
```

#### 삭제
```http
DELETE /api/v1/partners/{id}
```

#### 상태 변경
```http
PATCH /api/v1/partners/{id}/activate      # 활성화
PATCH /api/v1/partners/{id}/deactivate    # 비활성화
```

---

## 파일 관리 API

### 파일 정보 모델

```typescript
interface FileInfo {
  file_name: string             // 저장된 파일명 (UUID 포함)
  original_name: string         // 원본 파일명
  file_type: string             // drawing, photo, document
  file_size: number             // 파일 크기 (bytes)
  file_path: string             // 상대 경로
  uploaded_at: string           // 업로드 일시
  download_url: string          // 다운로드 URL
  preview_url: string           // 미리보기 URL
}
```

### 파일 타입별 허용 확장자

| 파일 타입 | 허용 확장자 |
|-----------|-------------|
| drawing | PDF, DWG, DXF, STEP, STP, IGS |
| photo | JPG, JPEG, PNG, GIF, WEBP |
| document | PDF, DOC, DOCX, XLS, XLSX, HWP |

### 파일 저장 구조

```
storage/uploads/
├── parts/{part_id}/
│   ├── drawings/
│   ├── photos/
│   └── documents/
└── partners/{partner_id}/
    └── documents/
```

### 부품 파일 API

#### 단일 파일 업로드
```http
POST /api/v1/parts/{part_id}/upload/{file_type}
Content-Type: multipart/form-data
```

**파라미터**:
- `part_id` (integer): 부품 ID
- `file_type` (string): drawing, photo, document
- `file` (file): 업로드할 파일

**응답**:
```json
{
  "success": true,
  "message": "도면 파일이 업로드되었습니다: drawing.pdf",
  "file_info": {
    "file_name": "abc123_drawing.pdf",
    "original_name": "drawing.pdf",
    "file_type": "drawing",
    "file_size": 1024000,
    "file_path": "parts/1/drawings/abc123_drawing.pdf",
    "uploaded_at": "2026-01-09T10:00:00+09:00",
    "download_url": "/api/v1/files/parts/1/drawings/abc123_drawing.pdf",
    "preview_url": "/api/v1/files/parts/1/drawings/abc123_drawing.pdf?preview=true"
  }
}
```

#### 다중 파일 업로드
```http
POST /api/v1/parts/{part_id}/upload/{file_type}/multiple
Content-Type: multipart/form-data
```

#### 부품 파일 목록 조회
```http
GET /api/v1/parts/{part_id}/files
```

**응답**:
```json
{
  "part_id": 1,
  "part_number": "DPI0001",
  "drawings": [...],
  "photos": [...],
  "documents": [...]
}
```

#### 파일 삭제
```http
DELETE /api/v1/parts/{part_id}/files/{file_type}/{file_index}
```

### 거래처 파일 API

#### 문서 업로드
```http
POST /api/v1/partners/{partner_id}/upload/document
Content-Type: multipart/form-data
```

#### 파일 목록 조회
```http
GET /api/v1/partners/{partner_id}/files
```

**응답**:
```json
{
  "partner_id": 1,
  "partner_code": "SUP-001",
  "documents": [
    {
      "file_name": "abc123_business_license.pdf",
      "original_name": "사업자등록증.pdf",
      "file_type": "document",
      "file_size": 512000,
      "file_path": "partners/1/documents/abc123_business_license.pdf",
      "uploaded_at": "2026-01-09T10:00:00+09:00",
      "download_url": "/api/v1/files/partners/1/documents/abc123_business_license.pdf",
      "preview_url": "/api/v1/files/partners/1/documents/abc123_business_license.pdf?preview=true"
    }
  ]
}
```

#### 파일 삭제
```http
DELETE /api/v1/partners/{partner_id}/files/{file_index}
```

### 파일 다운로드/미리보기

#### 다운로드
```http
GET /api/v1/files/{file_path}
```

**예시**:
```
GET /api/v1/files/parts/1/drawings/abc123_drawing.pdf
```

#### 미리보기
```http
GET /api/v1/files/{file_path}?preview=true
```

미리보기 모드에서는 `Content-Disposition` 헤더가 설정되지 않아 브라우저에서 직접 표시됩니다.

---

## 에러 코드

### 에러 응답 구조

**일반 에러**:
```json
{
  "detail": "에러 메시지"
}
```

**Service Layer 에러 (v0.6.0)**:
```json
{
  "detail": {
    "code": "NOT_FOUND",
    "message": "부품을 찾을 수 없습니다",
    "details": {
      "entity": "Part",
      "id": 999
    }
  }
}
```

### Pydantic 검증 에러 (422)

```json
{
  "detail": [
    {
      "loc": ["body", "partner_code"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 일반적인 에러 메시지

| HTTP 코드 | 메시지 | 설명 |
|-----------|--------|------|
| 400 | "이미 존재하는 코드입니다" | 코드 중복 |
| 400 | "허용되지 않는 파일 형식입니다" | 파일 확장자 검증 실패 |
| 400 | "파일 크기가 너무 큽니다" | 파일 크기 초과 (최대 50MB) |
| 404 | "항목을 찾을 수 없습니다" | 리소스가 존재하지 않음 |
| 404 | "부품을 찾을 수 없습니다" | 부품 ID 오류 |
| 404 | "거래처를 찾을 수 없습니다" | 거래처 ID 오류 |
| 404 | "파일을 찾을 수 없습니다" | 파일이 존재하지 않음 |
| 422 | "field required" | 필수 필드 누락 |
| 422 | "비즈니스 규칙 위반" | BusinessRuleException |
| 500 | "Internal Server Error" | 서버 오류 |

### Service Layer 에러 코드 (v0.6.0)

| 에러 코드 | HTTP 코드 | 설명 |
|-----------|-----------|------|
| `NOT_FOUND` | 404 | 리소스를 찾을 수 없음 |
| `ALREADY_EXISTS` | 400 | 이미 존재하는 리소스 |
| `VALIDATION_ERROR` | 400 | 유효성 검증 실패 |
| `BUSINESS_RULE_ERROR` | 422 | 비즈니스 규칙 위반 |
| `CIRCULAR_REFERENCE` | 400 | 순환 참조 감지 |
| `FILE_ERROR` | 400 | 파일 처리 오류 |
| `INTERNAL_ERROR` | 500 | 내부 서버 오류 |

---

## 예제 코드

### JavaScript (Axios) - 파일 업로드

```javascript
import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1'
})

// 부품 파일 업로드
async function uploadPartFile(partId, fileType, file) {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await apiClient.post(
      `/parts/${partId}/upload/${fileType}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    return response.data
  } catch (error) {
    console.error('Upload failed:', error.response?.data)
    throw error
  }
}

// 거래처 문서 업로드
async function uploadPartnerDocument(partnerId, file) {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await apiClient.post(
      `/partners/${partnerId}/upload/document`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    return response.data
  } catch (error) {
    console.error('Upload failed:', error.response?.data)
    throw error
  }
}

// 거래처 목록 조회 (공급업체만)
async function getSuppliers() {
  const response = await apiClient.get('/partners', {
    params: { is_supplier: true, is_active: true }
  })
  return response.data
}

// 거래처 생성
async function createPartner(data) {
  const response = await apiClient.post('/partners', data)
  return response.data
}
```

### Python (requests)

```python
import requests

BASE_URL = 'http://localhost:8000/api/v1'

# 부품 파일 업로드
def upload_part_file(part_id: int, file_type: str, file_path: str):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f'{BASE_URL}/parts/{part_id}/upload/{file_type}',
            files=files
        )
    return response.json()

# 거래처 목록 조회
def get_partners(is_supplier=None, is_customer=None):
    params = {}
    if is_supplier is not None:
        params['is_supplier'] = is_supplier
    if is_customer is not None:
        params['is_customer'] = is_customer

    response = requests.get(f'{BASE_URL}/partners', params=params)
    return response.json()

# 거래처 생성
def create_partner(data: dict):
    response = requests.post(f'{BASE_URL}/partners', json=data)
    return response.json()

# 사용 예
partners = get_partners(is_supplier=True)
new_partner = create_partner({
    'partner_code': 'SUP-002',
    'partner_name': 'LG전자',
    'is_supplier': True,
    'is_customer': False
})
```

### TypeScript (Vue.js)

```typescript
// src/api/partner.ts
import apiClient from './client'

export interface BusinessPartner {
  id: number
  partner_code: string
  partner_name: string
  is_supplier: boolean
  is_customer: boolean
  // ... 기타 필드
}

export interface FileInfo {
  file_name: string
  original_name: string
  file_type: string
  file_size: number
  file_path: string
  uploaded_at: string
  download_url: string
  preview_url: string
}

export const partnerApi = {
  getAll: (params?: { is_supplier?: boolean; is_customer?: boolean }) =>
    apiClient.get<BusinessPartner[]>('/partners', { params }),

  getById: (id: number) =>
    apiClient.get<BusinessPartner>(`/partners/${id}`),

  create: (data: Partial<BusinessPartner>) =>
    apiClient.post<BusinessPartner>('/partners', data),

  update: (id: number, data: Partial<BusinessPartner>) =>
    apiClient.put<BusinessPartner>(`/partners/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/partners/${id}`),

  uploadDocument: (partnerId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/partners/${partnerId}/upload/document`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  getFiles: (partnerId: number) =>
    apiClient.get(`/partners/${partnerId}/files`),

  deleteFile: (partnerId: number, fileIndex: number) =>
    apiClient.delete(`/partners/${partnerId}/files/${fileIndex}`)
}
```

---

## 발주서 API (v0.15.0)

### 데이터 모델

```typescript
interface PurchaseOrder {
  id: number
  po_number: string             // 발주서번호 (자동생성: PO-YYYYMMDD-001)
  supplier_id: number           // 공급업체 ID
  order_date: string            // 발주일
  expected_delivery_date?: string // 예상 납기일
  actual_delivery_date?: string // 실제 입고일
  total_amount: number          // 총 금액
  currency: string              // 통화 (KRW)
  status: string                // 상태 (DRAFT/ORDERED/CONFIRMED/RECEIVED/COMPLETED/CANCELLED)
  is_paid: boolean              // 결제 완료 여부
  paid_date?: string            // 결제일
  paid_amount?: number          // 결제 금액
  items?: PurchaseOrderItem[]   // 발주 항목
}
```

### 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/purchase-orders` | 목록 조회 |
| GET | `/purchase-orders/{id}` | 단건 조회 |
| POST | `/purchase-orders` | 발주서 생성 |
| PUT | `/purchase-orders/{id}` | 발주서 수정 (DRAFT만) |
| DELETE | `/purchase-orders/{id}` | 발주서 삭제 (DRAFT만) |
| POST | `/purchase-orders/{id}/order` | 주문 확정 (DRAFT → ORDERED) |
| POST | `/purchase-orders/{id}/confirm` | 납기 확정 (ORDERED → CONFIRMED) |
| POST | `/purchase-orders/{id}/receive` | 입고 처리 (→ RECEIVED) |
| POST | `/purchase-orders/{id}/complete` | 결재 완료 (RECEIVED → COMPLETED) |
| POST | `/purchase-orders/{id}/cancel` | 취소 |
| **PATCH** | **`/purchase-orders/{id}/payment`** | **결제 상태 변경 (v0.15.0 신규)** |

### 결제 상태 변경 API (신규)

```http
PATCH /api/v1/purchase-orders/{po_id}/payment
Content-Type: application/json

{
  "is_paid": true,
  "paid_date": "2026-01-16",
  "paid_amount": 1000000
}
```

---

## 작업지시서 API (v0.7.0)

### 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/work-orders` | 목록 조회 |
| GET | `/work-orders/{id}` | 단건 조회 |
| GET | `/work-orders/check-availability` | **생산 가용수량 체크** |
| POST | `/work-orders` | 생성 |
| POST | `/work-orders/{id}/approve` | 승인 |
| POST | `/work-orders/{id}/issue` | 부품 출고 (FIFO/로트 선택) |
| POST | `/work-orders/{id}/start` | 작업 시작 |
| POST | `/work-orders/{id}/complete` | 작업 완료 |

### 생산 가용수량 체크 API

```http
GET /api/v1/work-orders/check-availability?product_part_id=30&quantity=100
```

**응답**:
```json
{
  "can_produce": 85,
  "limiting_parts": [
    {
      "part_id": 123,
      "part_number": "BR-001",
      "required_per_unit": 2,
      "available": 170,
      "can_make": 85
    }
  ],
  "items": [...]
}
```

---

## 부품 마스터 API 변경 (v0.15.0)

### 삭제 API 변경 (2단계 삭제)

```http
DELETE /api/v1/parts/{part_id}?force=false
```

**동작**:
1. **1단계**: 상태가 ACTIVE/INACTIVE → OBSOLETE(단종)으로 변경
2. **2단계**: 상태가 OBSOLETE → DB에서 완전 삭제
3. **force=true**: 강제로 즉시 완전 삭제 (관리자용)

**응답**:
```json
{
  "action": "obsoleted",  // 또는 "deleted"
  "message": "부품 'HB01-DCP-00001'이(가) 단종 처리되었습니다."
}
```

**삭제 전 체크 사항**:
- BOM에서 사용 중인지
- 발주서 항목에서 사용 중인지
- 작업지시서 항목에서 사용 중인지
- 재고가 있는지

---

## API 로드맵

### 완료됨 (v0.15.0)
- [x] 코드 마스터 전체 CRUD
- [x] 부품 마스터 CRUD (2단계 삭제 포함)
- [x] 거래처 (공급업체/고객사) CRUD
- [x] 파일 업로드/다운로드/삭제
- [x] Service Layer 아키텍처 구현
- [x] Repository Pattern 구현
- [x] BOM 관리 API
- [x] 발주서 관리 API (결제 체크박스 포함)
- [x] 작업지시서 관리 API (로트/FIFO 출고)
- [x] 재고 관리 API (로트별 추적)

### 다음 버전 예정
- [ ] 대체품 관리 API
- [ ] 원가 계산 API
- [ ] 인증/인가 API (JWT)
- [ ] 대시보드 API

---

**최종 업데이트**: 2026-01-16
