import { createRouter, createWebHistory } from 'vue-router'
import { logPageView } from '@/api/activity'
// 라우트 지연 로딩(코드 분할): 화면별 청크로 쪼개 첫 로딩을 가볍게(특히 모바일).
// 라우트 정의의 component 참조는 그대로 두고, 정적 import만 동적 import 함수로 교체.
const DashboardView = () => import('../views/management/DashboardView.vue')
const CodeMasterView = () => import('../views/production/CodeMasterView.vue')
const CodeSimulatorView = () => import('../views/production/CodeSimulatorView.vue')
const PartsView = () => import('../views/production/PartsView.vue')
const PartnersView = () => import('../views/sales/PartnersView.vue')
const BOMView = () => import('../views/production/BOMView.vue')
const BomEditorView = () => import('../views/production/BomEditorView.vue')
const InventoryView = () => import('../views/production/InventoryView.vue')
const PurchaseOrderView = () => import('../views/production/PurchaseOrderView.vue')
const PurchaseOrderPrintView = () => import('../views/production/PurchaseOrderPrintView.vue')
const WorkOrderView = () => import('../views/production/WorkOrderView.vue')
const ProductionRequestView = () => import('../views/production/ProductionRequestView.vue')
const ProductionStatusView = () => import('../views/production/ProductionStatusView.vue')
const ProductionManagementView = () => import('../views/production/ProductionManagementView.vue')
const SalesManagementView = () => import('../views/sales/SalesManagementView.vue')
const CalendarView = () => import('../views/board/CalendarView.vue')
const AdminView = () => import('../views/sales/AdminView.vue')
const ApprovalListView = () => import('../views/mypage/ApprovalListView.vue')
const ApprovalWriteView = () => import('../views/mypage/ApprovalWriteView.vue')
const ApprovalDetailView = () => import('../views/mypage/ApprovalDetailView.vue')
const AboutView = () => import('../views/AboutView.vue')
const HelpView = () => import('../views/HelpView.vue')
const LoginView = () => import('../views/LoginView.vue')
const AppsLauncherView = () => import('../views/AppsLauncherView.vue')
const LeaveManagementView = () => import('../views/management/LeaveManagementView.vue')
const MyLeaveView = () => import('../views/mypage/MyLeaveView.vue')
const AnnouncementView = () => import('../views/board/AnnouncementView.vue')
const FreeBoardView = () => import('../views/board/FreeBoardView.vue')
// 게시판 그룹의 빈 페이지들 — 실제 화면이 없는 메뉴는 TemplatePage(빈 페이지)로 연결
const TemplatePage = () => import('../views/TemplatePage.vue')
const SalesStatusView = () => import('../views/sales/SalesStatusView.vue')
const SystemManagementView = () => import('../views/settings/SystemManagementView.vue')
const DbAdminView = () => import('../views/settings/DbAdminView.vue')
const ApprovalAdminView = () => import('../views/management/ApprovalAdminView.vue')
const UserManagementView = () => import('../views/settings/UserManagementView.vue')
const OrganizationView = () => import('../views/management/OrganizationView.vue')
const ScheduleRegisterView = () => import('../views/management/ScheduleRegisterView.vue')
const PermissionManagementView = () => import('../views/settings/PermissionManagementView.vue')
const ChangePasswordView = () => import('../views/mypage/ChangePasswordView.vue')
import { can, canAny, hasPermStrict } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      // 로그인 후 랜딩(대시보드) — '경영관리 > 대시보드'(/mgmt/dashboard)와 동일 화면
      path: '/',
      name: 'home',
      component: DashboardView,
    },
    // 모바일 모듈 런처(앱 메뉴) — 로그인 필요(beforeEach 규칙 적용)
    {
      path: '/menu',
      name: 'apps-launcher',
      component: AppsLauncherView,
    },
    {
      path: '/codes',
      name: 'codes',
      component: CodeMasterView,
      meta: { perm: 'code:edit' },  // 코드 '관리' 화면 → BOM/코드 관리자(code:edit)·ADMIN만. 드롭다운 읽기(code:view)와 분리
    },
    {
      path: '/code-simulator',
      name: 'code-simulator',
      component: CodeSimulatorView,
      meta: { perm: 'code:view' },
    },
    {
      path: '/parts',
      name: 'parts',
      component: PartsView,
      meta: { perm: 'part:view' },
    },
    {
      path: '/partners',
      name: 'partners',
      component: PartnersView,
      meta: { perm: 'partner:view' },
    },
    {
      // [DEPRECATED] /suppliers -> /partners 리다이렉트
      // 기존 북마크/링크 호환성을 위해 유지
      path: '/suppliers',
      redirect: '/partners',
    },
    {
      path: '/bom',
      name: 'bom',
      component: BOMView,
      meta: { perm: 'bom:view' },
    },
    {
      path: '/bom/:partId/edit',
      name: 'bom-editor',
      component: BomEditorView,
      meta: { perm: 'bom:view' },
    },
    {
      path: '/inventory',
      name: 'inventory',
      component: InventoryView,
      meta: { perm: 'inventory:view' },
    },
    {
      path: '/purchase-orders',
      name: 'purchase-orders',
      component: PurchaseOrderView,
      meta: { perm: 'purchase:view' },
    },
    {
      path: '/print/purchase-order/:id',
      name: 'purchase-order-print',
      component: PurchaseOrderPrintView,
      meta: { layout: 'print' },
    },
    // 영업관리 통합 라우트 (v0.24.0)
    {
      path: '/sales',
      name: 'sales',
      component: SalesManagementView,
      meta: { perm: 'sales:view' },
    },
    // 영업 대응 현황 (v0.27.0) → 영업관리 탭으로 통합
    {
      path: '/sales-activity',
      redirect: '/sales?tab=activity',
    },
    // 생산관리 통합 라우트 (v0.21.0)
    {
      path: '/production',
      name: 'production',
      component: ProductionManagementView,
      meta: { perm: 'production:view' },
    },
    // 기존 경로 리다이렉트 (하위 호환성)
    {
      path: '/production/requests',
      redirect: '/production?tab=requests',
    },
    {
      // v0.22.0: status 탭이 work-orders에 통합됨
      path: '/production/status',
      redirect: '/production?tab=work-orders',
    },
    {
      path: '/production/work-orders',
      redirect: '/production?tab=work-orders',
    },
    {
      path: '/production-requests',
      redirect: '/production?tab=requests',
    },
    {
      path: '/work-orders',
      redirect: '/production?tab=work-orders',
    },
    {
      path: '/calendar',
      name: 'calendar',
      component: CalendarView,
      // 업무 권한(아무거나 하나) 보유자만 — 전자결재 전용 계정은 차단. App.vue businessViews와 동일 의도.
      meta: { permAny: ['part:view', 'bom:view', 'inventory:view', 'partner:view', 'purchase:view', 'sales:view', 'production:view', 'code:view', 'price:view', 'sales_activity:view'] },
    },
    // 전자결재 (v0.33.0) — 로그인 필요(beforeEach 규칙 적용)
    {
      path: '/approvals',
      name: 'approvals',
      component: ApprovalListView,
      meta: { perm: 'approval:view' },
    },
    {
      path: '/approvals/write',
      name: 'approval-write',
      component: ApprovalWriteView,
    },
    {
      path: '/approvals/:id/edit',
      name: 'approval-edit',
      component: ApprovalWriteView,
    },
    {
      path: '/approvals/:id',
      name: 'approval-detail',
      component: ApprovalDetailView,
    },
    {
      path: '/leave-admin',
      name: 'leave-admin',
      component: LeaveManagementView,
      meta: { permStrict: 'leave:manage' },  // 연차=항상 보호 → 실제 권한 보유자만(경영지원팀/ADMIN)
    },
    {
      path: '/my-leave',
      name: 'my-leave',
      component: MyLeaveView,  // 전 직원 본인 연차 조회(로그인만)
    },
    {
      path: '/announcements',
      name: 'announcements',
      component: AnnouncementView,
      // 공지 읽기=전 직원(로그인만). 부서 타깃은 API가 필터. 권한 게이트 없음(enforce 시에도 전원 접근).
    },
    // ===== 게시판 그룹 — 실제 페이지가 없는 메뉴는 빈 페이지(TemplatePage)로 표시 =====
    // 공지사항(/announcements)·일정(/calendar)은 기존 페이지를 그대로 재사용한다(별도 정의 없음).
    {
      path: '/board/free',
      name: 'board-free',
      component: FreeBoardView,  // 자유게시판: 전 직원(로그인만) 열람/작성
    },
    {
      path: '/board/archive',
      name: 'board-archive',
      component: TemplatePage,
    },
    {
      path: '/board/employment-rules',
      name: 'board-employment-rules',
      component: TemplatePage,
    },
    {
      path: '/board/labor-law',
      name: 'board-labor-law',
      component: TemplatePage,
    },
    {
      path: '/board/safety',
      name: 'board-safety',
      component: TemplatePage,
    },
    // ===== 영업관리 그룹 — '영업대응'은 기존 /sales 재사용, 나머지는 빈 페이지 =====
    {
      path: '/sales/status',
      name: 'sales-status',
      component: SalesStatusView,  // 영업대응에서 분리한 '데이터 집계'
      meta: { perm: 'sales:view' },
    },
    {
      path: '/sales/orders',
      name: 'sales-orders',
      component: TemplatePage,
      meta: { perm: 'sales:view' },
    },
    {
      path: '/sales/payments',
      name: 'sales-payments',
      component: TemplatePage,
      meta: { perm: 'sales:view' },
    },
    // ===== 생산관리 그룹 — 실제 페이지 없는 메뉴는 빈 페이지(TemplatePage) =====
    {
      path: '/production/schedule',
      name: 'production-schedule',
      component: TemplatePage,
      meta: { perm: 'production:view' },
    },
    {
      // 구매관리 > 공급처 목록 (빈 페이지)
      path: '/production/suppliers',
      name: 'production-suppliers',
      component: TemplatePage,
      meta: { perm: 'purchase:view' },
    },
    {
      path: '/production/history',
      name: 'production-history',
      component: TemplatePage,
      meta: { perm: 'production:view' },
    },
    {
      path: '/production/work-standards',
      name: 'production-work-standards',
      component: TemplatePage,
      meta: { perm: 'production:view' },
    },
    // ===== 개발관리 그룹 — 모두 빈 페이지(TemplatePage) =====
    {
      path: '/dev/status',
      name: 'dev-status',
      component: TemplatePage,
    },
    {
      path: '/dev/project-new',
      name: 'dev-project-new',
      component: TemplatePage,
    },
    {
      path: '/dev/projects',
      name: 'dev-projects',
      component: TemplatePage,
    },
    {
      path: '/dev/support',
      name: 'dev-support',
      component: TemplatePage,
    },
    {
      path: '/dev/downloads',
      name: 'dev-downloads',
      component: TemplatePage,
    },
    // ===== 경영관리 그룹 — 휴가관리(/leave-admin)만 기존 페이지, 나머지는 빈 페이지 =====
    {
      // 경영관리 > 대시보드 — '/'(home)와 동일한 대시보드 화면
      path: '/mgmt/dashboard',
      name: 'mgmt-dashboard',
      component: DashboardView,
    },
    {
      // 관리 페이지에서 분리한 '전자결재 관리' — 기존과 동일하게 관리자 전용
      path: '/mgmt/approvals',
      name: 'mgmt-approvals',
      component: ApprovalAdminView,
      meta: { requiresAdmin: true },
    },
    {
      path: '/mgmt/hr-records',
      name: 'mgmt-hr-records',
      component: TemplatePage,
    },
    {
      path: '/mgmt/schedule-new',
      // 일정 등록(행사/휴가/외근/출장) — 게시판 > 일정 캘린더에 표시된다. 로그인한 전 직원.
      name: 'mgmt-schedule-new',
      component: ScheduleRegisterView,
    },
    {
      // 관리 페이지에서 분리한 '부서 관리' — 관리자 전용
      path: '/mgmt/organization',
      name: 'mgmt-organization',
      component: OrganizationView,
      meta: { requiresAdmin: true },
    },
    {
      path: '/mgmt/assets',
      name: 'mgmt-assets',
      component: TemplatePage,
    },
    {
      path: '/mgmt/documents',
      name: 'mgmt-documents',
      component: TemplatePage,
    },
    {
      path: '/mgmt/risk',
      name: 'mgmt-risk',
      component: TemplatePage,
    },
    {
      path: '/mgmt/control',
      name: 'mgmt-control',
      component: TemplatePage,
    },
    // ===== 내 메뉴 그룹 — 내 휴가현황(/my-leave)만 기존 페이지, 나머지는 빈 페이지 =====
    {
      path: '/me/favorites',
      name: 'me-favorites',
      component: TemplatePage,
    },
    {
      path: '/me/profile',
      name: 'me-profile',
      component: TemplatePage,
    },
    // 내 메뉴 개인 허브 — 모두 빈 페이지(TemplatePage)
    {
      path: '/me/dashboard',
      name: 'me-dashboard',
      component: TemplatePage,
    },
    {
      path: '/me/schedule',
      name: 'me-schedule',
      component: TemplatePage,
    },
    {
      path: '/me/messages',
      name: 'me-messages',
      component: TemplatePage,
    },
    {
      path: '/me/files',
      name: 'me-files',
      component: TemplatePage,
    },
    {
      path: '/me/photos',
      name: 'me-photos',
      component: TemplatePage,
    },
    {
      path: '/me/activity',
      name: 'me-activity',
      component: TemplatePage,
    },
    {
      path: '/me/contacts',
      name: 'me-contacts',
      component: TemplatePage,
    },
    {
      // 내 메뉴 > 비밀번호변경 (기존 모달을 페이지로)
      path: '/me/change-password',
      name: 'me-change-password',
      component: ChangePasswordView,
    },
    // ===== 설정 그룹 — 모두 빈 페이지(TemplatePage) =====
    {
      // 관리 페이지에서 분리한 '사용자 관리' — 관리자 전용
      path: '/settings/users',
      name: 'settings-users',
      component: UserManagementView,
      meta: { requiresAdmin: true },
    },
    {
      // 관리 페이지의 '권한 관리' + '권한 적용'을 통합 — 관리자 전용
      path: '/settings/permissions',
      name: 'settings-permissions',
      component: PermissionManagementView,
      meta: { requiresAdmin: true },
    },
    {
      // 관리 페이지에서 분리한 '시스템 관리'(DB 백업/동기화) — 관리자 전용
      path: '/settings/system',
      name: 'settings-system',
      component: SystemManagementView,
      meta: { requiresAdmin: true },
    },
    {
      // DB관리자 — DB/테이블을 골라 레코드 원본(raw data) 조회(읽기 전용), 관리자 전용
      path: '/settings/db',
      name: 'settings-db',
      component: DbAdminView,
      meta: { requiresAdmin: true },
    },
    {
      path: '/settings/files',
      name: 'settings-files',
      component: TemplatePage,
    },
    {
      path: '/admin',
      name: 'admin',
      component: AdminView,
      meta: { requiresAdmin: true },
    },
    {
      path: '/about',
      name: 'about',
      component: AboutView,
    },
    {
      path: '/help',
      name: 'help',
      component: HelpView,
    },
  ],
})

