# X-Manager CRM 현황 분석 및 Gap Analysis

> 작성일: 2026-04-15  
> 대상 DB: PostgreSQL 18.3 / xmanager  
> 백엔드: FastAPI + SQLAlchemy + Alembic  
> 프론트엔드: Vue 3 + TypeScript + Tailwind CSS

---

## 1. 현재 시스템 현황

### 1.1 DB 테이블 현황 (46개 테이블, 19,641행)

#### 마스터 데이터 (16 테이블)
| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| unit | 8 | 단위 |
| level | 8 | 레벨 (조립/원가 설정) |
| major_category | 4 | 대분류 |
| middle_category | 4 | 중분류 |
| minor_category | 3 | 소분류 |
| sub_category | 4 | 세분류 |
| item_code | 4 | 아이템 코드 |
| material | 11 | 소재 |
| treatment | 7 | 표면처리 |
| part_type | 12 | 부품 유형 |
| part_group | 27 | 부품 그룹 |
| development_type | 6 | 개발 유형 |
| drawing_type | 3 | 도면 유형 |
| procurement_type | 5 | 조달 유형 |
| product_line | 16 | 제품군 |
| product_description_code | 43 | 제품 설명 코드 |

#### 부품/BOM (4 테이블)
| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| parts | 3,569 | 부품 마스터 (가격, 원가, 스펙, 승인 워크플로우) |
| bom | 11,715 | BOM (부모-자식 관계, 수량, 유효기간) |
| part_part_type | 2 | 부품-유형 다대다 |
| price_history | 458 | 가격 이력 (구매/표준/견적별) |

#### 거래처 (4 테이블)
| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| **business_partner** | **36** | **통합 거래처 (공급/고객 듀얼)** |
| **business_partner_contact** | **37** | **거래처 담당자 (다중, 기본 담당자 플래그)** |
| **partner_note** | **0** | **거래처 메모 (신규, v0.32.0)** |
| supplier | 5 | 레거시 공급업체 (deprecated) |

#### 재고 (4 테이블)
| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| inventory | 3,557 | 재고 현황 (가용/예약/안전재고) |
| inventory_lot | 1 | 로트 추적 |
| inventory_transaction | 1 | 입출고 이력 |
| warehouse_location | 0 | 창고 위치 |

#### 구매 (2 테이블)
| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| purchase_order | 0 | 발주서 |
| purchase_order_item | 0 | 발주 품목 |

#### 생산 (8 테이블)
| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| production_request | 3 | 생산요청서 |
| production_request_item | 2 | 생산요청 품목 |
| work_order | 2 | 작업지시서 |
| work_order_item | 65 | 작업지시 자재 |
| work_order_product | 1 | 작업지시 생산품 |
| work_order_process_log | 1 | 공정 로그 |
| work_order_item_issue | 0 | 자재 불출 |
| work_order_task | 0 | 공정 작업 |

#### 영업 (4 테이블)
| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| **sales_activity** | **1** | **영업활동 (파이프라인, 단계 추적)** |
| **sales_activity_log** | **4** | **영업 이력 (자동 변경감지 + 수동 코멘트)** |
| **sales_document** | **3** | **견적서/PI/CI (문서 체인)** |
| **sales_document_item** | **3** | **문서 품목** |

#### 기타 (4 테이블)
| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| users | 5 | 사용자 (역할/직급/부서) |
| process_template | 4 | 공정 템플릿 |
| exchange_rate | 0 | 환율 |
| alembic_version | 1 | 마이그레이션 버전 |

#### 외래키 관계: 67개
- parts → 11개 마스터 테이블
- bom → parts (부모/자식)
- work_order → parts, production_request, parent WO
- sales_document → sales_activity, business_partner, source_document
- 다수 테이블 → business_partner (고객/공급 참조)

---

### 1.2 API 엔드포인트 현황 (22개 라우터, 150+ 엔드포인트)

