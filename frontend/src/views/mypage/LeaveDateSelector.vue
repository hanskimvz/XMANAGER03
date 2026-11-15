<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{ modelValue: string[]; single?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [string[]] }>()

const today = new Date()
const viewYear = ref(today.getFullYear())
const viewMonth = ref(today.getMonth()) // 0-11

const fmt = (y: number, m: number, d: number) =>
  `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`

const selectedSet = computed(() => new Set(props.modelValue))
const monthLabel = computed(() => `${viewYear.value}년 ${viewMonth.value + 1}월`)

interface Cell { d: number; dow: number; weekend: boolean; date: string }
const grid = computed<(Cell | null)[]>(() => {
  const first = new Date(viewYear.value, viewMonth.value, 1)
  const startDow = first.getDay() // 0=일
  const daysInMonth = new Date(viewYear.value, viewMonth.value + 1, 0).getDate()
  const cells: (Cell | null)[] = []
  for (let i = 0; i < startDow; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) {
    const dow = new Date(viewYear.value, viewMonth.value, d).getDay()
    cells.push({ d, dow, weekend: dow === 0 || dow === 6, date: fmt(viewYear.value, viewMonth.value, d) })
  }
  return cells
})

const lastClicked = ref<string | null>(null)

function setDates(set: Set<string>) {
  emit('update:modelValue', Array.from(set).sort())
}

function onClick(cell: Cell | null, ev: MouseEvent) {
  if (!cell || cell.weekend) return
  // 반차(single): 하루만 선택 — 같은 날 다시 클릭하면 해제, 다른 날 클릭하면 그 날로 교체
  if (props.single) {
    setDates(selectedSet.value.has(cell.date) ? new Set() : new Set([cell.date]))
    lastClicked.value = cell.date
    return
  }
  const set = new Set(props.modelValue)
  if (ev.shiftKey && lastClicked.value) {
    // 기간: lastClicked ~ cell 사이 주중 채우기
    let a = lastClicked.value, b = cell.date
    if (a > b) [a, b] = [b, a]
    let cur = new Date(a + 'T00:00:00')
    const end = new Date(b + 'T00:00:00')
    while (cur <= end) {
      const dow = cur.getDay()
      if (dow !== 0 && dow !== 6) set.add(fmt(cur.getFullYear(), cur.getMonth(), cur.getDate()))
      cur.setDate(cur.getDate() + 1)
    }
  } else {
    if (set.has(cell.date)) set.delete(cell.date)
    else set.add(cell.date)
    lastClicked.value = cell.date
  }
  setDates(set)
}

function prevMonth() {
  if (viewMonth.value === 0) { viewMonth.value = 11; viewYear.value-- } else viewMonth.value--
}
function nextMonth() {
  if (viewMonth.value === 11) { viewMonth.value = 0; viewYear.value++ } else viewMonth.value++
}
function clearAll() { setDates(new Set()) }

// 선택 요약: 달력상 연속 구간 묶기(주말이 끼면 끊김) — 원장과 동일 규칙
const runs = computed<string[]>(() => {
  const ds = [...props.modelValue].sort()
  if (!ds.length) return []
  const nextCal = (s: string) => {
    const d = new Date(s + 'T00:00:00')
    d.setDate(d.getDate() + 1)
    return fmt(d.getFullYear(), d.getMonth(), d.getDate())
  }
  const out: string[] = []
  let start = ds[0] as string
  let prev = ds[0] as string
  for (let i = 1; i < ds.length; i++) {
    const cur = ds[i] as string
    if (cur === nextCal(prev)) { prev = cur }
    else { out.push(start === prev ? start : `${start}~${prev}`); start = cur; prev = cur }
  }
  out.push(start === prev ? start : `${start}~${prev}`)
  return out
})
</script>

<template>
  <div class="lds">
    <div class="lds-head">
      <button type="button" class="lds-nav" @click="prevMonth">‹</button>
      <span class="lds-month">{{ monthLabel }}</span>
      <button type="button" class="lds-nav" @click="nextMonth">›</button>
      <span class="lds-hint">{{ single ? '반차: 하루만 선택하세요' : '날짜 클릭 = 개별 선택 / Shift+클릭 = 기간(주말 제외)' }}</span>
    </div>
    <div class="lds-dow">
      <span v-for="(w, i) in ['일','월','화','수','목','금','토']" :key="w" :class="{ wknd: i === 0 || i === 6 }">{{ w }}</span>
    </div>
    <div class="lds-grid">
      <template v-for="(cell, i) in grid" :key="i">
        <span v-if="!cell" class="lds-empty"></span>
        <button
          v-else
          type="button"
          class="lds-day"
          :class="{ wknd: cell.weekend, sel: selectedSet.has(cell.date) }"
          :disabled="cell.weekend"
          @click="onClick(cell, $event)"
        >{{ cell.d }}</button>
      </template>
    </div>
    <div class="lds-summary">
      <span class="lds-count">선택 {{ modelValue.length }}일</span>
      <span v-if="runs.length" class="lds-runs">{{ runs.join(', ') }}</span>
      <button v-if="modelValue.length" type="button" class="lds-clear" @click="clearAll">전체 해제</button>
    </div>
  </div>
</template>

<style scoped>
.lds { border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 12px; background: #fff; }
.lds-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.lds-nav { width: 26px; height: 26px; border: 1px solid #cbd5e1; border-radius: 6px; background: #f8fafc; cursor: pointer; }
.lds-month { font-weight: 700; color: #334155; min-width: 92px; text-align: center; }
.lds-hint { font-size: 11px; color: #94a3b8; margin-left: auto; }
.lds-dow { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; font-size: 11px; color: #64748b; margin-bottom: 2px; }
.lds-dow .wknd { color: #cbd5e1; }
.lds-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; }
.lds-empty { height: 32px; }
.lds-day { height: 32px; border: 1px solid transparent; border-radius: 6px; background: #f1f5f9; cursor: pointer; font-size: 13px; color: #334155; }
.lds-day:hover { background: #e2e8f0; }
.lds-day.wknd { background: transparent; color: #cbd5e1; cursor: not-allowed; }
.lds-day.sel { background: #2563eb; color: #fff; font-weight: 700; }
.lds-summary { display: flex; align-items: center; gap: 10px; margin-top: 8px; font-size: 12px; }
.lds-count { font-weight: 700; color: #2563eb; }
.lds-runs { color: #64748b; }
.lds-clear { margin-left: auto; color: #94a3b8; background: none; border: none; cursor: pointer; text-decoration: underline; }
</style>
