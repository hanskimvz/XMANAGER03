/**
 * 영업 대응 현황 API
 */

import apiClient from './client'

export interface SalesActivityLog {
  id: number
  activity_id: number
  log_type: string  // COMMENT / NEXT_STEP / PENDING_REASON / STATUS / INQUIRY_TYPE / ASSIGNEE
  content: string
  logged_by?: string
  attachment_files?: Array<{ filename: string; filepath?: string; mimetype?: string; size?: number }>
  edited_by?: string | null
  edited_at?: string | null
  created_at: string
}

export const LOG_TYPE_LABELS: Record<string, string> = {
  // 사용자 직접 입력 (5가지)
  COMMENT: '코멘트',
  CONTACT: '고객 컨택',
  CURRENT_STATUS: '진행 상황',
  NEXT_STEP: '다음 단계',
  ISSUE: '이슈/지연',
  // 자동 변경 감지
  STEP_UPDATE: '단계 업데이트',
  STATUS: '상태 변경',
  INQUIRY_TYPE: '문의 유형',
  PENDING_REASON: '지연 사유',
  ASSIGNEE: '담당자 변경',
  DOCUMENT: '문서 생성',
  AUTO_HOLD: '자동 보류',
}

export const LOG_TYPE_ICONS: Record<string, string> = {
  COMMENT: '💬',
  CONTACT: '📞',
  CURRENT_STATUS: '🎯',
  NEXT_STEP: '📝',
  ISSUE: '⚠',
  STEP_UPDATE: '📋',
  STATUS: '📋',
  INQUIRY_TYPE: '🏷',
  PENDING_REASON: '⚠',
  ASSIGNEE: '👤',
  DOCUMENT: '📄',
  AUTO_HOLD: '💤',
}

export const LOG_TYPE_COLORS: Record<string, string> = {
  COMMENT: 'bg-gray-100 text-gray-700 border-gray-300',
  CONTACT: 'bg-cyan-50 text-cyan-700 border-cyan-300',
  CURRENT_STATUS: 'bg-emerald-50 text-emerald-700 border-emerald-300',
  NEXT_STEP: 'bg-blue-50 text-blue-700 border-blue-300',
  ISSUE: 'bg-orange-50 text-orange-700 border-orange-300',
  STEP_UPDATE: 'bg-teal-50 text-teal-700 border-teal-300',
  STATUS: 'bg-purple-50 text-purple-700 border-purple-300',
  INQUIRY_TYPE: 'bg-indigo-50 text-indigo-700 border-indigo-300',
  PENDING_REASON: 'bg-orange-50 text-orange-700 border-orange-300',
  ASSIGNEE: 'bg-green-50 text-green-700 border-green-300',
  DOCUMENT: 'bg-sky-50 text-sky-700 border-sky-300',
  AUTO_HOLD: 'bg-gray-100 text-gray-600 border-gray-300',
}

// 사용자 직접 입력 가능한 유형 (드롭다운 옵션)
export const USER_LOG_TYPES = [
  { value: 'COMMENT', label: '💬 코멘트', placeholder: '자유롭게 메모를 남기세요...' },
  { value: 'CONTACT', label: '📞 고객 컨택', placeholder: '통화, 메일, 미팅 내용을 기록하세요...' },
  { value: 'CURRENT_STATUS', label: '🎯 진행 상황', placeholder: '현재 어디까지 진행되었는지 입력하세요...' },
  { value: 'ISSUE', label: '⚠ 이슈/지연', placeholder: '막힌 이유나 이슈를 입력하세요...' },
] as const

export interface SalesActivity {
  id: number
  customer_id?: number
  customer_name?: string
  country?: string
  title: string
  assigned_to?: string
  status: string
  inquiry_type?: string
  is_urgent?: boolean
  is_important?: boolean
  current_step?: string
  next_step?: string
  pending_reason?: string
  nextcloud_folder?: string | null
  expected_amount?: number
  expected_currency: string
  created_at: string
  updated_at?: string
  customer?: { id: number; partner_name?: string; partner_name_en?: string }
  logs?: SalesActivityLog[]
  log_count?: number
  last_log_date?: string
  // 진행 단계(리스트 주입)
  stage_type?: string   // QUOTATION/PI/CI/PRODUCTION
  stage_label?: string
  stage_doc_id?: number
}

export interface SalesActivityCreate {
  customer_id?: number
  customer_name?: string
  country?: string
  title: string
  assigned_to?: string
  status?: string
  inquiry_type?: string
  is_urgent?: boolean
  is_important?: boolean
  current_step?: string
  next_step?: string
  pending_reason?: string
  expected_amount?: number
  expected_currency?: string
}

export interface SalesActivityUpdate extends Partial<SalesActivityCreate> {}

