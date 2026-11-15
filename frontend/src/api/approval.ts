/**
 * 전자결재 API 서비스 (v0.33.0)
 *
 * 백엔드: /api/v1/approvals (설계노트 6장)
 * - 응답 스키마는 backend/app/schemas/approval.py 와 1:1 일치
 */

import apiClient from './client'

// ==================== 인터페이스 ====================

export type ApprovalStatus = 'DRAFT' | 'IN_PROGRESS' | 'APPROVED' | 'REJECTED' | 'CANCELED'
export type LineStatus = 'WAITING' | 'PENDING' | 'APPROVED' | 'REJECTED'
export type ActionType = 'SUBMIT' | 'APPROVE' | 'REJECT' | 'CANCEL' | 'RESUBMIT' | 'EXECUTE'
export type BoxType = 'drafted' | 'pending' | 'done' | 'reference' | 'execution'

/** 양식 필드 타입 */
export type FormFieldType = 'text' | 'textarea' | 'number' | 'date' | 'select'

/** 프로젝트 */
export interface ApprovalProject {
  id: number
  code: string
  name: string
  is_active: boolean
  sort_order: number
}

/** 양식 필드 정의 */
export interface FormField {
  key: string
  label: string
  type: FormFieldType
  required?: boolean
  placeholder?: string | null
  help?: string | null
  options?: string[] | null
}

/** 결재 양식 */
export interface ApprovalForm {
  id: number
  code: string
  name: string
  fields_schema: FormField[]
  sort_order: number
  /** 단계: NONE(단독) | PRE(사전) | POST(사후) */
  phase?: string
  /** POST 양식이 연결하는 짝 PRE 양식 code */
  linked_form_code?: string | null
}

/** 참조자 (상세 응답) */
export interface ApprovalReference {
  user_id: number
  name: string
  position?: string | null
}

/** 첨부파일 */
export interface ApprovalAttachment {
  id: number
  original_name: string
  file_size: number
  content_type?: string | null
  uploaded_at: string
}

/** 결재 의견(댓글) */
export interface ApprovalComment {
  id: number
  user_id: number
  user_name?: string | null
  content: string
  created_at: string
  can_delete: boolean
}

/** 연차 잔여 */
export interface LeaveBalance {
  year: number
  entitlement: number
  used: number
  remaining: number
}

/** 결재선 (상세 응답) */
export interface ApprovalLine {
  id: number
  step_order: number
  approver_id: number
  approver_name?: string | null
  approver_position?: string | null
  status: LineStatus
  acted_at?: string | null
  comment?: string | null
  seal_svg?: string | null
}

/** 결재선 입력 (create/update) */
export interface ApprovalLineInput {
  step_order: number
  approver_id: number
}

/** 결재 행위 이력 */
export interface ApprovalAction {
  id: number
  actor_id: number
  actor_name?: string | null
  action: ActionType
  comment?: string | null
  acted_at?: string | null
  ip_address?: string | null
}

/** 결재 문서 상세 */
export interface ApprovalDocument {
  id: number
  doc_number: string
  form_id?: number | null
  form_code?: string | null
  form_name?: string | null
  form_data?: Record<string, unknown> | null
  project_id?: number | null
  project_name?: string | null
  // 구매 구분 + 시행자/시행전후 (v0.64.0)
  purchase_category?: string | null   // 일반/과제/개발
  executor_id?: number | null
  executor_name?: string | null
  execution_status?: string | null    // PENDING(시행전)/DONE(시행후)
  executed_at?: string | null
  can_execute?: boolean
  title: string
  content?: string | null
  status: ApprovalStatus
  current_step: number
  drafter_id: number
  drafter_name?: string | null
  drafter_position?: string | null      // 편집화면에서 문서의 실제 기안자 표시용
  drafter_department?: string | null    // 편집화면에서 문서의 실제 기안자 표시용
  drafted_at?: string | null
  completed_at?: string | null
  is_corrected: boolean
  created_at: string
  updated_at?: string | null
  lines: ApprovalLine[]
  actions: ApprovalAction[]
  references: ApprovalReference[]
  attachments: ApprovalAttachment[]
  verify_code?: string | null
  can_act: boolean
  can_reject?: boolean  // 이미 승인한 결재자도 진행 중이면 반려 가능(v0.90.x)
  related_document_id?: number | null
  related_doc_number?: string | null
  related_title?: string | null
  related_documents?: { id: number; doc_number: string; title: string; status: string; form_name?: string | null }[]
  // 단계형 문서 연계 (사전→사후)
  form_phase?: string | null
  followup_form_code?: string | null
  followup_form_name?: string | null
  can_create_followup?: boolean
  /** 작성 가능한 후속 양식 목록 (다중) */
  followups?: { form_code: string; form_name: string }[]
  /** 이 문서를 선행으로 가리키는 후속 문서들 */
  linked_documents?: {
    id: number
    doc_number: string
    title: string
    status: string
    form_name?: string | null
  }[]
}

