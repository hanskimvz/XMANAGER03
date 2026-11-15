# X-Manager 개발 가이드 (통합본)

**프로젝트**: X-Manager v0.19.0+
**최종 업데이트**: 2026-03-30
**목적**: AI 개발 어시스턴트가 일관된 코드를 생성하기 위한 통합 레퍼런스

---

## 1. 프로젝트 개요

### 1.1 시스템 소개
X-Manager는 방산용 관통 커넥터 제조업체(엑스비하이텍)의 **전사 통합 관리 시스템(PLM)**이다.
부품 마스터, BOM, 원가 계산, 발주서, 작업지시서, 거래처 관리 기능을 제공하는 웹 기반 애플리케이션.

### 1.2 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| **백엔드** | Python + FastAPI | 3.12.10 / 0.110.0 |
| **ORM** | SQLAlchemy | 2.0.27 |
| **검증** | Pydantic | 2.6.1 |
| **마이그레이션** | Alembic | 1.13.1 |
| **DB** | PostgreSQL | 17.7 |
| **비동기 파일** | aiofiles | - |
| **프론트엔드** | Vue.js 3 (Composition API) + TypeScript | 3.4+ |
| **빌드** | Vite | 7.3.1 |
| **CSS** | Tailwind CSS | 3.4.0 |
| **상태관리** | Pinia | 2.1+ |
| **HTTP** | Axios | - |

### 1.3 프로젝트 구조

```
X-MANAGER_R0.1/
├── backend/
│   ├── app/
│   │   ├── api/v1/            # API 라우터
│   │   │   ├── code_master.py
│   │   │   ├── parts.py
│   │   │   ├── bom.py
│   │   │   ├── business_partner.py
│   │   │   ├── files.py
│   │   │   ├── purchase_order.py
│   │   │   ├── work_order.py
│   │   │   ├── inventory.py
│   │   │   ├── prices.py
│   │   │   └── deps.py        # 공통 의존성
│   │   ├── core/              # 설정, DB, 예외
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── exceptions.py
│   │   ├── models/            # SQLAlchemy 모델
│   │   ├── schemas/           # Pydantic 스키마
│   │   ├── services/          # 비즈니스 로직
│   │   └── repositories/      # 데이터 접근 계층
│   ├── alembic/               # DB 마이그레이션
│   └── seeds/                 # 초기 데이터
├── frontend/
│   └── src/
│       ├── api/               # API 서비스 모듈
│       ├── components/        # 재사용 컴포넌트
│       ├── views/             # 페이지 컴포넌트
│       ├── composables/       # Composable (useToast 등)
│       ├── router/
│       └── stores/            # Pinia 스토어
├── storage/                   # 파일 저장소
│   └── uploads/
│       ├── parts/{part_id}/drawings|photos|documents/
│       └── partners/{partner_id}/documents/
├── docs/                      # 문서
│   ├── claude.md              # ← 이 파일 (통합 개발 가이드)
│   ├── bom/                   # BOM 관련 문서
│   ├── harness/               # 하네스 엔지니어링 (AI Agent 역할 정의)
│   ├── infra/                 # 인프라/배포 가이드
│   └── archive/               # 아카이브 (과거 버전 문서)
├── scripts/                   # 유틸리티 스크립트
├── start-prod.bat             # 운영 서버 실행
└── start-dev.bat              # 개발 서버 실행
```

### 1.4 환경 분리

| 환경 | 백엔드 | 프론트엔드 | DB |
|------|--------|------------|-----|
| 운영 | :8000 | :5173 | xmanager |
| 개발 | :8001 | :5174 | xmanager_dev |

---

## 2. 아키텍처 패턴

### 2.1 백엔드 레이어 구조

```
API Router (요청 컨트롤러)
    ↓ Depends()
Service Layer (비즈니스 로직)
    ↓
Repository Layer (데이터 접근)
    ↓
SQLAlchemy Model
    ↓
PostgreSQL
```

**의존성 주입 패턴**:
```python
from fastapi import Depends
from app.core.database import get_db
from app.services.part_service import PartService

@router.get("/parts")
def get_parts(db: Session = Depends(get_db)):
    service = PartService(db)
    return service.get_all()
```

### 2.2 프론트엔드 구조

