/**
 * 작업지시서 관리 API 서비스
 *
 * v0.6.0: 입출고 관리 기능 추가
 * - 작업지시서 CRUD
 * - BOM 자동 전개
 * - 상태 전이 (7단계)
 * - 부품 출고 → 재고 자동 감소
 *
 * v0.19.0: 다중 제품 지원
 * - 하나의 작업지시서에 여러 제품(완제품/반제품) 등록 가능
 * - WorkOrderProduct 인터페이스 추가
 */

import apiClient from './client'

// 작업지시서 상태 (7단계)
export type WorkOrderStatus =
  | 'RECEIVED'
  | 'APPROVED'
  | 'ISSUED'
  | 'IN_PROGRESS'
  | 'INSPECTION'
  | 'PACKED'
  | 'SHIPPED'
  | 'CANCELLED'

// 우선순위
export type WorkOrderPriority = 0 | 1 | 2

// 부품 간략 정보
export interface PartInfo {
  id: number
  part_number: string
  part_number_display?: string
  part_name: string
  part_name_en?: string
  specification?: string
}

// 고객사 간략 정보
export interface CustomerInfo {
  id: number
  name: string
  partner_code?: string
  partner_name?: string
  business_number?: string
  contact_person?: string
  phone?: string
}

// 단위 간략 정보
export interface UnitInfo {
  id: number
  code: string
  name: string
}

// 작업지시서 항목
export interface WorkOrderItem {
  id: number
  work_order_id: number
  work_order_product_id?: number  // v0.19.0: 어느 제품의 BOM인지
  part_id: number
  bom_id?: number
  required_quantity: number
  issued_quantity: number
  additional_quantity: number
  returned_quantity: number
  unit_id?: number
  bom_level: number
  line_remarks?: string
  sort_order: number
  part?: PartInfo
  unit?: UnitInfo
  total_issued?: number
  pending_quantity?: number
}

// v0.19.0: 작업지시서 제품
export interface WorkOrderProduct {
  id: number
  work_order_id: number
  product_part_id: number
  order_quantity: number
  completed_quantity: number
  defective_quantity: number
  sort_order: number
  line_remarks?: string
  product_part?: PartInfo
}

// v0.19.0: 작업지시서 제품 생성 DTO
export interface WorkOrderProductCreate {
  product_part_id: number
  order_quantity: number
  line_remarks?: string
  sort_order?: number
}

// 작업지시서 항목 생성 DTO
export interface WorkOrderItemCreate {
  part_id: number
  required_quantity: number
  unit_id?: number
  bom_id?: number
  bom_level?: number
  line_remarks?: string
  sort_order?: number
}

// 작업지시서 인터페이스 (v0.19.0 다중 제품 지원)
export interface WorkOrder {
  id: number
  wo_number: string
  product_part_id?: number  // deprecated - 호환성용
  customer_id?: number
  customer_order_no?: string
  order_quantity?: number  // deprecated - 호환성용
  completed_quantity?: number  // deprecated - 호환성용
  defective_quantity?: number  // deprecated - 호환성용
  status: WorkOrderStatus
  priority: number
  // 단계별 일시
  received_date?: string
  approved_date?: string
  approved_by?: number
  issue_scheduled_date?: string
  issue_completed_date?: string
  production_scheduled_date?: string
  production_start_date?: string
  production_end_date?: string
  inspection_scheduled_date?: string
  inspection_completed_date?: string
  packing_scheduled_date?: string
  packing_completed_date?: string
  shipping_scheduled_date?: string
  shipping_completed_date?: string
  remarks?: string
  document_files?: any[]
  created_by?: number
  created_at: string
  updated_by?: number
  updated_at?: string
  source_request_modified?: boolean  // v0.21.0: 원본 요청서 수정됨
  production_request_id?: number  // v0.22.0: 생산요청 ID
  parent_wo_id?: number  // v0.31.0: 상위 WO
  target_part_id?: number  // v0.31.0: 목적 부품
  product_part?: PartInfo  // deprecated - 호환성용
  customer?: CustomerInfo
  items?: WorkOrderItem[]
  products?: WorkOrderProduct[]  // v0.19.0: 다중 제품
  // v0.22.0: 생산요청서 첨부파일 참조
  source_request_attachments?: { filename: string; filepath: string; mimetype: string; size?: number }[]
  source_request_number?: string
}

