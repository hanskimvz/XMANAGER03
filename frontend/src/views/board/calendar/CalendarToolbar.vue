<template>
  <div class="flex flex-col gap-4 mb-4">
    <!-- 상단: 네비게이션 -->
    <div class="flex items-center justify-between">
      <!-- 월 이동 버튼 -->
      <div class="flex items-center gap-2">
        <button
          @click="$emit('prevMonth')"
          class="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          title="이전 달"
        >
          <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <h2 class="text-xl font-bold text-gray-900 min-w-[140px] text-center">
          {{ monthLabel }}
        </h2>

        <button
          @click="$emit('nextMonth')"
          class="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          title="다음 달"
        >
          <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>

        <button
          @click="$emit('today')"
          class="ml-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          오늘
        </button>
      </div>

      <!-- 우측: 그룹 빠른 토글 + 필터 -->
      <div class="flex items-center gap-2 flex-wrap justify-end">
        <!-- 그룹 빠른 토글 버튼 (필터 왼쪽) -->
        <button
          @click="togglePO" title="발주서 켜기/끄기"
          class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors"
          :class="poActive ? 'bg-blue-50 text-blue-700 border-blue-300' : 'bg-white text-gray-400 border-gray-200 hover:bg-gray-50'"
        ><span class="w-2.5 h-2.5 rounded-full" :class="poActive ? 'bg-blue-500' : 'bg-gray-300'"></span>발주서</button>
        <button
          @click="toggleWOScheduled" title="작업지시서(예정) 켜기/끄기"
          class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors"
          :class="woSchedActive ? 'bg-indigo-50 text-indigo-700 border-indigo-300' : 'bg-white text-gray-400 border-gray-200 hover:bg-gray-50'"
        ><span class="w-2.5 h-2.5 rounded-full" :class="woSchedActive ? 'bg-indigo-500' : 'bg-gray-300'"></span>작업(예정)</button>
        <button
          @click="toggleWOCompleted" title="작업지시서(완료) 켜기/끄기"
          class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors"
          :class="woCompActive ? 'bg-green-50 text-green-700 border-green-300' : 'bg-white text-gray-400 border-gray-200 hover:bg-gray-50'"
        ><span class="w-2.5 h-2.5 rounded-full" :class="woCompActive ? 'bg-green-500' : 'bg-gray-300'"></span>작업(완료)</button>
        <button
          @click="toggleAP" title="휴가/출장 켜기/끄기"
          class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors"
          :class="apActive ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-white text-gray-400 border-gray-200 hover:bg-gray-50'"
        ><span class="w-2.5 h-2.5 rounded-full" :class="apActive ? 'bg-emerald-500' : 'bg-gray-300'"></span>휴가/출장</button>
        <button
          @click="toggleSC" title="등록 일정(행사/휴가/외근/출장) 켜기/끄기"
          class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors"
          :class="scActive ? 'bg-amber-50 text-amber-700 border-amber-300' : 'bg-white text-gray-400 border-gray-200 hover:bg-gray-50'"
        ><span class="w-2.5 h-2.5 rounded-full" :class="scActive ? 'bg-amber-500' : 'bg-gray-300'"></span>등록 일정</button>

        <span class="border-l border-gray-300 h-6 mx-1"></span>

        <!-- 필터 토글 버튼 -->
        <button
          @click="showFilters = !showFilters"
          class="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          :class="showFilters ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          필터
          <span
            v-if="activeFilterCount > 0"
            class="px-1.5 py-0.5 text-xs font-bold bg-blue-600 text-white rounded-full"
          >
            {{ activeFilterCount }}
          </span>
        </button>
      </div>
    </div>

    <!-- 필터 패널 -->
    <div v-if="showFilters" class="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- 발주서 필터 -->
        <div>
          <h3 @click="togglePO" title="클릭: 발주서 전체 켜기/끄기"
            class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2 cursor-pointer select-none hover:text-blue-600">
            <span class="w-3 h-3 bg-blue-500 rounded-full"></span>
            발주서
            <span class="ml-auto text-[11px] font-normal text-gray-400 border border-gray-200 rounded px-1.5 py-0.5">전체</span>
          </h3>
          <div class="space-y-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.poEvents.order"
                class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              />
              <span class="w-3 h-3 bg-blue-100 rounded"></span>
              <span class="text-sm text-gray-700">발주일</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.poEvents.deliveryExpected"
                class="w-4 h-4 text-orange-600 rounded border-gray-300 focus:ring-orange-500"
              />
              <span class="w-3 h-3 bg-orange-100 rounded"></span>
              <span class="text-sm text-gray-700">납기예정</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.poEvents.deliveryActual"
                class="w-4 h-4 text-green-600 rounded border-gray-300 focus:ring-green-500"
              />
              <span class="w-3 h-3 bg-green-100 rounded"></span>
              <span class="text-sm text-gray-700">입고완료</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.poEvents.payment"
                class="w-4 h-4 text-purple-600 rounded border-gray-300 focus:ring-purple-500"
              />
              <span class="w-3 h-3 bg-purple-100 rounded"></span>
              <span class="text-sm text-gray-700">결제</span>
            </label>
          </div>
        </div>

        <!-- 작업지시서 필터 - 예정일 -->
        <div>
          <h3 @click="toggleWOScheduled" title="클릭: 작업지시서(예정) 전체 켜기/끄기"
            class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2 cursor-pointer select-none hover:text-indigo-600">
            <span class="w-3 h-3 bg-indigo-500 rounded-full"></span>
            작업지시서 (예정)
            <span class="ml-auto text-[11px] font-normal text-gray-400 border border-gray-200 rounded px-1.5 py-0.5">전체</span>
          </h3>
          <div class="space-y-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.issueScheduled"
                class="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
              />
              <span class="w-3 h-3 bg-indigo-50 border-2 border-indigo-400 rounded"></span>
              <span class="text-sm text-gray-700">출고예정</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.productionScheduled"
                class="w-4 h-4 text-yellow-600 rounded border-gray-300 focus:ring-yellow-500"
              />
              <span class="w-3 h-3 bg-yellow-50 border-2 border-yellow-400 rounded"></span>
              <span class="text-sm text-gray-700">생산예정</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.inspectionScheduled"
                class="w-4 h-4 text-orange-600 rounded border-gray-300 focus:ring-orange-500"
              />
              <span class="w-3 h-3 bg-orange-50 border-2 border-orange-400 rounded"></span>
              <span class="text-sm text-gray-700">검사예정</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.packingScheduled"
                class="w-4 h-4 text-teal-600 rounded border-gray-300 focus:ring-teal-500"
              />
              <span class="w-3 h-3 bg-teal-50 border-2 border-teal-400 rounded"></span>
              <span class="text-sm text-gray-700">포장예정</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.shippingScheduled"
                class="w-4 h-4 text-purple-600 rounded border-gray-300 focus:ring-purple-500"
              />
              <span class="w-3 h-3 bg-purple-50 border-2 border-purple-400 rounded"></span>
              <span class="text-sm text-gray-700">출하예정</span>
            </label>
          </div>
        </div>

        <!-- 작업지시서 필터 - 완료일 -->
        <div>
          <h3 @click="toggleWOCompleted" title="클릭: 작업지시서(완료) 전체 켜기/끄기"
            class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2 cursor-pointer select-none hover:text-green-600">
            <span class="w-3 h-3 bg-green-500 rounded-full"></span>
            작업지시서 (완료)
            <span class="ml-auto text-[11px] font-normal text-gray-400 border border-gray-200 rounded px-1.5 py-0.5">전체</span>
          </h3>
          <div class="space-y-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.issueCompleted"
                class="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
              />
              <span class="w-3 h-3 bg-indigo-100 rounded"></span>
              <span class="text-sm text-gray-700">출고완료</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.productionStart"
                class="w-4 h-4 text-yellow-600 rounded border-gray-300 focus:ring-yellow-500"
              />
              <span class="w-3 h-3 bg-yellow-100 rounded"></span>
              <span class="text-sm text-gray-700">생산시작</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.productionEnd"
                class="w-4 h-4 text-yellow-600 rounded border-gray-300 focus:ring-yellow-500"
              />
              <span class="w-3 h-3 bg-yellow-200 rounded"></span>
              <span class="text-sm text-gray-700">생산완료</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.inspectionCompleted"
                class="w-4 h-4 text-orange-600 rounded border-gray-300 focus:ring-orange-500"
              />
              <span class="w-3 h-3 bg-orange-100 rounded"></span>
              <span class="text-sm text-gray-700">검사완료</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.packingCompleted"
                class="w-4 h-4 text-teal-600 rounded border-gray-300 focus:ring-teal-500"
              />
              <span class="w-3 h-3 bg-teal-100 rounded"></span>
              <span class="text-sm text-gray-700">포장완료</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.woEvents.shippingCompleted"
                class="w-4 h-4 text-purple-600 rounded border-gray-300 focus:ring-purple-500"
              />
              <span class="w-3 h-3 bg-purple-100 rounded"></span>
              <span class="text-sm text-gray-700">출하완료</span>
            </label>
          </div>
        </div>


        <!-- 결재 필터 - 휴가/출장 -->
        <div>
          <h3 @click="toggleAP" title="클릭: 휴가/출장 전체 켜기/끄기"
            class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2 cursor-pointer select-none hover:text-emerald-600">
            <span class="w-3 h-3 bg-emerald-500 rounded-full"></span>
            휴가 / 출장
            <span class="ml-auto text-[11px] font-normal text-gray-400 border border-gray-200 rounded px-1.5 py-0.5">전체</span>
          </h3>
          <div class="space-y-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.apEvents.leave"
                class="w-4 h-4 text-emerald-600 rounded border-gray-300 focus:ring-emerald-500"
              />
              <span class="w-3 h-3 bg-emerald-100 rounded"></span>
              <span class="text-sm text-gray-700">휴가</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="localFilters.apEvents.trip"
                class="w-4 h-4 text-violet-600 rounded border-gray-300 focus:ring-violet-500"
              />
              <span class="w-3 h-3 bg-violet-100 rounded"></span>
              <span class="text-sm text-gray-700">출장</span>
            </label>
          </div>
        </div>

        <!-- 등록 일정 필터 (경영관리 > 일정등록) -->
        <div>
          <h3 @click="toggleSC" title="클릭: 등록 일정 전체 켜기/끄기"
            class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2 cursor-pointer select-none hover:text-amber-600">
            <span class="w-3 h-3 bg-amber-500 rounded-full"></span>
            등록 일정
            <span class="ml-auto text-[11px] font-normal text-gray-400 border border-gray-200 rounded px-1.5 py-0.5">전체</span>
          </h3>
          <div class="space-y-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="localFilters.scEvents.event"
                class="w-4 h-4 text-amber-600 rounded border-gray-300 focus:ring-amber-500" />
              <span class="w-3 h-3 bg-amber-100 rounded"></span>
              <span class="text-sm text-gray-700">행사</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="localFilters.scEvents.leave"
                class="w-4 h-4 text-teal-600 rounded border-gray-300 focus:ring-teal-500" />
              <span class="w-3 h-3 bg-teal-100 rounded"></span>
              <span class="text-sm text-gray-700">휴가</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="localFilters.scEvents.fieldwork"
                class="w-4 h-4 text-sky-600 rounded border-gray-300 focus:ring-sky-500" />
              <span class="w-3 h-3 bg-sky-100 rounded"></span>
              <span class="text-sm text-gray-700">외근</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="localFilters.scEvents.trip"
                class="w-4 h-4 text-purple-600 rounded border-gray-300 focus:ring-purple-500" />
              <span class="w-3 h-3 bg-purple-100 rounded"></span>
              <span class="text-sm text-gray-700">출장</span>
            </label>
          </div>
        </div>
      </div>

      <!-- 우선순위 필터 -->
      <div class="mt-4 pt-4 border-t border-gray-200">
        <h3 class="text-sm font-semibold text-gray-900 mb-3">작업지시서 우선순위</h3>
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              v-model="localFilters.priorities.normal"
              class="w-4 h-4 text-gray-600 rounded border-gray-300 focus:ring-gray-500"
            />
            <span class="text-sm text-gray-700">보통</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              v-model="localFilters.priorities.high"
              class="w-4 h-4 text-yellow-600 rounded border-gray-300 focus:ring-yellow-500"
            />
            <span class="text-sm text-yellow-700 font-medium">높음</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              v-model="localFilters.priorities.urgent"
              class="w-4 h-4 text-red-600 rounded border-gray-300 focus:ring-red-500"
            />
            <span class="text-sm text-red-700 font-medium">긴급</span>
          </label>
        </div>
      </div>

      <!-- 빠른 필터 버튼 -->
      <div class="mt-4 pt-4 border-t border-gray-200 flex flex-wrap gap-2">
        <button
          @click="selectAllFilters"
          class="px-3 py-1.5 text-xs font-medium bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          전체 선택
        </button>
        <button
          @click="clearAllFilters"
          class="px-3 py-1.5 text-xs font-medium bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          전체 해제
        </button>
        <span class="border-l border-gray-300 mx-2"></span>
        <button
          @click="selectOnlyPO"
          class="px-3 py-1.5 text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
        >
          발주서만
        </button>
        <button
          @click="selectOnlyWO"
          class="px-3 py-1.5 text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          작업지시서만
        </button>
        <button
          @click="selectOnlyAP"
          class="px-3 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors"
        >
          휴가/출장만
        </button>
        <button
          @click="selectOnlyScheduled"
          class="px-3 py-1.5 text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200 rounded-lg hover:bg-yellow-100 transition-colors"
        >
          예정일만
        </button>
        <button
          @click="selectOnlyCompleted"
          class="px-3 py-1.5 text-xs font-medium bg-green-50 text-green-700 border border-green-200 rounded-lg hover:bg-green-100 transition-colors"
        >
          완료일만
        </button>
        <button
          @click="selectDeliveryOnly"
          class="px-3 py-1.5 text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200 rounded-lg hover:bg-orange-100 transition-colors"
        >
          입고/출하만
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { type CalendarFilterOptions, defaultFilterOptions } from '@/api/calendar'

