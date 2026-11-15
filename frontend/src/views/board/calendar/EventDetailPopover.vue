<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50"
      @click="$emit('close')"
    >
      <div
        class="absolute bg-white rounded-lg shadow-xl border border-gray-200 w-80 max-w-[90vw]"
        :style="popoverStyle"
        @click.stop
      >
        <!-- 헤더 -->
        <div
          class="px-4 py-3 rounded-t-lg border-b"
          :class="headerBgClass"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span
                class="px-2 py-0.5 text-xs font-medium rounded"
                :class="event.bgColor + ' ' + event.color"
              >
                {{ eventTypeLabel }}
              </span>
              <span
                v-if="event.priority !== undefined && event.priority > 0"
                class="px-2 py-0.5 text-xs font-medium rounded"
                :class="priorityClass"
              >
                {{ priorityLabel }}
              </span>
            </div>
            <button
              @click="$emit('close')"
              class="p-1 rounded hover:bg-black/10 transition-colors"
            >
              <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <h3 class="mt-2 text-lg font-bold text-gray-900">{{ event.title }}</h3>
          <p v-if="event.subtitle" class="text-sm text-gray-600 mt-0.5">{{ event.subtitle }}</p>
        </div>

        <!-- 본문 -->
        <div class="px-4 py-3 space-y-3">
          <!-- 날짜 -->
          <div class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span class="text-gray-700">{{ formattedDate }}</span>
          </div>

          <!-- 상태 (PO) -->
          <div v-if="event.category === 'PO' && poData" class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-gray-700">상태: {{ poStatusLabel }}</span>
          </div>

          <!-- 금액 (PO) -->
          <div v-if="event.category === 'PO' && poData?.total_amount" class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-gray-700">{{ formatCurrency(poData.total_amount) }}</span>
          </div>

          <!-- 상태 (AP: 휴가/출장) -->
          <div v-if="event.category === 'AP' && event.status" class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-gray-700">상태: {{ apStatusLabel }}</span>
          </div>

          <!-- 장소·메모·등록자 (SC: 등록 일정) -->
          <template v-if="event.category === 'SC' && scData">
            <div v-if="scData.location" class="flex items-center gap-3 text-sm">
              <svg class="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span class="text-gray-700">{{ scData.location }}</span>
            </div>
            <p v-if="scData.memo" class="text-sm text-gray-600 whitespace-pre-wrap break-words">{{ scData.memo }}</p>
            <p v-if="scData.created_by_name" class="text-xs text-gray-400">등록자: {{ scData.created_by_name }}</p>
          </template>

          <!-- 상태 (WO) -->
          <div v-if="event.category === 'WO' && woData" class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-gray-700">상태: {{ woStatusLabel }}</span>
          </div>

          <!-- 수량 (WO) -->
          <div v-if="event.category === 'WO' && woData" class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
            </svg>
            <span class="text-gray-700">
              수량: {{ woData.completed_quantity }} / {{ woData.order_quantity }}
            </span>
          </div>
        </div>

        <!-- 푸터 -->
        <div class="px-4 py-3 border-t bg-gray-50 rounded-b-lg flex justify-end gap-2">
          <button
            @click="goToDetail"
            class="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            {{ event.category === 'AP' ? '결재 문서 보기' : event.category === 'SC' ? '일정 등록 화면' : '상세보기' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { CalendarEvent } from '@/api/calendar'
import { eventTypeLabels } from '@/api/calendar'
import type { PurchaseOrder } from '@/api/purchaseOrder'
import { poStatusLabels } from '@/api/purchaseOrder'
import type { WorkOrder } from '@/api/workOrder'
import { woStatusLabels, priorityLabels } from '@/api/workOrder'
import type { ScheduleItem } from '@/api/schedule'

