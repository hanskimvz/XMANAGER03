/**
 * 원가 관리 API 서비스
 *
 * v0.18.0: 원가관리 기능 추가
 * - 부품 가격 정보 조회
 * - 기준단가 수정
 * - 평균단가 계산
 * - 가격 이력 조회
 * - 환율 관리
 */

import apiClient from './client'

// 가격 유형
export type PriceType = 'PURCHASE' | 'STANDARD' | 'MANUAL' | 'QUOTE'

// 통화 코드
export type Currency = 'KRW' | 'USD' | 'EUR' | 'JPY' | 'CNY'

// 부품 원가 정보
export interface PartPriceInfo {
  part_id: number
  part_number: string
  part_name: string
  // 기준단가
  standard_price: number
  standard_price_currency: string
  // 재고단가 (이동평균)
  inventory_avg_price: number
  inventory_avg_price_currency: string
  // 최근단가
  latest_price: number
  latest_price_currency: string
  latest_price_date?: string
  latest_price_supplier?: string
  // 평균단가 캐시
  avg_price_30d: number
  avg_price_90d: number
  avg_price_last5: number
  avg_price_last10: number
  // BOM 원가 정보 (v0.18.0)
  cost_type: 'MANUAL' | 'BOM' | 'PROCESS'
  material_cost: number
  material_cost_currency: string
  labor_cost: number
  labor_cost_currency: string
  overhead_cost: number
  overhead_cost_currency: string
  calculated_cost: number
  calculated_cost_currency: string
  cost_calculated_at?: string
}

// 가격 이력
export interface PriceHistory {
  id: number
  part_id: number
  price_type: PriceType
  unit_price: number
  currency: string
  exchange_rate?: number
  unit_price_krw?: number
  quantity?: number
  supplier_id?: number
  supplier_name?: string
  reference_type?: string
  reference_id?: string
  reference_date?: string
  remarks?: string
  created_by?: number
  created_at: string
}