| 라우터 | 프리픽스 | 주요 기능 |
|--------|---------|----------|
| auth | /auth | 로그인, 토큰 갱신, 사용자 관리 |
| code_master | /codes | 코드 마스터 CRUD (40+ 엔드포인트) |
| parts | /parts | 부품 마스터 CRUD, 검색, 엑셀 |
| **business_partner** | **/partners** | **거래처 CRUD, 담당자, 메모, 타임라인, 재주문** |
| supplier | /suppliers | 레거시 공급업체 (deprecated) |
| bom | /bom | BOM CRUD, 트리, 엑셀 업/다운 |
| inventory | /inventory | 재고 조정, 입출고, 로트 |
| purchase_order | /purchase-orders | 발주 CRUD, 입고, 결제 |
| production_request | /production-requests | 생산요청 CRUD, 승인 워크플로우 |
| work_order | /work-orders | 작업지시 CRUD, 7단계 상태 |
| work_order_task | /work-orders/{id}/tasks | 공정 작업 관리 |
| process_log | /process-logs | 공정 시간 추적 |
| process_template | /process-templates | 공정 템플릿 |
| **sales_activity** | **/sales-activities** | **영업활동 CRUD, 로그, 담당자** |
| **sales_document** | **/sales-documents** | **견적/PI/CI, 변환, 수금, 생산요청 생성** |
| price | /prices | 원가, 가격이력, 환율 |
| files | /files | 파일 업/다운로드 |
| dashboard | /dashboard | 대시보드 요약 |
| admin | /admin | 백업, 복원, 동기화 |
| calendar | (없음) | 일정 (PO/WO 통합) |
| product_description_code | /product-description-codes | 제품 설명 코드 |

**서비스 레이어: 14+ 서비스 클래스**  
**스키마: 150+ Pydantic 모델**  
**마이그레이션: 47개 (v0.5.0 ~ v0.32.0)**

---

### 1.3 프론트엔드 모듈 현황

| 모듈 | 뷰 | 컴포넌트 | API | 상태 |
|------|-----|---------|-----|------|
| 인증 | LoginView | - | client.ts | ✅ 완료 |
| 대시보드 | HomeView | 요약 카드 | 다수 | ✅ 완료 |
| 코드관리 | CodeMasterView | 2개 모달 | codeMaster.ts | ✅ 완료 |
| 부품 | PartsView | 4개 모달+필터 | parts.ts | ✅ 완료 |
| **거래처** | **PartnersView** | **PartnerFormModal, PartnerDetailModal** | **partner.ts** | **✅ 완료** |
| BOM | BOMView | 4개 컴포넌트 | bom.ts | ✅ 완료 |
| 재고 | InventoryView | 3개 모달 | inventory.ts, inventoryLot.ts | ✅ 완료 |
| 발주 | PurchaseOrderView | 3개 모달+인쇄 | purchaseOrder.ts | ✅ 완료 |
| **영업관리** | **SalesManagementView** | **4탭 (활동/견적/PI-CI/가격)** | **salesActivity.ts, salesDocument.ts** | **✅ 완료** |
| 생산관리 | ProductionManagementView | 3탭 (간편/요청/WO) | productionRequest.ts, workOrder.ts | ✅ 완료 |
| 일정 | CalendarView | 5개 컴포넌트 | calendar.ts | ✅ 완료 |
| 관리 | AdminView | - | admin.ts | ✅ 완료 |

**총계: 21개 뷰, 61개 컴포넌트, 18개 API 서비스, 2개 컴포저블, 2개 스토어**

---

## 2. 제안 스키마 vs 현재 시스템 비교

### 2.1 테이블 매핑 (기존 ↔ 제안)

| 제안 테이블 | 기존 테이블 | 매핑 상태 | 비고 |
|------------|-----------|----------|------|
| **customers** | **business_partner** | ✅ 이미 존재 (더 상세) | 공급/고객 통합, 36행 운영 중 |
| **customer_contacts** | **business_partner_contact** | ✅ 이미 존재 (더 상세) | 역할, 기본담당자, 37행 운영 중 |
| **sales_opportunities** | **sales_activity** | ✅ 이미 존재 (유사) | 차이점 아래 분석 |
| **sales_activities** | **sales_activity_log** | ✅ 이미 존재 (더 상세) | 9개 로그 유형, 자동 변경감지 |
| **documents** | **sales_document** + 파일 시스템 | ⚠️ 부분 존재 | 아래 상세 분석 |

### 2.2 재활용 가능한 기존 자산

#### ✅ customers → business_partner (100% 커버)
제안 스키마의 모든 필드가 이미 존재하며, 추가로 더 풍부한 데이터 보유:

