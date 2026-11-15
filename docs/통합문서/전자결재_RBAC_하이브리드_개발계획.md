# RBAC 하이브리드 강제 적용 — 상세 개발계획서

> 작성 2026-06-21. 방식: **C(규칙 가드, 기본) + A(엔드포인트별, 예외)** 하이브리드.
> 토대: v0.40.0(테이블 4종·레지스트리 16모듈·54권한·`require_permission` 정의 완료).
> 상태: **계획 확정(결정 D1~D4 완료) · 구현 전 단계 미착수**.
> 이 문서가 RBAC 강제적용의 **단일 정본**이다. (구 `전자결재_RBAC_강제적용_분석.md`, `전사_권한관리_RBAC_도입계획.md` 내용을 본 문서로 통합·대체함.)

---

## 0-A. 현황 진단 (코드 실측, 2026-06-21)

- **토대 완성, 강제 0%**: 권한 레지스트리(16모듈·54권한)·판정 유틸(`has_permission`)·관리 화면·`/auth/me` 권한 노출은 됨. 단 `require_permission`이 **어디에도 안 붙음**.
- **인증부터 비어 있음**: 전체 약 **401개 엔드포인트 중 ~86%(345개)가 무인증**(parts/bom/inventory/sales/purchase/workorder/code 등 require_auth=0). approval(35/37)·rbac·auth만 보호.
- **admin DB 백업/복원/삭제 6개 무인증**(Critical), **SECRET_KEY 하드코딩**(`auth.py:18`) — 강제 전 선결.
- **프론트 미가공**: auth store에 `permissions` 필드 없음, 메뉴/버튼 권한 게이팅 없음.

### 방안 비교 요약 (왜 C+A인가)
| 방식 | 정밀도 | 작업량 | 누락위험 | 결론 |
|---|---|---|---|---|
| A. 엔드포인트별 | 최고 | 345곳 | 높음(깜빡=구멍) | 단독은 비효율 |
| B. 라우터 레벨 | 낮음(view/edit 구분 불가) | 최소 | 낮음 | RBAC로 부적합 |
| **C+A (채택)** | 높음 | 가드+예외 | **0**(라우터 자동 커버) | **최종 완성도 최상** |
> C(규칙 가드)로 빠짐없이 덮고, 비CRUD/특수 지점만 A로 정밀 보강. 단일 방식보다 완성도 높음.

---

## 0. 목표 · 원칙

- **목표**: 관리자 페이지의 역할·권한이 실제 API 차단으로 연결되게 한다.
- **원칙**
  1. **무중단·롤백 가능**: `RBAC_MODE` 플래그(disabled→observe→enforce)로 단계 전환, 문제 시 즉시 disabled.
  2. **빠짐없음 우선**: 라우터 전체를 자동으로 덮어 "깜빡한 무방비 엔드포인트=0".
  3. **기존 동작 보존**: observe 단계까지는 차단 0. 운영 데이터로 격차 검증 후에만 enforce.
  4. **레지스트리 불변 우선**: 기존 54권한 안에서 매핑. 신규 액션 추가는 최소화(관리 UI 복잡도 억제).

---

## 1. 설계 개요

```
[모든 업무 라우터]  ──include_router(dependencies=[module_guard("part")])──►  C 규칙 가드
                                                                              │
                                  ┌───────────────────────────────────────────┘
                                  ▼
        ① RBAC_MODE 확인 (disabled→통과 / observe→로그만 / enforce→차단)
        ② require_auth (로그인 강제)  *공개 allowlist 제외
        ③ 동작 추론: 메서드 + 경로 동사로 action 결정 (§2)
        ④ has_permission(user, "module:action")  (와일드카드 통과)

[예외 라우터(A)] approval(기존 세분화 유지) / admin·rbac(require_admin) / auth(공개+user:manage)
```

핵심: 109개 "동작형" 엔드포인트를 **개별 부착(A)하지 않고**, 가드의 **동작 추론 규칙(§2)** 으로 자동 처리한다. 그 결과 진짜 A 예외는 **3개 라우터**로 축소된다.

---

## 2. 동작(action) 추론 규칙 — 가드 내부 로직