```
Pages (views/)
    ↓
Feature Components (components/)
    ↓
API Services (api/)   ←→   Composables (composables/)
```

### 2.3 예외 처리 체계

```python
# app/core/exceptions.py
AppException (기본)
├── NotFoundException
├── AlreadyExistsException
├── ValidationException
├── BusinessRuleException
├── CircularReferenceException
└── FileException
```

---

## 3. 품번 체계 (v1.1)

### 3.1 품번 구조

```
[대분류 4자리]-[소분류 3자리]-[항목코드 5자리]-[재질 2자리]-[후처리 2자리]

예시: HB01-DCP-00001-A6-NK
      ↑     ↑     ↑     ↑   └─ 후처리: NK(니켈도금)
      ↑     ↑     ↑     └────── 재질: A6(AL6061)
      ↑     ↑     └──────────── 항목코드: 00001 (자동/수동)
      ↑     └──────────────────── 소분류: DCP(더스트캡부품)
      └──────────────────────── 대분류: HB01(HXB11 제품라인)

총 길이: 20자리 (하이픈 포함)
```

### 3.2 핵심 규칙

- 재질 또는 후처리가 다르면 **별개의 부품** (재고 별도 관리)
- 레벨은 품번에 포함되지 않음 → BOM 속성으로 별도 관리
- 항목코드: 숫자 5자리, 대분류+소분류 내에서 자동 시퀀스 또는 수동 입력

### 3.3 코드 테이블 (현황)

**품번 구성 요소 (5개 테이블)**:
- `product_line` (대분류, 4자리): HB01, HB03, HB05, BI01, TF01, COM0 등
- `part_group` (소분류, 3자리): DCP, PLP, RCP, OCP, BLT, SOR 등
- `material` (재질, 2자리): A6, S4, NB, BR, L1, XX 등
- `treatment` (후처리, 2자리): NK, ZK, HB, WA, CD, NN 등
- `item_code` → DB 컬럼 VARCHAR(5), 테이블 없음

**분류 속성 (품번 미포함, 검색/필터용)**:
- `development_type` (개발구분): D/S/M/R/C/P
- `part_type` (부품유형, 다중선택 JSONB): P/E/O/M/G/I/W/A/C/H/X/T
- `drawing_type` (도면여부): D/S/N

**BOM 속성**:
- `level` (레벨): F(완성품)/P(패키지)/K(키트)/S(서브어셈블리)/R(단품)/M(조립공정)

**기타**:
- `procurement_type` (조달구분): MFG/PUR/INJ/SEM/FIN
- `unit` (단위): EA/SET/KIT/PKG/FP/M/G/ML

### 3.4 parts 테이블 주요 필드

```sql
parts (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(25) UNIQUE NOT NULL,  -- 자동생성 품번

    -- 품번 구성 FK
    product_line_id INT NOT NULL,   -- 대분류
    part_group_id INT NOT NULL,     -- 소분류
    item_code VARCHAR(5) NOT NULL,  -- 항목코드
    material_id INT NOT NULL,       -- 재질
    treatment_id INT NOT NULL,      -- 후처리

    -- 기본 정보
    part_name VARCHAR(200) NOT NULL,
    part_name_en VARCHAR(200),

    -- 분류 속성
    development_type_id INT NOT NULL,
    part_types JSONB DEFAULT '[]',     -- 다중선택 ["P","O"]
    drawing_type_id INT NOT NULL,
    level_id INT NOT NULL,

    -- 원가 (v0.18.0+)
    standard_price DECIMAL(15,2),
    standard_price_currency VARCHAR(10) DEFAULT 'KRW',
    latest_price DECIMAL(15,2),
    inventory_avg_price DECIMAL(15,2),
    cost_type VARCHAR(20),            -- MANUAL/BOM/PROCESS
    material_cost DECIMAL(15,2),
    labor_cost DECIMAL(15,2),
    overhead_cost DECIMAL(15,2),
    calculated_cost DECIMAL(15,2),

    -- 조달
    procurement_type_id INT,
    supplier_id INT,
    lead_time_days INT,

    -- 상태
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE/INACTIVE/OBSOLETE
    approval_status VARCHAR(20) DEFAULT 'DRAFT',

    -- 첨부파일 (JSON)
    drawing_files JSONB,
    photo_files JSONB,
    document_files JSONB
);
```

