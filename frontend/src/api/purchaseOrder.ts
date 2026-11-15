/**
 * 발주서 관리 API 서비스
 *
 * v0.6.0: 입출고 관리 기능 추가
 * - 발주서 CRUD
 * - 상태 전이 (DRAFT → ORDERED → CONFIRMED → RECEIVED)
 * - 결재는 is_paid 필드로 별도 관리
 * - 입고 처리 → 재고 자동 증가
 * v0.6.1: 상태 롤백 기능 추가
 */

import apiClient from './client'

// 발주서 상태 (COMPLETED는 기존 데이터 호환용 - 새 데이터는 is_paid로 결재 관리)
export type PurchaseOrderStatus = 'DRAFT' | 'ORDERED' | 'CONFIRMED' | 'RECEIVED' | 'COMPLETED' | 'CANCELLED'

// 부품 간략 정보
export interface PartInfo {
  id: number
  part_number: string
  part_number_display?: string
  part_name: string
  part_name_en?: string
  specification?: string
}

// 공급업체 간략 정보
export interface SupplierInfo {
  id: number
  partner_code: string
  partner_name: string
  business_number?: string
  representative?: string
  address?: string
  fax?: string
  manager_name?: string
  tel?: string
}

// 단위 간략 정보
export interface UnitInfo {
  id: number
  code: string
  name: string
}

// 발주서 항목
export interface PurchaseOrderItem {
  id: number
  purchase_order_id: number
  part_id?: number | null
  custom_product_code?: string | null   // BOM 미등록(자유입력) 품번
  custom_product_name?: string | null   // BOM 미등록(자유입력) 품명
  ordered_quantity: number
  received_quantity: number
  defective_quantity: number
  unit_price: number
  line_total?: number
  last_price?: number | null
  unit_id?: number
  line_remarks?: string
  sort_order: number
  part?: PartInfo
  unit?: UnitInfo
}

// 발주서 항목 생성 DTO
export interface PurchaseOrderItemCreate {
  part_id?: number | null
  custom_product_code?: string | null
  custom_product_name?: string | null
  ordered_quantity: number
  unit_price: number
  unit_id?: number
  line_remarks?: string
  sort_order?: number
}

// 발주서 항목 수정 DTO
export interface PurchaseOrderItemUpdate {
  ordered_quantity?: number
  unit_price?: number
  unit_id?: number
  line_remarks?: string
  sort_order?: number
}

// 발주서 인터페이스
export interface PurchaseOrder {
  id: number
  po_number: string
  supplier_id: number
  order_date: string
  expected_delivery_date?: string
  actual_delivery_date?: string
  total_amount: number
  currency: string
  tax_amount: number
  discount_amount: number
  status: PurchaseOrderStatus
  is_paid: boolean
  paid_date?: string
  paid_amount?: number
  payment_terms?: string
  delivery_terms?: string
  remarks?: string
  document_files?: any[]
  source_approval_id?: number | null
  sent_at?: string | null
  sent_by?: number | null
  disbursement_id?: number | null
  created_by?: number
  created_at: string
  updated_by?: number
  updated_at?: string
  supplier?: SupplierInfo
  items?: PurchaseOrderItem[]
}

// 발주서 목록 (간략)
export interface PurchaseOrderListItem {
  id: number
  po_number: string
  supplier_id: number
  order_date: string
  expected_delivery_date?: string
  total_amount: number
  status: PurchaseOrderStatus
  is_paid: boolean
  source_approval_id?: number | null
  sent_at?: string | null
  disbursement_id?: number | null
  created_at: string
  supplier?: SupplierInfo
  item_count?: number
}

// 발주서 생성 DTO
export interface PurchaseOrderCreate {
  supplier_id: number
  order_date: string
  expected_delivery_date?: string
  currency?: string
  payment_terms?: string
  delivery_terms?: string
  remarks?: string
  items?: PurchaseOrderItemCreate[]
}

// 발주서 수정 DTO
export interface PurchaseOrderUpdate {
  supplier_id?: number
  order_date?: string
  expected_delivery_date?: string
  currency?: string
  payment_terms?: string
  delivery_terms?: string
  remarks?: string
}

// 입고 항목 요청
export interface ReceiveItemRequest {
  item_id: number
  received_quantity: number
  defective_quantity?: number
  // 최종 입고 시 가격 조정 (선택)
  final_unit_price?: number
  final_line_total?: number
}