const props = defineProps<{
  monthLabel: string
  filters: CalendarFilterOptions
}>()

const emit = defineEmits<{
  (e: 'prevMonth'): void
  (e: 'nextMonth'): void
  (e: 'today'): void
  (e: 'updateFilters', filters: CalendarFilterOptions): void
}>()

const showFilters = ref(false)

// 로컬 필터 상태 (deep copy)
const localFilters = reactive<CalendarFilterOptions>(JSON.parse(JSON.stringify(props.filters)))

// 필터 변경 감지 및 emit
watch(
  localFilters,
  (newFilters) => {
    emit('updateFilters', JSON.parse(JSON.stringify(newFilters)))
  },
  { deep: true }
)

// props 변경 시 로컬 필터 동기화
// (동등성 가드: 우리 emit 으로 인한 되돌이 변경이면 재할당하지 않아 무한 루프 방지)
watch(
  () => props.filters,
  (newFilters) => {
    if (JSON.stringify(newFilters) === JSON.stringify(localFilters)) return
    Object.assign(localFilters, JSON.parse(JSON.stringify(newFilters)))
  },
  { deep: true }
)

// ===== 그룹 전체 토글 (헤더 클릭) =====
const WO_SCHEDULED_KEYS = ['issueScheduled', 'productionScheduled', 'inspectionScheduled', 'packingScheduled', 'shippingScheduled'] as const
const WO_COMPLETED_KEYS = ['issueCompleted', 'productionStart', 'productionEnd', 'inspectionCompleted', 'packingCompleted', 'shippingCompleted'] as const