// 작업지시서 목록 (간략) (v0.19.0 다중 제품 지원)
export interface WorkOrderListItem {
  id: number
  wo_number: string
  product_part_id?: number  // deprecated - 호환성용
  parent_wo_id?: number  // v0.31.0: 상위 WO
  target_part_id?: number  // v0.31.0: 목적 부품
  customer_id?: number
  order_quantity?: number  // deprecated - 호환성용
  completed_quantity?: number  // deprecated - 호환성용
  status: WorkOrderStatus
  priority: number
  shipping_scheduled_date?: string
  created_at: string
  source_request_modified?: boolean  // v0.21.0: 원본 요청서 수정됨
  product_part?: PartInfo  // deprecated - 호환성용
  customer?: CustomerInfo
  item_count?: number
  product_count?: number  // v0.19.0: 제품 수
  products?: WorkOrderProduct[]  // v0.19.0: 다중 제품
}

// 작업지시서 생성 DTO (v0.19.0 다중 제품 지원, v0.20.0 생산요청 연결)
export interface WorkOrderCreate {
  product_part_id?: number  // deprecated - 호환성용
  order_quantity?: number  // deprecated - 호환성용
  products?: WorkOrderProductCreate[]  // v0.19.0: 다중 제품
  production_request_id?: number  // v0.20.0: 생산요청 ID
  parent_wo_id?: number  // v0.31.0: 상위 WO
  target_part_id?: number  // v0.31.0: 목적 부품
  customer_id?: number
  customer_order_no?: string
  priority?: number
  remarks?: string
  auto_expand_bom?: boolean
  items?: WorkOrderItemCreate[]
  // 예정일
  issue_scheduled_date?: string
  production_scheduled_date?: string
  inspection_scheduled_date?: string
  packing_scheduled_date?: string
  shipping_scheduled_date?: string
}

// 작업지시서 수정 DTO (v0.19.0 다중 제품 지원)
export interface WorkOrderUpdate {
  customer_id?: number
  customer_order_no?: string
  order_quantity?: number  // deprecated
  products?: WorkOrderProductCreate[]  // v0.19.0: 다중 제품
  priority?: number
  remarks?: string
  issue_scheduled_date?: string
  production_scheduled_date?: string
  inspection_scheduled_date?: string
  packing_scheduled_date?: string
  shipping_scheduled_date?: string
}

// 부품 출고 요청
export interface IssueRequest {
  items?: { item_id: number; issue_quantity: number }[]
  remarks?: string
}

// 추가 출고 요청
export interface AdditionalIssueRequest {
  quantity: number
  reason?: string
}

// 반납 요청
export interface ReturnRequest {
  quantity: number
  reason?: string
}

// 생산 완료 요청
export interface ProductionCompleteRequest {
  completed_quantity: number
  defective_quantity?: number
  remarks?: string
}

// BOM 전개 미리보기 항목
export interface BOMPreviewItem {
  part_id: number
  part_number: string
  part_number_display?: string
  part_name: string
  bom_id?: number
  bom_level: number
  unit_quantity: number
  total_quantity: number
  current_stock?: number
  stock_status?: 'SUFFICIENT' | 'INSUFFICIENT'
}

// BOM 전개 미리보기 응답
export interface BOMPreviewResponse {
  product_part_id: number
  product_part_name: string
  order_quantity: number
  items: BOMPreviewItem[]
  has_insufficient_stock: boolean
}

// 검색 파라미터
export interface WorkOrderSearchParams {
  keyword?: string
  status?: WorkOrderStatus
  customer_id?: number
  product_part_id?: number
  priority?: number
  from_date?: string
  to_date?: string
  skip?: number
  limit?: number
  order_by?: string
  order_desc?: boolean
}

// 페이지네이션 응답
// v0.31.0: 작업지시 체인 응답
export interface WorkOrderChainItem {
  id: number
  wo_number: string
  status: string
  order_type?: string
  target_part?: { id: number; part_number_display: string; part_name: string } | null
  product_part_id?: number
}