const props = defineProps<{
  visible: boolean
  event: CalendarEvent
  position?: { x: number; y: number }
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const router = useRouter()

// 이벤트 유형 라벨
const eventTypeLabel = computed(() => {
  return eventTypeLabels[props.event.type] || props.event.type
})

// 등록 일정 데이터
const scData = computed(() => {
  if (props.event.category === 'SC') {
    return props.event.originalData as ScheduleItem | undefined
  }
  return undefined
})

// 날짜 포맷 (여러 날짜리 등록 일정은 기간으로 표시)
const formattedDate = computed(() => {
  const fmt = (s: string) => new Date(s).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
  const sc = scData.value
  if (sc && sc.start_date !== sc.end_date) return `${fmt(sc.start_date)} ~ ${fmt(sc.end_date)}`
  return fmt(props.event.date)
})

// 발주서 데이터
const poData = computed(() => {
  if (props.event.category === 'PO') {
    return props.event.originalData as PurchaseOrder | undefined
  }
  return undefined
})

// 작업지시서 데이터
const woData = computed(() => {
  if (props.event.category === 'WO') {
    return props.event.originalData as WorkOrder | undefined
  }
  return undefined
})

// 발주서 상태 라벨
const poStatusLabel = computed(() => {
  if (!poData.value) return ''
  return poStatusLabels[poData.value.status] || poData.value.status
})

// 작업지시서 상태 라벨
const woStatusLabel = computed(() => {
  if (!woData.value) return ''
  return woStatusLabels[woData.value.status] || woData.value.status
})

// 우선순위 라벨
const priorityLabel = computed(() => {
  if (props.event.priority === undefined) return ''
  return priorityLabels[props.event.priority as 0 | 1 | 2] || '보통'
})

// 우선순위 클래스
const priorityClass = computed(() => {
  switch (props.event.priority) {
    case 1:
      return 'bg-yellow-100 text-yellow-800'
    case 2:
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
})

// 헤더 배경색
const headerBgClass = computed(() => {
  if (props.event.category === 'PO') {
    return 'bg-blue-50 border-blue-100'
  }
  if (props.event.category === 'AP') {
    return props.event.type === 'AP_LEAVE'
      ? 'bg-emerald-50 border-emerald-100'
      : 'bg-violet-50 border-violet-100'
  }
  if (props.event.category === 'SC') {
    return 'bg-amber-50 border-amber-100'
  }
  return 'bg-indigo-50 border-indigo-100'
})

// 결재(휴가/출장) 상태 라벨
const apStatusLabel = computed(() => {
  const map: Record<string, string> = {
    IN_PROGRESS: '진행중',
    APPROVED: '승인완료',
    REJECTED: '반려',
    DRAFT: '임시저장',
    CANCELLED: '취소',
  }
  return props.event.status ? (map[props.event.status] || props.event.status) : ''
})

// 팝오버 위치 스타일
const popoverStyle = computed(() => {
  if (!props.position) {
    return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
  }

  const { x, y } = props.position
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  const popoverWidth = 320
  const popoverHeight = 300

  let left = x
  let top = y + 10

  // 오른쪽 경계 체크
  if (left + popoverWidth > viewportWidth - 20) {
    left = viewportWidth - popoverWidth - 20
  }

  // 하단 경계 체크
  if (top + popoverHeight > viewportHeight - 20) {
    top = y - popoverHeight - 10
  }

  // 상단 경계 체크
  if (top < 20) {
    top = 20
  }

  return {
    left: `${left}px`,
    top: `${top}px`,
  }
})

// 금액 포맷 (소수점 2자리까지)
const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(amount)
}

// 상세 페이지로 이동
const goToDetail = () => {
  emit('close')
  if (props.event.category === 'PO') {
    router.push(`/purchase-orders?highlight=${props.event.originalId}`)
  } else if (props.event.category === 'AP') {
    router.push(`/approvals/${props.event.originalId}`)
  } else if (props.event.category === 'SC') {
    router.push('/mgmt/schedule-new')
  } else {
    router.push(`/work-orders?highlight=${props.event.originalId}`)
  }
}
</script>
