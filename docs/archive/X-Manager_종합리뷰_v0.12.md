# X-Manager 프로젝트 종합 리뷰 및 향후 계획

**작성일**: 2026년 1월 15일
**최종 업데이트**: 2026년 1월 20일
**현재 버전**: v0.19.0
**문서 버전**: 2.0

---

## 1. 프로젝트 개요

### 1.1 시스템 소개
X-Manager는 제조업체를 위한 **부품 관리 시스템(PLM - Product Lifecycle Management)**입니다.
부품 마스터 관리, BOM(Bill of Materials) 구성, 거래처 관리, 파일 첨부 등의 기능을 제공합니다.

### 1.2 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| **Backend** | Python + FastAPI | 3.11 / 0.100+ |
| **Database** | SQLite (개발) / PostgreSQL (운영) | - |
| **ORM** | SQLAlchemy | 2.0+ |
| **Frontend** | Vue 3 (Composition API) | 3.4+ |
| **Type System** | TypeScript | 5.0+ |
| **Styling** | Tailwind CSS | 3.4+ |
| **Build Tool** | Vite | 5.0+ |
| **HTTP Client** | Axios | 1.6+ |

### 1.3 아키텍처 패턴

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3)                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Views   │  │Components│ │ API     │  │ Router  │        │
│  └─────────┘  └─────────┘  │ Client  │  └─────────┘        │
│                            └────┬────┘                      │
└─────────────────────────────────┼───────────────────────────┘
                                  │ HTTP/REST
┌─────────────────────────────────┼───────────────────────────┐
│                     Backend (FastAPI)                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ API     │→ │ Service │→ │ Repo    │→ │ Models  │        │
│  │ Router  │  │ Layer   │  │ Layer   │  │ (ORM)   │        │
│  └─────────┘  └─────────┘  └─────────┘  └────┬────┘        │
└─────────────────────────────────────────────┼───────────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    │    Database       │
                                    │   (SQLite/PG)     │
                                    └───────────────────┘
```

---

## 2. 핵심 기능 현황

### 2.1 코드 마스터 관리 (100% 완료)

#### 품번 구조 (v1.1)
```
[대분류(4)]-[소분류(3)]-[품목코드(5)]-[재질(2)]-[후처리(2)]
예시: HB01-DCP-00001-A6-NK

