/**
 * 캘린더 API 서비스
 * 발주서·작업지시서·전자결재(휴가/출장)·등록 일정(경영관리 > 일정등록)을 캘린더용으로 조회
 */

import { purchaseOrderApi, type PurchaseOrder, type PurchaseOrderStatus } from './purchaseOrder'
import { workOrderApi, type WorkOrder, type WorkOrderStatus } from './workOrder'
import apiClient from './client'
import { scheduleApi, type ScheduleItem, type ScheduleType } from './schedule'

// ==================== 이벤트 타입 정의 ====================

// 발주서 이벤트 유형
export type POEventType = 'PO_ORDER' | 'PO_DELIVERY_EXPECTED' | 'PO_DELIVERY_ACTUAL' | 'PO_PAYMENT'

// 작업지시서 이벤트 유형 (예정일)
export type WOScheduledEventType =
  | 'WO_ISSUE_SCHEDULED'
  | 'WO_PRODUCTION_SCHEDULED'
  | 'WO_INSPECTION_SCHEDULED'
  | 'WO_PACKING_SCHEDULED'
  | 'WO_SHIPPING_SCHEDULED'

// 작업지시서 이벤트 유형 (완료일)
export type WOCompletedEventType =
  | 'WO_ISSUE_COMPLETED'
  | 'WO_PRODUCTION_START'
  | 'WO_PRODUCTION_END'
  | 'WO_INSPECTION_COMPLETED'
  | 'WO_PACKING_COMPLETED'
  | 'WO_SHIPPING_COMPLETED'

export type WOEventType = WOScheduledEventType | WOCompletedEventType

// 결재(휴가/출장) 이벤트 유형
export type APEventType = 'AP_LEAVE' | 'AP_TRIP'

// 등록 일정(경영관리 > 일정등록) 이벤트 유형
export type SCEventType = 'SC_EVENT' | 'SC_LEAVE' | 'SC_FIELDWORK' | 'SC_TRIP'

export type CalendarEventType = POEventType | WOEventType | APEventType | SCEventType

// 결재 캘린더 이벤트 (백엔드 응답)
export interface ApprovalCalendarItem {
  id: number
  doc_number: string
  title: string
  form_code: 'TRIP' | 'LEAVE'
  drafter_name?: string
  start_date: string // YYYY-MM-DD
  end_date: string // YYYY-MM-DD
  status: string
  leave_type?: string
}

// ==================== 캘린더 이벤트 인터페이스 ====================

export interface CalendarEvent {
  id: string // 고유 ID (예: "PO_123_ORDER")
  type: CalendarEventType
  category: 'PO' | 'WO' | 'AP' | 'SC'
  date: string // YYYY-MM-DD
  title: string
  subtitle?: string
  status?: string
  priority?: number // 작업지시서 우선순위
  color: string // Tailwind 색상 클래스
  bgColor: string // 배경색
  borderColor?: string // 테두리색 (예정일용)
  originalId: number // 원본 데이터 ID
  originalData?: PurchaseOrder | WorkOrder | ScheduleItem
}

// ==================== 필터 옵션 ====================

export interface CalendarFilterOptions {
  // 발주서 필터
  poEvents: {
    order: boolean // 발주일
    deliveryExpected: boolean // 납기예정
    deliveryActual: boolean // 입고완료
    payment: boolean // 결제
  }
  // 작업지시서 필터
  woEvents: {
    // 예정일
    issueScheduled: boolean // 출고예정
    productionScheduled: boolean // 생산예정
    inspectionScheduled: boolean // 검사예정
    packingScheduled: boolean // 포장예정
    shippingScheduled: boolean // 출하예정
    // 완료일
    issueCompleted: boolean // 출고완료
    productionStart: boolean // 생산시작
    productionEnd: boolean // 생산완료
    inspectionCompleted: boolean // 검사완료
    packingCompleted: boolean // 포장완료
    shippingCompleted: boolean // 출하완료
  }
  // 결재(휴가/출장) 필터
  apEvents: {
    leave: boolean // 휴가
    trip: boolean // 출장
  }
  // 등록 일정 필터 (경영관리 > 일정등록)
  scEvents: {
    event: boolean // 행사
    leave: boolean // 휴가
    fieldwork: boolean // 외근
    trip: boolean // 출장
  }
  // 우선순위 필터 (작업지시서)
  priorities: {
    normal: boolean // 보통
    high: boolean // 높음
    urgent: boolean // 긴급
  }
}

