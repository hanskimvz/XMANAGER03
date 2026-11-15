/**
 * 재고 로트 API 서비스 (v0.7.0)
 *
 * 로트 관리, FIFO 출고, 생산가능수량 체크 관련 API
 */

import apiClient from './client'

// 로트 상태
export type LotStatus = 'ACTIVE' | 'DEPLETED' | 'EXPIRED'

// 공급업체 간략 정보
export interface SupplierInfo {
  id: number
  partner_code: string
  partner_name: string
}

// 로트 정보
export interface InventoryLot {
  id: number
  part_id: number
  lot_number: string
  quantity_received: number
  quantity_on_hand: number
  quantity_issued: number
  received_date: string
  expiry_date?: string
  supplier_lot_number?: string
  unit_cost?: number
  status: LotStatus
  purchase_order_id?: number
  supplier_id?: number
  supplier?: SupplierInfo  // 공급업체 정보
  remarks?: string
  created_at?: string
  updated_at?: string
}

// 로트 생성 DTO
export interface InventoryLotCreate {
  part_id: number
  lot_number: string
  quantity_received: number
  received_date?: string
  expiry_date?: string
  supplier_lot_number?: string
  unit_cost?: number
  purchase_order_id?: number
  supplier_id?: number
  warehouse_location_id?: number
  remarks?: string
}

// 로트 수정 DTO
export interface InventoryLotUpdate {
  expiry_date?: string
  supplier_lot_number?: string
  warehouse_location_id?: number
  remarks?: string
}

// FIFO 출고 제안 로트
export interface FIFOLotSuggestion {
  lot_id: number
  lot_number: string
  received_date: string
  available_quantity: number
  suggested_quantity: number
  expiry_date?: string
  unit_cost?: number
  supplier_name?: string  // 공급업체명
}

// FIFO 출고 제안 응답
export interface FIFOSuggestionResponse {
  part_id: number
  requested_quantity: number
  is_sufficient: boolean
  total_available: number
  shortage: number
  lots: FIFOLotSuggestion[]
}

// BOM 항목별 가용수량
export interface BOMItemAvailability {
  part_id: number
  part_number: string
  part_name: string
  required_per_unit: number
  required_quantity: number
  available_quantity: number
  shortage: number
  status: 'SUFFICIENT' | 'INSUFFICIENT' | 'OUT_OF_STOCK'
}

// 제한 부품 (병목)
export interface LimitingPart {
  part_id: number
  part_number: string
  part_name: string
  required_per_unit: number
  available_quantity: number
  can_produce: number
}

// 생산 가용수량 응답
export interface ProductionAvailabilityResponse {
  product_part_id: number
  requested_quantity: number
  can_produce: number
  limiting_parts: LimitingPart[]
  items: BOMItemAvailability[]
}

// 로트별 출고 항목
export interface LotIssueItem {
  lot_id: number
  quantity: number
}

// 작업지시서 항목 출고 요청
export interface WorkOrderItemIssueRequest {
  item_id: number
  issue_quantity: number
  use_fifo: boolean
  lot_selections?: LotIssueItem[]
}

// 작업지시서 출고 요청
export interface WorkOrderIssueRequest {
  items: WorkOrderItemIssueRequest[]
}

// 출고 기록
export interface WorkOrderItemIssueRecord {
  id: number
  work_order_item_id: number
  lot_id?: number
  lot_number?: string
  quantity: number
  issue_date: string
  returned_quantity: number
}

// 페이지네이션 응답
export interface PaginatedLotResponse {
  items: InventoryLot[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

// 로트 API 서비스
export const inventoryLotApi = {
  /**
   * 로트 목록 조회 (페이지네이션)
   */
  async getAll(params: {
    part_id?: number
    status?: LotStatus
    skip?: number
    limit?: number
  } = {}): Promise<PaginatedLotResponse> {
    const queryParams = new URLSearchParams()
    if (params.part_id) queryParams.append('part_id', String(params.part_id))
    if (params.status) queryParams.append('status', params.status)
    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    if (params.limit !== undefined) queryParams.append('limit', String(params.limit))

    const response = await apiClient.get(`/inventory/lots?${queryParams.toString()}`)
    return response.data
  },

  /**
   * 부품별 로트 목록 조회 (FIFO 순)
   */
  async getByPart(partId: number, includeDepleted: boolean = false): Promise<InventoryLot[]> {
    const response = await apiClient.get(`/inventory/${partId}/lots?include_depleted=${includeDepleted}`)
    return response.data
  },

  /**
   * FIFO 출고 제안 조회
   */
  async getFIFOSuggestion(partId: number, quantity: number): Promise<FIFOSuggestionResponse> {
    const response = await apiClient.get(`/inventory/${partId}/lots/available?quantity=${quantity}`)
    return response.data
  },

  /**
   * 로트 생성
   */
  async create(data: InventoryLotCreate): Promise<InventoryLot> {
    const response = await apiClient.post('/inventory/lots', data)
    return response.data
  },

  /**
   * 로트 상세 조회
   */
  async getById(lotId: number): Promise<InventoryLot> {
    const response = await apiClient.get(`/inventory/lots/${lotId}`)
    return response.data
  },

  /**
   * 로트 수정
   */
  async update(lotId: number, data: InventoryLotUpdate): Promise<InventoryLot> {
    const response = await apiClient.put(`/inventory/lots/${lotId}`, data)
    return response.data
  },

  /**
   * 로트 삭제 (소진된 로트만)
   */
  async delete(lotId: number): Promise<void> {
    await apiClient.delete(`/inventory/lots/${lotId}`)
  },

  /**
   * 누락된 로트 자동 생성
   * 재고가 있지만 로트가 없는 부품에 대해 초기 로트를 생성합니다.
   */
  async generateMissingLots(): Promise<{
    message: string
    created_count: number
    skipped_count: number
    details: Array<{
      part_id: number
      part_number: string
      part_name: string
      lot_number: string
      quantity: number
    }>
  }> {
    const response = await apiClient.post('/inventory/lots/generate-missing')
    return response.data
  },
}

// 작업지시서 로트 출고 API
export const workOrderLotApi = {
  /**
   * 생산 가용수량 체크
   */
  async checkAvailability(productPartId: number, quantity: number): Promise<ProductionAvailabilityResponse> {
    const response = await apiClient.get(`/work-orders/check-availability?product_part_id=${productPartId}&quantity=${quantity}`)
    return response.data
  },

  /**
   * 로트 선택 부품 출고
   */
  async issueWithLots(woId: number, request: WorkOrderIssueRequest): Promise<any> {
    const response = await apiClient.post(`/work-orders/${woId}/issue-with-lots`, request)
    return response.data
  },

  /**
   * 항목별 출고 기록 조회
   */
  async getIssueRecords(woId: number, itemId: number): Promise<WorkOrderItemIssueRecord[]> {
    const response = await apiClient.get(`/work-orders/${woId}/items/${itemId}/issue-records`)
    return response.data
  },
}