레지스트리에 존재하는 액션(view/create/edit/delete + 일부 export/approve/manage/backup)으로만 매핑한다.

판정 순서(먼저 맞는 규칙 적용):

| 순위 | 조건 | action |
|---|---|---|
| 1 | `price` 모듈의 모든 비-GET | **edit** (price엔 create/delete 없음) |
| 2 | `DELETE` | delete |
| 3 | `GET` + 경로에 export/pdf/excel/download/preview/template | `sales`면 **export**, 그 외 **view** |
| 4 | `GET` (일반) | view |
| 5 | POST/PUT/PATCH + 경로꼬리 ∈ **CREATE_NEW** | create |
| 6 | POST/PUT/PATCH + 경로꼬리 ∈ **WRITE_ON_EXISTING** | edit |
| 7 | POST | create |
| 8 | PUT/PATCH | edit |

- **CREATE_NEW** = `upload-excel, upload/excel, bulk, import, import-sales-tracking, create-work-order, shipping-invoices(생성)`
- **WRITE_ON_EXISTING(→edit)** = `approve, reject, cancel, confirm, complete, submit, resubmit, return, withdraw, hold, release-hold, status, change-status, payment, receive, ship, issue*, start, start-production, complete-*, rollback, restore, activate, deactivate, acknowledge*, reorder, move, refresh-cache, refresh, sync, save, save-all, deposit, deduct, shipment-date, balance/*, order, upload/document, upload/drawing, upload/photo`

> 설계 결정 D-1 (coarse-now): approve/ship/payment 같은 민감 워크플로를 1단계에선 모두 `edit`로 묶는다(=수정 권한자면 가능). 추후 필요한 것만 신규 액션(예: `purchase:confirm`, `workorder:ship`)으로 **승격**한다. 승격 후보는 §12에 명시.

---

## 3. 라우터 → 모듈 매핑표 (C 가드 부착 대상)

| 라우터(prefix) | 모듈 | 가드 |
|---|---|---|
| code_master `/codes` | code | C |
| product_description_code `/product-description-codes` | code | C |
| parts `/parts` | part | C |
| bom `/bom` | bom | C |
| business_partner `/partners` | partner | C |
| supplier `/suppliers`(deprecated) | partner | C |
| inventory `/inventory` | inventory | C |
| purchase_order `/purchase-orders` | purchase | C |
| work_order `/work-orders` | workorder | C |
| work_order_task `/work-orders/{id}/tasks` | workorder | C |
| process_log `/process-logs` | workorder | C |
| process_template `/process-templates` | workorder | C |
| production_request `/production-requests` | production | C |
| price `/prices` | price | C(+규칙1) |
| sales_document `/sales-documents` | sales | C(+export) |
| sales_activity `/sales-activities` | sales_activity | C |
| dashboard `/dashboard` | dashboard | C |
| project `/projects` | project | C(manage 처리, §4) |
| **files** `/parts·/files·/partners` | part/partner | C(특수, §4) |
| **approval** `/approvals` 등 | approval | **A(유지)** |
| **admin** `/admin` | system | **A(require_admin)** |
| **rbac** `/admin`(rbac) | system/user | **A(require_admin, 완료)** |
| **auth** `/auth·/users` | user | **A(공개+manage)** |

---

## 4. A 예외 (개별 처리 대상 — 단 4영역)

1. **approval 라우터**: 이미 엔드포인트별 인증/승인 분기가 정교함 → **C 가드 미적용, 현행 유지**. (필요 시 approval:approve/admin로 정렬만.)
2. **admin 라우터(DB 백업/복원/동기화 6개)**: 현재 **무인증(Critical)** → `require_admin` 부착(또는 system:backup/manage). 선결 보안과 함께.
3. **auth 라우터**: `/auth/login`,`/auth/refresh`,`/auth/me`,`/auth/change-password`=공개 또는 require_auth, `/users/*`=`user:manage`.
4. **files 라우터(공유 다운로드)**: `/files/{path}` 다운로드는 부모 모듈 판별이 모호 → **require_auth만**(로그인 사용자 허용), 업로드 엔드포인트는 부모 모듈(part/partner) edit로 §2 규칙 적용. **R3 대응 필수(§6).**