/** 목록 아이템 */
export interface ApprovalListItem {
  id: number
  doc_number: string
  title: string
  drafter_name?: string | null
  current_approver_name?: string | null
  status: ApprovalStatus
  current_step: number
  drafted_at?: string | null
  created_at: string
  form_code?: string | null
  form_name?: string | null
  project_name?: string | null
  purchase_category?: string | null
  executor_name?: string | null
  execution_status?: string | null
  is_my_turn?: boolean   // 결재대기함: 현재 내 차례(조치 필요) 여부
}

export interface ApprovalListResponse {
  items: ApprovalListItem[]
  total: number
  skip: number
  limit: number
}

/** 관리자 정정 이력 */
export interface ApprovalCorrection {
  id: number
  document_id: number
  target_table: string
  target_id: number
  field_name: string
  old_value?: string | null
  new_value?: string | null
  reason: string
  corrected_by?: string | null
  corrected_at: string
}

/** 관리자 정정 요청 본문 */
export interface ApprovalCorrectPayload {
  target_table: string
  target_id: number
  field_name: string
  new_value: string
  reason: string
}

/** 관리자 결재 문서 검색 파라미터 */
export interface AdminApprovalSearchParams {
  keyword?: string
  status?: ApprovalStatus | ''
  drafter_id?: number
  date_from?: string
  date_to?: string
  skip?: number
  limit?: number
}

/** 결재자 선택 후보 */
export interface ApproverCandidate {
  id: number
  name: string
  position?: string | null
  department?: string | null
}

/** 연결 가능한 출장신청서 (출장 정산서 작성 시) */
export interface LinkableTrip {
  id: number
  doc_number: string
  title: string
  expense: number | null
  start_date?: string | null
  end_date?: string | null
}

/** 연결 가능한 선행문서 (POST 양식 작성 시) — 일반화 */
export interface LinkablePredecessor {
  id: number
  doc_number: string
  title: string
  form_data?: Record<string, unknown> | null
  expense: number | null
  start_date?: string | null
  end_date?: string | null
}

export interface ApprovalDocumentCreate {
  title: string
  content?: string
  lines: ApprovalLineInput[]
  form_id?: number | null
  form_data?: Record<string, unknown> | null
  reference_ids?: number[]
  related_document_id?: number | null
  related_document_ids?: number[] | null
  project_id?: number | null
  purchase_category?: string | null
  executor_id?: number | null
}

export interface ApprovalDocumentUpdate {
  title?: string
  content?: string
  lines?: ApprovalLineInput[]
  form_id?: number | null
  form_data?: Record<string, unknown> | null
  reference_ids?: number[]
  related_document_id?: number | null
  related_document_ids?: number[] | null
  project_id?: number | null
  purchase_category?: string | null
  executor_id?: number | null
}

// ==================== API ====================