| 제안 필드 | 기존 필드 | 상태 |
|----------|----------|------|
| company_name | partner_name, partner_name_en | ✅ 한/영 모두 |
| country | country_code, country_name, continent | ✅ 더 상세 |
| region | continent | ✅ |
| customer_type | customer_type (OEM/SI/DISTRIBUTOR) | ✅ |
| trade_type | trade_type (DOMESTIC/EXPORT) | ✅ |
| notes | remark | ✅ |
| payment_terms | payment_terms, delivery_terms, credit_limit | ✅ 더 상세 |
| - | bank_name, swift_code, bank_address | ✅ 은행정보 추가 |
| - | default_margin_rate, short_code, hs_code | ✅ 거래 설정 추가 |
| - | document_files (JSONB) | ✅ 첨부 문서 |
| - | is_supplier + is_customer (듀얼 역할) | ✅ 공급/고객 통합 |

#### ✅ customer_contacts → business_partner_contact (100% 커버)

| 제안 필드 | 기존 필드 | 상태 |
|----------|----------|------|
| name | name | ✅ |
| email | email | ✅ |
| phone | tel_office, tel_mobile | ✅ 더 상세 |
| title | position | ✅ |
| is_decision_maker | is_primary | ✅ 유사 |
| - | role (PURCHASING/TECHNICAL/SALES/GENERAL) | ✅ 역할 구분 추가 |
| - | notes, sort_order | ✅ 추가 필드 |

#### ✅ sales_opportunities → sales_activity (90% 커버)

| 제안 필드 | 기존 필드 | 상태 |
|----------|----------|------|
| customer_id | customer_id (FK) | ✅ |
| title | title | ✅ |
| product_category | inquiry_type (TECHNICAL/QUOTATION/GENERAL/SAMPLE/CLAIM) | ⚠️ 유사하나 의미 다름 |
| project_name | title (프로젝트명으로 사용) | ✅ |
| stage | status (IN_PROGRESS/WAITING/COMPLETED/ON_HOLD) | ✅ |
| estimated_value | expected_amount, expected_currency | ✅ |
| - | current_step, next_step | ✅ 단계 추적 추가 |
| - | pending_reason | ✅ 지연사유 추가 |
| - | assigned_to | ✅ 담당자 추가 |
| - | country | ✅ 대상 국가 추가 |

#### ✅ sales_activities → sales_activity_log (100% 커버, 더 풍부)

| 제안 필드 | 기존 필드 | 상태 |
|----------|----------|------|
| customer_id | activity → customer_id (간접) | ✅ |
| opportunity_id | activity_id (FK) | ✅ |
| activity_type | log_type (9가지) | ✅ 더 상세 |
| title | - | ❌ 없음 (content로 대체) |
| description | content | ✅ |
| activity_date | created_at | ✅ |
| - | logged_by (작성자 추적) | ✅ 추가 |
| - | 자동 변경감지 (상태/담당자/단계) | ✅ 추가 |

로그 유형 9가지:
- 사용자 직접: COMMENT, CONTACT, CURRENT_STATUS, NEXT_STEP, ISSUE
- 자동 감지: STATUS, INQUIRY_TYPE, STEP_UPDATE, ASSIGNEE

#### ⚠️ documents → 부분적으로 분산 존재

| 제안 필드 | 기존 구현 | 상태 |
|----------|----------|------|
| file_name, file_path | 파일 시스템 (storage/) | ✅ |
| doc_type | sales_document.document_type (QUOTATION/PI/CI) | ✅ 견적/PI/CI만 |
| doc_number | sales_document.document_number (자동생성) | ✅ |
| customer_id | sales_document.customer_id | ✅ |
| opportunity_id | sales_document.sales_activity_id | ✅ |
| project_name | - | ❌ 없음 |
| trade_type | - (partner에서 참조 가능) | ⚠️ 간접 |
| year | document_date에서 추출 가능 | ⚠️ 간접 |
| activity_id | - | ❌ 로그와 직접 연결 없음 |

**문서 관리 현황:**
- 견적서/PI/CI: `sales_document` + `sales_document_item` (완전 구현)
- 부품 도면/사진: 파일 시스템 (`storage/parts/`) 
- 거래처 첨부: `business_partner.document_files` (JSONB)
- 발주서 첨부: `purchase_order` 첨부 필드
- 생산요청 첨부: `production_request.attachment_files` (JSONB)
- **통합 문서 메타데이터 테이블은 없음** → 이것이 유일한 Gap

