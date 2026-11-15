"""
권한 레지스트리 (v0.40.0)

RBAC 모듈×동작의 단일 진실원천(Single Source of Truth).
- 앱 부팅 시 이 레지스트리를 기준으로 `permissions` 테이블을 upsert 한다.
- 권한 코드는 항상 `module:action` 형식.
- 가산적(additive): 여기서 권한을 정의만 하며, 기존 업무 엔드포인트에는 검사를 부착하지 않는다.
"""

from typing import Dict, List

# 동작(action) 한글 라벨 맵
ACTION_LABELS: Dict[str, str] = {
    "view": "조회",
    "create": "생성",
    "edit": "수정",
    "delete": "삭제",
    "export": "출력",
    "approve": "승인",
    "manage": "관리",
    "backup": "백업",
    "admin": "관리자",
    "ci_delete": "CI 삭제",
}

# 모듈 정의: (코드, 한글 라벨, [동작...])
MODULE_DEFS: List[tuple] = [
    ("dashboard", "대시보드", ["view"]),
    ("code", "코드관리", ["view", "create", "edit", "delete"]),
    ("part", "부품", ["view", "create", "edit", "delete"]),
    ("bom", "BOM", ["view", "create", "edit", "delete"]),
    ("partner", "거래처", ["view", "create", "edit", "delete"]),
    ("inventory", "재고", ["view", "create", "edit", "delete"]),
    ("purchase", "발주", ["view", "create", "edit", "delete"]),
    ("workorder", "작업지시", ["view", "create", "edit", "delete"]),
    ("production", "생산요청", ["view", "create", "edit", "delete"]),
    ("production_simple", "생산 간편처리", ["view"]),  # v0.71.0 간편처리 탭 접근 권한(생산팀 상태보드)
    ("price", "원가", ["view", "edit"]),
    # ci_delete: CI 문서 삭제(특정인 별도 부여용). 견적·PI 삭제는 계속 관리자 전용 —
    # sales:delete 는 다수 역할이 보유하고 있어 문서 삭제와 연결하지 않음(sales_document.delete_router).
    ("sales", "영업문서", ["view", "create", "edit", "delete", "export", "ci_delete"]),
    ("sales_activity", "영업활동", ["view", "create", "edit", "delete"]),
    ("approval", "전자결재", ["view", "create", "approve", "admin"]),
    ("project", "프로젝트", ["view", "manage"]),
    ("user", "사용자관리", ["view", "manage"]),
    ("system", "시스템관리", ["manage", "backup"]),
    ("leave", "연차관리", ["manage"]),  # v0.45.0 연차 관리(경영지원팀) — 모든 화면 leave:manage(읽기 전용 분리 안 함)
    ("announcement", "공지사항", ["view", "create", "edit", "delete", "manage"]),  # v0.50.0 회사 공지사항(읽기=전 직원, 쓰기=announcement:manage)
]

# 모듈 코드 -> 한글 라벨
MODULE_LABELS: Dict[str, str] = {code: label for code, label, _ in MODULE_DEFS}


def _action_label(action: str) -> str:
    """동작 코드에 대한 한글 라벨 반환 (미정의 시 코드 그대로)."""
    return ACTION_LABELS.get(action, action)


def build_permissions() -> List[dict]:
    """
    레지스트리로부터 전체 권한 목록을 생성한다.
    각 항목: {code, module, action, label}
      - code: "module:action"
      - label: "<모듈 한글> <동작 한글>" (예: "부품 조회")
    """
    result: List[dict] = []
    for module, module_label, actions in MODULE_DEFS:
        for action in actions:
            result.append(
                {
                    "code": f"{module}:{action}",
                    "module": module,
                    "action": action,
                    "label": f"{module_label} {_action_label(action)}",
                }
            )
    return result


# 전체 권한 목록 (단일 진실원천)
ALL_PERMISSIONS: List[dict] = build_permissions()

# 빠른 조회용 코드 집합
ALL_PERMISSION_CODES = {p["code"] for p in ALL_PERMISSIONS}

# 와일드카드 (전체 권한) 표식
WILDCARD = "*"

# EMPLOYEE(일반사원) 기본 부여 권한
# code:view 는 단위/부품유형/재질 등 '기초 데이터 드롭다운'을 거의 모든 입력화면이 호출하므로
# 전 사원 공통으로 부여한다(코드 '관리' 화면 노출은 code:edit 로 분리 — App.vue/router).
DEFAULT_EMPLOYEE_PERMISSIONS: List[str] = [
    "dashboard:view",
    "approval:view",
    "approval:create",
    "code:view",
    "part:view",
    "bom:view",
    "inventory:view",
    "partner:view",
    "sales:view",
    "project:view",
    "announcement:view",  # v0.50.0 공지 열람(전 직원 — 부서 타깃은 API 레벨에서 필터)
]