---

## 5. 피처 플래그 · 관찰 모드

`app/core/config.py`(settings)에 추가:
```python
RBAC_MODE: str = "disabled"   # disabled | observe | enforce  (env override)
```
가드 동작:
- `disabled`: 아무 검사 안 함(현행과 동일).
- `observe`: require_auth는 적용(또는 미적용 선택), 권한 부족이면 **차단하지 않고** `logger.warning("[RBAC-MISS] user=.. perm=.. path=..")` 기록.
- `enforce`: 권한 부족 시 403.

> observe 단계에서 모인 `[RBAC-MISS]` 로그가 곧 "역할 권한 보강 목록"이 된다.

---

## 6. 공개/예외 경로 + R3(인쇄·다운로드) 대응

**공개 allowlist**(require_auth 제외): `/`, `/health`, `/api/health`, `/api/v1/auth/login`, `/api/v1/auth/refresh`, openapi/docs.

**R3 — `window.open(url)` 파일 열기 깨짐 (실측)**:
- 대상: `PartsView.vue:779`, `PartnersView.vue`, `InventoryView.vue` (도면/사진/엑셀), `FileList.vue downloadFile`.
- 원인: 브라우저 새 탭 이동은 Authorization 헤더 미전송 → 인증 켜면 401.
- **수정안(권장)**: 해당 호출을 **blob 다운로드 패턴으로 통일**(이미 `bom.ts:251`, `ApprovalDetailView`가 쓰는 방식). `apiClient.get(url,{responseType:'blob'})` → `URL.createObjectURL` → `<a download>` 또는 새 탭.
- 대안(비권장): 파일 GET을 공개 유지(정보유출) / 단기 서명토큰 쿼리. → blob 통일이 가장 안전·일관.

---

## 7. 표준 역할 · 권한 베이스라인 (시드)

enforce 전 **반드시** 확정. 10~30인 규모 기준 초안(관리자 페이지에서 조정 가능):

| 역할(code) | 성격 | 권한 개요 |
|---|---|---|
| ADMIN_SYS | 전체권한(와일드카드) | `*` (기존) |
| MANAGER | 부서장/관리 | 대부분 모듈 view+create+edit, 일부 delete/manage |
| STAFF_SALES | 영업팀 | sales/sales_activity/partner/project CRUD, 그 외 view |
| STAFF_PROD | 생산팀 | production/workorder/inventory/bom/part CRUD, 그 외 view |
| STAFF_MGMT | 경영지원 | purchase/price/partner CRUD, user/system 일부 |
| EMPLOYEE | 일반(기본) | 현행 9권한(대시보드/결재/조회류) |

작업: ①역할 시드(idempotent) ②전 사용자 역할 배정(관리자 페이지 사용 또는 마이그레이션 스크립트).

---

## 8. 프론트엔드 게이팅 (백엔드 enforce와 정합)

1. **auth store**: `AuthUser`에 `permissions: string[]` 추가, `login/refresh/fetchMe`에서 저장. `can(perm)` / `canAny(perms)` 헬퍼(와일드카드 `*` 통과).
2. **메뉴**: 각 메뉴 항목에 필요 권한 매핑 → 없는 메뉴 숨김.
3. **라우트 가드**: `router/index.ts` 각 라우트 `meta.perm` → beforeEach에서 `can()` 검사(없으면 홈/403).
4. **버튼**: 생성/수정/삭제 버튼 `v-if="can('part:edit')"` 류로 가림(서버가 최종 방어선, UI는 UX).

> 백엔드 observe로 먼저 배포 가능. 프론트 게이팅은 enforce 전환과 함께(또는 직전) 배포.

---

## 9. 작업 분해 (WBS) · 순서

