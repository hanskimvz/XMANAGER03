/**
 * 모듈 레지스트리 (모바일 모듈형 구조 기반)
 *
 * 새 모바일 모듈 추가 시 이 배열에 한 줄 등록하면 런처/메뉴에 자동 노출.
 * mobileReady=false 는 'PC 권장'으로 흐리게 표시(점진 출시).
 */

export interface AppModule {
  key: string
  title: string
  icon: string
  to: string
  description?: string
  mobileReady: boolean
  adminOnly?: boolean
  perm?: string  // 이 권한 보유자만 노출(미지정=전원). 예: 'approval:view'
  badge?: 'approvalPending' | null
}

export const appModules: AppModule[] = [
  {
    key: 'approvals',
    title: '전자결재',
    icon: '📝',
    to: '/approvals',
    perm: 'approval:view',
    description: '기안 작성 / 결재 처리',
    mobileReady: true,
    badge: 'approvalPending',
  },
  {
    key: 'purchase-orders',
    title: '구매관리',
    icon: '🧾',
    to: '/purchase-orders',
    perm: 'purchase:view',
    description: '발주 등록 / 현황',
    mobileReady: false,
  },
  {
    key: 'sales',
    title: '영업관리',
    icon: '💼',
    to: '/sales',
    perm: 'sales:view',
    description: '영업 활동 / PI·CI',
    mobileReady: true,
  },
  {
    key: 'production',
    title: '생산관리',
    icon: '🏭',
    to: '/production',
    perm: 'production:view',
    description: '생산요청 / 작업지시',
    mobileReady: false,
  },
  {
    key: 'inventory',
    title: '재고',
    icon: '📦',
    to: '/inventory',
    perm: 'inventory:view',
    description: '재고 현황',
    mobileReady: false,
  },
  {
    key: 'partners',
    title: '거래처',
    icon: '🤝',
    to: '/partners',
    perm: 'partner:view',
    description: '거래처 정보',
    mobileReady: true,
  },
  {
    key: 'admin',
    title: '견적설정',
    icon: '⚙️',
    to: '/admin',
    description: '견적 자동산출·회사 계좌 설정',
    mobileReady: true,
    adminOnly: true,
  },
]

/** 권한/관리자 필터 적용 목록. has(perm) = 실제 보유 권한 여부(hasPermStrict). */
export function visibleModules(opts: { isAdmin: boolean; has: (perm: string) => boolean }): AppModule[] {
  return appModules.filter((m) => {
    if (m.adminOnly) return opts.isAdmin
    if (m.perm) return opts.has(m.perm)
    return true
  })
}