// 기본 필터 (모두 선택)
export const defaultFilterOptions: CalendarFilterOptions = {
  poEvents: {
    order: true,
    deliveryExpected: true,
    deliveryActual: true,
    payment: true,
  },
  woEvents: {
    issueScheduled: true,
    productionScheduled: true,
    inspectionScheduled: true,
    packingScheduled: true,
    shippingScheduled: true,
    issueCompleted: true,
    productionStart: true,
    productionEnd: true,
    inspectionCompleted: true,
    packingCompleted: true,
    shippingCompleted: true,
  },
  apEvents: {
    leave: true,
    trip: true,
  },
  scEvents: {
    event: true,
    leave: true,
    fieldwork: true,
    trip: true,
  },
  priorities: {
    normal: true,
    high: true,
    urgent: true,
  },
}

// ==================== 색상 매핑 ====================

// 발주서 이벤트 색상
export const poEventColors: Record<POEventType, { color: string; bgColor: string }> = {
  PO_ORDER: { color: 'text-blue-700', bgColor: 'bg-blue-100' },
  PO_DELIVERY_EXPECTED: { color: 'text-orange-700', bgColor: 'bg-orange-100' },
  PO_DELIVERY_ACTUAL: { color: 'text-green-700', bgColor: 'bg-green-100' },
  PO_PAYMENT: { color: 'text-purple-700', bgColor: 'bg-purple-100' },
}

// 작업지시서 이벤트 색상 (예정일 - 테두리만)
export const woScheduledColors: Record<WOScheduledEventType, { color: string; borderColor: string; bgColor: string }> = {
  WO_ISSUE_SCHEDULED: { color: 'text-indigo-600', borderColor: 'border-indigo-400', bgColor: 'bg-indigo-50' },
  WO_PRODUCTION_SCHEDULED: { color: 'text-yellow-700', borderColor: 'border-yellow-400', bgColor: 'bg-yellow-50' },
  WO_INSPECTION_SCHEDULED: { color: 'text-orange-600', borderColor: 'border-orange-400', bgColor: 'bg-orange-50' },
  WO_PACKING_SCHEDULED: { color: 'text-teal-600', borderColor: 'border-teal-400', bgColor: 'bg-teal-50' },
  WO_SHIPPING_SCHEDULED: { color: 'text-purple-600', borderColor: 'border-purple-400', bgColor: 'bg-purple-50' },
}

// 작업지시서 이벤트 색상 (완료일 - 채움)
export const woCompletedColors: Record<WOCompletedEventType, { color: string; bgColor: string }> = {
  WO_ISSUE_COMPLETED: { color: 'text-indigo-700', bgColor: 'bg-indigo-100' },
  WO_PRODUCTION_START: { color: 'text-yellow-800', bgColor: 'bg-yellow-100' },
  WO_PRODUCTION_END: { color: 'text-yellow-800', bgColor: 'bg-yellow-200' },
  WO_INSPECTION_COMPLETED: { color: 'text-orange-700', bgColor: 'bg-orange-100' },
  WO_PACKING_COMPLETED: { color: 'text-teal-700', bgColor: 'bg-teal-100' },
  WO_SHIPPING_COMPLETED: { color: 'text-purple-700', bgColor: 'bg-purple-100' },
}

// 결재(휴가/출장) 이벤트 색상
export const apEventColors: Record<APEventType, { color: string; bgColor: string }> = {
  AP_LEAVE: { color: 'text-emerald-700', bgColor: 'bg-emerald-100' },
  AP_TRIP: { color: 'text-violet-700', bgColor: 'bg-violet-100' },
}