| 단계 | 산출물 | 파일 | 위험 |
|---|---|---|---|
| **0. 선결** | `RBAC_MODE` 플래그, admin require_admin, SECRET_KEY env화 | config.py, admin.py, auth.py | 낮음 |
| **1. 가드 구현** | `module_guard` + 동작 추론(§2) + observe/enforce 분기 + 캐시 | core/auth.py(or core/rbac_guard.py) | 낮음(미부착 시 무영향) |
| **2. 부착** | 업무 라우터에 `dependencies=[module_guard(...)]`, allowlist | main.py | 중(플래그로 통제) |
| **3. R3 수정** | 파일 열기 blob 통일 | PartsView/PartnersView/InventoryView/FileList | 중 |
| **4. 역할 시드** | 표준 역할·권한 + 사용자 배정 | rbac_service seed / 스크립트 | 낮음 |
| **5. 관찰** | observe 배포, `[RBAC-MISS]` 로그 수집·보강 | (운영) | 매우 낮음 |
| **6. 프론트 게이팅** | permissions/can/메뉴/라우트/버튼 | auth.ts, router, 메뉴, 뷰들 | 낮음 |
| **7. enforce** | 플래그 전환, 예외 override 미세조정 | config(env) | 중 |

---

## 10. 테스트 계획

- **단위**: 동작 추론 규칙 표(§2) 케이스별(메서드×경로꼬리→action) 단위테스트.
- **권한 행렬**: 역할별 대표 엔드포인트 매트릭스(통과/403) 자동 스모크.
- **회귀**: disabled 모드에서 기존 스모크(상태머신·결재·발주 등) 전부 통과 확인.
- **R3**: 도면/사진/엑셀/첨부 다운로드 + 인쇄 수동 확인.
- **잠금 방지**: 관리자(와일드카드) 전 기능 통과, EMPLOYEE 비허가 403, 신규 사용자(역할 없음) 동작 확인.

---

## 11. 배포 · 롤백

1. 0~1단계 배포(플래그 `disabled`) → 무영향.
2. 2~4단계 배포 후 `RBAC_MODE=observe` → 차단 없음, 로그 수집(수일).
3. 로그로 역할 보강 + 프론트 게이팅 배포.
4. `RBAC_MODE=enforce` 전환(저트래픽 시간) → 모니터링.
5. **롤백**: 이상 시 `RBAC_MODE=disabled`(재배포 불필요, env/재기동).

---

## 12. 리스크 대응 매트릭스

| ID | 리스크 | 대응 |
|---|---|---|
| R1 | 전면 잠금 | 플래그 + observe 선행 + allowlist |
| R2 | 역할 베이스라인 미비 | §7 시드 + 배정을 enforce 전 완료 |
| R3 | 인쇄/다운로드 401 | §6 blob 통일 |
| R4 | 메서드→동작 오판 | §2 동사 규칙 + observe 로그로 검증 |
| R5 | 하위 리소스/공유 라우터 | §3·§4 명시 매핑(files=require_auth) |
| R6 | 프론트 불일치 | §8 게이팅 동시 배포 |
| R7 | 선결 보안 결함 | §9 0단계 동시 처리 |
| R8 | 성능(요청당 join) | request.state 1회 캐시 |

**액션 승격 후보(추후 D-1 정밀화)**: `purchase:confirm/receive`, `workorder:ship/issue`, `sales:payment`, `production:approve` 등 재무·운영 민감 동작.

---

## 13. 결정 사항 (2026-06-21 확정)

- **D-1 [확정] coarse(→edit) 유지.** 민감 동작(발주확정·출고·입금·승인)을 1단계엔 edit로 묶음. 승격은 가산적이라 추후 용이(권한 1줄 추가 + 가드 1곳 변경 + 관리자 화면 체크, 데이터 이전 불필요). 승격 후보는 §12. *근거: 프로세스 미확립 단계에서 선분할은 되돌리기 비용이 더 큼.*
- **D-2 [확정] observe에서 require_auth ON (R3 수정 후).** 권한 게이트는 observe 동안 항상 로그만; **로그인 게이트는 시범운전 중 실제 적용**해 인증 깨짐(R3 등)을 조기 발견. (A안 채택 — 최종 상태는 A·B 동일, 차이는 문제 발견 시점뿐.)
- **D-3 [확정] §7 초안 6종 생성 → 관리자 페이지에서 수정.** 역할/권한은 코드 배포 없이 화면에서 변경 가능하므로 초안으로 시작.
- **D-4 [확정] files 공유 다운로드 = require_auth(로그인만).** *추후 검토: 다운로드 URL→부모 모듈 판별로 모듈 view 권한까지 정밀화(부품 도면=part:view 등). 1단계 범위 외.*

