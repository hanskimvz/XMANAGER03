<template>
  <div class="bg-white rounded-lg shadow">
    <!-- 요일 헤더 -->
    <div class="grid grid-cols-7 border-b border-gray-200">
      <div
        v-for="(day, index) in weekDays"
        :key="day"
        class="py-3 text-center text-sm font-semibold"
        :class="{
          'text-red-500': index === 0,
          'text-blue-500': index === 6,
          'text-gray-700': index > 0 && index < 6,
        }"
      >
        {{ day }}
      </div>
    </div>

    <!-- 날짜 그리드 -->
    <div class="grid grid-cols-7">
      <template v-for="(week, weekIndex) in weeks" :key="weekIndex">
        <div
          v-for="(day, dayIndex) in week.days"
          :key="day.dateString"
          class="min-h-[120px] border-b border-r border-gray-100 p-1 cursor-pointer hover:bg-gray-50 transition-colors"
          :class="{
            'bg-gray-50': !day.isCurrentMonth,
            'bg-blue-50': day.isToday,
            'border-r-0': dayIndex === 6,
          }"
          @click="$emit('dateClick', day)"
        >
          <!-- 날짜 숫자 -->
          <div class="flex items-center justify-between mb-1">
            <span
              class="inline-flex items-center justify-center w-7 h-7 text-sm rounded-full"
              :class="{
                'bg-blue-600 text-white font-bold': day.isToday,
                'text-gray-400': !day.isCurrentMonth && !day.isToday,
                'text-red-500': (dayIndex === 0 || !!holidayName(day.dateString)) && day.isCurrentMonth && !day.isToday,
                'text-blue-500': dayIndex === 6 && !holidayName(day.dateString) && day.isCurrentMonth && !day.isToday,
                'text-gray-900': !day.isWeekend && !holidayName(day.dateString) && day.isCurrentMonth && !day.isToday,
              }"
            >
              {{ day.day }}
            </span>
            <!-- 공휴일 이름 -->
            <span
              v-if="holidayName(day.dateString)"
              class="ml-1 flex-1 min-w-0 truncate text-right text-xs"
              :class="day.isCurrentMonth ? 'text-red-500' : 'text-red-300'"
              :title="holidayName(day.dateString)"
            >
              {{ holidayName(day.dateString) }}
            </span>
          </div>

          <!-- 이벤트 목록 -->
          <div class="space-y-0.5 overflow-hidden">
            <CalendarEvent
              v-for="event in getEventsForDay(day.dateString).slice(0, maxEventsPerDay)"
              :key="event.id"
              :event="event"
              @click.stop="$emit('eventClick', event)"
            />

            <!-- 더보기 표시 -->
            <div
              v-if="getEventsForDay(day.dateString).length > maxEventsPerDay"
              class="text-xs text-gray-500 pl-1 hover:text-gray-700 cursor-pointer"
              @click.stop="$emit('showMore', day, getEventsForDay(day.dateString))"
            >
              +{{ getEventsForDay(day.dateString).length - maxEventsPerDay }}개 더보기
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CalendarWeek } from '@/composables/useCalendar'
import type { CalendarEvent as CalendarEventType, Holiday } from '@/api/calendar'
import CalendarEvent from './CalendarEvent.vue'

const props = defineProps<{
  weeks: CalendarWeek[]
  events: CalendarEventType[]
  holidays?: Holiday[]
  maxEventsPerDay?: number
}>()

// 날짜별 공휴일 이름 (같은 날 2건이면 '·'로 이어 붙임)
const holidayMap = computed(() => {
  const map = new Map<string, string>()
  for (const h of props.holidays ?? []) {
    const prev = map.get(h.date)
    map.set(h.date, prev && prev !== h.name ? `${prev}·${h.name}` : h.name)
  }
  return map
})
const holidayName = (dateString: string): string => holidayMap.value.get(dateString) || ''

defineEmits<{
  (e: 'dateClick', day: CalendarWeek['days'][0]): void
  (e: 'eventClick', event: CalendarEventType): void
  (e: 'showMore', day: CalendarWeek['days'][0], events: CalendarEventType[]): void
}>()

const weekDays = ['일', '월', '화', '수', '목', '금', '토']
const maxEventsPerDay = computed(() => props.maxEventsPerDay ?? 3)

// 날짜별 이벤트 맵 생성
const eventsByDate = computed(() => {
  const map = new Map<string, CalendarEventType[]>()
  for (const event of props.events) {
    const existing = map.get(event.date) || []
    existing.push(event)
    map.set(event.date, existing)
  }
  return map
})

// 특정 날짜의 이벤트 조회
const getEventsForDay = (dateString: string): CalendarEventType[] => {
  return eventsByDate.value.get(dateString) || []
}
</script>
