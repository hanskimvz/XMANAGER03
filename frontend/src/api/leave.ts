import apiClient from './client'

export interface LeaveYearSummary {
  fiscal_year: number
  carried_in: number
  granted: number
  used: number
  allowance_paid: number
  adjust: number
  remaining: number
}

export interface LeaveLedgerEntry {
  id: number
  fiscal_year: number
  entry_type: string
  amount: number
  event_date?: string | null
  source_type: string
  source_doc_id?: number | null
  memo?: string | null
  voided?: boolean
  created_at?: string | null
  kind_label?: string      // 휴가구분: 종일휴가/오전반차/오후반차/경조휴가 등(부여·조정은 공란)
  date_display?: string    // 사용기간(날짜 또는 기간)
  memo_label?: string      // 비고: 휴가부여 / 관리자 조정 · 사유 / 경조 사유(조모상) 등
  admin_only?: boolean     // (미사용) 하위호환
}

export interface LeaveOverviewRow {
  user_id: number
  username: string
  name: string
  department?: string | null
  position?: string | null
  hire_date?: string | null
  resign_date?: string | null
  current_year: number
  current_remaining: number
  has_hire_date: boolean
  is_safety_officer: boolean
}

export interface LeaveDetail {
  user_id: number
  name: string
  hire_date?: string | null
  resign_date?: string | null
  current_year: number
  current_remaining: number
  years: LeaveYearSummary[]
  ledger: LeaveLedgerEntry[]
}

export interface Settlement {
  asof: string
  hire_date?: string | null
  legal_entitlement: number
  fiscal_granted: number
  adjust: number
  used: number
  allowance_paid: number
  unsettled_days: number
  note: string
}

export const ENTRY_LABELS: Record<string, string> = {
  GRANT: '발생',
  USAGE: '사용',
  ALLOWANCE_PAID: '수당지급',
  ADJUST: '조정',
}

export const leaveApi = {
  me: async (): Promise<LeaveDetail> => (await apiClient.get('/leave/me')).data,
  overview: async (): Promise<LeaveOverviewRow[]> => (await apiClient.get('/leave/overview')).data,
  detail: async (userId: number): Promise<LeaveDetail> => (await apiClient.get(`/leave/${userId}`)).data,
  setEmployment: async (userId: number, hire_date: string | null, resign_date: string | null): Promise<LeaveDetail> =>
    (await apiClient.put(`/leave/${userId}/employment`, { hire_date, resign_date })).data,
  setSafetyOfficer: async (userId: number, is_safety_officer: boolean): Promise<LeaveDetail> =>
    (await apiClient.put(`/leave/${userId}/safety-officer`, { is_safety_officer })).data,
  adjust: async (userId: number, fiscal_year: number, amount: number, memo: string): Promise<LeaveDetail> =>
    (await apiClient.post(`/leave/${userId}/adjust`, { fiscal_year, amount, memo })).data,
  addUsage: async (userId: number, event_date: string, days: number, memo?: string): Promise<LeaveDetail> =>
    (await apiClient.post(`/leave/${userId}/usage`, { event_date, days, memo })).data,
  companyWide: async (event_date: string, days: number, memo: string, exclude_user_ids: number[]): Promise<{ applied: number; excluded: number; event_date: string; days: number }> =>
    (await apiClient.post('/leave/company-wide', { event_date, days, memo, exclude_user_ids })).data,
  payAllowance: async (userId: number, fiscal_year: number, days: number, memo?: string): Promise<LeaveDetail> =>
    (await apiClient.post(`/leave/${userId}/allowance`, { fiscal_year, days, memo })).data,
  deleteEntry: async (entryId: number): Promise<void> => {
    await apiClient.delete(`/leave/ledger/${entryId}`)
  },
  settlement: async (userId: number, asof?: string): Promise<Settlement> =>
    (await apiClient.get(`/leave/${userId}/settlement`, { params: asof ? { asof } : {} })).data,
  ensureAll: async (): Promise<{ users: number; grants_recomputed: number }> =>
    (await apiClient.post('/leave/ensure-all')).data,
}
