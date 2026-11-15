/**
 * 부품 마스터 API 서비스
 *
 * v0.11.0: 품번 구조 (부품코드 관리기준서 적용)
 * - 품번 구성요소: product_line_id, part_group_id, item_code_prefix (사용자 입력 3자리) + item_code (자동완성 2자리)
 * - 분류 속성: development_type_id, part_type_ids (다중선택), drawing_type_id
 * - 공통 속성: material_id, treatment_id, level_id, procurement_type_id, unit_id
 */

import apiClient from './client'

// 코드 마스터 간략 정보 (relationship용)
interface CodeMasterInfo {
  id: number
  code: string
  name_ko: string
  name_en?: string
}

// 부품 인터페이스
export interface Part {
  id: number
  part_uid?: string  // v0.12.0: 고유 ID (PT-XXXXXXXX, 바코드용, 변경불가)
  part_number: string
  part_number_display: string
  part_name: string
  part_name_en?: string
  description?: string
  is_classified?: boolean  // BOM 개편: 미분류(false)면 품번 대신 공백 표시

  // 품번 구성요소
  product_line_id?: number
  part_group_id?: number
  item_code_prefix?: string  // 3자리 품목코드 앞자리 (사용자 입력)
  item_code?: string  // 5자리 품목코드 (앞 3자리 사용자 입력 + 뒤 2자리 자동생성)

  // 분류 속성
  development_type_id?: number
  drawing_type_id?: number
  part_type_ids?: number[]  // 다중선택

  // 품번 구성요소 관계
  product_line?: CodeMasterInfo
  part_group?: CodeMasterInfo
  development_type?: CodeMasterInfo
  drawing_type?: CodeMasterInfo
  part_types?: CodeMasterInfo[]  // 다중선택

  // 공통 속성
  material_id?: number
  treatment_id?: number
  level_id?: number
  material?: CodeMasterInfo
  treatment?: CodeMasterInfo
  level?: CodeMasterInfo

  // 조달 정보
  procurement_type_id?: number
  procurement_type?: CodeMasterInfo

  // 규격 정보
  specification?: string
  unit_id?: number
  unit?: CodeMasterInfo

  // 버전 관리
  version: string
  revision: number
  revision_note?: string

  // 가격 정보 (v0.18.0 원가관리)
  unit_price?: number
  currency: string
  price_updated_at?: string
  standard_price?: number
  standard_price_currency?: string
  inventory_avg_price?: number
  inventory_avg_price_currency?: string
  latest_price?: number
  latest_price_currency?: string
  latest_price_date?: string

  // 조달 정보
  supplier_id?: number
  lead_time_days?: number
  min_order_qty: number

  // v0.79.0: 전속(독점) 공급 계약
  is_protected?: boolean
  protected_customer_id?: number | null
  protection_note?: string | null
  protected_customer?: { id: number; partner_name?: string } | null

  // 첨부파일
  file_name?: string
  drawing_file?: string
  photo_file?: string
  document_files?: Record<string, any>

  // 승인 상태
  approval_status: string
  approved_by?: number
  approved_at?: string

  // 상태
  status: string
  is_active: boolean

  // 감사
  created_by?: number
  created_at: string
  updated_by?: number
  updated_at?: string

  // 비고
  remark?: string
}

// 코드 마스터 간략 정보 (목록 표시용)
interface CodeMasterListInfo {
  id: number
  code: string
  name_ko: string
  name_en?: string
}