function toggleKeys(obj: Record<string, boolean>, keys: readonly string[]) {
  const allOn = keys.every((k) => obj[k])
  keys.forEach((k) => { obj[k] = !allOn })
}
const togglePO = () => toggleKeys(localFilters.poEvents as unknown as Record<string, boolean>, Object.keys(localFilters.poEvents))
const toggleWOScheduled = () => toggleKeys(localFilters.woEvents as unknown as Record<string, boolean>, WO_SCHEDULED_KEYS as unknown as string[])
const toggleWOCompleted = () => toggleKeys(localFilters.woEvents as unknown as Record<string, boolean>, WO_COMPLETED_KEYS as unknown as string[])
const toggleAP = () => toggleKeys(localFilters.apEvents as unknown as Record<string, boolean>, Object.keys(localFilters.apEvents))

// 그룹 활성 상태(하나라도 켜져 있으면 활성) — 상단 빠른 토글 버튼 스타일용
const poActive = computed(() => Object.values(localFilters.poEvents).some(Boolean))
const woSchedActive = computed(() => WO_SCHEDULED_KEYS.some((k) => (localFilters.woEvents as unknown as Record<string, boolean>)[k]))
const woCompActive = computed(() => WO_COMPLETED_KEYS.some((k) => (localFilters.woEvents as unknown as Record<string, boolean>)[k]))
const apActive = computed(() => Object.values(localFilters.apEvents).some(Boolean))
const toggleSC = () => toggleKeys(localFilters.scEvents as unknown as Record<string, boolean>, Object.keys(localFilters.scEvents))
const scActive = computed(() => Object.values(localFilters.scEvents).some(Boolean))

