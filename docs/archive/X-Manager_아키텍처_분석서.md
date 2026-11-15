# X-Manager 아키텍처 분석 및 개선 제안서

**작성일**: 2026년 1월 9일
**최종 수정일**: 2026년 1월 9일
**분석 대상**: X-Manager v0.6.0
**목적**: 확장성 관점에서 현재 아키텍처 평가 및 개선 방안 제시

---

## 1. 현재 아키텍처 개요

### 1.1 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           X-Manager 시스템 아키텍처                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        프론트엔드 (Vue.js 3)                         │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │   │
│  │  │  Views  │  │Component│  │  Router │  │  Stores │  │   API   │   │   │
│  │  │ (페이지)│  │ (공통) │  │ (라우팅)│  │ (Pinia) │  │(Axios) │   │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   │   │
│  │       └───────────┴───────────┴───────────┴───────────┘           │   │
│  └──────────────────────────────────┬──────────────────────────────────┘   │
│                                     │ HTTP/REST                            │
│  ┌──────────────────────────────────▼──────────────────────────────────┐   │
│  │                         백엔드 (FastAPI)                             │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │           API Layer (api/v1/) - 얇은 컨트롤러 계층           │   │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │   │   │
│  │  │  │  parts   │ │ partners │ │  codes   │ │  files   │        │   │   │
│  │  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │   │   │
│  │  └───────┼────────────┼────────────┼────────────┼───────────────┘   │   │
│  │          │            │            │            │                   │   │
│  │  ┌───────▼────────────▼────────────▼────────────▼───────────────┐   │   │
│  │  │              ✅ Service Layer (services/) - 구현 완료         │   │   │
│  │  │  ┌────────────┐ ┌─────────────────┐ ┌──────────────────┐    │   │   │
│  │  │  │PartService │ │PartnerService   │ │CodeMasterService │    │   │   │
│  │  │  └────────────┘ └─────────────────┘ └──────────────────┘    │   │   │
│  │  │               ↑ BaseService (공통 CRUD)                      │   │   │
│  │  └───────┬────────────┬────────────┬────────────┬───────────────┘   │   │
│  │          │            │            │            │                   │   │
│  │  ┌───────▼────────────▼────────────▼────────────▼───────────────┐   │   │
│  │  │                      Model Layer (models/)                    │   │   │
│  │  │  ┌──────┐ ┌──────────────┐ ┌────────────┐ ┌──────┐           │   │   │
│  │  │  │ Part │ │BusinessPartner│ │ CodeMaster │ │Supplier│         │   │   │
│  │  │  └──────┘ └──────────────┘ └────────────┘ └──────┘           │   │   │
│  │  └───────┬────────────────────────────────────────────────────────┘   │   │
│  │          │ SQLAlchemy ORM                                         │   │
│  └──────────┼────────────────────────────────────────────────────────┘   │
│             │                                                             │
│  ┌──────────▼────────────────────────────────────────────────────────┐   │
│  │                      데이터베이스 (PostgreSQL)                     │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │   │
│  │  │   코드 마스터     │  │   마스터 데이터   │  │   트랜잭션      │  │   │
│  │  │ (10개 테이블)     │  │ (parts, partners)│  │   (미구현)      │  │   │
│  │  └──────────────────┘  └──────────────────┘  └─────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                        파일 스토리지 (storage/)                    │   │
│  │  uploads/parts/{id}/drawings/, photos/, documents/                │   │
│  │  uploads/partners/{id}/documents/                                 │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 현재 폴더 구조 (v0.6.0 기준)