// 부품 목록 (간략 버전)
export interface PartListItem {
  id: number
  part_uid?: string  // v0.12.0: 고유 ID (PT-XXXXXXXX, 바코드용)
  part_number: string
  part_number_display?: string | null  // Optional - 기존 데이터 호환
  part_name: string
  part_name_en?: string
  description?: string  // 설명
  item_code?: string  // 품목코드 5자리
  specification?: string
  version?: string | null  // Optional - 기존 데이터 호환
  status?: string | null  // Optional - 기존 데이터 호환
  is_active: boolean
  is_classified?: boolean  // BOM 개편: 미분류(false)=코드·레벨 미부여 잠정 부품
  created_at: string
  // 가격 정보
  standard_price?: number
  standard_price_currency?: string
  // 승인 상태
  approval_status?: string
  // v0.79.0: 전속(독점) 공급 계약
  is_protected?: boolean
  protected_customer_id?: number | null
  protection_note?: string | null
  protected_customer?: { id: number; partner_name?: string } | null
  // 관계 데이터 (v0.10.0)
  product_line?: CodeMasterListInfo
  part_group?: CodeMasterListInfo
  material?: CodeMasterListInfo
  level?: CodeMasterListInfo
}

// 부품 생성 DTO
export interface PartCreate {
  part_name: string
  part_name_en?: string
  description?: string

  // 품번 구성요소
  part_number?: string  // 직접 입력 모드용 (자유형식)
  product_line_id?: number
  part_group_id?: number
  item_code_prefix?: string  // 품목코드 앞 3자리 (사용자 입력)
  item_code_suffix?: string  // 품목코드 뒤 2자리 (직접 입력, 비워두면 자동생성)

  // 분류 속성
  development_type_id?: number
  drawing_type_id?: number
  part_type_ids?: number[]  // 다중선택

  // 공통 속성
  material_id?: number
  treatment_id?: number
  level_id?: number

  // 조달 정보
  procurement_type_id?: number

  // 규격 정보
  specification?: string
  unit_id?: number

  // 버전 관리
  version?: string
  revision?: number
  revision_note?: string

  // 가격 정보 (v0.18.0 원가관리)
  unit_price?: number
  currency?: string
  price_updated_at?: string
  standard_price?: number
  standard_price_currency?: string

  // BOM 원가 (v0.18.0)
  cost_type?: string
  material_cost?: number
  material_cost_currency?: string
  labor_cost?: number
  labor_cost_currency?: string
  overhead_cost?: number
  overhead_cost_currency?: string

  // 조달 정보
  supplier_id?: number
  lead_time_days?: number
  min_order_qty?: number

  // v0.79.0: 전속(독점) 공급 계약
  is_protected?: boolean
  protected_customer_id?: number | null
  protection_note?: string | null

  // 첨부파일
  file_name?: string
  drawing_file?: string
  photo_file?: string
  document_files?: Record<string, any>

  // 승인 상태
  approval_status?: string
  approved_by?: number
  approved_at?: string

  // 상태
  status?: string
  is_active?: boolean

  // 비고
  remark?: string
}

// 부품 수정 DTO
export interface PartUpdate extends Partial<PartCreate> {
  // v0.12.0: 품번 직접 수정 가능
  part_number?: string
  part_number_display?: string
}

// 조합/키트 생성 DTO (자유형식 코드)
export interface AssemblyCreate {
  part_number: string  // 자유형식 코드 (필수)
  part_name: string
  part_name_en?: string
  description?: string
  level_id: number  // K:키트, S:서브어셈블리, P:패키지, F:완제품 (필수)
  product_line_id?: number
  part_group_id?: number
  development_type_id?: number
  part_type_ids?: number[]
  drawing_type_id?: number
  specification?: string
  unit_id?: number
  unit_price?: number
  currency?: string
  status?: string
  is_active?: boolean
  remark?: string
}