총 20자리 (구분자 포함)
```

#### 코드 테이블 구성

| 테이블 | 코드 길이 | 품번 포함 | 설명 |
|--------|----------|----------|------|
| ProductLine | 4자리 | O | 대분류/제품라인 (HB01, BI03 등) |
| PartGroup | 3자리 | O | 소분류/품목군 (DCP, PLP 등) |
| Material | 2자리 | O | 재질 (A6, S4 등) |
| Treatment | 2자리 | O | 후처리 (NK, NN, WA 등) |
| DevelopmentType | 1자리 | X | 개발구분 (D, S, M, R, C, P) |
| PartType | 1자리 | X | 부품유형 (P, E, O, M 등) - **다중선택** |
| DrawingType | 1자리 | X | 도면여부 (D, S, N) |
| Level | 1자리 | X | BOM 레벨 (F, P, K, S, R) |
| Unit | 가변 | X | 단위 (EA, M, KG 등) |
| ProcurementType | - | X | 조달구분 |

### 2.2 부품 마스터 관리 (100% 완료)

#### 주요 기능
- [x] 부품 CRUD (생성/조회/수정/삭제)
- [x] 품번 자동생성 (`generate_part_number_v2`)
- [x] 검색/필터링 (품번, 부품명, 분류별)
- [x] 페이지네이션 (10/20/50/100건)
- [x] 정렬 (컬럼별 오름차순/내림차순)
- [x] 엑셀 내보내기
- [x] 파일 첨부 (도면, 사진, 문서)
- [x] 상세 조회 모달
- [x] 부품유형 다중선택

#### API 엔드포인트
```
GET    /api/v1/parts              - 목록 조회 (페이지네이션, 필터링)
GET    /api/v1/parts/{id}         - 단건 조회
GET    /api/v1/parts/number/{num} - 품번으로 조회
POST   /api/v1/parts              - 부품 생성 (품번 자동생성)
POST   /api/v1/parts/assembly     - 조합/키트 생성 (자유형식 코드)
PUT    /api/v1/parts/{id}         - 수정
DELETE /api/v1/parts/{id}         - 삭제
PATCH  /api/v1/parts/{id}/status  - 상태 변경
GET    /api/v1/parts/export/excel - 엑셀 내보내기
```

### 2.3 BOM 관리 (100% 완료)

#### 주요 기능
- [x] BOM 트리 구조 표시
- [x] 상위/하위 부품 관계 설정
- [x] 순환 참조 방지 검증
- [x] 수량/단위 관리
- [x] 유효기간 관리
- [x] 일괄 생성 (Bulk Create)
- [x] **조합/키트 등록** (자유형식 코드) - v0.12.0 신규

#### BOM 레벨 체계
| 코드 | 명칭 | 설명 |
|------|------|------|
| F | 완제품 | Finished Goods |
| P | 패키지 | Package |
| K | 키트 | Kit |
| S | 서브어셈블리 | Sub-Assembly |
| R | 단품 | Raw Material/Part |

#### API 엔드포인트
```
GET    /api/v1/bom                    - 목록 조회
GET    /api/v1/bom/{id}               - 단건 조회
GET    /api/v1/bom/children/{id}      - 하위 부품 목록
GET    /api/v1/bom/parents/{id}       - 상위 부품 목록
GET    /api/v1/bom/tree/{id}          - 트리 구조 조회
POST   /api/v1/bom                    - 생성
POST   /api/v1/bom/bulk               - 일괄 생성
PUT    /api/v1/bom/{id}               - 수정
DELETE /api/v1/bom/{id}               - 삭제
```

### 2.4 거래처 관리 (100% 완료)

#### 주요 기능
- [x] 공급업체/고객사 통합 관리
- [x] 거래처 유형 필터링
- [x] 담당자 정보 관리
- [x] 조달 조건 관리 (공급업체)
- [x] 신용/할인 관리 (고객사)
- [x] 문서 첨부
- [x] 엑셀 내보내기

#### API 엔드포인트
```
GET    /api/v1/business-partner       - 목록 조회
GET    /api/v1/business-partner/{id}  - 단건 조회
POST   /api/v1/business-partner       - 생성
PUT    /api/v1/business-partner/{id}  - 수정
DELETE /api/v1/business-partner/{id}  - 삭제
```

### 2.5 파일 첨부 시스템 (100% 완료)

#### 저장 구조
```
storage/uploads/
├── parts/{part_id}/
│   ├── drawings/    # 도면 (PDF, DWG, DXF, STEP)
│   ├── photos/      # 사진 (JPG, PNG, GIF)
│   └── documents/   # 문서 (PDF, DOC, XLS)
└── partners/{partner_id}/
    └── documents/   # 거래처 문서
```

#### API 엔드포인트
```
POST   /api/v1/parts/{id}/upload/{type}     - 부품 파일 업로드
POST   /api/v1/partners/{id}/upload         - 거래처 문서 업로드
GET    /api/v1/files/{entity}/{id}/{type}/{filename} - 다운로드
DELETE /api/v1/files/{entity}/{id}/{type}/{filename} - 삭제
```

---

## 3. 최근 완료된 작업

### 3.1 원가관리 시스템 (v0.18.0 ~ v0.19.0) 🆕

#### 핵심 기능

**1. 부품 원가 정보 확장**
- Parts 모델에 20개 이상의 원가 관련 필드 추가
- 다양한 단가 유형 지원:
  - 기준단가 (standard_price): 수동 입력
  - 재고단가 (inventory_avg_price): 이동평균법
  - 최근단가 (latest_price): 최종 입고가
  - 평균단가 (avg_price_30d, avg_price_90d, avg_price_last5, avg_price_last10): 캐시

**2. BOM 기반 원가 계산**
- 단품: 기준단가 > 최근단가 > 재고단가 우선순위
- 조립품: 하위 부품 단가 × 수량 재귀 합산
- 총원가 = 재료비 + 가공비 + 경비
- 순환 참조 감지 및 방지

**3. 가격 이력 시스템**
```
price_history 테이블
├── price_type: PURCHASE / STANDARD / MANUAL / QUOTE
├── unit_price, currency
├── exchange_rate, unit_price_krw (자동 원화 환산)
├── supplier_id, reference_type, reference_id
└── 인덱스 최적화 (part_date, part_supplier, part_type)
```

**4. 환율 관리**
- 다중 통화 지원 (KRW, USD, EUR, JPY, CNY)
- 유효 기간 기반 환율 적용
- 자동 원화 환산 기능

#### API 엔드포인트 (신규)
```
# 부품 원가 정보
GET    /api/v1/prices/parts/{part_id}              - 원가 정보 조회
PATCH  /api/v1/prices/parts/{part_id}/standard-price - 기준단가 수정
POST   /api/v1/prices/parts/{part_id}/refresh-cache - 평균단가 캐시 갱신