export const approvalApi = {
  // 결재함 조회 (기안함/결재대기/완료함)
  getBox: (params: {
    box: BoxType
    keyword?: string
    form_code?: string
    project_id?: number
    category?: string
    execution_status?: string
    skip?: number
    limit?: number
  }) => apiClient.get<ApprovalListResponse>('/approvals', { params }),
  // 시행 완료 (시행자)
  execute: (id: number) => apiClient.post<ApprovalDocument>(`/approvals/${id}/execute`),

  // 상세 조회
  getById: (id: number) => apiClient.get<ApprovalDocument>(`/approvals/${id}`),

  // 임시저장 생성 (DRAFT)
  create: (data: ApprovalDocumentCreate) =>
    apiClient.post<ApprovalDocument>('/approvals', data),

  // DRAFT 수정
  update: (id: number, data: ApprovalDocumentUpdate) =>
    apiClient.put<ApprovalDocument>(`/approvals/${id}`, data),

  // 품목 엑셀 파싱(구매기안서/지출결의서 품목표): 파일 → [{name,qty,unit_price,vendor,note}]
  parseItems: async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await apiClient.post('/approvals/items-parse', fd)
    return res.data.items as Array<{ name: string; qty: number | null; unit_price: number | null; note: string }>
  },

  // 상태 전이
  submit: (id: number) => apiClient.post<ApprovalDocument>(`/approvals/${id}/submit`),
  approve: (id: number, data?: { comment?: string; exec_date?: string }) =>
    apiClient.post<ApprovalDocument>(`/approvals/${id}/approve`, data ?? {}),
  reject: (id: number, data: { comment: string }) =>
    apiClient.post<ApprovalDocument>(`/approvals/${id}/reject`, data),
  cancel: (id: number) => apiClient.post<ApprovalDocument>(`/approvals/${id}/cancel`),
  remove: (id: number) => apiClient.delete(`/approvals/${id}`),  // 소프트 삭제(관리자)
  resubmit: (id: number, data?: ApprovalDocumentUpdate) =>
    apiClient.post<ApprovalDocument>(`/approvals/${id}/resubmit`, data ?? {}),

  // 결재 대기 건수
  pendingCount: () => apiClient.get<{ count: number }>('/approvals/pending-count'),

  // 결재자 선택 후보 (비관리자 사용 가능)
  getApprovers: (keyword?: string) =>
    apiClient.get<ApproverCandidate[]>('/approvals/approvers', {
      params: keyword ? { keyword } : undefined,
    }),

  // 도장 SVG 이미지 URL (img :src 로 사용)
  sealSvgUrl: (userId: number) => `${apiClient.defaults.baseURL}/users/seal/${userId}.svg`,

  // ─────────── 양식 ───────────
  getForms: () => apiClient.get<ApprovalForm[]>('/approvals/forms'),

  // ─────────── 프로젝트 (공용) ───────────
  // 활성 프로젝트 목록
  getProjects: () => apiClient.get<ApprovalProject[]>('/projects'),
  // 로그인 사용자 즉석추가 (생성된 프로젝트 반환)
  createProject: (data: { name: string; code?: string; sort_order?: number }) =>
    apiClient.post<ApprovalProject>('/projects', data),

  // ─────────── 연결 가능 출장신청서 (정산서 작성) ───────────
  getLinkableTrips: () => apiClient.get<LinkableTrip[]>('/approvals/linkable-trips'),

  // ─────────── 연결 가능 선행문서 (POST 양식 작성, 일반화) ───────────
  getLinkablePredecessors: (formCode: string) =>
    apiClient.get<LinkablePredecessor[]>('/approvals/linkable-predecessors', {
      params: { form_code: formCode },
    }),

  // ─────────── 연차 잔여 ───────────
  getLeaveBalance: (params?: { user_id?: number; year?: number }) =>
    apiClient.get<LeaveBalance>('/approvals/leave-balance', {
      params: params && (params.user_id || params.year) ? params : undefined,
    }),

  // ─────────── 첨부파일 ───────────
  uploadAttachment: (id: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<ApprovalAttachment>(`/approvals/${id}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listAttachments: (id: number) =>
    apiClient.get<ApprovalAttachment[]>(`/approvals/${id}/attachments`),
  attachmentDownloadUrl: (id: number, aid: number) =>
    `${apiClient.defaults.baseURL}/approvals/${id}/attachments/${aid}/download`,
  downloadAttachment: (id: number, aid: number) =>
    apiClient.get(`/approvals/${id}/attachments/${aid}/download`, { responseType: 'blob' }),
  deleteAttachment: (id: number, aid: number) =>
    apiClient.delete(`/approvals/${id}/attachments/${aid}`),

  // ─────────── 결재 의견(댓글) ───────────
  listComments: (id: number) =>
    apiClient.get<ApprovalComment[]>(`/approvals/${id}/comments`),
  addComment: (id: number, content: string) =>
    apiClient.post<ApprovalComment>(`/approvals/${id}/comments`, { content }),
  deleteComment: (id: number, commentId: number) =>
    apiClient.delete(`/approvals/${id}/comments/${commentId}`),

  // ─────────── 출력 ───────────
  getPrintHtml: (
    id: number,
    opts?: { history?: boolean; references?: boolean; printDate?: boolean; attachments?: boolean; docNumber?: boolean },
  ) =>
    apiClient.get<string>(`/approvals/${id}/print`, {
      responseType: 'text',
      params: {
        include_history: opts?.history ?? true,
        include_references: opts?.references ?? true,
        include_print_date: opts?.printDate ?? true,
        include_attachments: opts?.attachments ?? true,
        include_doc_number: opts?.docNumber ?? true,
      },
    }),
  printHtmlUrl: (id: number) => `${apiClient.defaults.baseURL}/approvals/${id}/print`,
  downloadPdf: (id: number) =>
    apiClient.get(`/approvals/${id}/pdf`, { responseType: 'blob' }),

  // ─────────── 관리자 (stub) ───────────
  getDefaultApprover: (userId: number) =>
    apiClient.get<{ approver_id: number | null; approver_name: string | null }>(
      `/admin/users/${userId}/default-approver`,
    ),
  setDefaultApprover: (userId: number, data: { approver_id: number | null }) =>
    apiClient.put<{ approver_id: number | null; approver_name: string | null }>(
      `/admin/users/${userId}/default-approver`,
      data,
    ),
  getActions: (id: number) => apiClient.get<ApprovalAction[]>(`/admin/approvals/${id}/actions`),

  // ─────────── 관리자 : 프로젝트 관리 (공용 /projects 계열) ───────────
  adminListProjects: () => apiClient.get<ApprovalProject[]>('/projects/all'),
  adminCreateProject: (data: { name: string; code?: string; sort_order?: number }) =>
    apiClient.post<ApprovalProject>('/projects', data),
  adminUpdateProject: (
    id: number,
    data: { name?: string; is_active?: boolean; sort_order?: number },
  ) => apiClient.put<ApprovalProject>(`/projects/${id}`, data),

  // ─────────── 관리자 : 전자결재 검색 / 정정 ───────────
  // 모든 결재 문서 검색 (ADMIN 전용)
  adminSearch: (params: AdminApprovalSearchParams) => {
    const q: Record<string, unknown> = {}
    if (params.keyword) q.keyword = params.keyword
    if (params.status) q.status = params.status
    if (params.drafter_id != null) q.drafter_id = params.drafter_id
    if (params.date_from) q.date_from = params.date_from
    if (params.date_to) q.date_to = params.date_to
    if (params.skip != null) q.skip = params.skip
    if (params.limit != null) q.limit = params.limit
    return apiClient.get<ApprovalListResponse>('/admin/approvals', { params: q })
  },

  // 정정 1건 저장 (ADMIN 전용)
  adminCorrect: (id: number, payload: ApprovalCorrectPayload) =>
    apiClient.put<ApprovalCorrection>(`/admin/approvals/${id}/correct`, payload),

  // 정정 이력 조회 (ADMIN 전용)
  getCorrections: (id: number) =>
    apiClient.get<ApprovalCorrection[]>(`/admin/approvals/${id}/corrections`),
  correctAction: (
    id: number,
    actionId: number,
    payload: { target_table: string; target_id: number; field_name: string; new_value: string; reason: string },
  ) => apiClient.put(`/admin/approvals/${id}/actions/${actionId}`, payload),

  // 관리자: 시행일자/결제일 사후 수정 (변경할 필드만 전송, 이력 미기록)
  adminSetDates: (id: number, payload: { executed_at?: string | null; exec_date?: string | null }) =>
    apiClient.put<ApprovalDocument>(`/admin/approvals/${id}/dates`, payload),

  // 관리자: 결재 문서 전체 정정 (작성 폼 payload + reason). 상태·결재선 보존, 정정 이력 기록
  adminFullEdit: (id: number, payload: any) =>
    apiClient.put<ApprovalDocument>(`/admin/approvals/${id}/full-edit`, payload),
}

// ==================== 표시 헬퍼 ====================

export const APPROVAL_STATUS_LABELS: Record<ApprovalStatus, string> = {
  DRAFT: '임시저장',
  IN_PROGRESS: '결재중',
  APPROVED: '승인완료',
  REJECTED: '반려',
  CANCELED: '회수',
}

/** 상태 배지 색 (Tailwind 클래스) */
export const APPROVAL_STATUS_BADGE: Record<ApprovalStatus, string> = {
  DRAFT: 'bg-gray-100 text-gray-700',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  APPROVED: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
  CANCELED: 'bg-yellow-100 text-yellow-800',
}

export const LINE_STATUS_LABELS: Record<LineStatus, string> = {
  WAITING: '대기',
  PENDING: '결재요청',
  APPROVED: '승인',
  REJECTED: '반려',
}

export const ACTION_LABELS: Record<ActionType, string> = {
  SUBMIT: '상신',
  APPROVE: '승인',
  REJECT: '반려',
  CANCEL: '회수',
  RESUBMIT: '재상신',
  EXECUTE: '시행',
}