// 활성화된 필터 개수 계산
const activeFilterCount = computed(() => {
  let count = 0
  const allTrue = defaultFilterOptions

  // 발주서 필터
  for (const key of Object.keys(localFilters.poEvents) as (keyof typeof localFilters.poEvents)[]) {
    if (localFilters.poEvents[key] !== allTrue.poEvents[key]) count++
  }

  // 작업지시서 필터
  for (const key of Object.keys(localFilters.woEvents) as (keyof typeof localFilters.woEvents)[]) {
    if (localFilters.woEvents[key] !== allTrue.woEvents[key]) count++
  }

  // 결재(휴가/출장) 필터
  for (const key of Object.keys(localFilters.apEvents) as (keyof typeof localFilters.apEvents)[]) {
    if (localFilters.apEvents[key] !== allTrue.apEvents[key]) count++
  }

  // 등록 일정 필터
  for (const key of Object.keys(localFilters.scEvents) as (keyof typeof localFilters.scEvents)[]) {
    if (localFilters.scEvents[key] !== allTrue.scEvents[key]) count++
  }

  // 우선순위 필터
  for (const key of Object.keys(localFilters.priorities) as (keyof typeof localFilters.priorities)[]) {
    if (localFilters.priorities[key] !== allTrue.priorities[key]) count++
  }

  return count
})

