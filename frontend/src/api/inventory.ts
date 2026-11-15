/**
 * 재고관리 API 서비스
 *
 * v0.5.0: 재고관리 기능 추가
 * - 재고 조회/조정
 * - 입출고 기록 (거래 이력)
 * - 부족 재고 알림
 */

import apiClient from './client'

// 부품 간략 정보 (재고 응답용)
export interface PartInfo {
  id: number
  part_number: string
  part_number_display?: string
  part_name: string
  part_name_en?: string
  specification?: string
}

// 재고 상태
export type InventoryStatus = 'NORMAL' | 'LOW' | 'EXCESS' | 'OUT_OF_STOCK'

// 거래 유형
export type TransactionType = 'IN' | 'OUT' | 'ADJUST' | 'RETURN' | 'COUNT'

// 재고 인터페이스
export interface Inventory {
  id: number
  part_id: number
  quantity_on_hand: number
  quantity_reserved?: number
  quantity_available?: number
  reorder_point?: number
  reorder_qty?: number
  warehouse_location_id?: number
  unit_cost?: number
  status: InventoryStatus
  last_count_date?: string
  remarks?: string
  is_active: boolean
  created_at: string
  updated_at?: string
  part?: PartInfo
}

// 재고 목록 (간략)
export interface InventoryListItem {
  id: number
  part_id: number
  quantity_on_hand: number
  reorder_point?: number
  unit_cost?: number
  status: InventoryStatus
  updated_at?: string
  part?: PartInfo
}

// 재고 생성 DTO
export interface InventoryCreate {
  part_id: number
  quantity_on_hand?: number
  reorder_point?: number
  reorder_qty?: number
  unit_cost?: number
  remarks?: string
}

// 재고 수정 DTO
export interface InventoryUpdate {
  reorder_point?: number
  reorder_qty?: number
  unit_cost?: number
  remarks?: string
}

// 재고 조정 DTO
export interface InventoryAdjust {
  quantity: number
  transaction_type: TransactionType
  reason?: string
  reference_type?: string
  reference_id?: string
  remarks?: string
  // 로트 생성 옵션 (입고 시 사용)
  create_lot?: boolean
  lot_number?: string
  unit_cost?: number
}

// 첨부 파일 정보
export interface DocumentFile {
  file_name: string
  file_path: string
  file_size: number
  content_type: string
  uploaded_at?: string
}

// 거래 이력 인터페이스
export interface InventoryTransaction {
  id: number
  inventory_id?: number
  part_id: number
  transaction_type: TransactionType
  quantity: number
  quantity_before?: number
  quantity_after?: number
  reference_type?: string
  reference_id?: string
  reason?: string
  remarks?: string
  transaction_date: string
  created_by?: number
  created_at: string
  part?: PartInfo
  document_files?: DocumentFile[]
}

// 검색 파라미터
export interface InventorySearchParams {
  keyword?: string
  status?: InventoryStatus
  low_stock_only?: boolean
  product_line_id?: number
  part_group_id?: number
  level_id?: number
  skip?: number
  limit?: number
  order_by?: string
  order_desc?: boolean
}

// 거래 이력 검색 파라미터
export interface TransactionSearchParams {
  transaction_type?: TransactionType
  skip?: number
  limit?: number
}

// 페이지네이션 응답
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

