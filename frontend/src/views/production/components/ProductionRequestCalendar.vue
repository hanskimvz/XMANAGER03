<template>
  <div>
    <!-- 툴바: 월 이동 + 토글 + 범례 -->
    <div class="flex flex-wrap items-center gap-2 mb-3">
      <div class="flex items-center gap-1">
        <button @click="prevMonth" class="px-2 py-1 border rounded hover:bg-gray-50 text-gray-600">‹</button>
        <span class="px-2 text-sm font-semibold text-gray-800 min-w-[7rem] text-center">{{ currentMonthLabel }}</span>
        <button @click="nextMonth" class="px-2 py-1 border rounded hover:bg-gray-50 text-gray-600">›</button>
        <button @click="goToToday" class="ml-1 px-2 py-1 text-xs border rounded text-gray-600 hover:bg-gray-50">오늘</button>
      </div>
      <div class="flex items-center gap-3 ml-auto text-xs">
        <label class="inline-flex items-center gap-1 cursor-pointer select-none">
          <input type="checkbox" v-model="showDue" class="w-3.5 h-3.5 rounded" />
          <span class="inline-block w-2.5 h-2.5 rounded-sm bg-blue-500"></span> 납기일
        </label>
        <label class="inline-flex items-center gap-1 cursor-pointer select-none">
          <input type="checkbox" v-model="showRequest" class="w-3.5 h-3.5 rounded" />
          <span class="inline-block w-2.5 h-2.5 rounded-sm bg-amber-400"></span> 요청일
        </label>
        <label class="inline-flex items-center gap-1 cursor-pointer select-none text-gray-500">
          <input type="checkbox" v-model="includeDone" class="w-3.5 h-3.5 rounded" />
          완료·취소 포함
        </label>
      </div>
    </div>

    <!-- 납기 미정 칩 (클릭 시 목록 → 날짜 지정) -->
    <div v-if="undated.length" class="mb-2 relative">
      <button @click="showUndated = !showUndated"
        class="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full bg-amber-100 text-amber-700 hover:bg-amber-200">
        🕒 납기 미정 <b>{{ undated.length }}</b>건 <span class="opacity-60">▾</span>
      </button>
      <div v-if="showUndated" class="absolute z-20 mt-1 w-80 max-h-64 overflow-y-auto bg-white border rounded-lg shadow-lg">
        <div class="px-3 py-1.5 text-[11px] text-gray-400 border-b">클릭하면 납기일을 지정할 수 있습니다</div>
        <button v-for="it in undated" :key="it.id" @click="openReschedule(it); showUndated = false"
          class="w-full text-left px-3 py-2 text-xs hover:bg-amber-50 border-b last:border-0">
          <span class="font-medium text-gray-800">{{ it.request_number }}</span>
          <span class="text-gray-500"> · {{ it.customer_name || '-' }}</span>
          <span class="ml-1 text-[10px] text-gray-400">{{ statusLabel(it.status) }}</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="py-10 text-center text-gray-400 text-sm">불러오는 중…</div>

    <!-- 캘린더 그리드 -->
    <div v-else class="border rounded-lg overflow-hidden select-none">
      <div class="grid grid-cols-7 bg-gray-50 border-b text-xs font-medium">
        <div v-for="(w, i) in weekDays" :key="w" class="px-2 py-1.5 text-center"
          :class="i === 0 ? 'text-red-500' : i === 6 ? 'text-blue-500' : 'text-gray-500'">{{ w }}</div>
      </div>
      <div v-for="(week, wi) in weeks" :key="wi" class="grid grid-cols-7 border-b last:border-b-0">
        <div v-for="(day, di) in week.days" :key="day.dateString"
          class="min-h-[92px] border-r last:border-r-0 p-1 align-top"
          :class="[day.isCurrentMonth ? 'bg-white' : 'bg-gray-50/60', day.isToday ? 'ring-1 ring-inset ring-blue-300' : '']">
          <div class="text-[11px] mb-0.5 px-0.5"
            :class="[day.isToday ? 'font-bold text-blue-600' : day.isWeekend && di===0 ? 'text-red-400' : day.isWeekend && di===6 ? 'text-blue-400' : 'text-gray-400', !day.isCurrentMonth && 'opacity-50']">
            {{ day.day }}
          </div>
          <div class="flex flex-col gap-0.5">
            <button v-for="m in markersByDate.get(day.dateString) || []" :key="m.key"
              @click="openReschedule(m)"
              :title="m.tooltip"
              class="text-left text-[10.5px] leading-tight px-1 py-0.5 rounded truncate"
              :class="m.cls">
              <span class="font-medium">{{ m.kind === 'due' ? '📦' : '📝' }} {{ m.request_number }}</span>
              <span class="opacity-80"> · {{ m.customer_name || '' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 납기 조정 모달 -->
    <Teleport to="body">
      <div v-if="sel" class="fixed inset-0 z-[80] bg-black/40 flex items-center justify-center p-4" @click.self="sel = null">
        <div class="bg-white rounded-lg shadow-xl w-full max-w-sm">
          <div class="px-4 py-3 border-b flex items-center justify-between">
            <h4 class="text-sm font-bold text-gray-800">📦 납기일 조정</h4>
            <button @click="sel = null" class="text-gray-400 hover:text-gray-600">✕</button>
          </div>
          <div class="px-4 py-3 space-y-2 text-sm">
            <div><span class="text-gray-500">요청번호</span> · <b>{{ sel.request_number }}</b></div>
            <div><span class="text-gray-500">고객사</span> · {{ sel.customer_name || '-' }}</div>
            <div><span class="text-gray-500">상태</span> · {{ statusLabel(sel.status) }}</div>
            <!-- 품목-수량 (납기 무리 여부 가늠용) -->
            <div class="border rounded-md bg-gray-50 px-2 py-1.5">
              <div class="text-[11px] text-gray-500 mb-0.5">품목</div>
              <div v-if="selItemsLoading" class="text-[11px] text-gray-400">불러오는 중…</div>
              <div v-else-if="!selItems.length" class="text-[11px] text-gray-400">품목 정보 없음</div>
              <ul v-else class="space-y-0.5">
                <li v-for="(it, i) in selItems" :key="i" class="flex justify-between gap-2">
                  <span class="font-mono text-xs text-gray-700 truncate">{{ it.code }}</span>
                  <span class="text-xs tabular-nums whitespace-nowrap">{{ it.qty.toLocaleString() }} {{ it.uom }}</span>
                </li>
              </ul>
            </div>
            <div class="pt-1">
              <label class="block text-xs text-gray-500 mb-1">납기일</label>
              <input v-model="newDue" type="date" class="w-full border rounded px-2 py-1.5 text-sm" />
              <p class="text-[11px] text-gray-400 mt-1">변경하면 생산팀에 알림이 발송됩니다.</p>
            </div>
          </div>
          <div class="px-4 py-3 border-t flex items-center justify-between gap-2">
            <button @click="$emit('openDetail', sel.id); sel = null"
              class="px-3 py-1.5 text-sm text-blue-600 border border-blue-200 rounded hover:bg-blue-50">상세 열기</button>
            <div class="flex gap-2">
              <button @click="sel = null" class="px-3 py-1.5 text-sm text-gray-600 border rounded hover:bg-gray-100">취소</button>
              <button @click="saveDue" :disabled="savingDue"
                class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                {{ savingDue ? '저장 중…' : '저장' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useCalendar } from '@/composables/useCalendar'
import { productionRequestApi, prStatusLabels, type ProductionCalendarItem, type ProductionRequestStatus } from '@/api/productionRequest'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ customerId?: number }>()
const emit = defineEmits<{ (e: 'openDetail', id: number): void }>()
const { showToast } = useToast()

const { currentMonthLabel, getWeeksInMonth, prevMonth, nextMonth, goToToday, currentDate } = useCalendar()
const weeks = getWeeksInMonth
const weekDays = ['일', '월', '화', '수', '목', '금', '토']

const loading = ref(false)
const items = ref<ProductionCalendarItem[]>([])
const showDue = ref(true)
const showRequest = ref(true)
const includeDone = ref(false)

// 기본 숨김 상태(완료·취소 포함 토글 off일 때)
const HIDDEN_DEFAULT: ProductionRequestStatus[] = ['DELIVERED', 'CANCELLED', 'REJECTED']

function statusLabel(s: ProductionRequestStatus) { return prStatusLabels[s] || s }
function todayStr() {
  const d = new Date(); const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
function localDate(iso?: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso); if (isNaN(d.getTime())) return null
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

// 그리드 표시 범위(첫 주 첫날 ~ 마지막 주 마지막날)
const gridRange = computed(() => {
  const ws = weeks.value
  const first = ws[0]?.days[0]?.dateString
  const last = ws[ws.length - 1]?.days[6]?.dateString
  return { from: first || '', to: last || '' }
})

async function load() {
  const { from, to } = gridRange.value
  if (!from || !to) return
  loading.value = true
  try {
    items.value = await productionRequestApi.calendar(from, to, props.customerId)
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '캘린더를 불러오지 못했습니다', 'error')
  } finally {
    loading.value = false
  }
}
watch(() => currentDate.value, load)
watch(() => props.customerId, load)

// 납기 마커 색상(상태별 + 지연 강조)
function dueCls(it: ProductionCalendarItem): string {
  const overdue = it.due_date && it.due_date < todayStr() && !['SHIPPED', 'DELIVERED', 'CANCELLED'].includes(it.status)
  if (overdue) return 'bg-red-100 text-red-700 hover:bg-red-200'
  switch (it.status) {
    case 'SHIPPED': return 'bg-green-100 text-green-700 hover:bg-green-200'
    case 'DELIVERED': return 'bg-slate-100 text-slate-600 hover:bg-slate-200'
    case 'IN_PROGRESS':
    case 'APPROVED': return 'bg-blue-100 text-blue-700 hover:bg-blue-200'
    case 'COMPLETED': return 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200'
    case 'CANCELLED':
    case 'REJECTED': return 'bg-gray-100 text-gray-400 line-through hover:bg-gray-200'
    default: return 'bg-gray-100 text-gray-600 hover:bg-gray-200' // REQUESTED/HOLD
  }
}

type Marker = ProductionCalendarItem & { key: string; kind: 'due' | 'request'; cls: string; tooltip: string }

// 날짜별 마커 맵
const markersByDate = computed(() => {
  const map = new Map<string, Marker[]>()
  const push = (date: string | null, m: Marker) => {
    if (!date) return
    const arr = map.get(date) || []; arr.push(m); map.set(date, arr)
  }
  for (const it of items.value) {
    if (!includeDone.value && HIDDEN_DEFAULT.includes(it.status)) continue
    if (showDue.value && it.due_date) {
      push(it.due_date, { ...it, key: `d${it.id}`, kind: 'due', cls: dueCls(it),
        tooltip: `[납기] ${it.request_number} · ${it.customer_name || ''} · ${statusLabel(it.status)}` })
    }
    if (showRequest.value) {
      const rd = localDate(it.requested_at)
      push(rd, { ...it, key: `r${it.id}`, kind: 'request', cls: 'bg-amber-50 text-amber-700 hover:bg-amber-100',
        tooltip: `[요청] ${it.request_number} · ${it.customer_name || ''}` })
    }
  }
  return map
})

// 납기 미정(활성) 건 — 상단 칩. 월 무관 항상 포함되어 옴
const undated = computed(() =>
  items.value.filter((it) => !it.due_date && !HIDDEN_DEFAULT.includes(it.status)),
)
const showUndated = ref(false)

// 납기 조정
const sel = ref<ProductionCalendarItem | null>(null)
const newDue = ref<string>('')
const savingDue = ref(false)
const selItems = ref<{ code: string; qty: number; uom: string }[]>([])
const selItemsLoading = ref(false)
async function openReschedule(m: ProductionCalendarItem) {
  sel.value = m
  newDue.value = m.due_date || ''
  // 품목-수량은 상세에서 조회(영업이 무리한 납기인지 가늠)
  selItems.value = []
  selItemsLoading.value = true
  try {
    const doc = await productionRequestApi.getById(m.id)
    selItems.value = (doc.items || []).map((it: any) => ({
      code: it.product_part?.part_number_display || it.product_part?.part_number || it.custom_product_code || '(품목)',
      qty: Number(it.requested_quantity) || 0,
      uom: it.uom || '',
    }))
  } catch { /* 품목 조회 실패해도 납기 조정은 가능 */ } finally {
    selItemsLoading.value = false
  }
}
async function saveDue() {
  if (!sel.value) return
  savingDue.value = true
  try {
    await productionRequestApi.updateDueDate(sel.value.id, newDue.value || null)
    showToast('납기일이 변경되었습니다 (생산팀 알림 발송)', 'success')
    sel.value = null
    await load()
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '납기 변경에 실패했습니다', 'error')
  } finally {
    savingDue.value = false
  }
}

onMounted(load)
</script>