### 2.3 신규 필요 항목

#### 이미 완전 구현된 것 (추가 불필요)
- ✅ 고객사 마스터 → `business_partner`
- ✅ 고객 담당자 → `business_partner_contact`  
- ✅ 영업 기회 → `sales_activity`
- ✅ 영업 활동 이력 → `sales_activity_log`
- ✅ 거래처 메모 → `partner_note` (v0.32.0 신규)
- ✅ 거래처 통합 타임라인 API (v0.32.0 신규)

#### 현재 없지만 제안에 포함된 것
| 항목 | 필요성 | 우선순위 | 비고 |
|------|--------|---------|------|
| 통합 문서 메타데이터 테이블 | 중간 | Phase 2 | 현재 분산된 파일을 한곳에서 검색 |
| xcloud 연동 | 높음 | Phase 3 | 외부 스토리지 연동 |
| 대시보드 강화 | 중간 | Phase 4 | 영업 파이프라인 시각화 |

---

## 3. 마이그레이션 리스크 및 주의사항

### 3.1 충돌 없음 (기존 자산 100% 재활용)

제안된 5개 테이블 중 4개가 이미 **더 상세한 형태로** 존재합니다.  
기존 테이블을 DROP 하거나 ALTER 할 필요가 **없습니다**.

### 3.2 주의사항

| 항목 | 리스크 | 대응 |
|------|--------|------|
| business_partner에 36개 운영 데이터 | 스키마 변경 시 데이터 손실 위험 | ALTER만 사용, DROP 금지 |
| sales_document에 3건 + 연결된 영업활동 | FK 관계 변경 주의 | 기존 FK 유지, 새 FK만 추가 |
| 파일이 5곳에 분산 저장 | 통합 시 기존 경로 참조 깨질 수 있음 | 메타데이터 테이블로 포인터만 추가 |
| supplier 테이블 (deprecated) | business_partner와 중복 | 당장 삭제하지 말고, 점진적 마이그레이션 |
| 47개 마이그레이션 히스토리 | 새 마이그레이션이 기존과 충돌 가능 | revision 체인 확인 필수 |

### 3.3 기존 API 영향

- **영향 없음**: 제안된 기능 대부분이 이미 구현되어 있어 기존 API 수정 불필요
- **추가만 필요**: 통합 문서 검색 API, xcloud 연동 API 등은 신규 엔드포인트로 추가

---

## 4. 구현 순서 제안 (현재 상태 기반)

### 현재 상태 요약
```
제안 5개 테이블 중:
  ✅ customers          → business_partner (완료, 36행 운영 중)
  ✅ customer_contacts   → business_partner_contact (완료, 37행)
  ✅ sales_opportunities → sales_activity (완료, 운영 중)
  ✅ sales_activities    → sales_activity_log (완료, 자동 변경감지)
  ⚠️ documents          → 부분 구현 (분산 저장, 통합 검색 없음)
```

### 제안 Phase 수정안

원래 제안:
```
Phase 1: 고객사 마스터 + 문서 관리 (MVP)     → ✅ 이미 완료
Phase 2: 영업 기회 + 활동 추적              → ✅ 이미 완료
Phase 3: xcloud 연동                      → 미구현
Phase 4: 대시보드 + 검색                    → 부분 구현
```

**수정된 제안:**

#### Phase 1: 통합 문서 검색 + 거래처 히스토리 강화 (현재 Sprint)
- ✅ ~~거래처 메모 (partner_note)~~ → 완료 (v0.32.0)
- ✅ ~~거래처 통합 타임라인 API~~ → 완료 (v0.32.0)
- ✅ ~~담당자 동기화 (contact → manager_name)~~ → 완료
- 🔲 통합 문서 메타데이터 뷰 (DB 뷰 또는 API) → 기존 데이터 조합으로 검색

#### Phase 2: 영업 파이프라인 대시보드
- 🔲 영업 현황 시각화 (상태별/담당자별/국가별)
- 🔲 매출 예측 (expected_amount 기반)
- 🔲 고객별 거래 요약 카드

#### Phase 3: xcloud 연동
- 🔲 Nextcloud/xcloud 파일 동기화
- 🔲 외부 스토리지 연결
- 🔲 문서 버전 관리