# 평균단가 계산
GET    /api/v1/prices/parts/{part_id}/avg-price    - 평균단가 계산 (기간/건수별)

# 가격 이력
GET    /api/v1/prices/parts/{part_id}/history      - 가격 이력 조회

# 환율 관리
GET    /api/v1/prices/exchange-rates/{currency}    - 환율 조회
POST   /api/v1/prices/exchange-rates               - 환율 등록
GET    /api/v1/prices/convert                      - 통화 환산

# BOM 기반 원가
GET    /api/v1/prices/parts/{part_id}/bom-cost     - BOM 원가 계산
GET    /api/v1/prices/parts/{part_id}/bom-cost/breakdown - 원가 상세 분석
POST   /api/v1/prices/parts/{part_id}/bom-cost/save - 계산 원가 저장
POST   /api/v1/prices/parts/{part_id}/bom-cost/save-all - BOM 전체 재계산
PATCH  /api/v1/prices/parts/{part_id}/labor-cost   - 가공비 수정
PATCH  /api/v1/prices/parts/{part_id}/overhead-cost - 경비 수정
```

### 3.2 BOM 페이지 최적화 (v0.12.0)

#### TypeScript 에러 수정
1. **Line 469**: `searchedParts.value[0]` undefined 처리
2. **Line 543**: `quickAddResults.value[0]` undefined 처리
3. **Line 645-646**: `dragIndex.value` null 가드 추가
4. **Line 917**: `selectedParentPart` 타입 단언 추가

#### 조합/키트 등록 기능 추가

**백엔드:**
- `AssemblyCreate` 스키마 추가 (자유형식 코드)
- `/api/v1/parts/assembly` 엔드포인트 추가
- `PartService.create_assembly()` 메서드 구현

**프론트엔드:**
- `AssemblyFormModal.vue` 컴포넌트 생성
- `BOMView.vue`에 조합/키트 버튼 추가
- `partApi.createAssembly()` API 메서드 추가

### 3.3 부품 생성 버그 수정

**문제**: `item_code_prefix`가 Part 모델에 존재하지 않아 부품 생성 실패

**해결**: `part_service.py`에서 `model_dump()` 호출 시 `item_code_prefix` 제외
```python
# 수정 전
part_data = part_in.model_dump(exclude={'part_type_ids'})