export interface SalesActivityListResponse {
  items: SalesActivity[]
  total: number
  skip: number
  limit: number
}

export const activityStatusLabels: Record<string, string> = {
  IN_PROGRESS: '진행중',
  WAITING: '대기',
  COMPLETED: '완료',
  ON_HOLD: '보류',
  DROPPED: '무산',
}

export const activityStatusStyles: Record<string, string> = {
  IN_PROGRESS: 'bg-blue-100 text-blue-800',
  WAITING: 'bg-yellow-100 text-yellow-800',
  COMPLETED: 'bg-green-100 text-green-800',
  ON_HOLD: 'bg-gray-100 text-gray-800',
  DROPPED: 'bg-rose-100 text-rose-700',
}

export const inquiryTypeLabels: Record<string, string> = {
  TECHNICAL: '기술 문의',
  QUOTATION: '견적 문의',
  GENERAL: '일반 문의',
  SAMPLE: '샘플 요청',
  CLAIM: '클레임',
  OTHER: '기타',
}

export const inquiryTypeStyles: Record<string, string> = {
  TECHNICAL: 'bg-purple-100 text-purple-800',
  QUOTATION: 'bg-blue-100 text-blue-800',
  GENERAL: 'bg-gray-100 text-gray-700',
  SAMPLE: 'bg-teal-100 text-teal-800',
  CLAIM: 'bg-red-100 text-red-800',
  OTHER: 'bg-slate-100 text-slate-700',
}

export const salesActivityApi = {
  getList: (params?: {
    status?: string[]        // 다중 상태(합집합)
    assigned_to?: string
    customer_id?: number
    country?: string
    inquiry_type?: string
    keyword?: string
    urgent?: boolean
    important?: boolean
    skip?: number
    limit?: number
  }) => apiClient.get<SalesActivityListResponse>('/sales-activities', {
    params,
    // status 배열을 ?status=a&status=b (대괄호 없이) 로 직렬화 → FastAPI List[str] 파싱
    paramsSerializer: { indexes: null },
  }),

  getById: (id: number) => apiClient.get<SalesActivity>(`/sales-activities/${id}`),

  create: (data: SalesActivityCreate) => apiClient.post<SalesActivity>('/sales-activities', data),

  update: (id: number, data: SalesActivityUpdate) => apiClient.put<SalesActivity>(`/sales-activities/${id}`, data),

  delete: (id: number) => apiClient.delete(`/sales-activities/${id}`),

  // 코멘트
  getLogs: (id: number) => apiClient.get<SalesActivityLog[]>(`/sales-activities/${id}/logs`),

  addLog: (id: number, data: { content: string; log_type?: string; logged_by?: string }) =>
    apiClient.post<SalesActivityLog>(`/sales-activities/${id}/logs`, data),

  // 코멘트(로그) 수정 — 수정자/시각 기록 (v0.80.0)
  updateLog: (activityId: number, logId: number, data: { content: string; edited_by?: string }) =>
    apiClient.put<SalesActivityLog>(`/sales-activities/${activityId}/logs/${logId}`, data),

  // 코멘트 첨부(스크린샷/사진) — v0.78.0
  uploadLogAttachment: (activityId: number, logId: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return apiClient.post<{ file: any; total_files: number }>(
      `/sales-activities/${activityId}/logs/${logId}/attachments`, fd,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },
  deleteLogAttachment: (activityId: number, logId: number, fileIndex: number) =>
    apiClient.delete(`/sales-activities/${activityId}/logs/${logId}/attachments/${fileIndex}`),
  // 인증 헤더 실은 blob (native img src는 401 → createObjectURL로 표시)
  fetchLogAttachmentBlob: async (activityId: number, logId: number, fileIndex: number): Promise<Blob> => {
    const res = await apiClient.get(
      `/sales-activities/${activityId}/logs/${logId}/attachments/${fileIndex}/preview`,
      { responseType: 'blob' },
    )
    return res.data as Blob
  },

  // 담당자 목록
  getAssignees: () => apiClient.get<string[]>('/sales-activities/assignees'),

  // Nextcloud 폴더 생성 (v0.60.0)
  createNextcloudFolder: (id: number, folder_name: string) =>
    apiClient.post<{ folder: string; domestic: boolean }>(`/sales-activities/${id}/nextcloud-folder`, { folder_name }),

  // 연결된 영업 문서 목록 (v0.31.0)
  getDocuments: (id: number) =>
    apiClient.get<{
      activity_id: number
      documents: ActivityRelatedDocument[]
    }>(`/sales-activities/${id}/documents`),
}

export interface ActivityRelatedDocument {
  id: number
  document_type: string
  document_number: string
  document_date?: string
  status: string
  total_amount: number
  currency: string
  payment_status?: string
}
