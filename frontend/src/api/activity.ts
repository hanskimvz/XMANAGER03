import apiClient from './client'

// 라우트 name → 사람이 읽을 화면명
const PAGE_LABELS: Record<string, string> = {
  home: '대시보드',
  'apps-launcher': '앱 메뉴',
  codes: '코드 관리',
  'code-simulator': '오더코드 시뮬레이터',
  parts: '부품 관리',
  partners: '거래처 관리',
  bom: 'BOM 관리',
  inventory: '재고 관리',
  'purchase-orders': '발주 관리',
  sales: '영업 관리',
  production: '생산 관리',
  calendar: '캘린더',
  approvals: '전자결재',
  'approval-write': '기안 작성',
  'approval-edit': '기안 수정',
  'approval-detail': '결재 문서 상세',
  'leave-admin': '연차 관리',
  'my-leave': '내 연차',
  announcements: '공지사항',
  admin: '관리',
  help: '도움말',
  about: '정보',
}

const APPROVAL_BOX_LABELS: Record<string, string> = {
  drafted: '기안함', pending: '결재대기', done: '완료함', reference: '참조함', execution: '시행함',
}

let _lastPage = ''

/** 화면 이동 시 호출 — 백엔드 로그에 '[화면] 이름(아이디) → 화면명' 기록(fire-and-forget) */
export function logPageView(routeName?: string | null, query?: Record<string, unknown>): void {
  if (!routeName || routeName === 'login' || routeName === 'purchase-order-print') return
  if (!localStorage.getItem('access_token')) return
  let page = PAGE_LABELS[routeName] || routeName
  // 전자결재 함(box) 등 의미있는 쿼리는 함께 표기
  if (routeName === 'approvals' && query?.box) {
    const box = String(query.box)
    page += ` · ${APPROVAL_BOX_LABELS[box] || box}`
  }
  if (page === _lastPage) return // 같은 화면 연속 중복 방지
  _lastPage = page
  apiClient.post('/activity/view', { page }).catch(() => { /* 로그 실패는 무시 */ })
}