#### Phase 4: 고급 검색 + 분석
- 🔲 전체 문서 통합 검색 (견적/PI/CI/PO/WO 횡단)
- 🔲 고객별 수익성 분석
- 🔲 가격 트렌드 분석

---

## 5. 실행 SQL (Phase 1)

### 이미 실행 완료된 SQL (v0.32.0)

```sql
-- 1. partner_note 테이블 (완료)
CREATE TABLE partner_note (
    id SERIAL PRIMARY KEY,
    partner_id INTEGER NOT NULL REFERENCES business_partner(id) ON DELETE CASCADE,
    note_type VARCHAR(20) NOT NULL DEFAULT 'GENERAL',
    content TEXT NOT NULL,
    is_pinned BOOLEAN DEFAULT false,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX idx_partner_note_partner_id ON partner_note(partner_id);

-- 2. sales_activity.current_step 추가 (완료)
ALTER TABLE sales_activity ADD COLUMN current_step TEXT;

-- 3. users.position 추가 (완료)
ALTER TABLE users ADD COLUMN position VARCHAR(50);
```

### 추가 실행 불필요

제안된 5개 테이블 중 4개는 이미 더 상세한 형태로 존재하므로, **CREATE TABLE이 추가로 필요하지 않습니다.**

남은 1개(documents 통합 메타데이터)는 DB 테이블 대신 **API 레벨에서 기존 테이블을 UNION 조회**하는 방식으로 구현되어 있습니다 (`GET /partners/{id}/timeline`).

향후 통합 문서 검색이 필요할 경우, DB 뷰로 구현 가능:

```sql
-- (필요 시) 통합 문서 검색 뷰
CREATE OR REPLACE VIEW v_all_documents AS
SELECT 
    'SALES_DOC' as source,
    sd.id, sd.document_type as doc_type, sd.document_number as doc_number,
    sd.customer_id as partner_id, bp.partner_name,
    sd.document_date as doc_date, sd.total_amount, sd.currency, sd.status,
    sd.created_at
FROM sales_document sd
LEFT JOIN business_partner bp ON bp.id = sd.customer_id

UNION ALL

SELECT 
    'PURCHASE_ORDER' as source,
    po.id, 'PO' as doc_type, po.po_number as doc_number,
    po.supplier_id as partner_id, bp.partner_name,
    po.order_date as doc_date, po.total_amount, po.currency, po.status,
    po.created_at
FROM purchase_order po
LEFT JOIN business_partner bp ON bp.id = po.supplier_id

UNION ALL

SELECT 
    'WORK_ORDER' as source,
    wo.id, 'WO' as doc_type, wo.wo_number as doc_number,
    wo.customer_id as partner_id, bp.partner_name,
    wo.created_at as doc_date, NULL as total_amount, NULL as currency, wo.status,
    wo.created_at
FROM work_order wo
LEFT JOIN business_partner bp ON bp.id = wo.customer_id;
```

---

## 6. 결론

### 핵심 발견

**제안된 CRM 스키마의 핵심 기능은 이미 X-Manager에 구현되어 있습니다.**

| 영역 | 구현율 | 평가 |
|------|--------|------|
| 고객사 마스터 | **100%** | business_partner가 제안보다 더 상세 |
| 담당자 관리 | **100%** | 다중 담당자 + 역할 구분 + 기본 담당자 동기화 |
| 영업 기회 추적 | **95%** | sales_activity + 단계/담당자/금액 추적 |
| 영업 활동 이력 | **100%** | 9가지 로그 유형 + 자동 변경감지 |
| 문서 관리 | **80%** | 견적/PI/CI 완전 체인, 통합 검색만 미구현 |
| 거래처 히스토리 | **100%** | partner_note + 통합 타임라인 (v0.32.0) |

### 즉시 활용 가능한 기능
- 거래처 상세 → 통합 히스토리 탭 (메모 + 영업 로그 + 문서 이력)
- 영업활동 → 현재/다음 단계 인라인 편집 + 자동 이력
- 견적서 → PI → CI 문서 체인 + 생산요청 연결
- 거래처별 최근 주문 + 재주문 기능

### 향후 로드맵
1. **Phase 2**: 영업 파이프라인 대시보드 시각화
2. **Phase 3**: xcloud/Nextcloud 연동
3. **Phase 4**: 통합 문서 검색 + 수익성 분석
