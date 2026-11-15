# X-Manager 네비게이션 · 메뉴 재구성 작업 문서

- 작성일: 2026-11-15
- 대상: X-Manager 프론트엔드 개발자 / 팀
- 범위: `frontend/` — 상단 네비바 + 좌측 사이드바 메뉴 체계 전면 재구성, 관리 페이지 분해, App.vue 컴포넌트 분리

---

## 1. 개요 / 목표

기존에는 상단 네비바에 모든 메뉴가 **평면(flat) 링크**로 나열되어 있었다. 이를 다음 구조로 바꿨다.

- 상단 네비바에는 **메뉴 그룹 버튼**만 표시한다.
- 그룹 버튼을 누르면 **왼쪽 사이드바**에 그 그룹의 하위 메뉴가 나타난다.
- 메뉴 구성은 **`frontend/src/router/menu.ts` 한 파일**에서 중앙 관리한다. 메뉴 추가/변경 시 이 파일만 수정하면 된다.
- 실제 페이지가 없는 메뉴는 **빈 페이지(`TemplatePage.vue`)**로 연결해 자리만 잡아둔다.

추가로, 비대해진 `AdminView(관리)` 페이지의 탭들을 **독립 페이지로 분해**해 각 메뉴 그룹 아래로 배치하고, `App.vue`에서 **NavBar / SideBar 컴포넌트를 분리**했다.

---

## 2. 아키텍처

### 2.1 핵심 파일

| 파일 | 역할 |
|---|---|
| `src/router/menu.ts` | 메뉴 구성(그룹/항목) 단일 정의. 컴포넌트가 이 데이터를 읽어 렌더링 |
| `src/composables/useMenu.ts` | 메뉴 가시성(권한 필터) · 활성 그룹 계산. NavBar/SideBar 공유 |
| `src/composables/useNavState.ts` | 공유 상태(싱글톤): 사이드바 접힘, 배지 카운트 |
| `src/components/NavBar.vue` | 상단 네비바(그룹 버튼, 알림 종, 모바일 메뉴, 사용자 영역) |
| `src/components/SideBar.vue` | 좌측 사이드바(활성 그룹의 2단 하위 메뉴) |
| `src/App.vue` | 얇은 셸(ToastContainer + NavBar + SideBar + main + MobileTabBar) |
| `src/views/TemplatePage.vue` | 빈 페이지(현재 route 정보 표시). 미구현 메뉴의 임시 화면 |

### 2.2 menu.ts 타입

```ts
export interface MenuItem {
  label: string
  path?: string          // 리프/하이브리드 경로. 순수 부모는 생략 가능
  perm?: string          // 보기 권한 키(hasPermStrict 기준)
  adminOnly?: boolean    // true면 관리자(role=ADMIN)에게만 노출
  children?: MenuItem[]  // 2단 서브메뉴
}

export interface MenuGroup {
  key: string
  label: string
  icon?: string
  perm?: string          // 그룹 노출 권한
  children: MenuItem[]
}
```

### 2.3 가시성 규칙 (`useMenu.ts`)

- **항목(adminOnly)**: `adminOnly && !isAdmin` → 숨김.
- **리프/하이브리드(자체 `path` 보유)**: `perm`만 맞으면 표시.
- **순수 부모(`path` 없음)**: 보이는 자식이 하나라도 있어야 표시.
- **그룹**: `perm` 조건을 만족하고, 보이는 하위 항목이 하나라도 있으면 노출.
- 참고: `hasPermStrict`는 `role === 'ADMIN'`이면 항상 `true`를 반환하므로, 관리자는 `perm` 게이트를 항상 통과한다.

### 2.4 2단 서브메뉴 / 하이브리드