// 입고 처리 요청
export interface ReceiveRequest {
  items: ReceiveItemRequest[]
  actual_delivery_date?: string
  remarks?: string
  is_final_receive?: boolean  // 최종 입고 여부 (가격 조정 시 true)
}

// 납기 확정 요청
export interface ConfirmDeliveryRequest {
  expected_delivery_date: string
  remarks?: string
}

// 결제 처리 요청
export interface PaymentRequest {
  is_paid: boolean
  paid_date?: string
  paid_amount?: number
}

// 검색 파라미터
export interface PurchaseOrderSearchParams {
  keyword?: string
  status?: PurchaseOrderStatus
  supplier_id?: number
  from_date?: string
  to_date?: string
  skip?: number
  limit?: number
  order_by?: string
  order_desc?: boolean
}

// 페이지네이션 응답
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

// 발주서 API 서비스
export const purchaseOrderApi = {
  /**
   * 발주서 목록 조회
   */
  async getAll(params: PurchaseOrderSearchParams = {}): Promise<PaginatedResponse<PurchaseOrderListItem>> {
    const queryParams = new URLSearchParams()

    if (params.keyword) queryParams.append('keyword', params.keyword)
    if (params.status) queryParams.append('status', params.status)
    if (params.supplier_id) queryParams.append('supplier_id', String(params.supplier_id))
    if (params.from_date) queryParams.append('from_date', params.from_date)
    if (params.to_date) queryParams.append('to_date', params.to_date)
    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    if (params.limit !== undefined) queryParams.append('limit', String(params.limit))
    if (params.order_by) queryParams.append('order_by', params.order_by)
    if (params.order_desc !== undefined) queryParams.append('order_desc', String(params.order_desc))

    const response = await apiClient.get(`/purchase-orders?${queryParams.toString()}`)
    return response.data
  },

  /**
   * 발주서 상세 조회
   */
  async getById(id: number): Promise<PurchaseOrder> {
    const response = await apiClient.get(`/purchase-orders/${id}`)
    return response.data
  },

  /**
   * 발주서 생성
   */
  async create(data: PurchaseOrderCreate): Promise<PurchaseOrder> {
    const response = await apiClient.post('/purchase-orders', data)
    return response.data
  },

  /**
   * 이 발주건으로 구매기안서(임시저장) 자동 생성 — 업체·품목 자동 등록 (중복 시 기존 반환)
   */
  async createApproval(id: number): Promise<{ approval_id: number; doc_number: string; title: string }> {
    const response = await apiClient.post(`/purchase-orders/${id}/create-approval`)
    return response.data
  },

  /**
   * 발주서 수정 (DRAFT 상태에서만)
   */
  async update(id: number, data: PurchaseOrderUpdate): Promise<PurchaseOrder> {
    const response = await apiClient.put(`/purchase-orders/${id}`, data)
    return response.data
  },

  /**
   * 발주서 삭제 (DRAFT 상태에서만)
   */
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/purchase-orders/${id}`)
  },

  // ==================== 항목 관리 ====================

  /**
   * 발주서 항목 추가
   */
  async addItem(poId: number, item: PurchaseOrderItemCreate): Promise<PurchaseOrder> {
    const response = await apiClient.post(`/purchase-orders/${poId}/items`, item)
    return response.data
  },

  /**
   * 발주서 항목 수정
   */
  async updateItem(poId: number, itemId: number, item: PurchaseOrderItemUpdate): Promise<PurchaseOrder> {
    const response = await apiClient.put(`/purchase-orders/${poId}/items/${itemId}`, item)
    return response.data
  },

  /**
   * 발주서 항목 삭제
   */
  async deleteItem(poId: number, itemId: number): Promise<PurchaseOrder> {
    const response = await apiClient.delete(`/purchase-orders/${poId}/items/${itemId}`)
    return response.data
  },

  // ==================== 상태 전이 ====================

  /**
   * 주문 확정 (DRAFT → ORDERED)
   */
  async order(id: number): Promise<PurchaseOrder> {
    const response = await apiClient.post(`/purchase-orders/${id}/order`)
    return response.data
  },

  /**
   * 납기 확정 (ORDERED → CONFIRMED)
   */
  async confirm(id: number, data: ConfirmDeliveryRequest): Promise<PurchaseOrder> {
    const response = await apiClient.post(`/purchase-orders/${id}/confirm`, data)
    return response.data
  },

  /**
   * 입고 처리 (→ RECEIVED)
   * 입고된 수량만큼 재고가 자동으로 증가합니다.
   */
  async receive(id: number, data: ReceiveRequest): Promise<PurchaseOrder> {
    const response = await apiClient.post(`/purchase-orders/${id}/receive`, data)
    return response.data
  },

  /**
   * 상태 롤백 (이전 상태로 되돌리기)
   * - ORDERED -> DRAFT
   * - CONFIRMED -> ORDERED
   * - RECEIVED -> CONFIRMED (재고 차감)
   */
  async rollback(id: number, reason?: string): Promise<PurchaseOrder> {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
    const response = await apiClient.post(`/purchase-orders/${id}/rollback${params}`)
    return response.data
  },

  /**
   * 발주 취소
   */
  async cancel(id: number, reason?: string): Promise<PurchaseOrder> {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
    const response = await apiClient.post(`/purchase-orders/${id}/cancel${params}`)
    return response.data
  },

  /**
   * 결제 상태 변경
   */
  async updatePayment(id: number, data: PaymentRequest): Promise<PurchaseOrder> {
    const response = await apiClient.patch(`/purchase-orders/${id}/payment`, data)
    return response.data
  },

  // 발주서 발송 완료/취소 (발송일 기록)
  async markSent(id: number, sent: boolean): Promise<PurchaseOrder> {
    const response = await apiClient.post(`/purchase-orders/${id}/mark-sent`, { sent })
    return response.data
  },

  // 선택한 여러 발주서를 하나의 지출결의서(임시저장)로 묶어 생성
  async createDisbursement(poIds: number[]): Promise<{ id: number; doc_number?: string; title?: string }> {
    const response = await apiClient.post('/purchase-orders/disbursement', { po_ids: poIds })
    return response.data
  },

  // ==================== 파일 첨부 ====================

  /**
   * 문서 파일 업로드
   */
  async uploadDocument(poId: number, file: File): Promise<PurchaseOrder> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post(`/purchase-orders/${poId}/upload/document`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  /**
   * 문서 파일 삭제
   */
  async deleteDocument(poId: number, fileIndex: number): Promise<PurchaseOrder> {
    const response = await apiClient.delete(`/purchase-orders/${poId}/files/${fileIndex}`)
    return response.data
  },

  /**
   * 부품별 이전 구매 가격 조회
   * 최근 구매 이력을 반환합니다.
   */
  async getPartPriceHistory(partId: number, limit: number = 5): Promise<{ unit_price: number; order_date: string; supplier_name: string }[]> {
    try {
      const response = await apiClient.get(`/purchase-orders/parts/${partId}/price-history?limit=${limit}`)
      return response.data
    } catch (e) {
      // API가 없으면 빈 배열 반환
      return []
    }
  },

  // ==================== PDF 다운로드 ====================

  /**
   * 발주서 PDF 다운로드
   * PDF 파일을 생성하여 다운로드합니다.
   * @param poId 발주서 ID
   * @param poNumber 발주번호 (파일명에 사용, 선택적)
   */
  async downloadPDF(poId: number, poNumber?: string): Promise<void> {
    const response = await apiClient.get(`/purchase-orders/${poId}/pdf`, {
      responseType: 'blob',
    })

    // Content-Disposition 헤더에서 파일명 추출
    const contentDisposition = response.headers['content-disposition']
    let filename = poNumber ? `발주서_${poNumber}.pdf` : `발주서_${poId}.pdf`
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename\*=UTF-8''(.+)/)
      if (filenameMatch) {
        filename = decodeURIComponent(filenameMatch[1])
      }
    }

    // Blob 다운로드
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
}

// 발주서 상태 한글 변환
export const poStatusLabels: Record<PurchaseOrderStatus, string> = {
  DRAFT: '작성중',
  ORDERED: '주문완료',
  CONFIRMED: '납기확정',
  RECEIVED: '입고완료',
  COMPLETED: '완료(구)', // 기존 데이터 호환용
  CANCELLED: '취소',
}

// 발주서 상태별 스타일 클래스
export const poStatusStyles: Record<PurchaseOrderStatus, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  ORDERED: 'bg-blue-100 text-blue-800',
  CONFIRMED: 'bg-indigo-100 text-indigo-800',
  RECEIVED: 'bg-green-100 text-green-800',
  COMPLETED: 'bg-purple-100 text-purple-800', // 기존 데이터 호환용
  CANCELLED: 'bg-red-100 text-red-800',
}