// 등록 일정 이벤트 색상 (일정등록 화면의 유형 색과 맞춤)
export const scEventColors: Record<SCEventType, { color: string; bgColor: string }> = {
  SC_EVENT: { color: 'text-amber-700', bgColor: 'bg-amber-100' },
  SC_LEAVE: { color: 'text-teal-700', bgColor: 'bg-teal-100' },
  SC_FIELDWORK: { color: 'text-sky-700', bgColor: 'bg-sky-100' },
  SC_TRIP: { color: 'text-purple-700', bgColor: 'bg-purple-100' },
}

// ==================== 이벤트 라벨 ====================

export const eventTypeLabels: Record<CalendarEventType, string> = {
  // 발주서
  PO_ORDER: '발주',
  PO_DELIVERY_EXPECTED: '납기예정',
  PO_DELIVERY_ACTUAL: '입고',
  PO_PAYMENT: '결제',
  // 작업지시서 (예정)
  WO_ISSUE_SCHEDULED: '출고예정',
  WO_PRODUCTION_SCHEDULED: '생산예정',
  WO_INSPECTION_SCHEDULED: '검사예정',
  WO_PACKING_SCHEDULED: '포장예정',
  WO_SHIPPING_SCHEDULED: '출하예정',
  // 작업지시서 (완료)
  WO_ISSUE_COMPLETED: '출고완료',
  WO_PRODUCTION_START: '생산시작',
  WO_PRODUCTION_END: '생산완료',
  WO_INSPECTION_COMPLETED: '검사완료',
  WO_PACKING_COMPLETED: '포장완료',
  WO_SHIPPING_COMPLETED: '출하완료',
  // 결재 (휴가/출장)
  AP_LEAVE: '휴가',
  AP_TRIP: '출장',
  // 등록 일정
  SC_EVENT: '행사',
  SC_LEAVE: '휴가',
  SC_FIELDWORK: '외근',
  SC_TRIP: '출장',
}

// ==================== 발주서 이벤트 변환 ====================

function convertPOToEvents(po: PurchaseOrder, filters: CalendarFilterOptions): CalendarEvent[] {
  const events: CalendarEvent[] = []
  const supplierName = po.supplier?.partner_name || '공급업체'

  // 발주일
  if (filters.poEvents.order && po.order_date) {
    const colors = poEventColors.PO_ORDER
    events.push({
      id: `PO_${po.id}_ORDER`,
      type: 'PO_ORDER',
      category: 'PO',
      date: po.order_date,
      title: po.po_number,
      subtitle: supplierName,
      status: po.status,
      color: colors.color,
      bgColor: colors.bgColor,
      originalId: po.id,
      originalData: po,
    })
  }

  // 납기예정일
  if (filters.poEvents.deliveryExpected && po.expected_delivery_date) {
    const colors = poEventColors.PO_DELIVERY_EXPECTED
    events.push({
      id: `PO_${po.id}_DELIVERY_EXPECTED`,
      type: 'PO_DELIVERY_EXPECTED',
      category: 'PO',
      date: po.expected_delivery_date,
      title: po.po_number,
      subtitle: `납기예정 - ${supplierName}`,
      status: po.status,
      color: colors.color,
      bgColor: colors.bgColor,
      originalId: po.id,
      originalData: po,
    })
  }

  // 실제 입고일
  if (filters.poEvents.deliveryActual && po.actual_delivery_date) {
    const colors = poEventColors.PO_DELIVERY_ACTUAL
    events.push({
      id: `PO_${po.id}_DELIVERY_ACTUAL`,
      type: 'PO_DELIVERY_ACTUAL',
      category: 'PO',
      date: po.actual_delivery_date,
      title: po.po_number,
      subtitle: `입고완료 - ${supplierName}`,
      status: po.status,
      color: colors.color,
      bgColor: colors.bgColor,
      originalId: po.id,
      originalData: po,
    })
  }

  // 결제일
  if (filters.poEvents.payment && po.paid_date) {
    const colors = poEventColors.PO_PAYMENT
    events.push({
      id: `PO_${po.id}_PAYMENT`,
      type: 'PO_PAYMENT',
      category: 'PO',
      date: po.paid_date,
      title: po.po_number,
      subtitle: `결제 - ${supplierName}`,
      status: po.status,
      color: colors.color,
      bgColor: colors.bgColor,
      originalId: po.id,
      originalData: po,
    })
  }

  return events
}