// 재고 API 서비스
export const inventoryApi = {
  /**
   * 재고 목록 조회
   */
  async getAll(params: InventorySearchParams = {}): Promise<PaginatedResponse<InventoryListItem>> {
    const queryParams = new URLSearchParams()

    if (params.keyword) queryParams.append('keyword', params.keyword)
    if (params.status) queryParams.append('status', params.status)
    if (params.low_stock_only) queryParams.append('low_stock_only', 'true')
    if (params.product_line_id) queryParams.append('product_line_id', String(params.product_line_id))
    if (params.part_group_id) queryParams.append('part_group_id', String(params.part_group_id))
    if (params.level_id) queryParams.append('level_id', String(params.level_id))
    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    if (params.limit !== undefined) queryParams.append('limit', String(params.limit))
    if (params.order_by) queryParams.append('order_by', params.order_by)
    if (params.order_desc !== undefined) queryParams.append('order_desc', String(params.order_desc))

    const response = await apiClient.get(`/inventory?${queryParams.toString()}`)
    return response.data
  },

  /**
   * 재고 상세 조회
   */
  async getById(id: number): Promise<Inventory> {
    const response = await apiClient.get(`/inventory/${id}`)
    return response.data
  },

  /**
   * 부품 ID로 재고 조회
   */
  async getByPartId(partId: number): Promise<Inventory> {
    const response = await apiClient.get(`/inventory/part/${partId}`)
    return response.data
  },

  /**
   * 부족 재고 목록 조회
   */
  async getLowStock(limit: number = 100): Promise<InventoryListItem[]> {
    const response = await apiClient.get(`/inventory/low-stock?limit=${limit}`)
    return response.data
  },

  /**
   * 재고 없음 목록 조회
   */
  async getOutOfStock(limit: number = 100): Promise<InventoryListItem[]> {
    const response = await apiClient.get(`/inventory/out-of-stock?limit=${limit}`)
    return response.data
  },

  /**
   * 재고 생성
   */
  async create(data: InventoryCreate): Promise<Inventory> {
    const response = await apiClient.post('/inventory', data)
    return response.data
  },

  /**
   * 재고 정보 수정 (재주문점, 단가 등)
   */
  async update(id: number, data: InventoryUpdate): Promise<Inventory> {
    const response = await apiClient.put(`/inventory/${id}`, data)
    return response.data
  },

  /**
   * 재고 조정 (입고/출고/조정)
   */
  async adjust(id: number, data: InventoryAdjust): Promise<Inventory> {
    const response = await apiClient.post(`/inventory/${id}/adjust`, data)
    return response.data
  },

  /**
   * 재고 삭제
   */
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/inventory/${id}`)
  },

  /**
   * 재고 ID로 거래 이력 조회
   */
  async getTransactions(
    inventoryId: number,
    params: TransactionSearchParams = {}
  ): Promise<PaginatedResponse<InventoryTransaction>> {
    const queryParams = new URLSearchParams()

    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    if (params.limit !== undefined) queryParams.append('limit', String(params.limit))

    const response = await apiClient.get(`/inventory/${inventoryId}/transactions?${queryParams.toString()}`)
    return response.data
  },

  /**
   * 부품 ID로 거래 이력 조회
   */
  async getTransactionsByPart(
    partId: number,
    params: TransactionSearchParams = {}
  ): Promise<PaginatedResponse<InventoryTransaction>> {
    const queryParams = new URLSearchParams()

    if (params.transaction_type) queryParams.append('transaction_type', params.transaction_type)
    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    if (params.limit !== undefined) queryParams.append('limit', String(params.limit))

    const response = await apiClient.get(`/inventory/part/${partId}/transactions?${queryParams.toString()}`)
    return response.data
  },

  /**
   * 엑셀 내보내기 URL 생성
   */
  getExportExcelUrl(params: InventorySearchParams = {}): string {
    const baseUrl = apiClient.defaults.baseURL || ''
    const queryParams = new URLSearchParams()

    if (params.keyword) queryParams.append('keyword', params.keyword)
    if (params.status) queryParams.append('status', params.status)
    if (params.low_stock_only) queryParams.append('low_stock_only', 'true')

    return `${baseUrl}/inventory/export/excel?${queryParams.toString()}`
  },

  /**
   * 거래 이력 파일 업로드
   */
  async uploadTransactionDocument(transactionId: number, file: File): Promise<InventoryTransaction> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post(`/inventory/transactions/${transactionId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  /**
   * 거래 이력 파일 삭제
   */
  async deleteTransactionDocument(transactionId: number, fileIndex: number): Promise<InventoryTransaction> {
    const response = await apiClient.delete(`/inventory/transactions/${transactionId}/files/${fileIndex}`)
    return response.data
  },
}

// 거래 유형 한글 변환
export const transactionTypeLabels: Record<TransactionType, string> = {
  IN: '입고',
  OUT: '출고',
  ADJUST: '조정',
  RETURN: '반품',
  COUNT: '실사',
}

// 재고 상태 한글 변환
export const inventoryStatusLabels: Record<InventoryStatus, string> = {
  NORMAL: '정상',
  LOW: '부족',
  EXCESS: '과잉',
  OUT_OF_STOCK: '재고없음',
}

// 재고 상태별 스타일 클래스
export const inventoryStatusStyles: Record<InventoryStatus, string> = {
  NORMAL: 'bg-green-100 text-green-800',
  LOW: 'bg-yellow-100 text-yellow-800',
  EXCESS: 'bg-blue-100 text-blue-800',
  OUT_OF_STOCK: 'bg-red-100 text-red-800',
}
