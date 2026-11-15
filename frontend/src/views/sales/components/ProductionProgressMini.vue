<template>
  <div v-if="!progress" class="inline-flex flex-col items-center">
    <span class="px-2 py-0.5 text-[11px] rounded-full bg-gray-100 text-gray-400 whitespace-nowrap">미착수</span>
  </div>
  <div v-else class="inline-flex flex-col items-center gap-1" :title="tooltip">
    <!-- 3칸 미니 스텝퍼: 생산 · 출고 · 배송 -->
    <div class="flex items-center">
      <template v-for="(s, i) in steps" :key="s.key">
        <span class="pm-dot" :class="dotClass(i + 1)">
          <svg v-if="dotState(i + 1) === 'done'" viewBox="0 0 24 24" class="pm-check"><path d="M4 12l6 6L20 6" /></svg>
        </span>
        <span v-if="i < steps.length - 1" class="pm-bar" :class="{ 'pm-bar-done': dotState(i + 1) === 'done' }"></span>
      </template>
    </div>
    <span class="text-[11px] font-medium whitespace-nowrap" :class="labelClass">{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ProductionProgress } from '@/api/salesDocument'

const props = defineProps<{ progress?: ProductionProgress | null }>()

const steps = [
  { key: 'prod', name: '생산' },
  { key: 'ship', name: '출고' },
  { key: 'deliv', name: '배송' },
] as const

// 모든 요청이 배송 완료(병목이 3)면 3칸 모두 완료
const allDone = computed(() => props.progress?.stage === 3)

// 각 단계(1생산/2출고/3배송) 상태: done(전부 통과) / current(병목) / todo
function dotState(step: number): 'done' | 'current' | 'todo' {
  const stage = props.progress?.stage ?? 1
  if (allDone.value) return 'done'
  if (step < stage) return 'done'
  if (step === stage) return 'current'
  return 'todo'
}
function dotClass(step: number) {
  const s = dotState(step)
  return { 'pm-done': s === 'done', 'pm-cur': s === 'current', 'pm-todo': s === 'todo' }
}

// 상세 breakdown 라벨: "생산 1 · 출고 2" (0은 생략), 전량 배송이면 "배송 완료"
const label = computed(() => {
  const p = props.progress
  if (!p) return ''
  if (allDone.value) return p.pr_total > 1 ? `배송 완료 · ${p.pr_total}건` : '배송 완료'
  const parts: string[] = []
  if (p.counts.prod) parts.push(`생산 ${p.counts.prod}`)
  if (p.counts.ship) parts.push(`출고 ${p.counts.ship}`)
  if (p.counts.deliv) parts.push(`배송 ${p.counts.deliv}`)
  return parts.join(' · ')
})
const labelClass = computed(() => {
  if (allDone.value) return 'text-purple-600'
  const stage = props.progress?.stage ?? 1
  return stage === 1 ? 'text-gray-500' : 'text-blue-600'
})

const tooltip = computed(() => {
  const p = props.progress
  if (!p) return '연결된 생산요청 없음'
  return `생산요청 ${p.pr_total}건 — 생산 ${p.counts.prod} · 출고 ${p.counts.ship} · 배송 ${p.counts.deliv}`
})
</script>

<style scoped>
.pm-dot { width: 15px; height: 15px; border-radius: 9999px; border: 2px solid #cbd5e1; background: #fff;
  display: grid; place-items: center; flex-shrink: 0; }
.pm-dot.pm-done { background: #2563eb; border-color: #2563eb; }
.pm-dot.pm-cur { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18); }
.pm-dot.pm-todo { border-color: #d1d5db; }
.pm-check { width: 9px; height: 9px; stroke: #fff; stroke-width: 3.5; fill: none; }
.pm-bar { width: 12px; height: 2px; background: #d1d5db; flex-shrink: 0; }
.pm-bar-done { background: #2563eb; }
</style>