// 모바일(좁은 화면) 여부 — Tailwind lg(1024px) 기준. 모바일 햄버거 메뉴 노출과 동일 기준.
function isMobileViewport(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(max-width: 1023px)').matches
}

// 라우트 가드: 로그인 필수 (v0.28.0)
router.beforeEach((to, _from, next) => {
  const isPublic = to.meta.public === true
  const token = localStorage.getItem('access_token')

  // 관리자 전용 라우트: role === 'ADMIN' 만 허용
  let isAdmin = false
  try {
    const u = JSON.parse(localStorage.getItem('user') || 'null')
    isAdmin = u?.role === 'ADMIN'
  } catch { /* ignore */ }

  if (!isPublic && !token) {
    next({ name: 'login' })
  } else if (to.name === 'login' && token) {
    // 로그인 직후: 모바일은 모바일 홈(/menu), 데스크톱은 대시보드(/)
    next(isMobileViewport() ? { name: 'apps-launcher' } : { path: '/' })
  } else if (to.meta.requiresAdmin && !isAdmin) {
    next({ path: '/' })
  } else if (to.meta.permStrict && !hasPermStrict(to.meta.permStrict as string)) {
    // 항상 enforce되는 민감 라우트(연차 등): 전역 모드 무관 실제 권한 보유자만
    next({ path: '/' })
  } else if (to.meta.permAny && !canAny(to.meta.permAny as string[])) {
    // 여러 권한 중 하나라도 있으면 허용(예: 일정=업무 권한 보유자). 전자결재 전용 계정 차단.
    next({ path: '/' })
  } else if (to.meta.perm && !can(to.meta.perm as string)) {
    // v0.41.0: enforce 모드에서 권한 없는 라우트 접근 차단(비enforce/관리자는 can()이 true)
    next({ path: '/' })
  } else if (to.name === 'home' && isMobileViewport()) {
    // 모바일에서 홈(/) 진입 시 모바일 홈(앱스 런처)으로. 데스크톱은 대시보드 유지.
    next({ name: 'apps-launcher' })
  } else {
    next()
  }
})

