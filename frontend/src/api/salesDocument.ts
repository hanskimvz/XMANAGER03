/**
 * 영업 문서 API 서비스
 * Quotation / PI / CI 관리
 */

import apiClient from './client'

// ==================== 인터페이스 ====================

export interface SalesDocumentItem {
  id?: number
  document_id?: number
  line_no: number
  product_code: string
  description?: string
  quantity: number
  quantity_text?: string | null
  uom: string
  unit_price: number
  unit_price_text?: string | null
  amount: number
  amount_text?: string | null
  currency: string
  line_remarks?: string
}

export interface CustomerBrief {
  id: number
  partner_code: string
  partner_name: string
  partner_name_en?: string
  short_code?: string
  country_code?: string  // ISO 3166-1 (KR / US / CN ...) — PDF 언어 필터링용
  country_name?: string
  trade_type?: string  // DOMESTIC / EXPORT
}

export interface SalesDocument {
  id: number
  document_type: string
  document_number: string
  document_date: string
  version?: number
  is_latest?: boolean
  is_moq?: boolean
  is_quote_only?: boolean
  version_group?: string
  source_document_id?: number
  customer_id: number
  customer_contact_id?: number | null
  prepared_by?: string
  prepared_email?: string
  customer_po_number?: string
  customer_po_date?: string
  po_attachment_files?: PoAttachmentFile[]
  shipping_invoice_files?: ShippingInvoiceFile[]
  sales_activity_id?: number
  payment_terms?: string
  delivery_terms?: string
  incoterms?: string
  freight_per_box?: number | string | null
  show_customer_tax_id?: boolean
  hs_code?: string
  country_of_origin?: string
  valid_until?: string
  bank_name?: string
  bank_address?: string
  swift_code?: string
  account_name?: string
  account_number?: string
  ship_to_name?: string
  ship_to_address?: string
  ship_to_contact?: string
  ship_to_phone?: string
  ship_to_email?: string
  ship_from?: string
  destination?: string
  transportation?: string
  shipment_date?: string
  packaging_boxes?: number
  packaging_dimensions?: string
  packaging_gross_weight?: number
  packaging_net_weight?: number
  packing_list?: Array<{ box_type?: string; quantity?: number; gross_weight?: number; net_weight?: number; length?: number; width?: number; height?: number; remarks?: string }>
  total_amount: number
  currency: string
  discount_amount?: number | null
  discount_reason?: string | null
  shipping_fee?: number | null
  status: string
  payment_status?: string
  paid_amount?: number
  paid_date?: string
  payment_remarks?: string
  remarks?: string
  created_at: string
  updated_at?: string
  customer?: CustomerBrief
  source_document?: { id: number; document_type: string; document_number: string; status: string }
  items: SalesDocumentItem[]
  // v0.31.0: 목록 표시용 (목록 API에서 자동 채움)
  representative_product?: string
  item_count?: number
  // PI 생산 진행 집계 (집계 A: 병목 기준) — 목록 API에서 PI만 채움
  production_progress?: ProductionProgress | null
}

// PI 진행 스텝퍼용 집계 (생산=1 / 출고=2 / 배송=3, stage=병목/현재)
export interface ProductionProgress {
  pr_total: number
  stage: 1 | 2 | 3
  counts: { prod: number; ship: number; deliv: number }
}

export interface SalesDocumentListResponse {
  items: SalesDocument[]
  total: number
  skip: number
  limit: number
}

export interface CustomerDefaults {
  customer_id: number
  partner_name: string
  partner_name_en?: string
  short_code?: string
  trade_type?: string
  payment_terms?: string
  delivery_terms?: string
  incoterms?: string
  freight_per_box?: number | null
  show_customer_tax_id?: boolean
  hs_code?: string
  default_margin_rate?: number
  bank_name?: string
  bank_address?: string
  swift_code?: string
  account_name?: string
  account_number?: string
  address?: string
  address_detail?: string
  manager_name?: string
  manager_email?: string
  tel?: string
  country_name?: string
}

export interface DescriptionComposeResponse {
  order_code: string
  description: string
  segments: { code: string; segment_type: string; description_en: string }[]
  unmatched: string[]
}

// ==================== API ====================

