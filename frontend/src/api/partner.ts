/**
 * 거래처 관리 API 서비스
 * 공급업체와 고객사를 통합 관리합니다.
 */

import apiClient from './client'

// 파일 정보 인터페이스
export interface FileInfo {
  file_name: string
  original_name: string
  file_type: string
  file_size: number
  file_path: string
  uploaded_at: string
  download_url: string
  preview_url: string
}

// 거래처 인터페이스
export interface BusinessPartner {
  id: number
  partner_code: string
  partner_name: string
  partner_name_en?: string
  business_number?: string
  representative?: string
  business_type?: string
  business_item?: string
  is_supplier: boolean
  is_customer: boolean
  trade_type?: string
  country_code?: string
  country_name?: string
  business_start_year?: number
  address?: string
  address_detail?: string
  postal_code?: string
  tel?: string
  fax?: string
  email?: string
  website?: string
  manager_name?: string
  manager_position?: string
  manager_tel?: string
  manager_mobile?: string
  manager_email?: string
  payment_terms?: string
  delivery_terms?: string
  lead_time_days?: number
  credit_limit?: number
  discount_rate?: number
  sales_rep?: string
  credit_rating?: string
  grade?: string
  bank_name?: string
  bank_account?: string
  bank_holder?: string
  default_margin_rate?: number
  show_statement_of_origin?: boolean
  default_shipping_mark?: string
  default_consignee?: string
  default_destination?: string
  remark?: string
  document_files?: FileInfo[]
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface BusinessPartnerListItem {
  id: number
  partner_code: string
  partner_name: string
  partner_name_en?: string
  is_supplier: boolean
  is_customer: boolean
  tel?: string
  manager_name?: string
  is_active: boolean
  created_at: string
}

export interface BusinessPartnerCreate {
  partner_code: string
  partner_name: string
  partner_name_en?: string
  business_number?: string
  representative?: string
  business_type?: string
  business_item?: string
  is_supplier?: boolean
  is_customer?: boolean
  trade_type?: string
  country_code?: string
  country_name?: string
  business_start_year?: number
  address?: string
  address_detail?: string
  postal_code?: string
  tel?: string
  fax?: string
  email?: string
  website?: string
  manager_name?: string
  manager_position?: string
  manager_tel?: string
  manager_mobile?: string
  manager_email?: string
  payment_terms?: string
  delivery_terms?: string
  lead_time_days?: number
  credit_limit?: number
  discount_rate?: number
  sales_rep?: string
  credit_rating?: string
  grade?: string
  bank_name?: string
  bank_account?: string
  bank_holder?: string
  default_margin_rate?: number
  show_statement_of_origin?: boolean
  default_shipping_mark?: string
  default_consignee?: string
  default_destination?: string
  remark?: string
  is_active?: boolean
}

export interface BusinessPartnerUpdate extends Partial<BusinessPartnerCreate> {}

// Partner 타입 alias (호환성 유지)
export type Partner = BusinessPartner

// 재주문 패널용
// 담당자 인터페이스 (v0.31.0)
export interface PartnerContact {
  id: number
  partner_id: number
  name: string
  position?: string
  role?: string  // PURCHASING / TECHNICAL / SALES / GENERAL
  email?: string
  tel_office?: string
  tel_mobile?: string
  is_primary: boolean
  sort_order: number
  notes?: string
  created_at: string
  updated_at?: string
}

export interface PartnerContactCreate {
  name: string
  position?: string
  role?: string
  email?: string
  tel_office?: string
  tel_mobile?: string
  is_primary?: boolean
  sort_order?: number
  notes?: string
}

export interface PartnerShippingAddress {
  id: number
  partner_id: number
  label?: string
  name?: string
  address?: string
  contact?: string
  phone?: string
  email?: string
  is_default: boolean
  sort_order: number
  created_at?: string
}

export interface PartnerShippingAddressCreate {
  label?: string
  name?: string
  address?: string
  contact?: string
  phone?: string
  email?: string
  is_default?: boolean
  sort_order?: number
}

export const CONTACT_ROLE_LABELS: Record<string, string> = {
  PURCHASING: '구매 담당',
  TECHNICAL: '기술 담당',
  SALES: '영업 담당',
  GENERAL: '일반',
}

export interface RecentOrderDocument {
  id: number
  document_type: string
  document_number: string
  document_date?: string
  total_amount: number
  currency: string
  status: string
  payment_status?: string
  representative_product?: string
  item_count: number
}

// 거래처 메모 (v0.32.0)
export interface PartnerNote {
  id: number
  partner_id: number
  note_type: string
  content: string
  is_pinned: boolean
  created_by?: string
  created_at: string
  updated_at?: string
}

export interface PartnerNoteCreate {
  note_type?: string
  content: string
  is_pinned?: boolean
  created_by?: string
}

export const NOTE_TYPE_LABELS: Record<string, string> = {
  GENERAL: '일반',
  STRATEGY: '전략',
  RISK: '주의',
  MEETING: '미팅',
  INTERNAL: '내부',
}

export const NOTE_TYPE_COLORS: Record<string, string> = {
  GENERAL: 'bg-gray-100 text-gray-700',
  STRATEGY: 'bg-blue-100 text-blue-700',
  RISK: 'bg-red-100 text-red-700',
  MEETING: 'bg-green-100 text-green-700',
  INTERNAL: 'bg-yellow-100 text-yellow-700',
}

// 통합 타임라인 (v0.32.0)
export interface TimelineItem {
  type: 'NOTE' | 'ACTIVITY_LOG' | 'DOCUMENT'
  content: string
  created_by?: string
  created_at?: string
  ref_id?: number
  // NOTE
  note_type?: string
  is_pinned?: boolean
  // ACTIVITY_LOG
  log_type?: string
  ref_title?: string
  // DOCUMENT
  doc_type?: string
  doc_number?: string
  doc_status?: string
  total_amount?: number
  currency?: string
}

// 선불 잔액 (v0.32.0)
export interface PartnerBalanceTransaction {
  id: number
  type: string
  amount: number
  currency: string
  balance_after: number
  reference_doc_number?: string
  reference_doc_id?: number
  memo?: string
  created_by?: string
  created_at?: string
}

export interface PartnerBalance {
  partner_id: number
  current_balance: number
  currency: string
  transactions: PartnerBalanceTransaction[]
}

export interface BusinessPartnerSearchParams {
  keyword?: string
  partner_type?: string
  is_supplier?: boolean
  is_customer?: boolean
  is_active?: boolean
  skip?: number
  limit?: number
  order_by?: string
  order_desc?: boolean
}

// 페이지네이션 응답 인터페이스
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

// 엑셀 업로드 결과 인터페이스
export interface ExcelUploadResultItem {
  row: number
  partner_code: string
  partner_id?: number
  status: 'success' | 'updated' | 'failed'
  message: string
}

export interface ExcelUploadResponse {
  success: boolean
  summary: {
    total: number
    success_count: number
    updated_count: number
    failed_count: number
  }
  results: ExcelUploadResultItem[]
}

// API 서비스
export const partnerApi = {
  /**
   * 거래처 목록 조회 (페이지네이션)
   */
  getAll: (params?: BusinessPartnerSearchParams) => {
    return apiClient.get<PaginatedResponse<BusinessPartnerListItem>>('/partners', { params })
  },

  /**
   * 거래처 단건 조회
   */
  getById: (id: number) => {
    return apiClient.get<BusinessPartner>(`/partners/${id}`)
  },

  /**
   * 거래처 코드로 조회
   */
  getByCode: (code: string) => {
    return apiClient.get<BusinessPartner>(`/partners/code/${code}`)
  },

  /**
   * 거래처 생성
   */
  create: (data: BusinessPartnerCreate) => {
    return apiClient.post<BusinessPartner>('/partners', data)
  },

  /**
   * 거래처 수정
   */
  update: (id: number, data: BusinessPartnerUpdate) => {
    return apiClient.put<BusinessPartner>(`/partners/${id}`, data)
  },

  /**
   * 거래처 삭제
   */
  delete: (id: number) => {
    return apiClient.delete(`/partners/${id}`)
  },

  /**
   * 거래처 활성화
   */
  activate: (id: number) => {
    return apiClient.patch<BusinessPartner>(`/partners/${id}/activate`)
  },

  /**
   * 거래처 비활성화
   */
  deactivate: (id: number) => {
    return apiClient.patch<BusinessPartner>(`/partners/${id}/deactivate`)
  },

  /**
   * 거래처 파일 업로드
   */
  uploadDocument: (partnerId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/partners/${partnerId}/upload/document`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  /**
   * 거래처 파일 목록 조회
   */
  getFiles: (partnerId: number) => {
    return apiClient.get(`/partners/${partnerId}/files`)
  },

  /**
   * 거래처 파일 삭제
   */
  deleteFile: (partnerId: number, fileIndex: number) => {
    return apiClient.delete(`/partners/${partnerId}/files/${fileIndex}`)
  },

  /**
   * 엑셀 내보내기 URL 생성
   * 운영(Caddy 프록시): 같은 origin /api/v1 사용
   * 개발(:5174/:5175): http://hostname:8001/api/v1 사용
   */
  getExportExcelUrl: (params?: BusinessPartnerSearchParams): string => {
    const frontendPort = window.location.port
    let baseUrl: string
    if (frontendPort === '5174' || frontendPort === '5175') {
      // 개발 환경
      baseUrl = `http://${window.location.hostname}:8001/api/v1/partners/export/excel`
    } else {
      // 운영 환경 (Caddy 프록시) - 같은 origin
      baseUrl = `${window.location.origin}/api/v1/partners/export/excel`
    }
    if (!params) return baseUrl
    const searchParams = new URLSearchParams()
    if (params.keyword) searchParams.append('keyword', params.keyword)
    if (params.is_supplier !== undefined) searchParams.append('is_supplier', String(params.is_supplier))
    if (params.is_customer !== undefined) searchParams.append('is_customer', String(params.is_customer))
    if (params.is_active !== undefined) searchParams.append('is_active', String(params.is_active))
    if (params.order_by) searchParams.append('order_by', params.order_by)
    if (params.order_desc !== undefined) searchParams.append('order_desc', String(params.order_desc))
    const queryString = searchParams.toString()
    return queryString ? `${baseUrl}?${queryString}` : baseUrl
  },