- **순수 부모**: `path` 없이 `children`만 가진다(예: `구매관리`, `인사관리`). 사이드바에서 라벨 클릭 또는 쉐브론으로 펼침/접힘.
- **하이브리드 부모**: `path` + `children` 동시 보유(예: `코드관리` → `/codes` + 부품/BOM). 라벨 클릭 시 자체 페이지로 이동, 오른쪽 쉐브론으로 하위 펼침.
- 사이드바 펼침 상태는 명시 토글이 없으면 "활성 자식이 있을 때 자동 펼침".

### 2.5 권한 가드(라우트)

관리자 전용 페이지는 메뉴에 `adminOnly: true`를 주는 동시에, 라우트 `meta: { requiresAdmin: true }`로 **URL 직접 접근까지 차단**한다(비관리자는 `/`로 리다이렉트). `router/index.ts`의 `beforeEach`가 처리.

---

## 3. 최종 메뉴 구조

범례: `(기존)` 기존 화면 재사용 · `(신규)` 이번에 분리/생성한 화면 · `(빈)` TemplatePage · `[admin]` 관리자 전용 · `[perm]` 권한 필요

```
📋 게시판
├ 공지사항            → /announcements            (기존)
├ 자유게시판          → /board/free               (빈)
├ 자료실              → /board/archive            (빈)
├ 일정                → /calendar                 (기존)
├ 취업규칙            → /board/employment-rules   (빈)
├ 근로기준법 및 법령  → /board/labor-law          (빈)
└ 안전보건관리규정    → /board/safety             (빈)

💼 영업관리  [perm: sales:view]
├ 영업현황            → /sales/status             (신규: 영업대응 '데이터 집계' 탭 분리)
├ 주문목록            → /sales/orders             (빈)
├ 영업대응            → /sales                     (기존 SalesManagementView)
├ 고객관리            → /partners                  (기존 거래처)
├ 대금관리            → /sales/payments           (빈)
└ 견적설정            → /admin                     (신규: 기존 '관리' 페이지 이동) [admin]

🏭 생산관리
├ 생산현황            → /production                (기존) [perm: production:view]
├ 생산일정            → /production/schedule       (빈)  [perm: production:view]
├ 구매관리 ▸ (부모)                                      [perm: purchase:view]
│   ├ 구매목록        → /purchase-orders           (기존 발주)
│   └ 공급처 목록     → /production/suppliers      (빈)
├ 생산이력            → /production/history        (빈)  [perm: production:view]
├ 작업 표준서         → /production/work-standards (빈)  [perm: production:view]
├ 코드관리 ▸ (하이브리드) → /codes                  (기존) [perm: code:edit]
│   ├ 부품            → /parts                     (기존) [perm: part:view]
│   └ BOM             → /bom                       (기존) [perm: bom:view]
└ 재고목록            → /inventory                 (기존) [perm: inventory:view]

💻 개발관리
├ 개발현황            → /dev/status               (빈)
├ 프로젝트 등록       → /dev/project-new          (빈)
├ 프로젝트            → /dev/projects             (빈)
├ 기술지원            → /dev/support              (빈)
└ 다운로드            → /dev/downloads            (빈)

🏢 경영관리
├ 대시보드            → /mgmt/dashboard            (신규: '/'와 동일한 DashboardView)
├ 전자결재            → /mgmt/approvals            (신규: 관리 '전자결재' 탭 분리) [admin]
├ 인사관리 ▸ (부모)
│   ├ 휴가관리        → /leave-admin               (기존 연차관리) [perm: leave:manage]
│   └ 인사기록부      → /mgmt/hr-records          (빈)
├ 일정등록            → /mgmt/schedule-new        (빈)
├ 조직관리            → /mgmt/organization         (신규: 관리 '부서 관리' 탭 분리) [admin]
├ 자산관리            → /mgmt/assets              (빈)
├ 문서관리            → /mgmt/documents           (빈)
├ 리스크관리          → /mgmt/risk                (빈)
└ 경영컨트롤          → /mgmt/control             (빈)

👤 내 메뉴
├ 자주쓰는 메뉴       → /me/favorites             (빈)
├ 대시보드            → /me/dashboard             (빈)
├ 내일정              → /me/schedule              (빈)
├ 대화                → /me/messages             (빈)
├ 파일                → /me/files                (빈)
├ 사진                → /me/photos               (빈)
├ 활동                → /me/activity             (빈)
├ 연락처              → /me/contacts             (빈)
├ 전자결재            → /approvals                 (기존 ApprovalListView) [perm: approval:view]
├ 사용자 프로필       → /me/profile               (빈)
├ 내 휴가현황         → /my-leave                  (기존 내 연차)
└ 비밀번호변경        → /me/change-password        (신규: 모달 → 페이지)

⚙️ 설정
├ 사용자목록          → /settings/users            (신규: 관리 '사용자 관리' 탭 분리) [admin]
├ 권한관리            → /settings/permissions      (신규: 관리 '권한관리'+'권한적용' 통합, 3탭) [admin]
├ 시스템관리          → /settings/system           (신규: 관리 '시스템 관리' 탭 분리) [admin]
└ 파일관리자          → /settings/files           (빈)
```