export const salesDocumentApi = {
  // 목록 조회
  getList: (params?: {
    document_type?: string
    customer_id?: number
    status?: string
    keyword?: string
    skip?: number
    limit?: number
    order_by?: string
    order_desc?: boolean
    include_old_versions?: boolean
  }) => apiClient.get<SalesDocumentListResponse>('/sales-documents', { params }),

  // 상세 조회
  getById: (id: number) => apiClient.get<SalesDocument>(`/sales-documents/${id}`),

  // 생성
  create: (data: Partial<SalesDocument> & { items: SalesDocumentItem[] }) =>
    apiClient.post<SalesDocument>('/sales-documents', data),

  // 수정
  update: (id: number, data: Partial<SalesDocument>) =>
    apiClient.put<SalesDocument>(`/sales-documents/${id}`, data),

  // 삭제
  delete: (id: number, force = false) => apiClient.delete(`/sales-documents/${id}`, { params: { force } }),

  // 상태 변경
  updateStatus: (id: number, status: string) =>
    apiClient.post<SalesDocument>(`/sales-documents/${id}/status/${status}`),

  // 버전 이력 조회 (v0.32.0)
  getVersions: (id: number) =>
    apiClient.get<{ id: number; document_number: string; version: number; is_latest: boolean; status: string; total_amount: number; currency: string; document_date: string; created_at: string }[]>(`/sales-documents/${id}/versions`),

  // CI 출고일자 설정/해제
  updateShipmentDate: (id: number, shipmentDate?: string) =>
    apiClient.post(`/sales-documents/${id}/shipment-date`, null, { params: { shipment_date: shipmentDate || '' } }),

  // 같은 유형 문서 합치기 (v0.32.0)
  merge: (sourceIds: number[]) =>
    apiClient.post<SalesDocument>('/sales-documents/merge', sourceIds),

  // Q→PI / PI→CI 전환 (단일)
  convert: (id: number, data: { customer_po_number?: string; customer_po_date?: string; is_quote_only?: boolean; document_date?: string; target_type?: string }) =>
    apiClient.post<SalesDocument>(`/sales-documents/${id}/convert`, data),

  // Q→PI / PI→CI / PI→INVOICE 전환 (다중 소스, N:M, v0.32.0)
  convertMultiple: (sourceIds: number[], data: { customer_po_number?: string; customer_po_date?: string; is_quote_only?: boolean; document_date?: string; target_type?: string }) =>
    apiClient.post<SalesDocument>(`/sales-documents/convert-multiple`, {
      source_ids: sourceIds,
      ...data,
    }),

  /**
   * 고객 PO 번호 정정 — 이미 발행된 문서도 버전 생성 없이 제자리 수정.
   * 일반 수정(update)은 SENT/CONFIRMED 문서에 새 버전을 만들어 문서번호가
   * 재발행되므로, 고객측 참조값인 PO 번호 정정에는 이 경로를 쓴다.
   * cascade=true 면 같은 PO 를 승계한 후속 문서(CI 등)도 함께 정정.
   */
  updatePoNumber: (
    id: number,
    data: { customer_po_number?: string | null; customer_po_date?: string | null; cascade?: boolean },
  ) =>
    apiClient.patch<{ document: SalesDocument; updated_count: number }>(
      `/sales-documents/${id}/po-number`,
      data,
    ),

  // 엑셀 다운로드
  exportExcel: (id: number) =>
    apiClient.get(`/sales-documents/${id}/export/excel`, { responseType: 'blob' }),

  // 고객 기본값 로드
  getCustomerDefaults: (customerId: number) =>
    apiClient.get<CustomerDefaults>(`/sales-documents/customer-defaults/${customerId}`),

  // 고객별 가격 이력
  getCustomerPriceHistory: (customerId: number, productCode?: string) =>
    apiClient.get<PriceHistoryItem[]>(`/sales-documents/price-history/${customerId}`, {
      params: productCode ? { product_code: productCode } : undefined,
    }),

  // 마지막 견적 가격 조회
  getLastQuotedPrice: (customerId: number, productCode: string) =>
    apiClient.get<LastQuotedPrice>(`/sales-documents/last-price/${customerId}/${encodeURIComponent(productCode)}`),

  // 견적 단가 자동산출 (백엔드 권위 계산) — overrides 로 상세 항목 조정 시 서버가 재계산
  suggestPrice: (data: {
    order_code: string
    length_m?: number
    quantity?: number
    customer_id?: number | null
    currency?: string
    overrides?: Record<string, any> | null
  }) => apiClient.post<SuggestPriceResult>('/sales-documents/suggest-price', data),

  // 견적 자동산출 설정 조회/저장(관리자)
  getQuoteConfig: () => apiClient.get<QuoteConfig>('/sales-documents/quote-config'),
  updateQuoteConfig: (data: QuoteConfig) => apiClient.put<QuoteConfig>('/sales-documents/quote-config', data),

  // 입금 상태 변경
  updatePayment: (id: number, data: {
    payment_status: string
    paid_amount?: number
    paid_date?: string
    payment_remarks?: string
  }) => apiClient.post<SalesDocument>(`/sales-documents/${id}/payment`, data),

  // 수금 현황 요약
  getCollectionSummary: () =>
    apiClient.get<CollectionSummary>('/sales-documents/collection/summary'),

  // 수금 현황 목록 (PI 기준 + 배송완료 여부)
  getCollectionDocuments: () =>
    apiClient.get<{ items: CollectionDoc[] }>('/sales-documents/collection/documents'),

  // PI 프로세스 현황 조회
  getProcessStatus: (docId: number) =>
    apiClient.get<PIProcessStatus>(`/sales-documents/${docId}/process-status`),

  // PI → 생산요청 초안 생성
  createProductionRequestDraft: (docId: number) =>
    apiClient.post<ProductionRequestDraftResult>(`/sales-documents/${docId}/create-production-request-draft`),

  // 관련 문서 체인 조회 (선행/후속 + 생산요청)
  getRelatedDocuments: (docId: number) =>
    apiClient.get<RelatedDocumentsResponse>(`/sales-documents/${docId}/related`),

  // PI 잔여 수량 조회
  getRemainingQuantities: (docId: number) =>
    apiClient.get<PIRemainingResponse>(`/sales-documents/${docId}/remaining-quantities`),

  // PO 첨부파일 업로드
  uploadPoAttachment: (docId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/sales-documents/${docId}/po-attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // PO 첨부파일 삭제
  deletePoAttachment: (docId: number, fileIndex: number) =>
    apiClient.delete(`/sales-documents/${docId}/po-attachments/${fileIndex}`),

  // PO 첨부파일 다운로드 URL
  getPoAttachmentDownloadUrl: (docId: number, fileIndex: number) =>
    `/api/v1/sales-documents/${docId}/po-attachments/${fileIndex}/download`,

  // ─────────── 운송장 (CI 전용) ───────────
  uploadShippingInvoice: (docId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/sales-documents/${docId}/shipping-invoices`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  deleteShippingInvoice: (docId: number, fileIndex: number) =>
    apiClient.delete(`/sales-documents/${docId}/shipping-invoices/${fileIndex}`),

  getShippingInvoiceDownloadUrl: (docId: number, fileIndex: number) =>
    `/api/v1/sales-documents/${docId}/shipping-invoices/${fileIndex}/download`,

  // 운송장 미리보기: blob URL 반환 (사용 후 revoke 필수)
  getShippingInvoicePreviewBlobUrl: async (
    docId: number,
    fileIndex: number,
  ): Promise<{ url: string; mimetype: string }> => {
    const res = await apiClient.get(
      `/sales-documents/${docId}/shipping-invoices/${fileIndex}/preview`,
      { responseType: 'blob' },
    )
    const mimetype = (res.data?.type as string) || (res.headers['content-type'] as string) || 'application/octet-stream'
    const blob = new Blob([res.data], { type: mimetype })
    return { url: URL.createObjectURL(blob), mimetype }
  },

  // ─────────── PDF 생성 (Phase 4) ───────────
  // 다운로드: 사용자가 파일로 저장
  downloadPdf: async (docId: number, lang: 'ko' | 'en' = 'ko', filename?: string) => {
    const res = await apiClient.get(`/sales-documents/${docId}/pdf`, {
      params: { lang, disposition: 'attachment' },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    try {
      const a = document.createElement('a')
      a.href = url
      a.download = filename || extractFilenameFromContentDisposition(res.headers['content-disposition']) || `document_${docId}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
    } finally {
      // 브라우저가 다운로드 시작 후 즉시 revoke 가능
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    }
  },

  // 미리보기: iframe src로 사용할 Blob URL 반환 (사용자가 사용 후 revoke 필수)
  getPdfPreviewBlobUrl: async (docId: number, lang: 'ko' | 'en' = 'ko'): Promise<string> => {
    const res = await apiClient.get(`/sales-documents/${docId}/pdf`, {
      params: { lang, disposition: 'inline' },
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    return URL.createObjectURL(blob)
  },
}

// Content-Disposition 헤더에서 filename 추출 (RFC 5987 단순 케이스)
function extractFilenameFromContentDisposition(header?: string): string | null {
  if (!header) return null
  const match = /filename\s*=\s*"?([^";\r\n]+)"?/i.exec(header)
  return match?.[1] ?? null
}