// 부품 검색 파라미터
export interface PartSearchParams {
  keyword?: string
  product_line_id?: number
  part_group_id?: number
  development_type_id?: number
  development_type_ids?: string  // v0.12.0: 다중 선택용 (콤마 구분 문자열)
  material_id?: number
  treatment_id?: number  // v0.12.0: 후처리 필터 추가
  drawing_type_id?: number  // v0.12.0: 도면유형 필터 추가
  procurement_type_id?: number  // v0.12.0: 조달유형 필터 추가
  unit_id?: number  // v0.12.0: 단위 필터 추가
  level_id?: number
  level_ids?: string  // v0.12.0: 다중 선택용 (콤마 구분 문자열)
  status?: string
  is_active?: boolean
  classified?: boolean  // 분류상태: undefined=전체, true=분류됨, false=미분류
  // 고급 필터: 미입력 필드 검색
  missing_fields?: string  // 콤마 구분 문자열 (예: "supplier_id,part_name_en")
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

// 부품 마스터 API
// BOM 개편 P1: 부품 첨부
export interface PartAttachment {
  id: number
  part_id: number
  kind: string  // DRAWING/SPEC/PHOTO/OTHER
  filename: string
  mime_type?: string | null
  size?: number | null
  uploaded_by?: number | null
  created_at?: string | null
}

export const partApi = {
  // 부품 목록 조회 (페이지네이션)
  getAll: (params?: PartSearchParams) =>
    apiClient.get<PaginatedResponse<PartListItem>>('/parts', { params }),

  // 부품 단건 조회
  getById: (id: number) => apiClient.get<Part>(`/parts/${id}`),

  // v0.79.0: 특정 고객의 전속(독점) 계약 부품 목록 (거래처 상세용)
  getProtectedByCustomer: (customerId: number) =>
    apiClient.get<PartListItem[]>(`/parts/by-protected-customer/${customerId}`),

  // 품번으로 조회
  getByNumber: (partNumber: string) => apiClient.get<Part>(`/parts/by-number/${partNumber}`),

  // 품번 중복 체크
  checkDuplicate: (partNumber: string, excludeId?: number) =>
    apiClient.get<{
      exists: boolean
      part: { id: number; part_number: string; part_number_display: string; part_name: string } | null
    }>('/parts/check-duplicate', {
      params: { part_number: partNumber, exclude_id: excludeId }
    }),

  // 부품 생성
  create: (data: PartCreate) => apiClient.post<Part>('/parts', data),

  // BOM 개편 P1: 최소 등록(미분류) — 이름만으로 부품 생성(코드·레벨 없이)
  // extra로 영문명/설명/레벨 등을 함께 넘길 수 있음(시작 위저드에서 사용)
  createMinimal: (partName: string, extra?: Partial<PartCreate>) =>
    apiClient.post<Part>('/parts', { part_name: partName, ...(extra || {}) }),

  // BOM 개편 P4: 미분류→정식 분류 승격 / 부품 병합
  classify: (id: number, data: Record<string, unknown>) => apiClient.post<Part>(`/parts/${id}/classify`, data),
  merge: (sourceId: number, targetId: number) => apiClient.post('/parts/merge', { source_id: sourceId, target_id: targetId }),

  // BOM 개편 P1: 부품 첨부(도면/스펙/사진)
  listAttachments: (partId: number) =>
    apiClient.get<PartAttachment[]>(`/parts/${partId}/attachments`),
  uploadAttachment: (partId: number, file: File, kind: string) => {
    const fd = new FormData(); fd.append('file', file); fd.append('kind', kind)
    return apiClient.post<PartAttachment>(`/parts/${partId}/attachments`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  attachmentPreviewUrl: (attId: number) => `${apiClient.defaults.baseURL || ''}/parts/attachments/${attId}/preview`,
  downloadAttachment: async (attId: number, filename: string) => {
    const res = await apiClient.get(`/parts/attachments/${attId}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data])); const a = document.createElement('a')
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
  },
  deleteAttachment: (attId: number) => apiClient.delete(`/parts/attachments/${attId}`),

  // 조합/키트 생성 (자유형식 코드)
  createAssembly: (data: AssemblyCreate) => apiClient.post<Part>('/parts/assembly', data),

  // 부품 수정
  update: (id: number, data: PartUpdate) => apiClient.put<Part>(`/parts/${id}`, data),

  // 부품 삭제 (2단계: 1차 단종, 2차 완전삭제)
  delete: (id: number, force: boolean = false) =>
    apiClient.delete<{ action: 'obsoleted' | 'deleted'; message: string }>(`/parts/${id}`, {
      params: force ? { force: true } : undefined,
    }),

  // 부품 활성화
  activate: (id: number) => apiClient.patch<Part>(`/parts/${id}/activate`),

  // 부품 비활성화
  deactivate: (id: number) => apiClient.patch<Part>(`/parts/${id}/deactivate`),

  // 부품 상태 변경
  updateStatus: (id: number, status: string) =>
    apiClient.patch<Part>(`/parts/${id}/status`, null, { params: { new_status: status } }),

  // 부품 승인 상태 변경
  updateApproval: (id: number, approvalStatus: string, approvedBy?: number) =>
    apiClient.patch<Part>(`/parts/${id}/approval`, null, {
      params: { approval_status: approvalStatus, approved_by: approvedBy },
    }),

  // UID 없는 부품에 대해 일괄 UID 생성
  generateMissingUids: () =>
    apiClient.post<{
      total_without_uid: number
      generated_count: number
      failed_count: number
      parts: Array<{
        id: number
        part_number: string
        part_name: string
        part_uid: string | null
        status: 'success' | 'failed'
        error?: string
      }>
    }>('/parts/generate-missing-uids'),

  // 엑셀 내보내기 URL 생성
  // 운영(Caddy 프록시): 같은 origin /api/v1 사용
  // 개발(:5174/:5175): http://hostname:8001/api/v1 사용
  getExportExcelUrl: (params?: PartSearchParams): string => {
    const frontendPort = window.location.port
    let baseUrl: string
    if (frontendPort === '5174' || frontendPort === '5175') {
      baseUrl = `http://${window.location.hostname}:8001/api/v1/parts/export/excel`
    } else {
      baseUrl = `${window.location.origin}/api/v1/parts/export/excel`
    }
    if (!params) return baseUrl
    const searchParams = new URLSearchParams()
    if (params.keyword) searchParams.append('keyword', params.keyword)
    if (params.product_line_id) searchParams.append('product_line_id', String(params.product_line_id))
    if (params.part_group_id) searchParams.append('part_group_id', String(params.part_group_id))
    // 단일 필터
    if (params.development_type_id) searchParams.append('development_type_id', String(params.development_type_id))
    if (params.level_id) searchParams.append('level_id', String(params.level_id))
    if (params.material_id) searchParams.append('material_id', String(params.material_id))
    // 다중 필터 (콤마 구분 문자열)
    if (params.level_ids) searchParams.append('level_ids', params.level_ids)
    if (params.development_type_ids) searchParams.append('development_type_ids', params.development_type_ids)
    // 추가 필터 (v0.12.0)
    if (params.treatment_id) searchParams.append('treatment_id', String(params.treatment_id))
    if (params.drawing_type_id) searchParams.append('drawing_type_id', String(params.drawing_type_id))
    if (params.procurement_type_id) searchParams.append('procurement_type_id', String(params.procurement_type_id))
    if (params.unit_id) searchParams.append('unit_id', String(params.unit_id))
    // 상태 및 정렬
    if (params.status) searchParams.append('status', params.status)
    if (params.is_active !== undefined) searchParams.append('is_active', String(params.is_active))
    if (params.order_by) searchParams.append('order_by', params.order_by)
    if (params.order_desc !== undefined) searchParams.append('order_desc', String(params.order_desc))
    const queryString = searchParams.toString()
    return queryString ? `${baseUrl}?${queryString}` : baseUrl
  },

  // 엑셀 업로드 (v0.21.0)
  uploadExcel: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<{
      total: number
      success_count: number
      price_updated_count?: number
      failed_count: number
      results: Array<{
        row: number
        part_number: string
        part_id?: number
        status: 'success' | 'failed' | 'skipped' | 'price_updated'
        message: string
        parsed_errors?: string[]
      }>
    }>('/parts/upload-excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}