---

## 4. 코딩 규칙

### 4.1 백엔드 명명 규칙

```
파일/모듈: snake_case         (part_service.py)
클래스: PascalCase            (PartService)
함수/변수: snake_case         (get_parts, total_count)
상수: UPPER_SNAKE_CASE        (MAX_PAGE_SIZE)
API prefix: /api/v1/          (모든 엔드포인트)
```

### 4.2 프론트엔드 명명 규칙

```
컴포넌트 파일: PascalCase      (PartFormModal.vue)
뷰 파일: PascalCase            (PartsView.vue)
API 서비스: camelCase           (codeMaster.ts)
TypeScript 인터페이스: PascalCase (CodeMaster)
```

### 4.3 모델 정의 패턴

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

### 4.4 스키마 정의 패턴

```python
# Base: 공통 필드
class PartBase(BaseModel):
    part_name: str = Field(..., max_length=200)
    # ...

# Create: 생성 시 필드
class PartCreate(PartBase):
    product_line_id: int
    # ...

# Update: 모든 필드 Optional
class PartUpdate(BaseModel):
    part_name: Optional[str] = None
    # ...

# Response: DB 필드 포함
class PartResponse(PartBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True
```

### 4.5 API 엔드포인트 패턴

```python
router = APIRouter(prefix="/parts", tags=["부품 마스터"])

@router.get("/", response_model=List[PartResponse])
def get_parts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = PartService(db)
    return service.get_all(skip=skip, limit=limit)

@router.post("/", response_model=PartResponse, status_code=201)
def create_part(data: PartCreate, db: Session = Depends(get_db)):
    service = PartService(db)
    return service.create(data)

@router.put("/{id}", response_model=PartResponse)
def update_part(id: int, data: PartUpdate, db: Session = Depends(get_db)):
    service = PartService(db)
    return service.update(id, data)

@router.delete("/{id}", status_code=204)
def delete_part(id: int, db: Session = Depends(get_db)):
    service = PartService(db)
    service.delete(id)
```

### 4.6 Vue 컴포넌트 패턴

```vue
<template>
  <div v-if="loading">로딩 중...</div>
  <div v-else-if="error">{{ error }}</div>
  <div v-else>
    <!-- 데이터 표시 -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Part } from '@/api/parts'

// Props & Emits
interface Props { show: boolean; isEdit?: boolean }
const props = withDefaults(defineProps<Props>(), { isEdit: false })
const emit = defineEmits<{ close: []; submit: [data: PartCreate] }>()

// 반응형 상태
const items = ref<Part[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// 데이터 로드
const loadData = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await partApi.getAll()
    items.value = response.data
  } catch (err) {
    error.value = '데이터를 불러오는데 실패했습니다'
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>
```

### 4.7 API 서비스 패턴

```typescript
import apiClient from './client'

export interface Part {
  id: number
  part_number: string
  part_name: string
  // ...
}

export const partApi = {
  getAll: (params?: object) => apiClient.get<Part[]>('/parts', { params }),
  getById: (id: number) => apiClient.get<Part>(`/parts/${id}`),
  create: (data: PartCreate) => apiClient.post<Part>('/parts', data),
  update: (id: number, data: Partial<PartCreate>) => apiClient.put<Part>(`/parts/${id}`, data),
  delete: (id: number) => apiClient.delete(`/parts/${id}`)
}
```

### 4.8 토스트 알림 패턴

```typescript
// composables/useToast.ts 사용
import { useToast } from '@/composables/useToast'
const { showToast } = useToast()

showToast('저장되었습니다', 'success')
showToast('오류가 발생했습니다', 'error')
```

### 4.9 모달 패턴

```vue
<Teleport to="body">
  <Transition name="modal">
    <div v-if="show" @click.self="$emit('close')">
      <!-- 모달 내용 -->
    </div>
  </Transition>
</Teleport>
```

---

## 5. 파일 업로드 패턴

### 5.1 저장 구조

```
storage/uploads/
├── parts/{part_id}/drawings|photos|documents/
├── partners/{partner_id}/documents/
├── purchase-orders/{po_id}/documents/
└── work-orders/{wo_id}/documents/
```

### 5.2 JSON 필드 변경 시 주의

