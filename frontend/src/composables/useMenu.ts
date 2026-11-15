// 네비바(NavBar)와 사이드바(SideBar)가 공유하는 메뉴 가시성/활성 그룹 로직.
// router/menu.ts 의 menuGroups 를 권한(perm/adminOnly) 기준으로 필터링한다.
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth, hasPermStrict } from '@/stores/auth'
import { menuGroups, findActiveGroup, type MenuItem } from '@/router/menu'

export function useMenu() {
  const route = useRoute()
  const { isAdmin } = useAuth()

  // 메뉴 항목 가시성
  //  - adminOnly: 관리자에게만
  //  - 리프/하이브리드(자체 path 보유): perm만 맞으면 표시
  //  - 순수 부모(path 없음): 보이는 자식이 하나라도 있어야 표시
  function itemVisible(item: MenuItem): boolean {
    if (item.adminOnly && !isAdmin.value) return false
    const permOk = !item.perm || hasPermStrict(item.perm)
    if (!permOk) return false
    if (item.path) return true
    return !!item.children && item.children.some(itemVisible)
  }

  function visibleItems(items: MenuItem[]): MenuItem[] {
    return items.filter(itemVisible)
  }

  // 2단 서브메뉴(부모 항목의 보이는 자식)
  function visibleSub(item: MenuItem): MenuItem[] {
    return (item.children ?? []).filter(itemVisible)
  }

  // 그룹/항목의 첫 '리프' 경로(중첩 포함) — 그룹 버튼 클릭 시 이동 대상
  function firstLeafPath(items: MenuItem[]): string | undefined {
    for (const it of visibleItems(items)) {
      if (it.children) {
        const p = firstLeafPath(it.children)
        if (p) return p
      } else if (it.path) {
        return it.path
      }
    }
    return undefined
  }

  // 그룹: perm 조건을 만족하고, 보이는 하위 항목이 하나라도 있으면 노출
  const visibleGroups = computed(() =>
    menuGroups.filter(
      (g) => (!g.perm || hasPermStrict(g.perm)) && visibleItems(g.children).length > 0,
    ),
  )

  const activeGroup = computed(() => findActiveGroup(route.path))
  // 현재 활성 그룹에서 '보이는' 하위 메뉴만(사이드바 렌더용)
  const activeGroupChildren = computed(() =>
    activeGroup.value ? visibleItems(activeGroup.value.children) : [],
  )

  return {
    itemVisible,
    visibleItems,
    visibleSub,
    firstLeafPath,
    visibleGroups,
    activeGroup,
    activeGroupChildren,
  }
}