---

## 14. 향후 과제 — 부서/행(row) 단위 스코프 (별도 Phase, 신중)

본 계획의 범위는 **(A) 기능 단위 = 모듈:동작** 접근제어다. "자기 부서/본인 데이터만" 같은 **(B) 행 단위 스코프**는 위험이 커서 분리한다.

| 단위 | 의미 | 리스크 | 비고 |
|---|---|---|---|
| (A) 모듈:동작 | "영업팀은 sales 편집, 생산은 view만" | **낮음~중** | 본 계획(가드 추가뿐, 쿼리 무변경) |
| (B) 부서/본인 행 | "내 부서 발주서만 조회", "본인 기안만" | **높음** | 모든 조회 쿼리에 소유/부서 조건 → 누락 시 유출·조인/통계/엑셀 깨짐 |

- **설계 선결**: parts/code_master/bom 등은 **부서·소유자 개념 자체가 없음** → 컬럼·인덱스 추가가 선행. 결재/영업문서/발주는 작성자(부서)로 스코프 가능.
- **권고 순서**: 대상 모듈 한정(결재·영업·발주) → 소유부서/작성자 컬럼 정비 → 리포지토리 공통 스코프 필터 + 테스트 → 관찰→차단.
- 결론: **(A)는 지금 안전하게, (B)는 별도 Phase로 신중히.**

---

## 15. 구현 진행 상태 (v0.41.0 — 2026-06-21 구현 완료)

| 단계(§9) | 상태 | 비고 |
|---|---|---|
| 0. 선결(플래그·admin·SECRET_KEY) | ✅ 완료 | `RBAC_MODE` 설정, admin.py 라우터 require_admin, auth.py SECRET_KEY→settings, 운영 placeholder 기동차단 |
| 1. 가드 구현 | ✅ 완료 | `app/core/rbac_guard.py`(module_guard/login_guard/_infer_action) |
| 2. 부착 | ✅ 완료 | main.py 업무 라우터 dependencies 부착, A예외(approval/admin/auth/rbac) 제외, files=login_guard |
| 3. R3 파일 blob | ✅ 대부분 | `utils/download.ts` + 엑셀export 3뷰 + FileList + PartnerDetailModal + SalesDocumentFormModal/SalesManagementView. **잔여 ↓** |
| 4. 역할 시드 | ✅ 완료 | `ensure_standard_roles`(부서장/영업/생산/경영지원) 부팅 idempotent |
| 5. 관찰(observe) | ⏳ 검증 절차 확정(B) | 코드 완료. **검증 절차 §18 정의**(역할별 계정 배정→observe 일주→`[RBAC-MISS]` 실측→매트릭스 보강). 교차 모듈 갭 분석 §17. dev 실측 대기 |
| 6. 프론트 게이팅 | ✅ 완료 | auth `can()/canAny()`, 라우트 meta.perm+가드, App.vue 메뉴 v-if. **code 메뉴는 `code:edit`로 분리**(드롭다운 읽기=`code:view` 전원). 버튼단위는 §16 |
| 7. enforce 전환 | ⏳ 운영전환 | 코드 완료. `RBAC_MODE=enforce` 설정 시 작동. **전 §18 6단계(MISS 0 확인) 선행** |

**검증**: 백엔드 가드 13/13 통과(disabled/enforce/observe), `_infer_action` 케이스 통과, 실서버 부팅·로그인·`/auth/me` 정상, 프론트 vue-tsc EXIT 0.
**기본값 `RBAC_MODE=disabled`** — 코드만 들어가고 기존 동작 무변경. 운영에서 플래그로 단계 전환.

