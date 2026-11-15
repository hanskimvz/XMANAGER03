<template>
  <div
    class="px-1.5 py-0.5 rounded text-xs truncate cursor-pointer transition-all hover:opacity-80"
    :class="[
      event.bgColor,
      event.color,
      event.borderColor ? `border-l-2 ${event.borderColor}` : '',
      priorityRingClass,
    ]"
    :title="tooltipText"
  >
    <span class="font-medium">{{ eventTypeLabel }}</span>
    <span class="ml-1 opacity-75">{{ event.title }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CalendarEvent } from '@/api/calendar'
import { eventTypeLabels } from '@/api/calendar'

const props = defineProps<{
  event: CalendarEvent
}>()

// 이벤트 유형 라벨
const eventTypeLabel = computed(() => {
  return eventTypeLabels[props.event.type] || props.event.type
})

// 우선순위에 따른 링 스타일 (작업지시서만)
const priorityRingClass = computed(() => {
  if (props.event.category !== 'WO' || props.event.priority === undefined) {
    return ''
  }

  switch (props.event.priority) {
    case 1: // 높음
      return 'ring-1 ring-yellow-400'
    case 2: // 긴급
      return 'ring-2 ring-red-500 animate-pulse'
    default:
      return ''
  }
})

// 툴팁 텍스트
const tooltipText = computed(() => {
  let text = `${eventTypeLabel.value}: ${props.event.title}`
  if (props.event.subtitle) {
    text += `\n${props.event.subtitle}`
  }
  if (props.event.category === 'WO' && props.event.priority !== undefined) {
    const priorityLabels = ['보통', '높음', '긴급']
    text += `\n우선순위: ${priorityLabels[props.event.priority] || '보통'}`
  }
  return text
})
</script>
