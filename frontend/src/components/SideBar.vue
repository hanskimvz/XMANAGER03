<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuth } from '@/stores/auth'
import { useMenu } from '@/composables/useMenu'
import { useNavState } from '@/composables/useNavState'
import type { MenuItem } from '@/router/menu'

const route = useRoute()
const { isLoggedIn } = useAuth()
const { visibleSub, activeGroup, activeGroupChildren } = useMenu()
const { sidebarCollapsed } = useNavState()

const isLoginPage = computed(() => route.name === 'login')
// 로그인 상태 + 로그인 페이지 아님 + 활성 그룹 존재 + (햄버거로) 접히지 않음
const showSidebar = computed(
  () => !isLoginPage.value && isLoggedIn.value && !!activeGroup.value && !sidebarCollapsed.value,
)

// ===== 2단 서브메뉴 펼침/접힘 상태 =====
const expandedKeys = ref<Record<string, boolean>>({})
function parentHasActiveChild(item: MenuItem): boolean {
  return visibleSub(item).some(
    (c) => c.path && (route.path === c.path || route.path.startsWith(c.path + '/')),
  )
}
// 명시적으로 토글했으면 그 값, 아니면 활성 자식이 있을 때 자동 펼침
function isOpen(item: MenuItem): boolean {
  return expandedKeys.value[item.label] ?? parentHasActiveChild(item)
}
function toggleOpen(item: MenuItem) {
  expandedKeys.value[item.label] = !isOpen(item)
}
</script>

<template>
  <!-- 좌측 사이드바 (lg 이상에서만, 활성 그룹의 하위 메뉴) — navbar(h-14=3.5rem) 바로 아래에 고정 -->
  <aside
    v-if="showSidebar"
    class="hidden lg:block w-56 shrink-0 bg-white border-r border-gray-200 lg:sticky lg:top-14 lg:self-start lg:h-[calc(100vh-3.5rem)] overflow-y-auto"
  >
    <nav class="p-3 space-y-1">
      <div class="px-3 py-2 text-xs font-bold text-gray-400 uppercase tracking-wide">
        {{ activeGroup?.label }}
      </div>
      <template v-for="item in activeGroupChildren" :key="item.path || item.label">
        <!-- 2단 부모(보이는 자식 보유): 라벨(이동/펼침) + 쉐브론(펼침/접힘) -->
        <template v-if="visibleSub(item).length">
          <div class="flex items-center">
            <!-- 라벨: path 있으면 이동 링크, 없으면 펼침 토글 -->
            <RouterLink
              v-if="item.path"
              :to="item.path"
              class="side-link flex-1"
              exact-active-class="side-link-active"
            >{{ item.label }}</RouterLink>
            <button
              v-else
              type="button"
              class="side-link flex-1 text-left"
              @click="toggleOpen(item)"
            >{{ item.label }}</button>
            <!-- 쉐브론: 펼침/접힘 -->
            <button
              type="button"
              class="shrink-0 p-1.5 rounded-md text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              :aria-label="isOpen(item) ? '접기' : '펼치기'"
              @click="toggleOpen(item)"
            >
              <svg
                class="w-4 h-4 transition-transform"
                :class="{ 'rotate-90': isOpen(item) }"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
          <div v-show="isOpen(item)" class="ml-3 pl-2 border-l border-gray-200 space-y-1">
            <RouterLink
              v-for="sub in visibleSub(item)"
              :key="sub.path"
              :to="sub.path!"
              class="side-link text-[13px]"
              exact-active-class="side-link-active"
            >{{ sub.label }}</RouterLink>
          </div>
        </template>
        <!-- 리프(또는 보이는 자식이 없는 노드) -->
        <RouterLink
          v-else
          :to="item.path!"
          class="side-link"
          exact-active-class="side-link-active"
        >{{ item.label }}</RouterLink>
      </template>
    </nav>
  </aside>
</template>

<style scoped>
/* 좌측 사이드바 메뉴 */
.side-link {
  @apply block px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors;
}
.side-link-active {
  @apply bg-blue-600 text-white hover:bg-blue-700 hover:text-white;
}
</style>