// ==================== 작업지시서 이벤트 변환 ====================

function convertWOToEvents(wo: WorkOrder, filters: CalendarFilterOptions): CalendarEvent[] {
  const events: CalendarEvent[] = []
  const productName = wo.product_part?.part_name || '완제품'

  // 우선순위 필터 확인
  const priorityMatch =
    (wo.priority === 0 && filters.priorities.normal) ||
    (wo.priority === 1 && filters.priorities.high) ||
    (wo.priority === 2 && filters.priorities.urgent)

  if (!priorityMatch) {
    return events
  }

  // 예정일 이벤트들
  const scheduledEvents: { filter: boolean; date?: string; type: WOScheduledEventType }[] = [
    { filter: filters.woEvents.issueScheduled, date: wo.issue_scheduled_date, type: 'WO_ISSUE_SCHEDULED' },
    { filter: filters.woEvents.productionScheduled, date: wo.production_scheduled_date, type: 'WO_PRODUCTION_SCHEDULED' },
    { filter: filters.woEvents.inspectionScheduled, date: wo.inspection_scheduled_date, type: 'WO_INSPECTION_SCHEDULED' },
    { filter: filters.woEvents.packingScheduled, date: wo.packing_scheduled_date, type: 'WO_PACKING_SCHEDULED' },
    { filter: filters.woEvents.shippingScheduled, date: wo.shipping_scheduled_date, type: 'WO_SHIPPING_SCHEDULED' },
  ]

  for (const event of scheduledEvents) {
    if (event.filter && event.date) {
      const colors = woScheduledColors[event.type]
      events.push({
        id: `WO_${wo.id}_${event.type}`,
        type: event.type,
        category: 'WO',
        date: event.date,
        title: wo.wo_number,
        subtitle: `${eventTypeLabels[event.type]} - ${productName}`,
        status: wo.status,
        priority: wo.priority,
        color: colors.color,
        bgColor: colors.bgColor,
        borderColor: colors.borderColor,
        originalId: wo.id,
        originalData: wo,
      })
    }
  }

  // 완료일 이벤트들
  const completedEvents: { filter: boolean; date?: string; type: WOCompletedEventType }[] = [
    { filter: filters.woEvents.issueCompleted, date: wo.issue_completed_date, type: 'WO_ISSUE_COMPLETED' },
    { filter: filters.woEvents.productionStart, date: wo.production_start_date, type: 'WO_PRODUCTION_START' },
    { filter: filters.woEvents.productionEnd, date: wo.production_end_date, type: 'WO_PRODUCTION_END' },
    { filter: filters.woEvents.inspectionCompleted, date: wo.inspection_completed_date, type: 'WO_INSPECTION_COMPLETED' },
    { filter: filters.woEvents.packingCompleted, date: wo.packing_completed_date, type: 'WO_PACKING_COMPLETED' },
    { filter: filters.woEvents.shippingCompleted, date: wo.shipping_completed_date, type: 'WO_SHIPPING_COMPLETED' },
  ]

  for (const event of completedEvents) {
    if (event.filter && event.date) {
      const colors = woCompletedColors[event.type]
      events.push({
        id: `WO_${wo.id}_${event.type}`,
        type: event.type,
        category: 'WO',
        date: event.date,
        title: wo.wo_number,
        subtitle: `${eventTypeLabels[event.type]} - ${productName}`,
        status: wo.status,
        priority: wo.priority,
        color: colors.color,
        bgColor: colors.bgColor,
        originalId: wo.id,
        originalData: wo,
      })
    }
  }

  return events
}

// ==================== 결재(휴가/출장) 이벤트 변환 ====================

/**
 * 'YYYY-MM-DD' 문자열 기준으로 start~end 사이 모든 날짜를 반환 (타임존 이슈 회피)
 */