```python
# 중요: JSON/ARRAY 필드 업데이트 후 반드시 flag_modified 호출
from sqlalchemy.orm.attributes import flag_modified

part.document_files = updated_files
flag_modified(part, "document_files")
db.commit()
```

---

## 6. 데이터베이스 운영

### 6.1 마이그레이션 절차

```bash
# 1. 마이그레이션 생성
cd backend
set APP_ENV=development
alembic revision --autogenerate -m "설명"

# 2. 개발 DB 적용 → 테스트
alembic upgrade head

# 3. 운영 DB 적용 (배포 시)
set APP_ENV=production
alembic upgrade head

# 4. 서버 재시작
```

### 6.2 배포 체크리스트

- [ ] 마이그레이션 파일 새로 생성되는가? → 운영 DB에 적용 필수
- [ ] 개발 서버에서 테스트 완료했는가?
- [ ] 운영 DB 백업했는가?

---

## 7. 신기능 개발 워크플로우

### 7.1 백엔드 순서

```
1. Model 정의 (models/)
2. Alembic 마이그레이션 생성 → 적용
3. Schema 정의 (schemas/) - Base/Create/Update/Response
4. Repository 구현 (repositories/) - 필요시
5. Service 구현 (services/)
6. API Router 구현 (api/v1/)
7. Router 등록 (main.py)
8. Swagger 확인 (/docs)
```

### 7.2 프론트엔드 순서

```
1. TypeScript 인터페이스 + API 서비스 (api/)
2. 컴포넌트 구현 (components/ 또는 views/)
3. Router 등록 (router/index.ts)
4. 네비게이션 메뉴 추가 (App.vue)
5. 브라우저 테스트
```

### 7.3 개발 체크리스트

**백엔드**:
- [ ] Model 정의
- [ ] 마이그레이션 생성/적용
- [ ] Schema 정의 (Base/Create/Update/Response)
- [ ] Service 구현
- [ ] API Router 구현
- [ ] Router 등록 (main.py)
- [ ] Swagger 확인

**프론트엔드**:
- [ ] TypeScript 인터페이스
- [ ] API 서비스 모듈
- [ ] 컴포넌트/뷰 구현
- [ ] Router 등록
- [ ] 브라우저 테스트

**문서**:
- [ ] 개발진행상황.md 업데이트

---

## 8. 현재 구현 상태 (v0.19.0 기준)

### 8.1 완료된 모듈

| 모듈 | 상태 | 핵심 API |
|------|------|----------|
| 코드 마스터 | 100% | `/api/v1/codes/*` (10개 테이블 CRUD) |
| 부품 마스터 | 100% | `/api/v1/parts` (CRUD + 검색 + 엑셀) |
| 거래처 관리 | 100% | `/api/v1/partners` (공급업체+고객사 통합) |
| BOM 관리 | 100% | `/api/v1/bom` (재귀 트리 + 일괄등록) |
| 파일 첨부 | 100% | `/api/v1/files/*` (도면/사진/문서) |
| 원가 관리 | 100% | `/api/v1/prices` (BOM 원가계산, 환율, 가격이력) |
| 발주서 관리 | 100% | `/api/v1/purchase-orders`, `/api/v1/work-orders` |
| 재고 관리 | 100% | `/api/v1/inventory` (로트, FIFO) |

### 8.2 미완료 모듈

| 모듈 | 상태 | 비고 |
|------|------|------|
| 공정 관리 | 0% | 코드마스터로 대체 가능 |
| 대체품 관리 | 0% | 향후 구현 |
| 승인 프로세스 | 0% | 워크플로우 설계 필요 |
| 사용자/권한 | 0% | JWT 인증 미구현 |
| BOM 엑셀 업로드 | 개발중 | 요청서 v2 기준 |

### 8.3 주요 비즈니스 로직

**부품 삭제**: 2단계 삭제 (ACTIVE→OBSOLETE→완전 삭제)
**발주서 상태 흐름**: DRAFT→CONFIRMED→SHIPPED→RECEIVED (+롤백 가능)
**작업지시서**: 취소/복원 가능, CANCELLED 상태에서만 완전 삭제
**원가 계산**: BOM 재귀 계산, 이동평균법 재고단가, 다중 통화 환율 관리
**재고**: 로트별 추적, FIFO 출고