```
X-MANAGER_R0.1/
├── backend/
│   ├── app/
│   │   ├── api/v1/               # API 엔드포인트 (라우터)
│   │   │   ├── __init__.py
│   │   │   ├── deps.py           # ✅ 공통 의존성 (NEW)
│   │   │   ├── code_master.py    # 코드 CRUD (Service 사용)
│   │   │   ├── parts.py          # 부품 CRUD (Service 사용)
│   │   │   ├── business_partner.py # 거래처 CRUD (Service 사용)
│   │   │   ├── files.py          # 파일 업로드/다운로드
│   │   │   └── supplier.py       # Legacy
│   │   │
│   │   ├── core/                 # 핵심 설정
│   │   │   ├── config.py         # 설정 관리
│   │   │   ├── database.py       # DB 연결
│   │   │   └── exceptions.py     # ✅ 커스텀 예외 (NEW)
│   │   │
│   │   ├── services/             # ✅ 비즈니스 로직 계층 (NEW)
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # BaseService (공통 CRUD)
│   │   │   ├── part_service.py   # 부품 서비스
│   │   │   ├── partner_service.py # 거래처 서비스
│   │   │   └── code_master_service.py # 코드 마스터 서비스
│   │   │
│   │   ├── models/               # SQLAlchemy 모델
│   │   │   ├── code_master.py    # 10개 코드 테이블
│   │   │   ├── parts.py          # 부품 마스터
│   │   │   ├── business_partner.py
│   │   │   └── supplier.py       # Legacy
│   │   │
│   │   ├── schemas/              # Pydantic 스키마
│   │   │   ├── code_master.py
│   │   │   ├── parts.py
│   │   │   └── business_partner.py
│   │   │
│   │   ├── utils/
│   │   │   └── part_number_generator.py
│   │   └── main.py
│   │
│   ├── alembic/                  # DB 마이그레이션
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/                  # API 클라이언트
│   │   │   ├── client.ts         # Axios 클라이언트 (동적 호스트)
│   │   │   ├── codeMaster.ts
│   │   │   ├── parts.ts
│   │   │   ├── partner.ts
│   │   │   └── files.ts
│   │   ├── components/           # 공통 컴포넌트
│   │   ├── views/                # 페이지
│   │   ├── router/
│   │   ├── stores/               # Pinia (미활용)
│   │   └── utils/
│   └── package.json
│
├── storage/                      # 파일 저장소
└── docs/                         # 문서
```

---

## 2. 현재 아키텍처 평가

### 2.1 잘 된 점 ✅

| 항목 | 평가 | 설명 |
|------|------|------|
| **기술 스택 선정** | ⭐⭐⭐⭐⭐ | FastAPI + Vue.js 3 + PostgreSQL은 확장성 있는 조합 |
| **API 버저닝** | ⭐⭐⭐⭐⭐ | `/api/v1/` 프리픽스로 버전 관리 준비됨 |
| **DB 마이그레이션** | ⭐⭐⭐⭐⭐ | Alembic 사용으로 스키마 변경 관리 가능 |
| **모델 분리** | ⭐⭐⭐⭐ | SQLAlchemy 모델과 Pydantic 스키마 분리 |
| **파일 구조** | ⭐⭐⭐⭐ | 기본 폴더 구조가 명확함 |
| **문서화** | ⭐⭐⭐⭐⭐ | 개발 문서, API 문서 잘 관리됨 |
| **Service Layer** | ⭐⭐⭐⭐⭐ | ✅ **구현 완료** - 비즈니스 로직 분리됨 |
| **예외 처리** | ⭐⭐⭐⭐⭐ | ✅ **구현 완료** - 커스텀 예외 클래스 |

### 2.2 개선이 필요한 점 ⚠️

| 항목 | 심각도 | 문제점 | 상태 |
|------|--------|--------|------|
| **Service Layer 부재** | ~~🔴 높음~~ | ~~비즈니스 로직이 API 라우터에 직접 구현됨~~ | ✅ 해결됨 |
| **상태 관리 미활용** | 🟠 중간 | Pinia Store가 거의 사용되지 않음 | 미해결 |
| **컴포넌트 비대화** | 🟠 중간 | 모달 컴포넌트가 17~20KB로 너무 큼 | 미해결 |
| **에러 처리 일관성** | ~~🟡 낮음~~ | ~~통일된 에러 핸들링 패턴 부재~~ | ✅ 해결됨 |
| **타입 정의 분산** | 🟡 낮음 | TypeScript 타입이 각 파일에 분산됨 | 미해결 |
| **테스트 부재** | 🔴 높음 | 자동화된 테스트 코드 없음 | 미해결 |

---

## 3. 구현된 Service Layer 상세

### 3.1 BaseService

모든 서비스의 기본 클래스로, 공통 CRUD 기능을 제공합니다.

**파일 위치**: `backend/app/services/base.py`

```python
class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """기본 서비스 클래스"""

    # 기본 CRUD
    def get(self, id: int) -> Optional[ModelType]
    def get_or_raise(self, id: int) -> ModelType
    def get_all(self, skip, limit, filters, order_by) -> List[ModelType]
    def count(self, filters) -> int
    def create(self, obj_in) -> ModelType
    def update(self, id, obj_in) -> Optional[ModelType]
    def delete(self, id) -> bool
    def soft_delete(self, id) -> Optional[ModelType]

    # 유틸리티
    def exists(self, id) -> bool
    def get_by_field(self, field, value) -> Optional[ModelType]
    def get_active(self, skip, limit) -> List[ModelType]
    def bulk_create(self, objects_in) -> List[ModelType]
    def search(self, keyword, search_fields, skip, limit) -> List[ModelType]
```