function expandDateRange(start: string, end: string): string[] {
  const dates: string[] = []
  if (!start) return dates
  const endStr = end || start
  // 시작이 종료보다 늦으면 시작일만
  if (start > endStr) return [start]

  const sp = start.split('-')
  const ep = endStr.split('-')
  const sy = Number(sp[0]), sm = Number(sp[1]), sd = Number(sp[2])
  const ey = Number(ep[0]), em = Number(ep[1]), ed = Number(ep[2])
  // 파싱 실패 시 시작일만
  if ([sy, sm, sd, ey, em, ed].some(n => Number.isNaN(n))) return [start]
  // UTC 기준으로 일 단위 증가 (DST/타임존 영향 없음)
  let cur = Date.UTC(sy, sm - 1, sd)
  const endTime = Date.UTC(ey, em - 1, ed)

  while (cur <= endTime) {
    const d = new Date(cur)
    const y = d.getUTCFullYear()
    const m = String(d.getUTCMonth() + 1).padStart(2, '0')
    const day = String(d.getUTCDate()).padStart(2, '0')
    dates.push(`${y}-${m}-${day}`)
    cur += 24 * 60 * 60 * 1000
  }

  return dates
}

function convertApprovalToEvents(ev: ApprovalCalendarItem, filters: CalendarFilterOptions): CalendarEvent[] {
  const events: CalendarEvent[] = []
  const isLeave = ev.form_code === 'LEAVE'

  // 필터 확인
  if (isLeave && !filters.apEvents.leave) return events
  if (!isLeave && !filters.apEvents.trip) return events

  const type: APEventType = isLeave ? 'AP_LEAVE' : 'AP_TRIP'
  const colors = apEventColors[type]
  const drafter = ev.drafter_name || ''
  const kindLabel = isLeave ? (ev.leave_type || '휴가') : '출장'
  const title = `${drafter} ${kindLabel}`.trim()

  for (const date of expandDateRange(ev.start_date, ev.end_date)) {
    events.push({
      id: `AP_${ev.id}_${date}`,
      type,
      category: 'AP',
      date,
      title,
      subtitle: ev.title,
      status: ev.status,
      color: colors.color,
      bgColor: colors.bgColor,
      originalId: ev.id,
    })
  }

  return events
}

// ==================== 등록 일정 이벤트 변환 ====================

const SC_TYPE_MAP: Record<ScheduleType, { type: SCEventType; filter: keyof CalendarFilterOptions['scEvents'] }> = {
  EVENT: { type: 'SC_EVENT', filter: 'event' },
  LEAVE: { type: 'SC_LEAVE', filter: 'leave' },
  FIELDWORK: { type: 'SC_FIELDWORK', filter: 'fieldwork' },
  TRIP: { type: 'SC_TRIP', filter: 'trip' },
}

function convertScheduleToEvents(
  sc: ScheduleItem,
  filters: CalendarFilterOptions,
  fromDate: string,
  toDate: string,
): CalendarEvent[] {
  const events: CalendarEvent[] = []
  const mapped = SC_TYPE_MAP[sc.schedule_type]
  if (!mapped || !filters.scEvents[mapped.filter]) return events

  const colors = scEventColors[mapped.type]
  // 휴가/외근/출장은 누구 일정인지 보이도록 대상자 이름을 앞에 붙인다
  const title = sc.target_name ? `${sc.target_name} ${sc.title}` : sc.title
  // 긴 일정은 화면에 보이는 구간만 펼친다
  const start = sc.start_date < fromDate ? fromDate : sc.start_date
  const end = sc.end_date > toDate ? toDate : sc.end_date

  for (const date of expandDateRange(start, end)) {
    events.push({
      id: `SC_${sc.id}_${date}`,
      type: mapped.type,
      category: 'SC',
      date,
      title,
      subtitle: sc.location || undefined,
      color: colors.color,
      bgColor: colors.bgColor,
      originalId: sc.id,
      originalData: sc,
    })
  }

  return events
}

// ==================== 캘린더 API ====================

// 공휴일 (date: YYYY-MM-DD)
export interface Holiday {
  date: string
  name: string
}

