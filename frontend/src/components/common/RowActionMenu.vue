<template>
  <button
    ref="triggerRef"
    type="button"
    @click.stop="toggle"
    class="inline-flex items-center gap-0.5 px-2 py-0.5 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded transition-colors whitespace-nowrap"
  >
    {{ label }}
    <svg class="w-2.5 h-2.5 text-gray-500" fill="currentColor" viewBox="0 0 12 12">
      <path d="M3 5l3 3 3-3z" />
    </svg>
  </button>

  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[60]" @click="close"></div>
    <div
      v-if="open"
      class="fixed z-[61] bg-white border rounded-md shadow-lg py-1 min-w-[150px]"
      :style="menuStyle"
    >
      <template v-for="(a, i) in visibleActions" :key="i">
        <div v-if="a.divider" class="border-t border-gray-100 my-1"></div>
        <button
          v-else
          type="button"
          @click="handleClick(a)"
          :class="a.variant === 'danger'
            ? 'text-red-600 hover:bg-red-50'
            : 'text-gray-700 hover:bg-gray-50'"
          class="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-left whitespace-nowrap"
        >
          <span v-if="a.icon" class="text-sm leading-none">{{ a.icon }}</span>
          <span>{{ a.label }}</span>
        </button>
      </template>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'

export interface RowAction {
  label?: string  // divider면 생략
  icon?: string
  onClick?: () => void
  variant?: 'default' | 'danger'
  divider?: boolean
  show?: boolean  // false면 숨김 (기본 true)
}

interface Props {
  actions: RowAction[]
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: '액션',
})

const triggerRef = ref<HTMLButtonElement | null>(null)
const open = ref(false)
const menuStyle = ref<Record<string, string>>({})

// show=false 제거 + 연속/양끝 divider 정리
const visibleActions = computed<RowAction[]>(() => {
  const list = props.actions.filter((a) => a.divider || a.show !== false)
  // 양끝 divider 제거 + 연속 divider 1개로 축약
  const cleaned: RowAction[] = []
  for (const a of list) {
    if (a.divider) {
      if (cleaned.length === 0) continue
      if (cleaned[cleaned.length - 1]?.divider) continue
      cleaned.push(a)
    } else {
      cleaned.push(a)
    }
  }
  while (cleaned.length && cleaned[cleaned.length - 1]?.divider) cleaned.pop()
  return cleaned
})

function toggle() {
  if (open.value) {
    close()
    return
  }
  const el = triggerRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const MENU_W = 150
  const estHeight = Math.min(visibleActions.value.length * 30 + 12, 320)

  let top = rect.bottom + 4
  let left = rect.right - MENU_W  // 우측 정렬
  if (left < 8) left = 8
  if (left + MENU_W > window.innerWidth - 8) left = window.innerWidth - MENU_W - 8
  // 아래 공간 부족하면 위로
  if (top + estHeight > window.innerHeight - 8) {
    top = rect.top - estHeight - 4
    if (top < 8) top = 8
  }
  menuStyle.value = { top: `${top}px`, left: `${left}px` }
  open.value = true
}

function close() {
  open.value = false
}

function handleClick(a: RowAction) {
  close()
  a.onClick?.()
}

onBeforeUnmount(() => {
  open.value = false
})
</script>