  // ==================== 담당자 관리 (v0.31.0) ====================

  getContacts: (partnerId: number) =>
    apiClient.get<PartnerContact[]>(`/partners/${partnerId}/contacts`),

  createContact: (partnerId: number, data: PartnerContactCreate) =>
    apiClient.post<PartnerContact>(`/partners/${partnerId}/contacts`, data),

  updateContact: (partnerId: number, contactId: number, data: Partial<PartnerContactCreate>) =>
    apiClient.put<PartnerContact>(`/partners/${partnerId}/contacts/${contactId}`, data),

  deleteContact: (partnerId: number, contactId: number) =>
    apiClient.delete(`/partners/${partnerId}/contacts/${contactId}`),

  // ==================== 배송지 관리 (v0.58.0) ====================

  getShippingAddresses: (partnerId: number) =>
    apiClient.get<PartnerShippingAddress[]>(`/partners/${partnerId}/shipping-addresses`),

  createShippingAddress: (partnerId: number, data: PartnerShippingAddressCreate) =>
    apiClient.post<PartnerShippingAddress>(`/partners/${partnerId}/shipping-addresses`, data),

  updateShippingAddress: (partnerId: number, addressId: number, data: Partial<PartnerShippingAddressCreate>) =>
    apiClient.put<PartnerShippingAddress>(`/partners/${partnerId}/shipping-addresses/${addressId}`, data),