// 가격 이력 목록 응답
export interface PriceHistoryListResponse {
  items: PriceHistory[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

// 평균단가 응답
export interface AvgPriceResponse {
  part_id: number
  avg_price: number
  avg_price_krw: number
  currency: string
  count: number
  from_date?: string
  to_date?: string
  min_price: number
  max_price: number
}

// 기준단가 수정 요청
export interface StandardPriceUpdate {
  standard_price: number
  standard_price_currency?: string
  remarks?: string
}

// 환율
export interface ExchangeRate {
  id: number
  currency_code: string
  currency_name?: string
  rate: number
  effective_date: string
  expiry_date?: string
  source: string
  is_active: string
  created_at: string
}

// 환율 생성 요청
export interface ExchangeRateCreate {
  currency_code: string
  currency_name?: string
  rate: number
  effective_date: string
  expiry_date?: string
  source?: string
}

// 통화 환산 응답
export interface ConvertCurrencyResponse {
  original_amount: number
  original_currency: string
  converted_amount: number
  converted_currency: string
  exchange_rate: number
  date: string
}

// 가격 이력 검색 파라미터
export interface PriceHistorySearchParams {
  price_type?: PriceType
  supplier_id?: number
  from_date?: string
  to_date?: string
  skip?: number
  limit?: number
}

// 평균단가 계산 파라미터
export interface AvgPriceParams {
  from_date?: string
  to_date?: string
  last_count?: number
  supplier_id?: number
}

// BOM 원가 계산 결과
export interface BOMCostResult {
  part_id: number
  part_number: string
  part_name: string
  cost_type: 'MANUAL' | 'BOM' | 'PROCESS'
  material_cost: number
  labor_cost: number
  overhead_cost: number
  total_cost: number
  has_bom: boolean
  bom_items: BOMCostItem[]
}

// BOM 구성품 원가
export interface BOMCostItem {
  bom_id: number
  child_part_id: number
  child_part_number: string
  child_part_name: string
  quantity: number
  unit_cost: number
  line_cost: number
  has_bom: boolean
}

// BOM 원가 분석 결과
export interface BOMCostBreakdown {
  part_info: {
    id: number
    part_number: string
    part_number_display?: string
    part_name: string
  }
  cost_summary: {
    cost_type: string
    material_cost: number
    labor_cost: number
    overhead_cost: number
    total_cost: number
    currency: string
  }
  has_bom: boolean
  bom_items: BOMCostItem[]
}

// 원가 관리 API
export const priceApi = {
  /**
   * 부품 원가 정보 조회
   */
  async getPartPriceInfo(partId: number): Promise<PartPriceInfo> {
    const response = await apiClient.get(`/prices/parts/${partId}`)
    return response.data
  },

  /**
   * 기준단가 수정
   */
  async updateStandardPrice(partId: number, data: StandardPriceUpdate): Promise<PartPriceInfo> {
    const response = await apiClient.patch(`/prices/parts/${partId}/standard-price`, data)
    return response.data
  },

  /**
   * 평균단가 캐시 갱신
   */
  async refreshAvgPriceCache(partId: number): Promise<PartPriceInfo> {
    const response = await apiClient.post(`/prices/parts/${partId}/refresh-cache`)
    return response.data
  },

  /**
   * 평균단가 계산
   */
  async calculateAvgPrice(partId: number, params: AvgPriceParams = {}): Promise<AvgPriceResponse> {
    const queryParams = new URLSearchParams()

    if (params.from_date) queryParams.append('from_date', params.from_date)
    if (params.to_date) queryParams.append('to_date', params.to_date)
    if (params.last_count) queryParams.append('last_count', String(params.last_count))
    if (params.supplier_id) queryParams.append('supplier_id', String(params.supplier_id))

    const query = queryParams.toString()
    const url = `/prices/parts/${partId}/avg-price${query ? `?${query}` : ''}`
    const response = await apiClient.get(url)
    return response.data
  },

  /**
   * 가격 이력 조회
   */
  async getPriceHistory(partId: number, params: PriceHistorySearchParams = {}): Promise<PriceHistoryListResponse> {
    const queryParams = new URLSearchParams()

    if (params.price_type) queryParams.append('price_type', params.price_type)
    if (params.supplier_id) queryParams.append('supplier_id', String(params.supplier_id))
    if (params.from_date) queryParams.append('from_date', params.from_date)
    if (params.to_date) queryParams.append('to_date', params.to_date)
    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    if (params.limit !== undefined) queryParams.append('limit', String(params.limit))

    const query = queryParams.toString()
    const url = `/prices/parts/${partId}/history${query ? `?${query}` : ''}`
    const response = await apiClient.get(url)
    return response.data
  },

  /**
   * 환율 조회
   */
  async getExchangeRate(currencyCode: string, date?: string): Promise<{ currency_code: string; rate: number; date: string }> {
    const params = date ? `?date=${date}` : ''
    const response = await apiClient.get(`/prices/exchange-rates/${currencyCode}${params}`)
    return response.data
  },

  /**
   * 환율 등록
   */
  async createExchangeRate(data: ExchangeRateCreate): Promise<ExchangeRate> {
    const response = await apiClient.post('/prices/exchange-rates', data)
    return response.data
  },

  /**
   * 통화 환산
   */
  async convertCurrency(amount: number, fromCurrency: string, toCurrency: string = 'KRW', date?: string): Promise<ConvertCurrencyResponse> {
    const params = new URLSearchParams({
      amount: String(amount),
      from_currency: fromCurrency,
      to_currency: toCurrency,
    })
    if (date) params.append('date', date)

    const response = await apiClient.get(`/prices/convert?${params.toString()}`)
    return response.data
  },

  // ==================== BOM 기반 원가 계산 (v0.18.0) ====================

  /**
   * BOM 기반 원가 계산
   */
  async calculateBOMCost(partId: number): Promise<BOMCostResult> {
    const response = await apiClient.get(`/prices/parts/${partId}/bom-cost`)
    return response.data
  },

  /**
   * BOM 원가 분석 (상세 내역)
   */
  async getBOMCostBreakdown(partId: number): Promise<BOMCostBreakdown> {
    const response = await apiClient.get(`/prices/parts/${partId}/bom-cost/breakdown`)
    return response.data
  },

  /**
   * 계산된 원가 저장
   */
  async saveCalculatedCost(partId: number): Promise<PartPriceInfo> {
    const response = await apiClient.post(`/prices/parts/${partId}/bom-cost/save`)
    return response.data
  },

  /**
   * BOM 전체 원가 재계산 및 저장 (하위 BOM 포함)
   */
  async saveAllBOMCosts(partId: number): Promise<{ count: number; message: string; part_price_info: PartPriceInfo }> {
    const response = await apiClient.post(`/prices/parts/${partId}/bom-cost/save-all`)
    return response.data
  },

  /**
   * 가공비 업데이트
   */
  async updateLaborCost(partId: number, laborCost: number, currency: string = 'KRW'): Promise<PartPriceInfo> {
    const response = await apiClient.patch(`/prices/parts/${partId}/labor-cost`, null, {
      params: { labor_cost: laborCost, currency }
    })
    return response.data
  },

  /**
   * 경비 업데이트
   */
  async updateOverheadCost(partId: number, overheadCost: number, currency: string = 'KRW'): Promise<PartPriceInfo> {
    const response = await apiClient.patch(`/prices/parts/${partId}/overhead-cost`, null, {
      params: { overhead_cost: overheadCost, currency }
    })
    return response.data
  },
}

// 가격 유형 한글 변환
export const priceTypeLabels: Record<PriceType, string> = {
  PURCHASE: '구매',
  STANDARD: '기준단가',
  MANUAL: '수동입력',
  QUOTE: '견적',
}

// 통화 한글 변환
export const currencyLabels: Record<Currency, string> = {
  KRW: '원화 (₩)',
  USD: '미국 달러 ($)',
  EUR: '유로 (€)',
  JPY: '일본 엔 (¥)',
  CNY: '중국 위안 (¥)',
}

// 통화 기호
export const currencySymbols: Record<string, string> = {
  KRW: '₩',
  USD: '$',
  EUR: '€',
  JPY: '¥',
  CNY: '¥',
}

// 통화별 소수 자리수 (국제 통용: 원화·엔·위안은 정수, 달러·유로 등은 2자리)
const ZERO_DECIMAL_CURRENCIES = new Set(['KRW', 'JPY', 'CNY'])
export function currencyFractionDigits(currency: string = 'KRW'): number {
  return ZERO_DECIMAL_CURRENCIES.has((currency || 'KRW').toUpperCase()) ? 0 : 2
}

/**
 * 금액 숫자 포맷 (천 단위 콤마 + 통화별 소수 자리, 기호 없음).
 * 예: formatAmount(1234000,'KRW') → '1,234,000' / formatAmount(1234.5,'USD') → '1,234.50'
 * 판매 화면의 `{{ currency }} {{ formatAmount(x, currency) }}` 패턴에 사용.
 */
export function formatAmount(amount: number | undefined | null, currency: string = 'KRW'): string {
  if (amount === undefined || amount === null || isNaN(Number(amount))) return '-'
  const d = currencyFractionDigits(currency)
  return Number(amount).toLocaleString('ko-KR', {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  })
}

/**
 * 금액 포맷팅 — 통화 기호 + 천 단위 콤마 + 통화별 소수 자리.
 * 예: '₩1,234,000' / '$1,234.56'
 */
export function formatPrice(amount: number | undefined | null, currency: string = 'KRW'): string {
  if (amount === undefined || amount === null) return '-'
  const symbol = currencySymbols[(currency || 'KRW').toUpperCase()] || ''
  return `${symbol}${formatAmount(amount, currency)}`
}
