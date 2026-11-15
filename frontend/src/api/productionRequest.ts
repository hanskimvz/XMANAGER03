/**
 * 생산 요청서 관리 API 서비스
 *
 * v0.20.0: 생산 요청서 기능 추가
 * - 영업팀이 생산팀에 생산을 요청하는 문서
 * - 작업지시서와 1:N 관계
 *
 * v0.22.0: 다중 제품 지원
 * - ProductionRequestItem 추가
 */

import apiClient from './client'

// 생산 요청서 상태
export type ProductionRequestStatus = 'REQUESTED' | 'HOLD' | 'REJECTED' | 'APPROVED' | 'IN_PROGRESS' | 'COMPLETED' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED'

// 부품 간략 정보
export interface PartInfo {
  id: number
  part_number?: string
  part_number_display?: string
  part_name?: string
  part_name_en?: string
}

// 고객사 간략 정보
export interface CustomerInfo {
  id: number
  partner_name?: string
  partner_code?: string
}

// 작업지시서 간략 정보
export interface WorkOrderInfo {
  id: number
  wo_number: string
  status: string
  created_at?: string
}

// 생산 요청서 제품 항목 (v0.22.0)
export interface ProductionRequestItem {
  id: number
  production_request_id: number
  product_part_id?: number | null   // 커스텀/외주 항목이면 null
  custom_product_code?: string | null
  custom_product_name?: string | null
  requested_quantity: number
  uom?: string
  line_remarks?: string
  customer_requirements?: string
  sort_order: number
  product_part?: PartInfo
  work_order_id?: number
  attachment_files?: Array<{ filename: string; filepath?: string; mimetype?: string; size?: number }>
}

// 생산 요청서 제품 항목 생성 DTO (v0.22.0)
export interface ProductionRequestItemCreate {
  id?: number  // 수정 시 기존 항목 식별 → in-place 수정(PI 링크/고객요구사항 보존)
  product_part_id?: number | null   // BOM 미등록(외주) 항목이면 null
  custom_product_code?: string | null
  custom_product_name?: string | null
  requested_quantity: number
  uom?: string
  line_remarks?: string
  customer_requirements?: string
  sort_order?: number
}

// 생산 요청서 인터페이스 (v0.22.0 다중 제품 지원)
export interface ProductionRequest {
  id: number
  request_number: string
  customer_id?: number
  customer_order_no?: string
  // deprecated - 호환성용 (첫번째 제품)
  product_part_id?: number
  requested_quantity?: number
  due_date?: string
  status: ProductionRequestStatus
  is_draft?: boolean   // 초안(미전송) 여부
  priority: number
  pi_number?: string
  payment_status?: string
  country?: string
  production_period?: string
  shipping_mark?: string
  consignee?: string
  destination?: string
  prepared_by_name?: string
  remarks?: string
  requested_by?: number
  requested_at?: string
  approved_by?: number
  approved_at?: string
  rejection_reason?: string
  created_at?: string
  updated_at?: string
  customer?: CustomerInfo
  product_part?: PartInfo  // deprecated - 첫번째 제품
  work_orders?: WorkOrderInfo[]
  // v0.22.0: 다중 제품
  items?: ProductionRequestItem[]
  item_count?: number
  // v0.22.0: 첨부파일
  attachment_files?: Array<{ filename: string; filepath: string; mimetype: string; size?: number }>
  // v0.69.0: 생산 시작 단계 자료
  manager_memo?: string
  process_checks?: ProcessCheckRow[]
  // v0.77.0: 출고 포장 명세
  packing_list?: PackingBox[] | null
  shipped_at?: string | null
  delivered_at?: string | null
  // v0.90.0: 분할선적 박스 분할계획(영업 작성 → 생산 포장 → 박스별 CI)
  box_plan?: BoxPlanBox[] | null
  has_box_plan?: boolean  // 목록 배지용
}

// 생산요청 캘린더 아이템(경량)
export interface ProductionCalendarItem {
  id: number
  request_number: string
  customer_name?: string | null
  due_date?: string | null       // YYYY-MM-DD
  requested_at?: string | null   // ISO datetime
  status: ProductionRequestStatus
  priority?: number
}