### 잔여 작업 (enforce/observe 켜기 전 마무리 권장)
- **R3 미완 2곳**(반응형 `<img :src>`/`<a :href>` 첨부 미리보기, observe/enforce 시 401):
  - `components/WorkOrderFormModal.vue` — `getPRAttachmentUrl`/`getWOFileUrl`(`:src` 416·429·463·479), `getPRAttachmentDownloadUrl`/`getWOFileDownloadUrl`(`:href` 421·433·445·469·484·499)
  - `components/ProductionRequestDetailModal.vue` — `getAttachmentUrl`(`:src` 93·115, `:href` 99·120·142)
  - 패턴: `fetchAuthedObjectUrl`(미리보기 object URL) / `downloadAuthedUrl`(다운로드)로 교체. v-for 리스트라 index→objectURL 비동기 로딩 필요(FileList 썸네일 방식 참고).
- 표준 역할↔실제 사용자 배정(관리자 화면) — enforce 전 필수(미배정 비관리자는 전부 차단).

## 16. 향후(선택) — 버튼 단위 게이팅
메뉴/라우트/서버는 가드 완료. 생성/수정/삭제 **버튼 v-if="can('part:edit')"** 등 화면 내 버튼 게이팅은 미적용(서버가 최종 방어선이라 기능상 안전, UX 다듬기 항목).

---

## 17. 교차 모듈 의존성 — 전이적 읽기 권한 (2026-06-22 실측)

> 배경: "각 페이지가 복잡하게 얽혀 있어 RBAC가 데이터 연결을 깨뜨리지 않나?"라는 우려에 대한 코드 실측 답.

### 17.1 먼저 구분 — 데이터 연결성 ≠ 화면 교차호출
| 대상 | enforce 영향 |
|---|---|
| **데이터 연결성(FK·조인·저장·집계)** | ❌ **안 깨짐.** 가드는 "요청이 닿는 라우터 진입"만 막을 뿐 쿼리/조인/행을 건드리지 않음. 발주↔부품, 영업↔BOM 데이터 연결 그대로. (행 단위 필터링은 §14에서 **의도적으로 미도입** — 그게 들어가야 조인/엑셀 깨짐 위험 발생) |
| **화면의 교차 모듈 호출** | ⚠️ **위험 지점.** 한 화면이 여러 모듈 API를 부르는데 사용자가 **일부 모듈 읽기권한이 없으면 그 부분만 403**. |

→ "데이터가 얽혀 문제"는 DB 문제가 아니라 **"화면이 옆 모듈을 읽을 권한이 있느냐"** 문제다.

### 17.2 화면별 교차 모듈 호출 지도 (frontend 실측)
| 화면 (메뉴 권한) | 실제 호출 모듈 |
|---|---|
| **BOM** (`bom:view`) | bom + **part** + **code** + **price** |
| **부품** (`part:view`) | part + **code** + **partner** + **inventory** |
| **재고** (`inventory:view`) | inventory + **code** |
| **영업관리** (`sales:view`) | sales + **sales_activity** + **partner** + **part** + **code**(설명코드=product-description-codes→code 모듈) |
| **발주** (`purchase:view`) | purchase + **partner** |
| **생산관리** (`production:view`) | production + **workorder** + **partner** + **inventory**(lot) |

→ 메뉴는 `X:view` 하나로 열리지만, 화면을 **실제로 쓰려면 옆 모듈 읽기권한이 추가로 필요**. `code:view`·`price:view`·`partner:view`는 사실상 **여러 화면 공통 "전이적(transitive) 읽기"** 권한.

### 17.3 예측 갭 (역할 × 화면 대조 — enforce 시 깨질 곳)
| 심각 | 역할 | 누락 | 깨지는 화면/부분 |
|---|---|---|---|
| 🔴 | **STAFF_MGMT(경영지원)** | `code:view` | 부품·BOM·재고·영업 화면의 단위/재질/레벨 드롭다운 전부 403 |
| 🔴 | **EMPLOYEE(일반사원)** | `price:view` | BOM 화면 원가 카드(`priceApi`) 403 |
| 🟠 | **EMPLOYEE** | (과한 `sales:view`) | 영업관리 메뉴는 보이나 영업활동(`sales_activity:view`)·문서작성(`sales:create`) 403 → 메뉴 부여 자체 재검토 |
| 🟢 | STAFF_SALES / STAFF_PROD | — | 각자 화면의 교차 모듈을 전부 보유(영업팀=sales/activity/partner/part/code, 생산팀=production/workorder/partner/inventory) → 정상 |