export const calendarApi = {
  /**
   * 캘린더 이벤트 조회
   * @param fromDate 시작일 (YYYY-MM-DD)
   * @param toDate 종료일 (YYYY-MM-DD)
   * @param filters 필터 옵션
   */
  async getEvents(
    fromDate: string,
    toDate: string,
    filters: CalendarFilterOptions = defaultFilterOptions
  ): Promise<CalendarEvent[]> {
    const events: CalendarEvent[] = []

    // 발주서 필터가 하나라도 켜져있으면 조회
    const needPO = Object.values(filters.poEvents).some(v => v)
    // 작업지시서 필터가 하나라도 켜져있으면 조회
    const needWO = Object.values(filters.woEvents).some(v => v)
    // 결재(휴가/출장) 필터가 하나라도 켜져있으면 조회
    const needAP = filters.apEvents.leave || filters.apEvents.trip
    // 등록 일정 필터가 하나라도 켜져있으면 조회
    const needSC = Object.values(filters.scEvents).some(v => v)

    const promises: Promise<void>[] = []

    // 발주서 조회
    if (needPO) {
      promises.push(
        purchaseOrderApi.getAll({
          from_date: fromDate,
          to_date: toDate,
          limit: 1000,
        }).then(async (response) => {
          // 상세 정보가 필요한 경우 개별 조회
          for (const po of response.items) {
            try {
              const detail = await purchaseOrderApi.getById(po.id)
              events.push(...convertPOToEvents(detail, filters))
            } catch (e) {
              // 개별 조회 실패 시 기본 정보로 이벤트 생성
              const basicPO: PurchaseOrder = {
                ...po,
                total_amount: po.total_amount,
                currency: 'KRW',
                tax_amount: 0,
                discount_amount: 0,
                is_paid: po.is_paid,
              }
              events.push(...convertPOToEvents(basicPO, filters))
            }
          }
        })
      )
    }

    // 작업지시서 조회
    if (needWO) {
      promises.push(
        workOrderApi.getAll({
          from_date: fromDate,
          to_date: toDate,
          limit: 1000,
        }).then(async (response) => {
          for (const wo of response.items) {
            try {
              const detail = await workOrderApi.getById(wo.id)
              events.push(...convertWOToEvents(detail, filters))
            } catch (e) {
              // 개별 조회 실패 시 기본 정보로 이벤트 생성
              const basicWO: WorkOrder = {
                ...wo,
                defective_quantity: 0,
              }
              events.push(...convertWOToEvents(basicWO, filters))
            }
          }
        })
      )
    }

    // 결재(휴가/출장) 조회
    if (needAP) {
      promises.push(
        apiClient.get('/approvals/calendar', {
          params: { date_from: fromDate, date_to: toDate },
        }).then((response) => {
          const items: ApprovalCalendarItem[] = response.data || []
          for (const item of items) {
            events.push(...convertApprovalToEvents(item, filters))
          }
        })
      )
    }

    // 등록 일정(경영관리 > 일정등록) 조회
    if (needSC) {
      promises.push(
        scheduleApi.calendar(fromDate, toDate).then((items) => {
          for (const item of items) {
            events.push(...convertScheduleToEvents(item, filters, fromDate, toDate))
          }
        })
      )
    }

    await Promise.all(promises)

    // 날짜순 정렬
    events.sort((a, b) => a.date.localeCompare(b.date))

    return events
  },

  /**
   * 공휴일 조회 (백엔드가 data.go.kr 특일 정보를 대신 조회·캐시)
   * 실패해도 캘린더는 떠야 하므로 빈 배열을 돌려준다.
   */
  async getHolidays(fromDate: string, toDate: string): Promise<Holiday[]> {
    try {
      const response = await apiClient.get('/holidays', {
        params: { date_from: fromDate, date_to: toDate },
      })
      return response.data || []
    } catch (e) {
      console.warn('Failed to load holidays:', e)
      return []
    }
  },

  /**
   * 특정 날짜의 이벤트 조회
   */
  getEventsForDate(events: CalendarEvent[], dateString: string): CalendarEvent[] {
    return events.filter(e => e.date === dateString)
  },

  /**
   * 이벤트를 날짜별로 그룹화
   */
  groupEventsByDate(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
    const grouped = new Map<string, CalendarEvent[]>()

    for (const event of events) {
      const existing = grouped.get(event.date) || []
      existing.push(event)
      grouped.set(event.date, existing)
    }

    return grouped
  },
}

export default calendarApi
