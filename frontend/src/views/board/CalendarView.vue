<template>
  <div class="container mx-auto px-4 py-6">
    <!-- 페이지 헤더 -->
    <div class="mb-6 flex items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">일정 캘린더</h1>
        <p class="mt-1 text-sm text-gray-500">
          발주서 · 작업지시서 · 휴가/출장 · 등록 일정(행사/외근 등)을 한눈에 확인하세요
        </p>
      </div>
      <router-link
        to="/mgmt/schedule-new"
        class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
      >
        <span class="text-base leading-none">+</span> 일정 등록
      </router-link>
    </div>

    <!-- 캘린더 툴바 (네비게이션 + 필터) -->
    <CalendarToolbar
      :month-label="currentMonthLabel"
      :filters="filters"
      @prev-month="prevMonth"
      @next-month="nextMonth"
      @today="goToToday"
      @update-filters="handleFilterUpdate"
    />

    <!-- 로딩 상태 -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="flex items-center gap-3 text-gray-500">
        <svg class="animate-spin h-6 w-6" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>일정을 불러오는 중...</span>
      </div>
    </div>

    <!-- 에러 상태 -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
      <div class="flex items-center gap-2 text-red-800">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="font-medium">일정을 불러오는 중 오류가 발생했습니다</span>
      </div>
      <p class="mt-1 text-sm text-red-600">{{ error }}</p>
      <button
        @click="loadEvents"
        class="mt-2 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 rounded-lg hover:bg-red-200 transition-colors"
      >
        다시 시도
      </button>
    </div>

    <!-- 캘린더 그리드 -->
    <MonthCalendar
      v-else
      :weeks="getWeeksInMonth"
      :events="events"
      :holidays="holidays"
      :max-events-per-day="4"
      @date-click="handleDateClick"
      @event-click="handleEventClick"
      @show-more="handleShowMore"
    />

    <!-- 이벤트 요약 -->
    <div class="mt-4 flex items-center justify-between text-sm text-gray-500">
      <span>
        총 {{ events.length }}개의 일정
        <span v-if="countSummary" class="ml-2">({{ countSummary }})</span>
      </span>
      <button
        @click="showLegend = !showLegend"
        class="flex items-center gap-1 hover:text-gray-700 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        범례 {{ showLegend ? '숨기기' : '보기' }}
      </button>
    </div>

    <!-- 범례 -->
    <CalendarLegend v-if="showLegend" class="mt-4" />

    <!-- 이벤트 상세 팝오버 -->
    <EventDetailPopover
      v-if="selectedEvent"
      :visible="!!selectedEvent"
      :event="selectedEvent"
      :position="popoverPosition"
      @close="selectedEvent = null"
    />

    <!-- 더보기 모달 -->
    <Teleport to="body">
      <div
        v-if="showMoreModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click="showMoreModal = false"
      >
        <div
          class="bg-white rounded-lg shadow-xl w-96 max-w-[90vw] max-h-[80vh] overflow-hidden"
          @click.stop
        >
          <div class="px-4 py-3 border-b bg-gray-50">
            <div class="flex items-center justify-between">
              <h3 class="font-semibold text-gray-900">
                {{ moreModalDate?.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' }) }}
              </h3>
              <button
                @click="showMoreModal = false"
                class="p-1 rounded hover:bg-gray-200 transition-colors"
              >
                <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
          <div class="p-4 overflow-y-auto max-h-[60vh] space-y-2">
            <div
              v-for="event in moreModalEvents"
              :key="event.id"
              class="px-3 py-2 rounded-lg cursor-pointer transition-all hover:shadow-md"
              :class="[event.bgColor, event.borderColor ? `border-l-4 ${event.borderColor}` : '']"
              @click="handleEventClick(event, $event)"
            >
              <div class="flex items-center gap-2">
                <span class="text-xs font-medium" :class="event.color">
                  {{ eventTypeLabels[event.type] }}
                </span>
                <span
                  v-if="event.priority !== undefined && event.priority > 0"
                  class="px-1.5 py-0.5 text-xs rounded"
                  :class="event.priority === 2 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'"
                >
                  {{ event.priority === 2 ? '긴급' : '높음' }}
                </span>
              </div>
              <div class="mt-1 font-medium text-gray-900">{{ event.title }}</div>
              <div v-if="event.subtitle" class="text-sm text-gray-600">{{ event.subtitle }}</div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useCalendar, type CalendarDay } from '@/composables/useCalendar'
import { calendarApi, defaultFilterOptions, eventTypeLabels, type CalendarEvent, type CalendarFilterOptions, type Holiday } from '@/api/calendar'
import MonthCalendar from './calendar/MonthCalendar.vue'
import CalendarToolbar from './calendar/CalendarToolbar.vue'
import CalendarLegend from './calendar/CalendarLegend.vue'
import EventDetailPopover from './calendar/EventDetailPopover.vue'

// 캘린더 훅
const {
  currentMonthLabel,
  getWeeksInMonth,
  monthRange,
  prevMonth,
  nextMonth,
  goToToday,
} = useCalendar()

// 상태
const loading = ref(false)
const error = ref<string | null>(null)
const events = ref<CalendarEvent[]>([])
const filters = ref<CalendarFilterOptions>(JSON.parse(JSON.stringify(defaultFilterOptions)))
const showLegend = ref(false)

// 선택된 이벤트 (팝오버용)
const selectedEvent = ref<CalendarEvent | null>(null)
const popoverPosition = ref<{ x: number; y: number } | undefined>()

// 더보기 모달
const showMoreModal = ref(false)
const moreModalDate = ref<Date | null>(null)
const moreModalEvents = ref<CalendarEvent[]>([])

// 이벤트 카운트
const poEventCount = computed(() => events.value.filter(e => e.category === 'PO').length)
const woEventCount = computed(() => events.value.filter(e => e.category === 'WO').length)
const apEventCount = computed(() => events.value.filter(e => e.category === 'AP').length)
const scEventCount = computed(() => events.value.filter(e => e.category === 'SC').length)

// 요약 문구 (발주서/작업지시서/휴가·출장 카운트)
const countSummary = computed(() => {
  const parts: string[] = []
  if (poEventCount.value > 0) parts.push(`발주서 ${poEventCount.value}건`)
  if (woEventCount.value > 0) parts.push(`작업지시서 ${woEventCount.value}건`)
  if (apEventCount.value > 0) parts.push(`휴가/출장 ${apEventCount.value}건`)
  if (scEventCount.value > 0) parts.push(`등록 일정 ${scEventCount.value}건`)
  return parts.join(', ')
})

// 이벤트 로드
const loadEvents = async () => {
  loading.value = true
  error.value = null

  try {
    const { start, end } = monthRange.value
    events.value = await calendarApi.getEvents(start, end, filters.value)
  } catch (e: any) {
    console.error('Failed to load calendar events:', e)
    error.value = e.message || '알 수 없는 오류가 발생했습니다'
  } finally {
    loading.value = false
  }
}

// 공휴일 로드 (필터와 무관 — 월이 바뀔 때만). 늦게 도착한 이전 달 응답은 버린다.
const holidays = ref<Holiday[]>([])
const loadHolidays = async () => {
  const { start, end } = monthRange.value
  const result = await calendarApi.getHolidays(start, end)
  if (monthRange.value.start === start) holidays.value = result
}

// 필터 업데이트 핸들러
const handleFilterUpdate = (newFilters: CalendarFilterOptions) => {
  filters.value = newFilters
  loadEvents()
}

// 날짜 클릭 핸들러
const handleDateClick = (day: CalendarDay) => {
  // 해당 날짜의 이벤트가 있으면 더보기 모달 표시
  const dayEvents = events.value.filter(e => e.date === day.dateString)
  if (dayEvents.length > 0) {
    moreModalDate.value = day.date
    moreModalEvents.value = dayEvents
    showMoreModal.value = true
  }
}

// 이벤트 클릭 핸들러
const handleEventClick = (event: CalendarEvent, mouseEvent?: MouseEvent) => {
  selectedEvent.value = event
  if (mouseEvent) {
    popoverPosition.value = {
      x: mouseEvent.clientX,
      y: mouseEvent.clientY,
    }
  } else {
    popoverPosition.value = undefined
  }
  // 더보기 모달 닫기
  showMoreModal.value = false
}

// 더보기 핸들러
const handleShowMore = (day: CalendarDay, dayEvents: CalendarEvent[]) => {
  moreModalDate.value = day.date
  moreModalEvents.value = dayEvents
  showMoreModal.value = true
}

// 월 변경 시 이벤트 다시 로드
watch(monthRange, () => {
  loadEvents()
  loadHolidays()
})

// 초기 로드
onMounted(() => {
  loadEvents()
  loadHolidays()
})
</script>
