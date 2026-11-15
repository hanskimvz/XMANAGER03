// 네비게이션 메뉴 구성
// ----------------------------------------------------------------------------
// 상단 네비바에는 "메뉴 그룹"이 버튼으로 표시되고, 그룹을 누르면
// 왼쪽 사이드바에 그 그룹의 하위 메뉴(children)가 나타난다.
// 메뉴를 추가/변경할 때는 이 파일만 수정하면 된다.
//
// - path: 라우터 경로. 실제 페이지가 없는 항목은 router/index.ts 에서
//         TemplatePage.vue(빈 페이지)로 연결해 두었다.
//         하위 children을 가진 '부모' 항목은 path를 생략할 수 있다(클릭 시 펼침).
// - perm: (선택) 보기 권한 키. 지정하면 해당 권한 보유자에게만 메뉴가 보인다.
// - children: (선택) 2단 서브메뉴. 사이드바에서 부모 아래로 펼쳐진다.

export interface MenuItem {
  label: string
  path?: string
  perm?: string
  adminOnly?: boolean // true면 관리자(role=ADMIN)에게만 보임
  children?: MenuItem[]
}

export interface MenuGroup {
  key: string
  label: string
  icon?: string
  perm?: string // (선택) 그룹 노출 권한 키. 지정하면 해당 권한 보유자에게만 그룹이 보인다.
  children: MenuItem[]
}