export interface PoAttachmentFile {
  filename: string
  filepath: string
  mimetype?: string
  size?: number
}

export interface ShippingInvoiceFile {
  filename: string
  filepath: string
  mimetype?: string
  size?: number
  uploaded_at?: string
}

export interface RelatedDocumentRef {
  id: number
  document_type: string
  document_number: string
  document_date?: string
  status: string
}

export interface RelatedProductionRequest {
  id: number
  request_number: string
  status: string
  due_date?: string
  created_at?: string
}

export interface RelatedDocumentsResponse {
  source: RelatedDocumentRef | null
  forward: RelatedDocumentRef[]
  production_requests: RelatedProductionRequest[]
  sales_activity?: { id: number; title: string; status?: string; customer_name?: string } | null
}

export interface PIRemainingItem {
  pi_item_id: number
  product_code: string
  description?: string
  total_qty: number
  requested_qty: number
  remaining_qty: number
}

export interface PIRemainingResponse {
  pi_id: number
  pi_number: string
  document_type: string
  items: PIRemainingItem[]
}

export interface PriceHistoryItem {
  product_code: string
  unit_price: number
  currency: string
  quantity: number
  document_id?: number
  document_number: string
  document_type: string
  document_date: string
  status: string
}

export interface LastQuotedPrice {
  found: boolean
  unit_price?: number
  quantity?: number | null
  uom?: string | null
  currency?: string
  document_number?: string
  document_date?: string
  document_type?: string
  message?: string
}