// 분할선적 박스 분할계획 (v0.90.0)
export interface BoxPlanLine {
  pr_item_id?: number | null
  product_code?: string | null
  quantity: number
}
export interface BoxPlanBox {
  box_no: number
  items: BoxPlanLine[]
  remarks?: string | null
  // 발행 추적(잔여박스) — 박스별 CI 발행 시 기록
  ci_document_id?: number | null
  ci_number?: string | null
}

// 출고 packing list 박스 라인 (v0.77.0)
export interface PackingBox {
  box_type?: string | null       // 박스 종류/식별
  quantity?: number | null       // 동일 박스 개수
  gross_weight?: number | null   // 총중량 kg (박스당)
  net_weight?: number | null     // 순중량 kg (박스당)
  length?: number | null         // cm
  width?: number | null          // cm
  height?: number | null         // cm
  remarks?: string | null        // 내용물/비고
}

// 공정 확인표 한 행
export interface ProcessCheckRow {
  seq: number
  content: string
  date?: string
  checker?: string
  note?: string
  action?: string
}

// 생산 요청서 목록 아이템 (v0.22.0 다중 제품 지원)
export interface ProductionRequestListItem {
  id: number
  request_number: string
  customer_id?: number
  // deprecated - 호환성용 (첫번째 제품)
  product_part_id?: number
  requested_quantity?: number
  due_date?: string
  status: ProductionRequestStatus
  is_draft?: boolean   // 초안(미전송) 여부
  priority: number
  pi_number?: string
  payment_status?: string
  prepared_by_name?: string  // 영업 담당자
  requested_at?: string
  created_at?: string
  // 진행 체크박스
  insert_shipped?: boolean
  insert_not_applicable?: boolean   // 인서트 해당없음(N/A)
  production_shipped?: boolean
  needs_review?: boolean
  insert_shipped_at?: string | null
  production_shipped_at?: string | null
  review_note?: string | null   // 검토 필요 사유
  shipped_at?: string | null     // 생산 출고 시각
  delivered_at?: string | null   // 발송 완료 시각(영업 처리)
  packing_list?: PackingBox[] | null  // 출고 포장 명세(박스별)
  has_box_plan?: boolean              // v0.90.0 분할선적 박스계획 존재 여부(배지)
  customer?: CustomerInfo
  product_part?: PartInfo  // deprecated - 첫번째 제품
  work_order_count: number
  // v0.22.0: 다중 제품
  item_count: number
  items?: ProductionRequestItem[]
  // v0.74.0: 첨부(도면/사진)
  attachment_files?: Array<{ filename: string; filepath?: string; mimetype?: string; size?: number }>
}

// 생산 요청서 생성 DTO (v0.22.0 다중 제품 지원)
export interface ProductionRequestCreate {
  customer_id?: number
  customer_order_no?: string
  // deprecated - 단일 제품 필드
  product_part_id?: number
  requested_quantity?: number
  due_date?: string
  priority?: number
  pi_number?: string
  payment_status?: string
  country?: string
  production_period?: string
  shipping_mark?: string
  consignee?: string
  destination?: string
  prepared_by_name?: string
  remarks?: string
  requested_by?: number
  // v0.22.0: 다중 제품
  items?: ProductionRequestItemCreate[]
}

// 생산 요청서 수정 DTO (v0.22.0 다중 제품 지원)
export interface ProductionRequestUpdate {
  customer_id?: number
  customer_order_no?: string
  // deprecated - 단일 제품 필드
  product_part_id?: number
  requested_quantity?: number
  due_date?: string
  priority?: number
  pi_number?: string
  payment_status?: string
  country?: string
  production_period?: string
  shipping_mark?: string
  consignee?: string
  destination?: string
  prepared_by_name?: string
  remarks?: string
  // v0.22.0: 다중 제품
  items?: ProductionRequestItemCreate[]
}

// 승인 요청
export interface ProductionRequestApprove {
  approved_by?: number
  remarks?: string
}

// 반려 요청
export interface ProductionRequestReject {
  rejection_reason: string
}

// 보류 요청
export interface ProductionRequestHold {
  remarks?: string
}

// 검색 파라미터
export interface ProductionRequestSearchParams {
  keyword?: string
  status?: ProductionRequestStatus
  customer_id?: number
  priority?: number
  is_draft?: boolean   // false=초안제외(생산), true=초안만(영업)
  from_date?: string
  to_date?: string
  skip?: number
  limit?: number
  order_by?: string
  order_desc?: boolean
}