export const menuGroups: MenuGroup[] = [
  {
    key: 'board',
    label: '게시판',
    icon: '📋',
    children: [
      { label: '공지사항', path: '/announcements' },        // 기존 페이지 재사용
      { label: '자유게시판', path: '/board/free' },          // FreeBoardView
      { label: '자료실', path: '/board/archive' },           // TemplatePage(빈 페이지)
      { label: '일정', path: '/calendar' },                  // 기존 페이지 재사용
      { label: '취업규칙', path: '/board/employment-rules' }, // TemplatePage(빈 페이지)
      { label: '근로기준법 및 법령', path: '/board/labor-law' }, // TemplatePage(빈 페이지)
      { label: '안전보건관리규정', path: '/board/safety' },   // TemplatePage(빈 페이지)
    ],
  },
  {
    key: 'sales',
    label: '영업관리',
    icon: '💼',
    perm: 'sales:view',
    children: [
      { label: '영업현황', path: '/sales/status' },     // TemplatePage(빈 페이지)
      { label: '주문목록', path: '/sales/orders' },      // TemplatePage(빈 페이지)
      { label: '영업대응', path: '/sales' },             // 기존 영업관리 페이지 재사용
      { label: '고객관리', path: '/partners' },          // 기존 거래처 페이지 재사용
      { label: '대금관리', path: '/sales/payments' },    // TemplatePage(빈 페이지)
      { label: '견적설정', path: '/admin', adminOnly: true }, // 기존 '관리' 페이지(견적 설정·회사 계좌) 이동, 관리자 전용
    ],
  },
  {
    key: 'production',
    label: '생산관리',
    icon: '🏭',
    // 항목별 권한이 제각각이라 그룹 perm은 두지 않고, 보이는 하위 메뉴가 하나라도 있으면 그룹 노출
    children: [
      { label: '생산현황', path: '/production', perm: 'production:view' },             // 기존 생산관리 페이지 재사용
      { label: '생산일정', path: '/production/schedule', perm: 'production:view' },     // TemplatePage(빈 페이지)
      // 구매관리: 2단 서브메뉴(부모) — 클릭 시 하위 메뉴 펼침
      {
        label: '구매관리',
        perm: 'purchase:view',
        children: [
          { label: '구매목록', path: '/purchase-orders', perm: 'purchase:view' },   // 기존 발주 페이지 이동
          { label: '공급처 목록', path: '/production/suppliers', perm: 'purchase:view' }, // TemplatePage(빈 페이지)
        ],
      },
      { label: '생산이력', path: '/production/history', perm: 'production:view' },      // TemplatePage(빈 페이지)
      { label: '작업 표준서', path: '/production/work-standards', perm: 'production:view' }, // TemplatePage(빈 페이지)
      // 코드관리: path(코드 페이지) + children(부품·BOM) 하이브리드 — 라벨 클릭=이동, 쉐브론=펼침
      {
        label: '코드관리',
        path: '/codes',
        perm: 'code:edit',
        children: [
          { label: '부품', path: '/parts', perm: 'part:view' }, // 기존 부품 페이지 이동
          { label: 'BOM', path: '/bom', perm: 'bom:view' },     // 기존 BOM 페이지 이동
        ],
      },
      { label: '재고목록', path: '/inventory', perm: 'inventory:view' },               // 기존 재고 페이지 이동
    ],
  },
  {
    key: 'dev',
    label: '개발관리',
    icon: '💻',
    children: [
      { label: '개발현황', path: '/dev/status' },       // TemplatePage(빈 페이지)
      { label: '프로젝트 등록', path: '/dev/project-new' }, // TemplatePage(빈 페이지)
      { label: '프로젝트', path: '/dev/projects' },      // TemplatePage(빈 페이지)
      { label: '기술지원', path: '/dev/support' },       // TemplatePage(빈 페이지)
      { label: '다운로드', path: '/dev/downloads' },     // TemplatePage(빈 페이지)
    ],
  },
  {
    key: 'management',
    label: '경영관리',
    icon: '🏢',
    children: [
      { label: '대시보드', path: '/mgmt/dashboard' },   // TemplatePage(빈 페이지)
      { label: '전자결재', path: '/mgmt/approvals', adminOnly: true }, // 관리에서 분리한 전자결재 관리(관리자 전용)
      // 인사관리: 2단 부모(순수 부모 — 자체 페이지 없음)
      {
        label: '인사관리',
        children: [
          { label: '휴가관리', path: '/leave-admin', perm: 'leave:manage' }, // 기존 연차관리 이동
          { label: '인사기록부', path: '/mgmt/hr-records' },                 // TemplatePage(빈 페이지)
        ],
      },
      { label: '일정등록', path: '/mgmt/schedule-new' }, // 일정 등록(행사/휴가/외근/출장) → 게시판 > 일정에 표시
      { label: '조직관리', path: '/mgmt/organization', adminOnly: true }, // 관리에서 분리한 부서 관리(관리자 전용)
      { label: '자산관리', path: '/mgmt/assets' },       // TemplatePage(빈 페이지)
      { label: '문서관리', path: '/mgmt/documents' },    // TemplatePage(빈 페이지)
      { label: '리스크관리', path: '/mgmt/risk' },       // TemplatePage(빈 페이지)
      { label: '경영컨트롤', path: '/mgmt/control' },    // TemplatePage(빈 페이지)
    ],
  },
  {
    key: 'me',
    label: '내 메뉴',
    icon: '👤',
    children: [
      { label: '자주쓰는 메뉴', path: '/me/favorites' }, // TemplatePage(빈 페이지)
      { label: '대시보드', path: '/me/dashboard' },      // TemplatePage(빈 페이지)
      { label: '내일정', path: '/me/schedule' },         // TemplatePage(빈 페이지)
      { label: '대화', path: '/me/messages' },           // TemplatePage(빈 페이지)
      { label: '파일', path: '/me/files' },              // TemplatePage(빈 페이지)
      { label: '사진', path: '/me/photos' },             // TemplatePage(빈 페이지)
      { label: '활동', path: '/me/activity' },           // TemplatePage(빈 페이지)
      { label: '연락처', path: '/me/contacts' },         // TemplatePage(빈 페이지)
      { label: '전자결재', path: '/approvals', perm: 'approval:view' }, // 기존 전자결재 이동
      { label: '사용자 프로필', path: '/me/profile' },   // TemplatePage(빈 페이지)
      { label: '내 휴가현황', path: '/my-leave' },       // 기존 내 연차 이동
      { label: '비밀번호변경', path: '/me/change-password' }, // 기존 네비바 비밀번호 변경(모달→페이지)
    ],
  },
  {
    key: 'settings',
    label: '설정',
    icon: '⚙️',
    children: [
      { label: '사용자목록', path: '/settings/users', adminOnly: true }, // 관리에서 분리한 사용자 관리(관리자 전용)
      { label: '권한관리', path: '/settings/permissions', adminOnly: true }, // 관리에서 분리(권한관리+권한적용 통합, 관리자 전용)
      { label: '시스템관리', path: '/settings/system', adminOnly: true }, // 관리에서 분리(DB 백업/동기화) — 관리자 전용
      { label: 'DB관리자', path: '/settings/db', adminOnly: true }, // DB/테이블 raw data 조회(읽기 전용) — 관리자 전용
      { label: '파일관리자', path: '/settings/files' },      // TemplatePage(빈 페이지)
    ],
  },
]

// 그룹에 속한 모든 리프 경로(중첩 children 포함)를 평탄화해 반환.
function collectPaths(items: MenuItem[]): string[] {
  const out: string[] = []
  for (const it of items) {
    if (it.path) out.push(it.path)
    if (it.children) out.push(...collectPaths(it.children))
  }
  return out
}

// 현재 경로가 어느 그룹에 속하는지 찾는다(사이드바 노출/활성 그룹 판단용).
export function findActiveGroup(path: string): MenuGroup | null {
  return (
    menuGroups.find((g) =>
      collectPaths(g.children).some((p) => path === p || path.startsWith(p + '/')),
    ) || null
  )
}