export interface WorkOrderChainResponse {
  wo_id: number
  wo_number: string
  parent: WorkOrderChainItem | null
  children: WorkOrderChainItem[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

// 작업지시서 API 서비스
export const workOrderApi = {
  /**
   * 작업지시서 목록 조회
   */
  async getAll(params: WorkOrderSearchParams = {}): Promise<PaginatedResponse<WorkOrderListItem>> {
    const queryParams = new URLSearchParams()

    if (params.keyword) queryParams.append('keyword', params.keyword)
    if (params.status) queryParams.append('status', params.status)
    if (params.customer_id) queryParams.append('customer_id', String(params.customer_id))
    if (params.product_part_id) queryParams.append('product_part_id', String(params.product_part_id))
    if (params.priority !== undefined) queryParams.append('priority', String(params.priority))
    if (params.from_date) queryParams.append('from_date', params.from_date)
    if (params.to_date) queryParams.append('to_date', params.to_date)
    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    if (params.limit !== undefined) queryParams.append('limit', String(params.limit))
    if (params.order_by) queryParams.append('order_by', params.order_by)
    if (params.order_desc !== undefined) queryParams.append('order_desc', String(params.order_desc))

    const response = await apiClient.get(`/work-orders?${queryParams.toString()}`)
    return response.data
  },

  /**
   * 작업지시서 상세 조회
   */
  async getById(id: number): Promise<WorkOrder> {
    const response = await apiClient.get(`/work-orders/${id}`)
    return response.data
  },

  /**
   * BOM 전개 미리보기
   */
  async getBOMPreview(productPartId: number, orderQuantity: number): Promise<BOMPreviewResponse> {
    const response = await apiClient.get(
      `/work-orders/preview/bom?product_part_id=${productPartId}&order_quantity=${orderQuantity}`
    )
    return response.data
  },

  /**
   * 작업지시서 BOM 전개 미리보기
   */
  async getWorkOrderBOMPreview(woId: number): Promise<BOMPreviewResponse> {
    const response = await apiClient.get(`/work-orders/${woId}/bom-preview`)
    return response.data
  },

  /**
   * 작업지시서 생성
   */
  async create(data: WorkOrderCreate): Promise<WorkOrder> {
    const response = await apiClient.post('/work-orders', data)
    return response.data
  },

  /**
   * 작업지시서 수정 (RECEIVED 상태에서만)
   */
  async update(id: number, data: WorkOrderUpdate): Promise<WorkOrder> {
    const response = await apiClient.put(`/work-orders/${id}`, data)
    return response.data
  },

  /**
   * 작업지시서 삭제 (RECEIVED 상태에서만)
   */
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/work-orders/${id}`)
  },

  // ==================== 상태 전이 ====================

  /**
   * 승인 (RECEIVED → APPROVED)
   */
  async approve(id: number, approvedBy?: number): Promise<WorkOrder> {
    const params = approvedBy ? `?approved_by=${approvedBy}` : ''
    const response = await apiClient.post(`/work-orders/${id}/approve${params}`)
    return response.data
  },

  /**
   * 부품 출고 (APPROVED → ISSUED)
   * 출고된 수량만큼 재고가 자동으로 감소합니다.
   */
  async issueParts(id: number, data?: IssueRequest): Promise<WorkOrder> {
    const response = await apiClient.post(`/work-orders/${id}/issue`, data || {})
    return response.data
  },

  /**
   * 추가 출고
   */
  async issueAdditional(woId: number, itemId: number, data: AdditionalIssueRequest): Promise<WorkOrder> {
    const response = await apiClient.post(`/work-orders/${woId}/items/${itemId}/issue-additional`, data)
    return response.data
  },

  /**
   * 부품 반납
   */
  async returnParts(woId: number, itemId: number, data: ReturnRequest): Promise<WorkOrder> {
    const response = await apiClient.post(`/work-orders/${woId}/items/${itemId}/return`, data)
    return response.data
  },

  /**
   * 작업 시작 (ISSUED → IN_PROGRESS)
   */
  async startProduction(id: number): Promise<WorkOrder> {
    const response = await apiClient.post(`/work-orders/${id}/start-production`)
    return response.data
  },

  /**
   * 작업 완료 (IN_PROGRESS → INSPECTION)
   */
  async completeProduction(id: number, data: ProductionCompleteRequest): Promise<WorkOrder> {
    const response = await apiClient.post(`/work-orders/${id}/complete-production`, data)
    return response.data
  },

  /**
   * 검사 완료 (INSPECTION → PACKED)
   */
  async completeInspection(id: number): Promise<WorkOrder> {
    const response = await apiClient.post(`/work-orders/${id}/complete-inspection`)
    return response.data
  },

  /**
   * 출하 (PACKED → SHIPPED)
   */
  async ship(id: number): Promise<WorkOrder> {
    const response = await apiClient.post(`/work-orders/${id}/ship`)
    return response.data
  },

  /**
   * 작업지시 취소
   * 출고된 부품은 재고로 자동 복구됩니다.
   */
  async cancel(id: number, reason?: string): Promise<WorkOrder> {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
    const response = await apiClient.post(`/work-orders/${id}/cancel${params}`)
    return response.data
  },

  /**
   * 상태 롤백 (이전 상태로 되돌리기)
   * - APPROVED -> RECEIVED
   * - ISSUED -> APPROVED (재고 복구)
   * - IN_PROGRESS -> ISSUED
   * - INSPECTION -> IN_PROGRESS
   * - PACKED -> INSPECTION
   */
  async rollback(id: number, reason?: string): Promise<WorkOrder> {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
    const response = await apiClient.post(`/work-orders/${id}/rollback${params}`)
    return response.data
  },

  /**
   * 취소된 작업지시서 복원
   * 취소 전 상태로 되돌립니다.
   * 출고 상태였던 경우 APPROVED 상태로 복원됩니다.
   */
  async restore(id: number, reason?: string): Promise<WorkOrder> {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
    const response = await apiClient.post(`/work-orders/${id}/restore${params}`)
    return response.data
  },

  // ==================== 원본 요청서 수정 알림 (v0.21.0) ====================

  /**
   * 원본 요청서가 수정된 작업지시서 목록 조회 (v0.23.0)
   */
  async getModified(skip: number = 0, limit: number = 20): Promise<WorkOrderListItem[]> {
    const response = await apiClient.get(`/work-orders/modified?skip=${skip}&limit=${limit}`)
    return response.data
  },

  /**
   * 원본 요청서 수정 알림 확인
   * source_request_modified 플래그를 리셋합니다.
   */
  async acknowledgeModification(id: number): Promise<WorkOrder> {
    const response = await apiClient.post(`/work-orders/${id}/acknowledge-modification`)
    return response.data
  },

  // ==================== 작업지시 체인 (v0.31.0) ====================

  /**
   * 작업지시 체인 조회 (선행/후속 관계)
   */
  async getChain(id: number): Promise<WorkOrderChainResponse> {
    const response = await apiClient.get(`/work-orders/${id}/chain`)
    return response.data
  },

  // ==================== 파일 첨부 ====================

  /**
   * 문서 파일 업로드
   */
  async uploadDocument(woId: number, file: File): Promise<WorkOrder> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post(`/work-orders/${woId}/upload/document`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  /**
   * 문서 파일 삭제
   */
  async deleteDocument(woId: number, fileIndex: number): Promise<WorkOrder> {
    const response = await apiClient.delete(`/work-orders/${woId}/files/${fileIndex}`)
    return response.data
  },

  // ==================== 파일 미리보기/다운로드 (v0.22.0) ====================

  /**
   * 작업지시서 첨부파일 미리보기 URL
   */
  getDocumentPreviewUrl(woId: number, fileIndex: number): string {
    return `/api/v1/work-orders/${woId}/files/${fileIndex}/preview`
  },

  /**
   * 작업지시서 첨부파일 다운로드 URL
   */
  getDocumentDownloadUrl(woId: number, fileIndex: number): string {
    return `/api/v1/work-orders/${woId}/files/${fileIndex}/download`
  },

  /**
   * 생산요청서 첨부파일 미리보기 URL (참조용)
   */
  getSourceAttachmentPreviewUrl(prId: number, fileIndex: number): string {
    return `/api/v1/production-requests/${prId}/attachments/${fileIndex}/preview`
  },

  /**
   * 생산요청서 첨부파일 다운로드 URL (참조용)
   */
  getSourceAttachmentDownloadUrl(prId: number, fileIndex: number): string {
    return `/api/v1/production-requests/${prId}/attachments/${fileIndex}/download`
  },
}

// 작업지시서 상태 한글 변환
export const woStatusLabels: Record<WorkOrderStatus, string> = {
  RECEIVED: '접수',
  APPROVED: '승인',
  ISSUED: '부품출고',
  IN_PROGRESS: '작업중',
  INSPECTION: '검사',
  PACKED: '포장완료',
  SHIPPED: '출하완료',
  CANCELLED: '취소',
}

// 작업지시서 상태별 스타일 클래스
export const woStatusStyles: Record<WorkOrderStatus, string> = {
  RECEIVED: 'bg-gray-100 text-gray-800',
  APPROVED: 'bg-blue-100 text-blue-800',
  ISSUED: 'bg-indigo-100 text-indigo-800',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  INSPECTION: 'bg-orange-100 text-orange-800',
  PACKED: 'bg-green-100 text-green-800',
  SHIPPED: 'bg-purple-100 text-purple-800',
  CANCELLED: 'bg-red-100 text-red-800',
}

// 우선순위 한글 변환
export const priorityLabels: Record<WorkOrderPriority, string> = {
  0: '보통',
  1: '높음',
  2: '긴급',
}

// 우선순위별 스타일 클래스
export const priorityStyles: Record<WorkOrderPriority, string> = {
  0: 'bg-gray-100 text-gray-800',
  1: 'bg-orange-100 text-orange-800',
  2: 'bg-red-100 text-red-800',
}