> navbar 평면 링크는 전부 제거되어 그룹 버튼만 남았다.

---

## 4. '관리(AdminView)' 페이지 분해

기존 `/admin`(AdminView)의 탭들을 각 메뉴 그룹 아래 **독립 페이지**로 옮겼다. 분리된 페이지는 해당 패널 컴포넌트를 그대로 재사용(래퍼 뷰)하거나 인라인 내용을 추출해 구성했다.

| 기존 관리 탭 | 이동 위치 | 새 라우트 / 뷰 |
|---|---|---|
| 시스템 관리 | 설정 > 시스템관리 | `/settings/system` → `SystemManagementView.vue` (인라인 추출) |
| 전자결재(관리) | 경영관리 > 전자결재 | `/mgmt/approvals` → `ApprovalAdminView.vue` (`ApprovalAdminPanel` 래핑) |
| 사용자 관리 | 설정 > 사용자목록 | `/settings/users` → `UserManagementView.vue` (`UserManagementPanel` 래핑) |
| 부서 관리 | 경영관리 > 조직관리 | `/mgmt/organization` → `OrganizationView.vue` (`DepartmentManagementPanel` 래핑) |
| 권한 관리 + 권한 적용 | 설정 > 권한관리 | `/settings/permissions` → `PermissionManagementView.vue` (3탭 통합) |
| 견적 설정 · 회사 계좌 | 영업관리 > 견적설정 | `/admin`(AdminView 유지, 제목만 '견적설정'으로 변경) |

### 4.1 권한관리 3탭 통합
`PermissionManagementView.vue`는 상위 3탭으로 구성:
1. **역할·권한 매트릭스** / 2. **사용자역할배정** → `RolePermissionPanel`(내부 서브탭을 상위에서 제어)
3. **권한적용** → `ModulePolicyPanel`

이를 위해 `RolePermissionPanel.vue`에 props를 추가했다.
- `hideTabs?: boolean` — 내부 탭바 숨김(상위 페이지가 탭 제어)
- `tab?: 'roles' | 'assign'` — 외부에서 서브탭 지정
→ 상위 페이지의 매트릭스/배정 탭이 단일 `RolePermissionPanel` 인스턴스의 서브탭만 전환(탭바 중복 없음).

### 4.2 분해 후 AdminView
- 제목 '관리' → **'견적설정'**, 남은 탭은 **견적 설정 · 회사 계좌** 2개.
- 접근 경로: **영업관리 > 견적설정** (관리자 전용). URL `/admin`은 유지(모바일 런처 `modules/registry.ts` 호환).

---

## 5. 기타 변경

### 5.1 `/` 대시보드 → 파일명 변경 + 메뉴 연결
- `HomeView.vue` → **`DashboardView.vue`로 이름 변경**.
- `/`(home)와 **경영관리 > 대시보드(`/mgmt/dashboard`)**가 동일한 `DashboardView`를 사용(홈 = 대시보드).