> 해결 원칙: `code:view`·`price:view`·`partner:view`를 **"거의 전 역할 공통 읽기 베이스라인"** 으로 취급해 누락 역할에 채우거나, 옆 모듈을 많이 끌어쓰는 화면(BOM·영업관리)을 해당 역할 메뉴에서 제외. **확정은 §18 observe 실측으로** 한다.

---

## 18. enforce 전 검증 절차 — **B(observe 로그 실측) 채택** (2026-06-22 결정)

§17 갭은 코드 분석 기반 "예측"이다. **선제 베이스라인 편집(A)** 보다, **observe로 실제 로그를 모아 보강(B)** 을 채택한다(누락 0 보장·운영 무영향). A는 §17.3 명백 갭에만 최소 적용, 나머지는 B로 확정.

### 절차
1. **역할별 테스트 계정 1개씩 배정**(관리 → 권한 관리): EMPLOYEE/STAFF_SALES/STAFF_PROD/STAFF_MGMT/MANAGER 각 1명. *미배정 시 그 역할 경로는 로그가 안 나옴.*
2. `RBAC_MODE=observe` 로 기동(차단 0, 로그만):
   ```powershell
   $env:APP_ENV="development"; $env:RBAC_MODE="observe"
   uvicorn app.main:app --host 127.0.0.1 --port 8001 *> rbac.log
   ```
3. **각 역할 계정으로 로그인 → 전 화면 일주**(부품·BOM·재고·발주·영업·생산·결재·일정 + 각 탭/모달 열기). §17.2 교차호출까지 트리거되도록 모달·상세까지 클릭.
4. 보강 목록(고유 권한×경로) 추출:
   ```powershell
   Select-String "RBAC-MISS" rbac.log |
     ForEach-Object { ($_ -split 'perm=')[1] } | Sort-Object -Unique
   ```
5. 추출된 `module:action` 을 **관리 → 권한 관리 매트릭스**에서 해당 역할에 체크(코드 배포 불필요). §17.3 예측과 대조.
6. 보강 후 **다시 observe 일주 → MISS 0 확인** → 저트래픽 시간에 `RBAC_MODE=enforce` 전환.
7. 이상 시 즉시 `RBAC_MODE=disabled`(재배포 불필요, env+재기동).

### 주의
- **메뉴 숨김은 observe에서 안 보인다**(`rbac_enforced`=enforce에서만 `can()`이 권한 평가; observe는 항상 true=UX 무변경). 메뉴 가시화 확인은 enforce에서.
- `[RBAC-MISS]` 는 서버 stdout → `*> rbac.log` 로 받아 `Select-String` 필터(DEBUG 로그가 많아 육안 식별 곤란).
- 로그인 게이트(401)는 observe에서도 실제 적용(D-2=A) → 인증 깨짐(R3 등) 조기 발견.

---

## 19. 전자결재 우선 도입 — coarse 2역할 (2026-06-22 구현·검증 완료)

> 현황: 정식 서버를 **영업팀만 사용 중**. 전자결재를 전 직원에 도입하되, **비영업 직원은 전자결재만** 쓰게 한다. 세분권한은 추후 프로세스별로 단계 적용(D-1 coarse 철학).

### 19.1 2역할 (`rbac_service.STANDARD_ROLES` 시드)
| code | 이름 | 권한 | enforce 동작 |
|---|---|---|---|
| **APPROVAL_ONLY** | 전자결재 전용 | `dashboard:view`, `approval:view/create/approve` | 전자결재·홈만. 그 외 모듈 메뉴 숨김 + API 403 |
| **FULL** | 전체 사용(영업팀 등) | `_FULL_PERMS` = user/system 제외 전 권한(**50종**) | 현재와 동일 전체 사용(무중단) |

- 원리: 전자결재=A 예외(`module_guard` 미적용, 자체 require_auth) → 권한 0이어도 동작. 타 모듈=가드라 권한 없으면 403.
- **default-deny**: 신규 계정은 RBAC 역할 자동 미부여(`auth.create_user`가 UserRole 안 만듦) → 관리 화면에서 배정 필수.
- 일정(캘린더)도 업무성 화면 → `canAny(businessViews)`로 게이팅(App.vue + router `meta.permAny` + beforeEach). 전자결재 전용은 일정도 숨김.

