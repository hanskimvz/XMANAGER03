<script setup lang="ts">
// 모바일 전용 하단 탭바. lg(1024px) 미만에서만 노출(데스크톱 영향 없음).
// 자주 쓰는 모바일 동작(홈/공지/결재)에 빠르게 접근. 권한 없는 탭은 숨김.
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { can, hasPermStrict } from '@/stores/auth'

const props = defineProps<{ pending?: number; announceUnread?: number }>()
const route = useRoute()

interface Tab {
  to: string
  label: string
  icon: string
  show: boolean
  badge?: number
  match: (path: string) => boolean
}

const tabs = computed<Tab[]>(() => [
  { to: '/menu', label: '홈', icon: '🏠', show: true, match: (p: string) => p === '/menu' || p === '/' },
  { to: '/announcements', label: '공지', icon: '📢', show: can('announcement:view'), badge: props.announceUnread, match: (p: string) => p.startsWith('/announcements') },
  { to: '/approvals', label: '결재', icon: '📝', show: hasPermStrict('approval:view'), badge: props.pending, match: (p: string) => p.startsWith('/approvals') },
].filter((t) => t.show))
</script>

<template>
  <nav
    class="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-gray-200 flex justify-around"
    style="padding-bottom: env(safe-area-inset-bottom)"
  >
    <RouterLink
      v-for="t in tabs"
      :key="t.to"
      :to="t.to"
      class="relative flex flex-col items-center justify-center flex-1 py-1.5 text-[11px]"
      :class="t.match(route.path) ? 'text-blue-600 font-bold' : 'text-gray-500'"
    >
      <span class="text-lg leading-none" aria-hidden="true">{{ t.icon }}</span>
      <span class="mt-0.5">{{ t.label }}</span>
      <span
        v-if="t.badge && t.badge > 0"
        class="absolute top-0.5 right-[22%] min-w-[16px] h-4 px-1 flex items-center justify-center text-[10px] font-bold rounded-full bg-red-500 text-white"
      >{{ t.badge }}</span>
    </RouterLink>
  </nav>
</template>