---

## 9. BOM 엑셀 업로드 규격 요약

### 9.1 엑셀 구조 (7컬럼)

| 컬럼 | 헤더 | 필수 | 설명 |
|:----:|------|:----:|------|
| A | 레벨 | O | L1, L2, L3... 또는 U |
| B | 품번 | O | 품번 + 레벨코드 접미사 `[X]` |
| C | 품명 | | 부품 이름 |
| D | 규격 | | 사양 |
| E | 수량 | | 기본 1 |
| F | 단위 | | 기본 EA |
| G | 비고 | | 메모 |

### 9.2 레벨코드 접미사

`[U]`완성품/유닛, `[F]`완성품, `[K]`키트, `[P]`패키지, `[S]`서브조합, `[C]`조합, `[R]`원자재, `[O]`외주(LOT), `[M]`제조가공

### 9.3 핵심 규칙

- 첫 행은 반드시 L1 또는 U
- 레벨은 1단계씩만 증가 가능 (L2→L4 불가)
- L1이 다시 나오면 새 BOM 트리 시작
- U가 존재하면 모든 레벨 +1 변환

---

## 10. 알려진 문제 및 해결법

| 문제 | 원인 | 해결 |
|------|------|------|
| Alembic UnicodeDecodeError | alembic.ini 한글 주석 | 영문으로 변경 |
| JSON 필드 업데이트 안 됨 | SQLAlchemy 변경 감지 | `flag_modified()` 사용 |
| Tailwind 디렉티브 에러 | v4 자동 설치 | v3.4로 다운그레이드 |
| API URL 이중 프리픽스 | 라우터 등록 중복 | prefix 확인 |
| Relationship 오류 | FK 여러 개 시 모호성 | `foreign_keys=[]` 명시 |
| PowerShell 한글 깨짐 | 콘솔 인코딩 | `io.TextIOWrapper` UTF-8 |
| Pydantic Extra inputs | .env 변수 추가 | Settings 클래스에 필드 추가 |

---

## 11. 하네스 엔지니어링 프로세스

### 11.0 에이전트 자동 호출 규칙

**Claude는 아래 규칙에 따라 페르소나 파일을 자동으로 읽고 해당 역할로 응답한다.**

| 트리거 | 읽을 파일 | 동작 |
|--------|----------|------|
| `@architect` 또는 설계/아키텍처 요청 | `docs/harness/agents/architect.md` | 아키텍트 관점으로 설계 |
| `@backend` 또는 백엔드 구현 요청 | `docs/harness/agents/backend.md` | 백엔드 개발자로 구현 |
| `@frontend` 또는 프론트엔드 구현 요청 | `docs/harness/agents/frontend.md` | 프론트엔드 개발자로 구현 |
| `@sales-export` 또는 영업/수출 관점 리뷰 요청 | `docs/harness/reviewers/sales-export.md` | 영업 담당자 관점으로 리뷰 |
| `@production-qa` 또는 생산/품질 관점 리뷰 요청 | `docs/harness/reviewers/production-qa.md` | 생산/품질 담당자 관점으로 리뷰 |
| `@manager` 또는 경영진/전략 관점 리뷰 요청 | `docs/harness/reviewers/manager-cxo.md` | CxO 관점으로 평가 |
| `@review-all` 또는 전체 리뷰 요청 | 위 3개 리뷰어 파일 모두 | 3개 관점 순차 리뷰 |

**자동 판단 규칙** (명시적 @호출 없이도):
- 신기능 개발 요청 → `@architect` 먼저 설계 → `@backend`/`@frontend` 구현
- "리뷰해줘", "검증해줘" → 해당 도메인의 리뷰어 자동 선택
- 구현 완료 후 "확인해줘" → `@review-all` (3개 관점 리뷰)

**컨텍스트 파일**: 작업 시작/종료 시 아래 파일도 참조/업데이트:
- `docs/harness/context/current-state.md` — 시스템 현재 상태
- `docs/harness/context/task-tracker.md` — 태스크 현황

### 11.1 개요

X-MANAGER 개발은 아래 프로세스를 따른다.
기획은 COO/CTO가 직접 수행하며, 개발 단계부터 AI Agent 기반 하네스 엔지니어링을 적용한다.