export interface QuoteConfig {
  channel_margins: Record<string, number>   // {"2":60, "4":55, "6":56}
  exchange_rate: number
  domestic_premium: number
  price_increase_global: number
  price_increase_by_item: Record<string, number>  // {CODE: %}
}

export interface SuggestPriceResult {
  unit_price: number | null
  amount: number | null
  currency: string
  cost_breakdown: {
    connector_a?: number
    connector_b?: number
    cable?: number
    assembly?: number
    option_delta?: number
    extra_items?: { label: string; amount: number }[]
    extra_total?: number
    subtotal?: number
    base_cost_krw?: number | null
    adjusted_cost_krw?: number | null
    cable_rate?: number | null
  }
  applied: {
    margin_rate?: number | null
    margin_source?: string
    exchange_rate?: number
    domestic_premium?: number
    price_increase_pct?: number
    assembly_stages?: number
  }
  warnings: string[]
  parsed: {
    size?: string | null
    form?: string | null
    material?: string | null
    core?: string | null
    channel?: number | null
    mode?: string | null
    is_sa?: boolean
    endface?: string | null
  }
}

export interface CollectionSummary {
  total_documents: number
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  unpaid_count: number
  partial_count: number
  paid_count: number
}

// 수금 현황 목록 아이템 (PI + 배송완료 여부)
export interface CollectionDoc {
  id: number
  document_number: string
  customer_id?: number
  customer?: { partner_name?: string } | null
  customer_po_number?: string | null
  currency: string
  total_amount: number
  paid_amount: number
  payment_status: string
  paid_date?: string | null
  delivered: boolean
}

export interface PIProcessStep {
  key: string
  label: string
  done: boolean
  detail?: string
}

export interface PIProcessStatus {
  steps: PIProcessStep[]
}

export interface ProductionRequestDraftResult {
  success: boolean
  production_request_id?: number
  request_number?: string
  items_created?: number
  items_skipped?: string[]
  message: string
}

// Description 자동 조합
export const descriptionCodeApi = {
  compose: (orderCode: string, language: string = 'en') =>
    apiClient.post<DescriptionComposeResponse>('/product-description-codes/compose', { order_code: orderCode, language }),

  getAll: (params?: { segment_type?: string; is_active?: boolean }) =>
    apiClient.get('/product-description-codes', { params }),
}