### 3.2 PartService

부품 관련 비즈니스 로직을 처리합니다.

**파일 위치**: `backend/app/services/part_service.py`

```python
class PartService(BaseService[Part, PartCreate, PartUpdate]):
    """부품 서비스"""

    # 조회
    def get_by_part_number(self, part_number: str) -> Optional[Part]
    def search_parts(self, keyword, filters...) -> List[Part]
    def count_parts(self, keyword, filters...) -> int

    # 생성 (품번 자동 생성 포함)
    def create_part(self, part_in: PartCreate) -> Part

    # 수정 (분류 변경 시 품번 재생성)
    def update_part(self, part_id: int, part_in: PartUpdate) -> Part

    # 상태 관리
    def activate(self, part_id: int) -> Part
    def deactivate(self, part_id: int) -> Part
    def update_status(self, part_id: int, new_status: str) -> Part

    # 승인 프로세스
    def update_approval_status(self, part_id, approval_status, approved_by) -> Part
    def submit_for_approval(self, part_id: int) -> Part
    def approve(self, part_id: int, approved_by: int) -> Part
    def reject(self, part_id: int, approved_by: int) -> Part

    # 파일 관련
    def update_files(self, part_id, drawing_file, photo_file, document_files) -> Part
```

### 3.3 BusinessPartnerService

거래처(공급업체/고객사) 관련 비즈니스 로직을 처리합니다.

**파일 위치**: `backend/app/services/partner_service.py`

```python
class BusinessPartnerService(BaseService[BusinessPartner, ...]):
    """거래처 서비스"""

    # 조회
    def get_by_code(self, partner_code: str) -> Optional[BusinessPartner]
    def search_partners(self, keyword, is_supplier, is_customer, is_active) -> List
    def get_suppliers(self, is_active, skip, limit) -> List[BusinessPartner]
    def get_customers(self, is_active, skip, limit) -> List[BusinessPartner]

    # 생성/수정 (코드 중복 검사 포함)
    def create_partner(self, partner_in) -> BusinessPartner
    def update_partner(self, partner_id, partner_in) -> BusinessPartner

    # 파일 관련
    def update_document_files(self, partner_id, document_files) -> BusinessPartner
    def add_document_file(self, partner_id, file_info) -> BusinessPartner
    def remove_document_file(self, partner_id, file_path) -> BusinessPartner
```

### 3.4 CodeMasterService

10개의 코드 테이블을 통합 관리합니다.

**파일 위치**: `backend/app/services/code_master_service.py`

```python
class CodeMasterService:
    """코드 마스터 서비스"""

    # 동적 테이블 지정 CRUD
    def get(self, table_name: str, id: int) -> Optional[Base]
    def get_by_code(self, table_name: str, code: str) -> Optional[Base]
    def get_all(self, table_name: str, is_active, skip, limit) -> List[Base]
    def create(self, table_name: str, data: Dict) -> Base
    def update(self, table_name: str, id: int, data: Dict) -> Base
    def delete(self, table_name: str, id: int) -> bool

    # 유틸리티
    def get_all_tables_summary(self) -> Dict[str, int]
    def update_sort_orders(self, table_name, sort_orders) -> List[Base]

    # 지원 테이블
    # major-categories, middle-categories, minor-categories,
    # sub-categories, item-codes, materials, treatments,
    # levels, procurement-types, units
```

### 3.5 커스텀 예외 클래스

**파일 위치**: `backend/app/core/exceptions.py`

```python
# 기본 예외
class AppException(Exception)

# 리소스 관련
class NotFoundException(AppException)      # 404
class AlreadyExistsException(AppException) # 409

# 검증 관련
class ValidationException(AppException)    # 400
class InvalidOperationException(AppException)

# 비즈니스 로직
class BusinessRuleException(AppException)  # 422
class CircularReferenceException(BusinessRuleException)  # BOM용
class DependencyException(BusinessRuleException)

# 권한 관련
class UnauthorizedException(AppException)  # 401
class ForbiddenException(AppException)     # 403

# 파일 관련
class FileException(AppException)
class FileNotFoundException(FileException)
class FileSizeExceededException(FileException)
class InvalidFileTypeException(FileException)
```

### 3.6 API 의존성

**파일 위치**: `backend/app/api/v1/deps.py`

