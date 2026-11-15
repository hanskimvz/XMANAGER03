import apiClient from './client'

export type ScheduleType = 'EVENT' | 'LEAVE' | 'FIELDWORK' | 'TRIP'

// 유형 코드/라벨/색 — 백엔드 models/schedule.py 의 SCHEDULE_TYPES 와 동일하게 유지
export const SCHEDULE_TYPES: { value: ScheduleType; label: string; dot: string; badge: string }[] = [
  { value: 'EVENT', label: '행사', dot: 'bg-amber-500', badge: 'bg-amber-100 text-amber-700' },
  { value: 'LEAVE', label: '휴가', dot: 'bg-teal-500', badge: 'bg-teal-100 text-teal-700' },
  { value: 'FIELDWORK', label: '외근', dot: 'bg-sky-500', badge: 'bg-sky-100 text-sky-700' },
  { value: 'TRIP', label: '출장', dot: 'bg-purple-500', badge: 'bg-purple-100 text-purple-700' },
]

export function scheduleTypeLabel(code: string): string {
  return SCHEDULE_TYPES.find((t) => t.value === code)?.label || code
}

export interface ScheduleItem {
  id: number
  schedule_type: ScheduleType
  title: string
  target_user_id?: number | null
  target_name?: string | null // 행사(대상자 없음)면 null
  start_date: string // YYYY-MM-DD
  end_date: string // YYYY-MM-DD
  location?: string | null
  memo?: string | null
  source: string // MANUAL = 직접 등록
  created_by_name?: string | null
  can_edit: boolean
  created_at?: string | null
}

export interface ScheduleListResponse {
  items: ScheduleItem[]
  total: number
  page: number
  size: number
}

export interface SchedulePayload {
  schedule_type: ScheduleType
  title: string
  target_user_id?: number | null
  start_date: string
  end_date?: string | null
  location?: string | null
  memo?: string | null
}

export const scheduleApi = {
  list: async (params: {
    page?: number
    size?: number
    schedule_type?: ScheduleType
    month?: string // YYYY-MM
    q?: string
  } = {}): Promise<ScheduleListResponse> => (await apiClient.get('/schedules', { params })).data,

  // 캘린더 표기용 — 조회 구간과 겹치는 등록 일정
  calendar: async (dateFrom: string, dateTo: string): Promise<ScheduleItem[]> =>
    (await apiClient.get('/schedules/calendar', { params: { date_from: dateFrom, date_to: dateTo } })).data || [],

  create: async (payload: SchedulePayload): Promise<ScheduleItem> =>
    (await apiClient.post('/schedules', payload)).data,

  update: async (id: number, payload: SchedulePayload): Promise<ScheduleItem> =>
    (await apiClient.put(`/schedules/${id}`, payload)).data,

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/schedules/${id}`)
  },
}
