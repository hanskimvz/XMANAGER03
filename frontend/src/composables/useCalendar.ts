/**
 * 캘린더 Composable
 * 날짜 계산, 월 이동, 이벤트 관리 로직
 */

import { ref, computed } from 'vue'

export interface CalendarDay {
  date: Date
  day: number
  isCurrentMonth: boolean
  isToday: boolean
  isWeekend: boolean
  dateString: string // YYYY-MM-DD 형식
}

export interface CalendarWeek {
  days: CalendarDay[]
}

export function useCalendar() {
  const currentDate = ref(new Date())
  const viewMode = ref<'month' | 'week'>('month')

  // 현재 년월
  const currentYear = computed(() => currentDate.value.getFullYear())
  const currentMonth = computed(() => currentDate.value.getMonth())

  // 년월 문자열 (표시용)
  const currentMonthLabel = computed(() => {
    return `${currentYear.value}년 ${currentMonth.value + 1}월`
  })

  // 날짜를 YYYY-MM-DD 형식으로 변환
  const formatDateString = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  // 오늘 날짜인지 확인
  const isToday = (date: Date): boolean => {
    const today = new Date()
    return (
      date.getFullYear() === today.getFullYear() &&
      date.getMonth() === today.getMonth() &&
      date.getDate() === today.getDate()
    )
  }

  // 주말인지 확인
  const isWeekend = (date: Date): boolean => {
    const day = date.getDay()
    return day === 0 || day === 6
  }

  // 해당 월의 첫 날
  const getFirstDayOfMonth = (year: number, month: number): Date => {
    return new Date(year, month, 1)
  }

  // 해당 월의 마지막 날
  const getLastDayOfMonth = (year: number, month: number): Date => {
    return new Date(year, month + 1, 0)
  }

  // 월 캘린더의 주 배열 생성 (6주 고정)
  const getWeeksInMonth = computed((): CalendarWeek[] => {
    const year = currentYear.value
    const month = currentMonth.value
    const firstDay = getFirstDayOfMonth(year, month)
    const lastDay = getLastDayOfMonth(year, month)

    const weeks: CalendarWeek[] = []

    // 첫 주의 시작일 계산 (일요일부터 시작)
    const startDate = new Date(firstDay)
    startDate.setDate(startDate.getDate() - firstDay.getDay())

    // 6주 생성
    for (let week = 0; week < 6; week++) {
      const days: CalendarDay[] = []

      for (let day = 0; day < 7; day++) {
        const date = new Date(startDate)
        date.setDate(startDate.getDate() + (week * 7) + day)

        days.push({
          date: new Date(date),
          day: date.getDate(),
          isCurrentMonth: date.getMonth() === month,
          isToday: isToday(date),
          isWeekend: isWeekend(date),
          dateString: formatDateString(date),
        })
      }

      weeks.push({ days })
    }

    return weeks
  })

  // 현재 월의 시작/끝 날짜 (API 조회용)
  const monthRange = computed(() => {
    const year = currentYear.value
    const month = currentMonth.value

    // 캘린더에 표시되는 첫 날 (이전 달 포함)
    const firstDay = getFirstDayOfMonth(year, month)
    const startDate = new Date(firstDay)
    startDate.setDate(startDate.getDate() - firstDay.getDay())

    // 캘린더에 표시되는 마지막 날 (다음 달 포함)
    const endDate = new Date(startDate)
    endDate.setDate(endDate.getDate() + 41) // 6주 * 7일 - 1

    return {
      start: formatDateString(startDate),
      end: formatDateString(endDate),
    }
  })

  // 이전 달로 이동
  const prevMonth = () => {
    const newDate = new Date(currentDate.value)
    newDate.setMonth(newDate.getMonth() - 1)
    currentDate.value = newDate
  }

  // 다음 달로 이동
  const nextMonth = () => {
    const newDate = new Date(currentDate.value)
    newDate.setMonth(newDate.getMonth() + 1)
    currentDate.value = newDate
  }

  // 오늘로 이동
  const goToToday = () => {
    currentDate.value = new Date()
  }

  // 특정 날짜로 이동
  const goToDate = (date: Date) => {
    currentDate.value = new Date(date)
  }

  // 두 날짜가 같은지 비교
  const isSameDay = (d1: Date, d2: Date): boolean => {
    return (
      d1.getFullYear() === d2.getFullYear() &&
      d1.getMonth() === d2.getMonth() &&
      d1.getDate() === d2.getDate()
    )
  }

  return {
    currentDate,
    viewMode,
    currentYear,
    currentMonth,
    currentMonthLabel,
    getWeeksInMonth,
    monthRange,
    prevMonth,
    nextMonth,
    goToToday,
    goToDate,
    formatDateString,
    isSameDay,
    isToday,
    isWeekend,
  }
}