// 배포로 청크 해시가 바뀐 뒤 열어둔 옛 탭이 사라진 청크를 lazy-load 하다 실패하면
// (Failed to fetch dynamically imported module) 최신 번들로 1회 자동 새로고침해 복구.
// 무한 루프 방지: sessionStorage 플래그로 1회만, 성공 이동 시 해제.
const CHUNK_RELOAD_KEY = 'xm:chunk-reload'
function isChunkLoadError(err: unknown): boolean {
  const msg = (err as Error)?.message || ''
  return /dynamically imported module|Importing a module script failed|error loading dynamically imported module|Failed to fetch/i.test(msg)
}
router.onError((error, to) => {
  if (isChunkLoadError(error) && !sessionStorage.getItem(CHUNK_RELOAD_KEY)) {
    sessionStorage.setItem(CHUNK_RELOAD_KEY, '1')
    // 의도한 경로로 전체 문서 로드 → 최신 index.html + 새 청크 수신
    window.location.assign(to?.fullPath || window.location.pathname)
  }
})
// 새 배포 감지: 열어둔 탭은 이미 받은 화면 코드를 메모리에 계속 써서 배포 후에도 옛 화면이 보인다.
// 서버 index.html 의 엔트리 번들이 바뀌었으면 '다음 화면 이동' 때 전체 로드로 최신 화면을 받는다
// (작성 중인 화면을 그 자리에서 새로고침하지 않음). 개발 서버(/src/main.ts)에서는 동작하지 않음.
const ENTRY_RE = /\/assets\/index-[\w-]+\.js/
const currentEntry =
  document.querySelector<HTMLScriptElement>('script[type="module"][src*="/assets/index-"]')?.src.match(ENTRY_RE)?.[0] || ''
let newBuildReady = false
let lastBuildCheck = 0
async function checkNewBuild() {
  if (!currentEntry || newBuildReady || Date.now() - lastBuildCheck < 60_000) return
  lastBuildCheck = Date.now()
  try {
    const res = await fetch('/index.html', { cache: 'no-store' })
    const latest = res.ok ? (await res.text()).match(ENTRY_RE)?.[0] : undefined
    if (latest && latest !== currentEntry) newBuildReady = true
  } catch { /* 오프라인 등 — 다음 이동 때 재확인 */ }
}
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') checkNewBuild()
})
router.beforeEach((to, from) => {
  if (newBuildReady && from.matched.length) {
    window.location.assign(to.fullPath)
    return false
  }
  checkNewBuild()
})
router.afterEach((to) => {
  // 정상 이동에 성공하면 플래그 해제(이후 다른 배포에서도 다시 복구 가능)
  if (sessionStorage.getItem(CHUNK_RELOAD_KEY)) sessionStorage.removeItem(CHUNK_RELOAD_KEY)
  // 활동 로그: 누가 어느 화면을 봤는지 (fire-and-forget)
  logPageView(to.name as string | undefined, to.query as Record<string, unknown>)
})

export default router