  deleteShippingAddress: (partnerId: number, addressId: number) =>
    apiClient.delete(`/partners/${partnerId}/shipping-addresses/${addressId}`),

  /**
   * 거래처 최근 주문 이력 조회 (재주문 패널용)
   */
  getRecentOrders: (partnerId: number, limit = 10) =>
    apiClient.get<{
      partner_id: number
      documents: RecentOrderDocument[]
    }>(`/partners/${partnerId}/recent-orders`, { params: { limit } }),

  /**
   * 재주문 영업활동 자동 생성
   */
  createReorder: (partnerId: number, sourceDocId: number) =>
    apiClient.post<{
      activity_id: number
      source_document_id: number
      source_document_type: string
      source_document_number: string
      customer_id: number
    }>(`/partners/${partnerId}/reorder/${sourceDocId}`),

  // ==================== 메모 관리 (v0.32.0) ====================

  getNotes: (partnerId: number) =>
    apiClient.get<PartnerNote[]>(`/partners/${partnerId}/notes`),

  createNote: (partnerId: number, data: PartnerNoteCreate) =>
    apiClient.post<PartnerNote>(`/partners/${partnerId}/notes`, data),

  updateNote: (partnerId: number, noteId: number, data: Partial<PartnerNoteCreate>) =>
    apiClient.put<PartnerNote>(`/partners/${partnerId}/notes/${noteId}`, data),