```
COO/CTO + Claude (기획)
        ↓
   기획 산출물 (PRD, 요구사항)
        ↓
┌─────────────────────────────────────────┐
│        하네스 엔지니어링 영역            │
│                                       │
│  ① 개발 (이 문서의 규칙에 따라 코드 생성) │
│        ↓                              │
│  ② AI 실무 검증                        │
│     실무 담당자 페르소나로 시뮬레이션      │
│     → 피드백 → ①로 회귀 가능            │
│        ↓                              │
│  ③ 실제 직원 최종 확인                   │
│        ↓                              │
│  ④ 테스트 → 배포                       │
└─────────────────────────────────────────┘
```

### 11.2 AI 실무 검증 페르소나

개발된 기능을 아래 3가지 관점에서 시뮬레이션 검증한다.
상세 페르소나 정의는 `docs/harness/reviewers/` 에 별도 관리.

**① 영업/수출 담당자 관점**
- 고객사/견적/매출 조회가 직관적인가
- 영문 데이터 입출력이 원활한가
- 수출 시장별 제품 필터링이 가능한가

**② 생산/품질 담당자 관점**
- BOM 조회 시 필요한 정보가 다 보이는가
- 작업지시서 → 출고 → 재고 흐름이 자연스러운가
- 부품 상태/이력 추적이 가능한가

**③ 관리자(CTO/CEO) 관점**
- 전체 현황을 한눈에 파악할 수 있는가
- 원가/매출/재고 데이터가 의사결정에 충분한가
- 시스템 간 데이터 정합성이 유지되는가

### 11.3 배포 절차

```
1. 개발 서버 테스트 (localhost:8001/5174)
2. AI 실무 검증 (페르소나별 체크리스트)
3. 직원 최종 확인 (실제 데이터로 테스트)
4. 마이그레이션 적용 (개발 DB → 운영 DB)
5. 운영 서버 재시작 (start-prod.bat)
```

---

## 부록 A: 참고 문서 목록

| 문서 | 위치 | 용도 |
|------|------|------|
| 개발기획서 v1.3 | `docs/X-Manager_개발기획서_v1_3.md` | 원본 설계서 |
| 부품코드 관리기준서 v1.1 | `docs/X-Manager_부품코드_관리기준서_v1_1.md` | 품번 체계 정의 |
| 개발진행상황 | `docs/00_개발진행상황.md` | 버전별 변경 이력 |
| 사용설명서 v1.0 | `docs/X-Manager_사용설명서_v1_0.md` | 사용자 매뉴얼 |
| 배포/운영 가이드 | `docs/배포_및_운영_가이드.md` | 서버 운영 |
| BOM 엑셀 출력 규격 | `docs/bom/BOM_EXCEL_OUTPUT_SPEC.md` | Claude Skills용 |
| BOM 업로드 요청서 v2 | `docs/bom/BOM_업로드_기능_수정_요청서_v2.md` | 개발 참조 |
| 하네스 프로세스 | `docs/harness/PROCESS.md` | 개발 프로세스 전체 흐름 |
| AWS 인프라 가이드 | `docs/infra/AWS_HYBRID_INFRASTRUCTURE_GUIDE.md` | 배포 인프라 |

## 부록 B: 아카이브 문서 (직접 참조 불필요)

아래 문서들은 `docs/archive/`로 이동. 초기 설정이나 과거 버전 분석이므로 일상 개발에서는 참조하지 않는다.

- `X-Manager_프로젝트_지침.md` → claude.md로 통합됨
- `X-Manager_아키텍처_분석서.md` → v0.6.0 기준, 현재 구조와 차이
- `X-Manager_종합리뷰_v0_12.md` → 개발진행상황.md에 중복
- `검토사항_및_개선방안.md` → v0.2.0 기준, 대부분 완료
- `X-Manager_개발환경_설치가이드.md` → 1회성 설치 가이드
- `X-Manager_Claude_Code_시작가이드.md` → 1회성 가이드
- `X-Manager_환경설정_가이드.md` → 배포 가이드로 통합
- `BOM_엑셀업로드_개발요청서.md` → v2로 대체됨
- `claude_v0.5.0_backup.md` → 이전 버전 claude.md 백업