```python
# 서비스 의존성 주입
def get_part_service(db: Session = Depends(get_db)) -> PartService
def get_partner_service(db: Session = Depends(get_db)) -> BusinessPartnerService
def get_code_master_service(db: Session = Depends(get_db)) -> CodeMasterService

# 페이지네이션
class PaginationParams
def get_pagination(...) -> PaginationParams

# 예외 처리
def handle_service_exception(e: Exception) -> None

# 공통 응답
def create_response(data, message, pagination, total) -> dict
```

---

## 4. API 라우터 구조 (리팩토링 완료)

### 4.1 리팩토링 전 (구조)

```python
# ❌ 이전 구조 - 비즈니스 로직이 라우터에 직접 있음
@router.post("", response_model=PartResponse)
def create_part(part: PartCreate, db: Session = Depends(get_db)):
    # 품번 생성 로직
    part_number, part_number_display = generate_part_number(...)

    # DB 저장 로직
    db_part = Part(**part_data, part_number=part_number)
    db.add(db_part)
    db.commit()

    return db_part
```

### 4.2 리팩토링 후 (현재)

```python
# ✅ 현재 구조 - Service를 통한 비즈니스 로직 처리
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
```

### 4.3 주요 장점

1. **관심사 분리**: API 라우터는 요청/응답만, Service는 비즈니스 로직
2. **테스트 용이**: Service 단위로 테스트 가능
3. **재사용성**: Service를 다른 API나 배치 작업에서 재사용
4. **유지보수성**: 비즈니스 로직 변경 시 Service만 수정

---

## 5. 향후 개선 로드맵

### Phase 1: ✅ 완료

| 작업 | 설명 | 상태 |
|------|------|------|
| Service Layer 기본 구조 | BaseService, PartService 생성 | ✅ 완료 |
| 공통 예외 처리 | exceptions.py, handle_service_exception | ✅ 완료 |
| API 리팩토링 | Service 호출 방식으로 변경 | ✅ 완료 |
| 공통 의존성 | deps.py 생성 | ✅ 완료 |

### Phase 2: 테스트 환경 구축 (권장)

| 작업 | 설명 | 우선순위 |
|------|------|----------|
| pytest 설정 | conftest.py, 테스트 DB | 높음 |
| Service 단위 테스트 | PartService, PartnerService 테스트 | 높음 |
| API 통합 테스트 | 주요 API 엔드포인트 테스트 | 중간 |

### Phase 3: 프론트엔드 개선

| 작업 | 설명 | 우선순위 |
|------|------|----------|
| Pinia Store 구현 | parts, partners, codes 스토어 | 중간 |
| 컴포넌트 분리 | 모달 → 작은 컴포넌트 | 중간 |
| TypeScript 타입 정리 | types/ 폴더 구성 | 낮음 |

### Phase 4: BOM 기능 구현

| 작업 | 설명 | 우선순위 |
|------|------|----------|
| BOM 모델/스키마 | 재귀 구조 설계 | 높음 |
| BOMService | 트리 조회, 원가 계산, 순환 참조 검사 | 높음 |
| BOM 트리 컴포넌트 | 재귀 트리 UI | 높음 |

---

## 6. 결론

### 6.1 완료된 개선 사항

1. ✅ **Service Layer 구현**: 모든 주요 API가 Service를 통해 비즈니스 로직 처리
2. ✅ **커스텀 예외 체계**: 일관된 에러 처리 패턴 구축
3. ✅ **API 리팩토링**: 라우터 단순화, 관심사 분리 완료

### 6.2 현재 아키텍처 상태

| 기능 | 현재 상태 | 확장 준비도 |
|------|-----------|-------------|
| 부품 관리 | ✅ Service Layer 적용 | 높음 |
| 거래처 관리 | ✅ Service Layer 적용 | 높음 |
| 코드 마스터 | ✅ Service Layer 적용 | 높음 |
| BOM 관리 | 미구현 | **준비됨** - BOMService 추가만 필요 |
| 원가 계산 | 미구현 | **준비됨** - CostService 추가만 필요 |
| 승인 프로세스 | 기본 구현 | 높음 |

### 6.3 권장 다음 단계

> **Service Layer 구현 완료!**
>
> 이제 BOM, 원가 계산 등 복잡한 기능을 안전하게 추가할 수 있는 기반이 마련되었습니다.
> 다음 단계로 테스트 환경 구축을 권장합니다.

---

**작성자**: Claude AI
**최종 검토일**: 2026-01-09