  deleteNote: (partnerId: number, noteId: number) =>
    apiClient.delete(`/partners/${partnerId}/notes/${noteId}`),

  // ==================== 선불 잔액 관리 (v0.32.0) ====================

  getBalance: (partnerId: number) =>
    apiClient.get<PartnerBalance>(`/partners/${partnerId}/balance`),

  depositBalance: (partnerId: number, amount: number, currency = 'USD', memo = '') =>
    apiClient.post(`/partners/${partnerId}/balance/deposit?amount=${amount}&currency=${currency}&memo=${encodeURIComponent(memo)}`),

  deductBalance: (partnerId: number, amount: number, currency = 'USD', refDocNumber = '', refDocId?: number, memo = '') => {
    const params = new URLSearchParams({ amount: String(amount), currency, memo })
    if (refDocNumber) params.append('reference_doc_number', refDocNumber)
    if (refDocId) params.append('reference_doc_id', String(refDocId))
    return apiClient.post(`/partners/${partnerId}/balance/deduct?${params.toString()}`)
  },

  // ==================== 통합 타임라인 (v0.32.0) ====================

  getTimeline: (partnerId: number, limit = 50) =>
    apiClient.get<{ partner_id: number; items: TimelineItem[] }>(`/partners/${partnerId}/timeline`, { params: { limit } }),

  /**
   * 거래처 엑셀 업로드
   */
  uploadExcel: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<ExcelUploadResponse>('/partners/upload/excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

// 파일 관련 유틸리티 - 환경별 API URL
// 운영(Caddy 프록시): 같은 origin /api/v1 사용
// 개발(:5174/:5175): http://hostname:8001/api/v1 사용
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  const frontendPort = window.location.port
  if (frontendPort === '5174' || frontendPort === '5175') {
    return `http://${window.location.hostname}:8001/api/v1`
  }
  return `${window.location.origin}/api/v1`
}

export const partnerFileApi = {
  getDownloadUrl: (filePath: string): string => {
    return `${getApiBaseUrl()}/files/${filePath}`
  },
  getPreviewUrl: (filePath: string): string => {
    return `${getApiBaseUrl()}/files/${filePath}?preview=true`
  },
  isImageFile: (fileName: string): boolean => {
    const ext = fileName.toLowerCase().split('.').pop()
    return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext || '')
  },
  isPdfFile: (fileName: string): boolean => {
    return fileName.toLowerCase().endsWith('.pdf')
  },
  formatFileSize: (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  },
}