// 전체 선택
const selectAllFilters = () => {
  Object.assign(localFilters, JSON.parse(JSON.stringify(defaultFilterOptions)))
}

// 전체 해제
const clearAllFilters = () => {
  for (const key of Object.keys(localFilters.poEvents) as (keyof typeof localFilters.poEvents)[]) {
    localFilters.poEvents[key] = false
  }
  for (const key of Object.keys(localFilters.woEvents) as (keyof typeof localFilters.woEvents)[]) {
    localFilters.woEvents[key] = false
  }
  for (const key of Object.keys(localFilters.apEvents) as (keyof typeof localFilters.apEvents)[]) {
    localFilters.apEvents[key] = false
  }
  for (const key of Object.keys(localFilters.scEvents) as (keyof typeof localFilters.scEvents)[]) {
    localFilters.scEvents[key] = false
  }
  for (const key of Object.keys(localFilters.priorities) as (keyof typeof localFilters.priorities)[]) {
    localFilters.priorities[key] = false
  }
}

// 발주서만
const selectOnlyPO = () => {
  clearAllFilters()
  for (const key of Object.keys(localFilters.poEvents) as (keyof typeof localFilters.poEvents)[]) {
    localFilters.poEvents[key] = true
  }
  // 우선순위는 전체 선택
  for (const key of Object.keys(localFilters.priorities) as (keyof typeof localFilters.priorities)[]) {
    localFilters.priorities[key] = true
  }
}