### 19.2 검증 결과 (실데이터 dev, `RBAC_MODE=enforce`, FastAPI TestClient)
운영 백업 복원본(users 6/parts 3574 등) 위에서 2역할 사용자 생성·배정 후 HTTP 검증:

| 계정(역할) | `/approvals/forms` | `/parts` | `/sales-documents` | `/inventory` | rbac_enforced |
|---|---|---|---|---|---|
| APPROVAL_ONLY | **200** | **403** | **403** | **403** | true |
| FULL | 200 | 200 | 200 | 200 | true |

→ **ALL PASS.** APPROVAL_ONLY 권한=`[approval:approve, approval:create, approval:view, dashboard:view]`, FULL 권한 50종. (검증용 임시계정은 즉시 삭제)

### 19.3 운영 도입 런북
1. 영업팀 사용자 → **FULL** 배정(관리→권한 관리).
2. `RBAC_MODE=observe` 하루 → 영업팀 `[RBAC-MISS]` 0 확인(FULL 충분성 검증). 나오면 FULL에 보강.
3. 전 직원 계정 생성 + 비영업 → **APPROVAL_ONLY** 배정.
4. `RBAC_MODE=enforce` 전환(저트래픽). 이상 시 `disabled` 즉시 롤백.
5. 추후: FULL을 영업/생산/경영지원으로 분할(관리 화면, 코드·마이그레이션 불필요).

---

## 20. 모듈별 enforce 토글 — 단계적 적용 (v0.47.0 구현 완료)

> 배경: 전역 `RBAC_MODE`를 한 번에 enforce로 켜면 전 모듈이 동시에 걸려 리스크가 큼. **권한 강제를 모듈 단위로 켜고 끄는** 구조를 추가해 "민감한 건 즉시 보호, 업무 모듈은 준비된 것부터 하나씩".

### 20.1 3계층
| 계층 | 모듈 | 정책 |
|---|---|---|
| **민감(항상 enforce·토글 불가)** | `leave`(연차) | 코드 상수 `SENSITIVE_MODULES`. 전역 모드 무관 항상 권한 강제. (admin/user/system 은 라우터 자체 require_admin 로 별도 보호) |
| **토글(관리자 on/off)** | 업무 12모듈(dashboard/code/part/bom/partner/inventory/purchase/workorder/production/price/sales/sales_activity) | `rbac_module_policy` 테이블 + 관리 UI |
| **전역 baseline** | 위 외 | `RBAC_MODE`(disabled/observe/enforce) |

판정: `effective_mode(module) = enforce if (민감 or 토글ON) else RBAC_MODE`. `module_guard`/`leave_manager` 가 이 실효 모드 사용.

### 20.2 데이터/코드
- 마이그레이션 `v5w6x7y8z9a0`: `rbac_module_policy(module PK, enforced, updated_at)`.
- `rbac_service`: `SENSITIVE_MODULES`/`TOGGLE_MODULES`/`effective_mode`/`set_module_policy`/`list_module_policy`.
- API(admin): `GET /admin/module-policy`, `PUT /admin/module-policy/{module}?enforced=`.
- 프론트: 관리 → **권한 적용** 탭(`ModulePolicyPanel`) — 모듈별 토글 스위치(민감=locked).

### 20.3 검증(전역 disabled 기준)
part 토글ON → 무인증 `/parts` 401 / `/sales-documents` 여전히 200 / admin(와일드카드) 통과 / 연차 항상 401 / 민감(leave) 변경 거부 400 / OFF 복구 200 — **ALL PASS**.

### 20.4 모듈 켜는 순서(안전)
1. 그 모듈 권한을 **역할에 배정**(권한 관리). 안 하면 정당 사용자도 403.
2. (선택) 전역 observe로 그 모듈 `[RBAC-MISS]` 확인.
3. **권한 적용** 탭에서 모듈 토글 ON.
4. 이상 시 토글 OFF(즉시).
> 전역 enforce 일괄 전환(§19) 대신, **모듈별로 하나씩** 켜면 한 번에 한 모듈만 검증하면 되어 더 안전.