### 5.2 비밀번호 변경: 모달 → 페이지
- 네비바의 '비밀번호 변경' 버튼 제거.
- **내 메뉴 > 비밀번호변경(`/me/change-password`)** 페이지(`ChangePasswordView.vue`)로 구현.
- 기존 `ChangePasswordModal.vue`는 미사용(삭제 후보).

### 5.3 App.vue 컴포넌트 분리
- 약 600줄 → 약 40줄. 네비바/사이드바 로직을 `NavBar.vue` / `SideBar.vue`로 이관.
- 공유 메뉴 로직은 `useMenu.ts`, 공유 상태(사이드바 접힘·배지)는 `useNavState.ts` 싱글톤.
- 알림 종(인앱 알림)·웹푸시·배지 타이머·`xm:announce-refresh` 리스너는 NavBar로 이동.

### 5.4 레이아웃
- 네비바: 화면 맨 위 **full-width 고정(`sticky top-0 z-30`)**, 맨 왼쪽부터 **햄버거 → 로고 → 그룹 버튼 → 알림/사용자**.
- 햄버거: 데스크톱은 좌측 사이드바 접기/펼치기, 모바일은 상단 드롭다운 토글.
- 사이드바: 네비바 아래 `sticky top-14`로 고정, 내용이 길면 자체 스크롤.

---

## 6. 신규/변경 파일

**신규**
- `src/composables/useMenu.ts`, `src/composables/useNavState.ts`
- `src/components/NavBar.vue`, `src/components/SideBar.vue`
- `src/views/SystemManagementView.vue`, `ApprovalAdminView.vue`, `UserManagementView.vue`, `OrganizationView.vue`, `PermissionManagementView.vue`, `SalesStatusView.vue`, `ChangePasswordView.vue`
- `src/router/menu.ts`

**주요 변경**
- `src/App.vue` (셸로 축소), `src/router/index.ts` (라우트 다수 추가/연결)
- `src/views/AdminView.vue` (탭 분해, 견적설정으로 축소)
- `src/views/DashboardView.vue` (← HomeView.vue 이름 변경)
- `src/views/SalesManagementView.vue` ('데이터 집계' 탭 제거)
- `src/components/RolePermissionPanel.vue` (`hideTabs`/`tab` props 추가)
- `src/views/TemplatePage.vue` (`<script setup lang="ts">`)
- `src/modules/registry.ts` (admin 런처 '견적설정'으로 라벨 변경)

---

## 7. 남은 작업 (TODO)

아래 메뉴는 현재 **빈 페이지(TemplatePage)**로, 실제 화면 구현이 필요하다.

- **게시판**: 자유게시판, 자료실, 취업규칙, 근로기준법 및 법령, 안전보건관리규정
- **영업관리**: 주문목록, 대금관리
- **생산관리**: 생산일정, 생산이력, 작업 표준서, 구매관리 > 공급처 목록
- **개발관리**: 개발현황, 프로젝트 등록, 프로젝트, 기술지원, 다운로드
- **경영관리**: 인사관리 > 인사기록부, 일정등록, 자산관리, 문서관리, 리스크관리, 경영컨트롤
- **내 메뉴**: 자주쓰는 메뉴, 대시보드, 내일정, 대화, 파일, 사진, 활동, 연락처, 사용자 프로필
- **설정**: 파일관리자

### 검토 필요 항목
- **구매관리 vs 발주**: '구매관리 > 구매목록'이 기존 발주(`/purchase-orders`)를 가리킴. '구매관리'라는 새 개념과 기존 발주의 역할 정리 필요.
- **내 메뉴 대시보드/내일정**: 기존 `DashboardView`/`CalendarView` 연결 또는 개인용 별도 구현 결정 필요.
- **권한 체계**: 신규 빈 페이지들의 접근 권한(perm) 기준 확정 필요(현재 대부분 로그인만).
- `ChangePasswordModal.vue` 삭제 여부.