// 작업지시서만
const selectOnlyWO = () => {
  clearAllFilters()
  for (const key of Object.keys(localFilters.woEvents) as (keyof typeof localFilters.woEvents)[]) {
    localFilters.woEvents[key] = true
  }
  // 우선순위는 전체 선택
  for (const key of Object.keys(localFilters.priorities) as (keyof typeof localFilters.priorities)[]) {
    localFilters.priorities[key] = true
  }
}

// 휴가/출장만 (전자결재 + 직접 등록한 휴가·외근·출장)
const selectOnlyAP = () => {
  clearAllFilters()
  for (const key of Object.keys(localFilters.apEvents) as (keyof typeof localFilters.apEvents)[]) {
    localFilters.apEvents[key] = true
  }
  localFilters.scEvents.leave = true
  localFilters.scEvents.fieldwork = true
  localFilters.scEvents.trip = true
}

// 예정일만
const selectOnlyScheduled = () => {
  clearAllFilters()
  // 발주서 예정 관련
  localFilters.poEvents.deliveryExpected = true
  // 작업지시서 예정일
  localFilters.woEvents.issueScheduled = true
  localFilters.woEvents.productionScheduled = true
  localFilters.woEvents.inspectionScheduled = true
  localFilters.woEvents.packingScheduled = true
  localFilters.woEvents.shippingScheduled = true
  // 우선순위는 전체 선택
  for (const key of Object.keys(localFilters.priorities) as (keyof typeof localFilters.priorities)[]) {
    localFilters.priorities[key] = true
  }
}

// 완료일만
const selectOnlyCompleted = () => {
  clearAllFilters()
  // 발주서 완료 관련
  localFilters.poEvents.deliveryActual = true
  localFilters.poEvents.payment = true
  // 작업지시서 완료일
  localFilters.woEvents.issueCompleted = true
  localFilters.woEvents.productionStart = true
  localFilters.woEvents.productionEnd = true
  localFilters.woEvents.inspectionCompleted = true
  localFilters.woEvents.packingCompleted = true
  localFilters.woEvents.shippingCompleted = true
  // 우선순위는 전체 선택
  for (const key of Object.keys(localFilters.priorities) as (keyof typeof localFilters.priorities)[]) {
    localFilters.priorities[key] = true
  }
}

// 입고/출하만
const selectDeliveryOnly = () => {
  clearAllFilters()
  // 발주서 입고
  localFilters.poEvents.deliveryExpected = true
  localFilters.poEvents.deliveryActual = true
  // 작업지시서 출하
  localFilters.woEvents.shippingScheduled = true
  localFilters.woEvents.shippingCompleted = true
  // 우선순위는 전체 선택
  for (const key of Object.keys(localFilters.priorities) as (keyof typeof localFilters.priorities)[]) {
    localFilters.priorities[key] = true
  }
}
</script>