// 분할선적 미리보기
export interface CiSplitLine {
  pr_id: number
  pr_item_id: number
  product_code: string
  product_name?: string | null
  uom?: string | null
  ordered: number
  issued: number
  remaining: number
  unit_price?: number | null
  currency?: string | null
  is_custom: boolean
}
export interface CiSplitPreview {
  customer?: string | null
  currency: string
  lines: CiSplitLine[]
}

// 페이지네이션 응답
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

// 생산 요청서 API 서비스
export const productionRequestApi = {
  // 생산 단계별 알림 수신자(지정 인원) 조회
  // { recipients: {requested, in_progress, shipped}, users: [{id,name,department,position}] }
  async getNotifyRecipients(): Promise<{
    recipients: { requested: number[]; in_progress: number[]; shipped: number[] }
    user_ids: number[]
    users: Array<{ id: number; name: string; department?: string; position?: string }>
  }> {
    const res = await apiClient.get('/production-requests/notify-recipients')
    return res.data
  },
  // 생산 단계별 알림 수신자 지정(관리자)
  async setNotifyRecipients(recipients: { requested: number[]; in_progress: number[]; shipped: number[] }): Promise<{ recipients: any }> {
    const res = await apiClient.put('/production-requests/notify-recipients', { recipients })
    return res.data
  },
  /**
   * 생산 요청서 목록 조회
   */
  async getAll(params: ProductionRequestSearchParams = {}): Promise<PaginatedResponse<ProductionRequestListItem>> {
    const queryParams = new URLSearchParams()

    if (params.keyword) queryParams.append('keyword', params.keyword)
    if (params.status) queryParams.append('status', params.status)
    if (params.customer_id) queryParams.append('customer_id', String(params.customer_id))
    if (params.priority !== undefined) queryParams.append('priority', String(params.priority))
    if (params.is_draft !== undefined) queryParams.append('is_draft', String(params.is_draft))
    if (params.from_date) queryParams.append('from_date', params.from_date)
    if (params.to_date) queryParams.append('to_date', params.to_date)
    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    if (params.limit !== undefined) queryParams.append('limit', String(params.limit))
    if (params.order_by) queryParams.append('order_by', params.order_by)
    if (params.order_desc !== undefined) queryParams.append('order_desc', String(params.order_desc))

    const response = await apiClient.get(`/production-requests?${queryParams.toString()}`)
    return response.data
  },

  /**
   * 생산 요청서 상세 조회
   */
  async getById(id: number): Promise<ProductionRequest> {
    const response = await apiClient.get(`/production-requests/${id}`)
    return response.data
  },

  /**
   * 대기 중인 생산 요청서 목록 조회 (REQUESTED 상태)
   */
  async getPending(skip: number = 0, limit: number = 50): Promise<ProductionRequest[]> {
    const response = await apiClient.get(`/production-requests/pending?skip=${skip}&limit=${limit}`)
    return response.data
  },

  /**
   * 대기 중인 생산 요청서 개수 조회
   */
  async getPendingCount(): Promise<number> {
    const response = await apiClient.get('/production-requests/pending/count')
    return response.data.count
  },

  /**
   * 생산 요청서 생성
   */
  async create(data: ProductionRequestCreate, overrideProtection = false): Promise<ProductionRequest> {
    const q = overrideProtection ? '?override_protection=true' : ''
    const response = await apiClient.post(`/production-requests${q}`, data)
    return response.data
  },

  /**
   * 생산 요청서 수정 (REQUESTED/HOLD/APPROVED 상태에서만)
   */
  async update(id: number, data: ProductionRequestUpdate, overrideProtection = false): Promise<ProductionRequest> {
    const q = overrideProtection ? '?override_protection=true' : ''
    const response = await apiClient.put(`/production-requests/${id}${q}`, data)
    return response.data
  },

  /**
   * 진행 체크박스 토글 (인서트출고 / 생산출고 / 검토필요) — 모든 상태에서 가능
   */
  // ── 출고 포장사진(납품 트리) ──
  async listPackingPhotos(id: number): Promise<{ enabled: boolean; folder: string | null; photos: { name: string; size: number; mtime: number }[] }> {
    const res = await apiClient.get(`/production-requests/${id}/packing-photos`)
    return res.data
  },
  async uploadPackingPhoto(id: number, file: File): Promise<{ name: string; folder: string }> {
    const fd = new FormData()
    fd.append('file', file)
    const res = await apiClient.post(`/production-requests/${id}/packing-photos`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },
  async packingPhotoBlobUrl(id: number, name: string): Promise<string> {
    const res = await apiClient.get(`/production-requests/${id}/packing-photos/preview`, {
      params: { name }, responseType: 'blob',
    })
    const mime = (res.headers['content-type'] as string) || 'image/*'
    return URL.createObjectURL(new Blob([res.data], { type: mime }))
  },
  async deletePackingPhoto(id: number, name: string): Promise<void> {
    // POST(삭제) — 생산요청 삭제권한(관리자)이 아닌 업로드와 동일 쓰기권한으로 담당자도 가능
    await apiClient.post(`/production-requests/${id}/packing-photos/delete`, null, { params: { name } })
  },

  // ── 측정자료(손실값측정 엑셀 등, 납품 트리) ──
  async listMeasurementFiles(id: number): Promise<{ enabled: boolean; folder: string | null; files: { name: string; size: number; mtime: number }[] }> {
    const res = await apiClient.get(`/production-requests/${id}/measurement-files`)
    return res.data
  },
  async uploadMeasurementFile(id: number, file: File): Promise<{ name: string; folder: string }> {
    const fd = new FormData()
    fd.append('file', file)
    const res = await apiClient.post(`/production-requests/${id}/measurement-files`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },
  async downloadMeasurementFile(id: number, name: string): Promise<void> {
    const res = await apiClient.get(`/production-requests/${id}/measurement-files/download`, {
      params: { name }, responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },
  async deleteMeasurementFile(id: number, name: string): Promise<void> {
    await apiClient.post(`/production-requests/${id}/measurement-files/delete`, null, { params: { name } })
  },

  // 초안(is_draft) 생산요청을 정식 전송 — 생산팀 노출 + 알림
  async submitDraft(id: number): Promise<ProductionRequest> {
    const res = await apiClient.post(`/production-requests/${id}/submit`)
    return res.data
  },

  // 초안(임시) 생산요청 회수(삭제) — 영업이 전송 전 임시 건만. DELETE 대신 POST(영업 권한)
  async withdrawDraft(id: number): Promise<void> {
    await apiClient.post(`/production-requests/${id}/withdraw-draft`)
  },

  // 캘린더용 경량 데이터(기간 내 납기일/요청일 마커). 초안 제외.
  async calendar(from: string, to: string, customerId?: number): Promise<ProductionCalendarItem[]> {
    const p = new URLSearchParams({ from, to })
    if (customerId) p.set('customer_id', String(customerId))
    const res = await apiClient.get(`/production-requests/calendar?${p.toString()}`)
    return res.data
  },

  // 납기일 변경(변경 시 생산팀 알림). due_date=null 이면 미정으로.
  async updateDueDate(id: number, dueDate: string | null): Promise<ProductionRequest> {
    const res = await apiClient.put(`/production-requests/${id}/due-date`, { due_date: dueDate })
    return res.data
  },

  async updateFlags(id: number, flags: {
    insert_shipped?: boolean
    production_shipped?: boolean
    needs_review?: boolean
    review_note?: string | null
    insert_shipped_at?: string | null    // YYYY-MM-DD (출고일 명시 수정)
    production_shipped_at?: string | null
    insert_not_applicable?: boolean       // 인서트 해당없음(N/A)
  }): Promise<ProductionRequest> {
    const response = await apiClient.patch(`/production-requests/${id}/flags`, flags)
    return response.data
  },

  /**
   * 출고건에서 CI(Commercial Invoice) 생성 — 연결된 PI를 CI로 전환.
   * 이미 CI가 있으면 already_exists=true 로 기존 CI를 반환.
   */
  async createCi(id: number): Promise<{ ci_id: number; ci_number: string; already_exists: boolean }> {
    const response = await apiClient.post(`/production-requests/${id}/create-ci`)
    return response.data
  },

  /** 여러 출고건을 하나의 CI로 합배송 발행(같은 고객). */
  async createCiMerged(prIds: number[]): Promise<{ ci_id: number; ci_number: string; merged_count: number }> {
    const response = await apiClient.post(`/production-requests/create-ci-merged`, { pr_ids: prIds })
    return response.data
  },

  /** 분할선적 미리보기 — 품목별 전량/기발행/잔여/단가. */
  async ciSplitPreview(prIds: number[]): Promise<CiSplitPreview> {
    const response = await apiClient.post(`/production-requests/ci-split-preview`, { pr_ids: prIds })
    return response.data
  },

  /** 분할선적 — 지정 품목·수량으로 CI 발행. */
  async createCiSplit(data: {
    pr_ids: number[]
    lines: { pr_item_id: number; quantity: number; unit_price?: number | null }[]
    document_date?: string | null
  }): Promise<{ ci_id: number; ci_number: string }> {
    const response = await apiClient.post(`/production-requests/create-ci-split`, data)
    return response.data
  },

  /**
   * 생산 시작 단계 자료 저장 — 총괄자 메모 / 공정 확인표 (모든 상태에서 가능)
   */
  async updateProductionNotes(id: number, payload: {
    manager_memo?: string
    process_checks?: ProcessCheckRow[]
  }): Promise<ProductionRequest> {
    const response = await apiClient.patch(`/production-requests/${id}/production-notes`, payload)
    return response.data
  },

  /**
   * 생산 요청서 삭제 (REQUESTED/CANCELLED/REJECTED 상태에서만)
   */
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/production-requests/${id}`)
  },

  // ==================== 상태 전이 ====================

  /**
   * 승인 (REQUESTED → APPROVED)
   */
  async approve(id: number, data: ProductionRequestApprove = {}): Promise<ProductionRequest> {
    const response = await apiClient.post(`/production-requests/${id}/approve`, data)
    return response.data
  },

  /**
   * 반려 (REQUESTED/HOLD → REJECTED)
   */
  async reject(id: number, data: ProductionRequestReject): Promise<ProductionRequest> {
    const response = await apiClient.post(`/production-requests/${id}/reject`, data)
    return response.data
  },

  /**
   * 보류 (REQUESTED → HOLD)
   */
  async hold(id: number, data: ProductionRequestHold = {}): Promise<ProductionRequest> {
    const response = await apiClient.post(`/production-requests/${id}/hold`, data)
    return response.data
  },

  /**
   * 보류 해제 (HOLD → REQUESTED)
   */
  async releaseHold(id: number): Promise<ProductionRequest> {
    const response = await apiClient.post(`/production-requests/${id}/release-hold`)
    return response.data
  },

  /**
   * 취소
   */
  async cancel(id: number, reason?: string): Promise<ProductionRequest> {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
    const response = await apiClient.post(`/production-requests/${id}/cancel${params}`)
    return response.data
  },

  /**
   * 간편 상태 변경 (v0.32.0)
   */
  async changeStatus(id: number, newStatus: ProductionRequestStatus): Promise<ProductionRequest> {
    const response = await apiClient.post(`/production-requests/${id}/change-status?new_status=${newStatus}`)
    return response.data
  },

  /**
   * 생산 출고 처리 — packing list와 함께 SHIPPED로 전환 (IN_PROGRESS/COMPLETED → SHIPPED)
   */
  async ship(id: number, packingList: PackingBox[]): Promise<ProductionRequest> {
    const response = await apiClient.post(`/production-requests/${id}/ship`, { packing_list: packingList })
    return response.data
  },

  /**
   * 출고 후 패킹 정보 수정 — 상태 전이 없이 packing list 만 갱신(출고 이력 보존)
   */
  async updatePackingList(id: number, packingList: PackingBox[]): Promise<ProductionRequest> {
    const response = await apiClient.put(`/production-requests/${id}/packing-list`, { packing_list: packingList })
    return response.data
  },

  /**
   * 분할선적 박스 분할계획 저장 — 영업 작성(자동생성 후 수기조정). null이면 계획 해제.
   */
  async updateBoxPlan(id: number, boxPlan: BoxPlanBox[] | null): Promise<ProductionRequest> {
    const response = await apiClient.put(`/production-requests/${id}/box-plan`, { box_plan: boxPlan })
    return response.data
  },

  /**
   * 박스 단위 CI 발행 — 박스 분할계획의 1개 박스를 1 CI로(내용물 + 박스당 운임).
   */
  async createBoxCi(id: number, boxNo: number, documentDate?: string): Promise<{ ci_id: number; ci_number: string; box_no: number }> {
    const response = await apiClient.post(`/production-requests/${id}/box-plan/${boxNo}/create-ci`, { document_date: documentDate || null })
    return response.data
  },

  // ==================== 제품별 작업지시서 생성 (v0.29.0) ====================

  createWOForItem(prId: number, itemId: number) {
    return apiClient.post(`/production-requests/${prId}/items/${itemId}/create-work-order`)
  },

  // ==================== 첨부파일 관리 (v0.22.0) ====================

  /**
   * 첨부파일 업로드
   */
  async uploadAttachment(id: number, file: File): Promise<{ message: string; file: any; total_files: number }> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post(`/production-requests/${id}/attachments`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  /**
   * 첨부파일 삭제
   */
  async deleteAttachment(id: number, fileIndex: number): Promise<{ message: string; total_files: number }> {
    const response = await apiClient.delete(`/production-requests/${id}/attachments/${fileIndex}`)
    return response.data
  },

  /**
   * 첨부파일 다운로드 URL 가져오기
   */
  getAttachmentDownloadUrl(id: number, fileIndex: number): string {
    return `/api/v1/production-requests/${id}/attachments/${fileIndex}/download`
  },

  /**
   * 첨부파일 미리보기 URL 가져오기
   */
  getAttachmentPreviewUrl(id: number, fileIndex: number): string {
    return `/api/v1/production-requests/${id}/attachments/${fileIndex}/preview`
  },

  /**
   * 첨부파일을 Blob으로 로드 (인증 헤더 실림 → 미리보기/다운로드 401 방지)
   */
  async fetchAttachmentBlob(id: number, fileIndex: number): Promise<Blob> {
    const response = await apiClient.get(
      `/production-requests/${id}/attachments/${fileIndex}/preview`,
      { responseType: 'blob' },
    )
    return response.data as Blob
  },

  // ── 품목별 도면/첨부 (v0.75.0) ──
  async uploadItemAttachment(prId: number, itemId: number, file: File): Promise<{ file: any; total_files: number }> {
    const fd = new FormData()
    fd.append('file', file)
    const res = await apiClient.post(`/production-requests/${prId}/items/${itemId}/attachments`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },
  async deleteItemAttachment(prId: number, itemId: number, fileIndex: number): Promise<{ total_files: number }> {
    const res = await apiClient.delete(`/production-requests/${prId}/items/${itemId}/attachments/${fileIndex}`)
    return res.data
  },
  async fetchItemAttachmentBlob(prId: number, itemId: number, fileIndex: number): Promise<Blob> {
    const res = await apiClient.get(`/production-requests/${prId}/items/${itemId}/attachments/${fileIndex}/preview`, { responseType: 'blob' })
    return res.data as Blob
  },
}

// 생산 요청서 상태 한글 변환
export const prStatusLabels: Record<ProductionRequestStatus, string> = {
  REQUESTED: '요청됨',
  HOLD: '보류',
  REJECTED: '반려됨',
  APPROVED: '생산부 확인',
  IN_PROGRESS: '생산 진행중',
  COMPLETED: '생산 완료',
  SHIPPED: '출고 완료',
  DELIVERED: '발송 완료',
  CANCELLED: '취소됨',
}

// 생산 요청서 상태별 스타일 클래스
export const prStatusStyles: Record<ProductionRequestStatus, string> = {
  REQUESTED: 'bg-yellow-100 text-yellow-800',
  HOLD: 'bg-orange-100 text-orange-800',
  REJECTED: 'bg-red-100 text-red-800',
  APPROVED: 'bg-blue-100 text-blue-800',
  IN_PROGRESS: 'bg-indigo-100 text-indigo-800',
  COMPLETED: 'bg-green-100 text-green-800',
  SHIPPED: 'bg-teal-100 text-teal-800',
  DELIVERED: 'bg-purple-100 text-purple-800',
  CANCELLED: 'bg-gray-100 text-gray-800',
}

// 우선순위 라벨
export const priorityLabels: Record<number, string> = {
  0: '보통',
  1: '높음',
  2: '긴급',
}

// 우선순위 스타일
export const priorityStyles: Record<number, string> = {
  0: 'bg-gray-100 text-gray-800',
  1: 'bg-yellow-100 text-yellow-800',
  2: 'bg-red-100 text-red-800',
}