# 수정 후
part_data = part_in.model_dump(exclude={'part_type_ids', 'item_code_prefix'})
```

---

## 4. 프로젝트 구조

### 4.1 백엔드 디렉토리 구조
```
backend/
├── app/
│   ├── api/v1/              # API 라우터
│   │   ├── bom.py
│   │   ├── business_partner.py
│   │   ├── code_master.py
│   │   ├── deps.py          # 의존성 주입
│   │   ├── files.py
│   │   ├── parts.py
│   │   └── supplier.py
│   ├── core/                # 핵심 설정
│   │   ├── config.py
│   │   ├── database.py
│   │   └── exceptions.py
│   ├── models/              # SQLAlchemy 모델
│   │   ├── bom.py
│   │   ├── business_partner.py
│   │   ├── code_master.py
│   │   ├── parts.py
│   │   └── supplier.py
│   ├── repositories/        # 데이터 접근 계층
│   │   ├── base.py
│   │   ├── bom_repository.py
│   │   ├── code_master_repository.py
│   │   ├── part_repository.py
│   │   └── partner_repository.py
│   ├── schemas/             # Pydantic 스키마
│   │   ├── bom.py
│   │   ├── business_partner.py
│   │   ├── code_master.py
│   │   ├── parts.py
│   │   └── supplier.py
│   ├── services/            # 비즈니스 로직
│   │   ├── base.py
│   │   ├── bom_service.py
│   │   ├── code_master_service.py
│   │   ├── part_service.py
│   │   └── partner_service.py
│   ├── utils/               # 유틸리티
│   │   └── part_number_generator.py
│   └── main.py              # FastAPI 진입점
├── alembic/                 # DB 마이그레이션
├── storage/                 # 파일 저장소
└── requirements.txt
```

### 4.2 프론트엔드 디렉토리 구조
```
frontend/
├── src/
│   ├── api/                 # API 클라이언트
│   │   ├── client.ts        # Axios 설정
│   │   ├── bom.ts
│   │   ├── codeMaster.ts
│   │   ├── files.ts
│   │   ├── partner.ts
│   │   ├── parts.ts
│   │   └── supplier.ts
│   ├── components/          # Vue 컴포넌트
│   │   ├── AssemblyFormModal.vue
│   │   ├── BOMFormModal.vue
│   │   ├── BOMTreeNode.vue
│   │   ├── CodeMasterModal.vue
│   │   ├── FileList.vue
│   │   ├── FileUpload.vue
│   │   ├── Pagination.vue
│   │   ├── PartDetailModal.vue
│   │   ├── PartFormModal.vue
│   │   ├── PartnerDetailModal.vue
│   │   ├── PartnerFormModal.vue
│   │   ├── SortIcon.vue
│   │   └── ...
│   ├── views/               # 페이지 뷰
│   │   ├── BOMView.vue
│   │   ├── CodeMasterView.vue
│   │   ├── CodeSimulatorView.vue
│   │   ├── PartnersView.vue
│   │   ├── PartsView.vue
│   │   └── ...
│   ├── router/              # Vue Router
│   │   └── index.ts
│   ├── stores/              # Pinia 상태관리
│   └── App.vue
├── vite.config.ts
└── package.json
```

---

## 5. 보완 필요 사항

### 5.1 즉시 보완 필요 (High Priority)

#### 1) BOM 페이지 UX 개선
- [ ] 상위 부품에서 조합/키트 생성 후 바로 선택 연동
- [ ] BOM 구성 추가 시 빠른 부품 검색 개선
- [ ] 드래그앤드롭으로 BOM 순서 변경 시 서버 동기화

#### 2) 에러 처리 강화
- [ ] 네트워크 에러 시 재시도 로직
- [ ] 사용자 친화적 에러 메시지
- [ ] 로딩 상태 표시 개선

#### 3) 데이터 검증 강화
- [ ] 프론트엔드 폼 유효성 검사 강화
- [ ] 백엔드 비즈니스 규칙 검증 추가
- [ ] 중복 데이터 방지 로직

### 5.2 중기 보완 사항 (Medium Priority)

#### 1) 성능 최적화
- [ ] 대용량 데이터 조회 시 가상 스크롤링
- [ ] API 응답 캐싱 (Redis)
- [ ] 이미지 리사이징/썸네일 생성

#### 2) 테스트 코드 작성
- [ ] 백엔드 단위 테스트 (pytest)
- [ ] API 통합 테스트
- [ ] 프론트엔드 컴포넌트 테스트 (Vitest)

#### 3) 문서화
- [ ] API 문서 자동 생성 (OpenAPI/Swagger 개선)
- [ ] 개발자 가이드 보완
- [ ] 사용자 매뉴얼 작성

### 5.3 코드 품질 개선

#### 1) 백엔드
- [ ] Legacy 코드 정리 (supplier.py 등)
- [ ] 공통 응답 포맷 표준화
- [ ] 로깅 시스템 구축

#### 2) 프론트엔드
- [ ] 컴포넌트 재사용성 개선
- [ ] Pinia 상태관리 활용 확대
- [ ] TypeScript 타입 정의 강화

---

## 6. 향후 개발 계획

### 6.1 1단계 완료 작업 (현재 80%)

#### 남은 작업
| 기능 | 우선순위 | 예상 작업량 | 상태 |
|------|---------|------------|------|
| ~~원가 계산~~ | ~~중~~ | ~~대~~ | ✅ 완료 (v0.18.0) |
| 대체품 관리 | 중 | 중 | 미착수 |
| 승인 프로세스 | 중 | 중 | 미착수 |
| 공정 관리 | 저 | 중 | 코드마스터로 대체 가능 |

### 6.2 2단계: 재고/구매 관리

| 기능 | 설명 |
|------|------|
| 재고 관리 | 창고별 재고 현황, 입출고 이력 |
| 구매 요청 | 부품별 구매 요청 생성 |
| 발주 관리 | PO 생성, 발주 이력 |
| 입고 관리 | 입고 검수, 품질 검사 |

### 6.3 3단계: 생산/품질 관리

| 기능 | 설명 |
|------|------|
| 생산 계획 | MPS (Master Production Schedule) |
| 작업 지시 | 생산 작업 지시서 |
| 품질 관리 | 검사 기준, 불량 관리 |
| 추적성 | Lot/Serial 추적 |

### 6.4 4단계: 고도화

| 기능 | 설명 |
|------|------|
| 대시보드 | 통계, 차트, KPI |
| 리포트 | 다양한 보고서 생성 |
| 알림 시스템 | 이메일/푸시 알림 |
| 사용자 관리 | 권한, 역할 관리 |
| 다국어 지원 | i18n |

---

## 7. 기술 부채 목록

### 7.1 백엔드

| 항목 | 현황 | 개선 방안 |
|------|------|----------|
| Supplier 모듈 | Legacy, BusinessPartner로 통합됨 | 삭제 또는 비활성화 |
| 하드코딩된 설정 | 일부 존재 | config.py로 이동 |
| 에러 핸들링 | 일부 누락 | 전역 예외 처리 강화 |
| 로깅 | 미구현 | Python logging 모듈 적용 |

### 7.2 프론트엔드

| 항목 | 현황 | 개선 방안 |
|------|------|----------|
| 상태관리 | 컴포넌트 로컬 상태 위주 | Pinia 활용 확대 |
| API 에러 처리 | 일부 누락 | 공통 에러 핸들러 적용 |
| 타입 정의 | 일부 any 사용 | 엄격한 타입 적용 |
| 반응형 디자인 | 부분 적용 | 모바일 최적화 |

---

## 8. 버전 히스토리

| 버전 | 날짜 | 주요 내용 |
|------|------|----------|
| **v0.19.0** | **2026-01-20** | **원가관리 프론트엔드 연동**, 부품 스키마 확장 |
| **v0.18.0** | **2026-01-18** | **원가관리 백엔드 구현** (가격이력, 환율, BOM 원가계산) |
| v0.16.0 | 2026-01-16 | 작업지시서 취소/복원, 발주서 롤백 |
| v0.15.0 | 2026-01-16 | 입출고 관리, 로트 관리, FIFO 출고 |
| v0.14.0 | 2026-01-15 | 검색 시스템 개선, 다중선택 모달 |
| v0.13.0 | 2026-01-15 | 토스트 알림, API 재시도 로직 |
| v0.12.0 | 2026-01-15 | BOM 페이지 최적화, 조합/키트 등록 |
| v0.11.0 | 2026-01-12 | 품번 구조 v1.1 적용 (대분류 4자리) |
| v0.10.0 | 2026-01-12 | 품번 구조 대폭 변경 (부품코드 관리기준서 적용) |
| v0.9.0 | 2026-01-12 | BOM 관리 기능 구현 |
| v0.8.0 | 2026-01-09 | 엑셀 내보내기 기능 |
| v0.7.0 | 2026-01-09 | Repository Pattern, 페이지네이션, 정렬 |
| v0.6.0 | 2026-01-09 | Service Layer 아키텍처 |
| v0.5.0 | 2026-01-09 | 파일 첨부 시스템 |
| v0.4.0 | 2026-01-08 | 거래처 관리 통합 |
| v0.3.0 | 2026-01-08 | 공급업체 관리, UI/UX 개선 |
| v0.2.0 | 2026-01-07 | 부품 마스터 관리 |
| v0.1.0 | 2026-01-06 | 코드 마스터 관리 |

---

## 9. 결론

X-Manager 프로젝트는 1단계 목표의 약 **95%**를 달성했습니다.

**완료된 핵심 기능:**
- 코드 마스터 관리 (품번 구조 v1.1)
- 부품 마스터 관리 (자동 품번 생성)
- BOM 관리 (트리 구조, 조합/키트)
- 거래처 관리 (공급업체/고객사 통합)
- 파일 첨부 시스템
- **원가 관리 시스템** (v0.18.0~v0.19.0 신규)
  - 가격 이력 관리 (price_history)
  - 환율 관리 (exchange_rate)
  - BOM 기반 원가 계산 (재귀, 순환참조 방지)
  - 재고단가 (이동평균법)
  - 평균단가 (기간별/건수별)

**향후 집중 필요 영역:**
1. 대체품 관리 기능
2. 승인 프로세스
3. 테스트 코드 및 문서화
4. 성능 최적화

시스템의 기본 구조가 안정적으로 구축되어 있어, 향후 기능 확장에 좋은 기반이 마련되어 있습니다.

---

*문서 작성: Claude Code*
*최종 검토: 2026-01-20*
