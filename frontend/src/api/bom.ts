/**
 * BOM (Bill of Materials) API 서비스
 * 부품 구성 관리를 위한 API입니다.
 */

import apiClient from './client'

// 부품 간략 정보
export interface PartBrief {
  id: number
  part_number: string
  part_number_display?: string
  part_name: string
  description?: string  // v0.22.0: 설명 필드 추가
  specification?: string
  unit_name?: string
  is_classified?: boolean  // 미분류(false)면 품번 대신 공백/미분류 표시
}

// BOM 생성 인터페이스
export interface BOMCreate {
  parent_part_id: number
  child_part_id: number
  quantity: number
  unit_id?: number
  bom_level?: number
  sort_order?: number
  effective_date?: string
  expiry_date?: string
  remark?: string
  is_active?: boolean
}

// BOM 수정 인터페이스
export interface BOMUpdate {
  quantity?: number
  unit_id?: number
  sort_order?: number
  effective_date?: string
  expiry_date?: string
  remark?: string
  is_active?: boolean
}

// BOM 응답 인터페이스
export interface BOMResponse {
  id: number
  parent_part_id: number
  child_part_id: number
  quantity: number
  unit_id?: number
  bom_level: number
  sort_order: number
  effective_date?: string
  expiry_date?: string
  remark?: string
  is_active: boolean
  created_at?: string
  updated_at?: string
}

// BOM 상세 응답 (부품 정보 포함)
export interface BOMDetailResponse extends BOMResponse {
  parent_part?: PartBrief
  child_part?: PartBrief
  unit_name?: string
}

// BOM 트리 노드 (재귀 구조)
export interface BOMTreeNode {
  id: number
  part_id: number
  part_number: string
  part_number_display?: string
  part_name: string
  description?: string  // v0.21.0: 부품명 표시용
  specification?: string
  quantity: number
  unit_name?: string
  bom_level: number
  level_code?: string  // 부품 레벨코드(색상 구분용)
  is_classified?: boolean
  attachment_count?: number
  children: BOMTreeNode[]
}

// BOM 목록 아이템
export interface BOMListItem {
  id: number
  parent_part_id: number
  parent_part_number: string
  parent_part_name: string
  child_part_id: number
  child_part_number: string
  child_part_name: string
  child_specification?: string
  quantity: number
  unit_name?: string
  bom_level: number
  sort_order: number
  is_active: boolean
}

// BOM 일괄 추가 인터페이스
export interface BOMBulkCreate {
  parent_part_id: number
  items: BOMItemCreate[]
}

export interface BOMItemCreate {
  child_part_id: number
  quantity: number
  unit_id?: number
  sort_order?: number
  remark?: string
}

// 검색 파라미터
export interface BOMSearchParams {
  parent_part_id?: number
  child_part_id?: number
  is_active?: boolean
  skip?: number
  limit?: number
}

// 페이지네이션 응답
export interface BOMPaginatedResponse {
  items: BOMListItem[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

// BOM API 서비스
export const bomApi = {
  /**
   * BOM 목록 조회
   */
  getAll: (params?: BOMSearchParams) => {
    return apiClient.get<BOMPaginatedResponse>('/bom', { params })
  },

  /**
   * BOM 단건 조회
   */
  getById: (id: number) => {
    return apiClient.get<BOMDetailResponse>(`/bom/${id}`)
  },

  /**
   * 상위 부품의 하위 부품 목록 조회
   */
  getChildren: (parentPartId: number, isActive?: boolean) => {
    const params = isActive !== undefined ? { is_active: isActive } : {}
    return apiClient.get<BOMDetailResponse[]>(`/bom/children/${parentPartId}`, { params })
  },

  /**
   * 하위 부품이 사용되는 상위 부품 목록 조회
   */
  getParents: (childPartId: number, isActive?: boolean) => {
    const params = isActive !== undefined ? { is_active: isActive } : {}
    return apiClient.get<BOMDetailResponse[]>(`/bom/parents/${childPartId}`, { params })
  },

  /**
   * BOM 트리 구조 조회
   */
  getTree: (parentPartId: number) => {
    return apiClient.get<BOMTreeNode[]>(`/bom/tree/${parentPartId}`)
  },

  /**
   * 여러 부품의 하위 BOM 개수 일괄 조회
   */
  getChildrenCountBatch: (parentPartIds: number[]) => {
    return apiClient.post<Record<number, number>>('/bom/children-count', parentPartIds)
  },

  /**
   * BOM 생성
   */
  create: (data: BOMCreate) => {
    return apiClient.post<BOMResponse>('/bom', data)
  },

  /**
   * BOM 일괄 생성
   */
  createBulk: (data: BOMBulkCreate) => {
    return apiClient.post<BOMResponse[]>('/bom/bulk', data)
  },

  /**
   * BOM 수정
   */
  update: (id: number, data: BOMUpdate) => {
    return apiClient.put<BOMResponse>(`/bom/${id}`, data)
  },

  /**
   * BOM 삭제
   */
  delete: (id: number) => {
    return apiClient.delete(`/bom/${id}`)
  },

  /**
   * 상위 부품의 모든 BOM 삭제
   */
  deleteByParent: (parentPartId: number) => {
    return apiClient.delete(`/bom/parent/${parentPartId}`)
  },

  /**
   * BOM 정렬 순서 업데이트
   */
  updateSortOrders: (parentPartId: number, orders: { id: number; sort_order: number }[]) => {
    return apiClient.patch(`/bom/sort-order/${parentPartId}`, orders)
  },

  // BOM 개편 P2/P3: 드래그 이동·상위묶기·변경로그
  move: (bomId: number, newParentPartId: number) =>
    apiClient.post(`/bom/${bomId}/move`, { new_parent_part_id: newParentPartId }),
  groupUnder: (childBomIds: number[], newParentPartId: number) =>
    apiClient.post(`/bom/group-under`, { child_bom_ids: childBomIds, new_parent_part_id: newParentPartId }),
  changeLog: (parentPartId?: number, limit = 100) =>
    apiClient.get(`/bom/audit/change-log`, { params: { parent_part_id: parentPartId, limit } }),

  /**
   * BOM 엑셀 내보내기 URL 생성
   * @param parentPartId 상위 부품 ID
   * @param includeTree 전체 트리 포함 여부 (기본: true)
   */
  getExportExcelUrl: (parentPartId: number, includeTree: boolean = true): string => {
    const baseUrl = apiClient.defaults.baseURL || ''
    return `${baseUrl}/bom/export/excel/${parentPartId}?include_tree=${includeTree}`
  },

  /**
   * BOM 엑셀 다운로드
   */
  exportExcel: async (parentPartId: number, includeTree: boolean = true): Promise<void> => {
    const url = `/bom/export/excel/${parentPartId}?include_tree=${includeTree}`
    const response = await apiClient.get(url, { responseType: 'blob' })

    // Content-Disposition에서 파일명 추출
    const contentDisposition = response.headers['content-disposition']
    let filename = `BOM_${parentPartId}.xlsx`
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename=(.+)/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/"/g, '')
      }
    }

    // Blob 다운로드
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  },

  // BOM 개편 2026-09: 업로드용 빈 양식(템플릿) 다운로드
  downloadUploadTemplate: async (): Promise<void> => {
    const response = await apiClient.get('/bom/upload/template', { responseType: 'blob' })
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = 'BOM_upload_template.xlsx'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  },

  /**
   * BOM에 등록된 부품 목록 조회 (v0.20.0, v0.22.0 필터 추가)
   * @param params.keyword 검색어 (품번/품명)
   * @param params.part_type 부품 유형: 'parent' (상위), 'child' (하위), 'all' (전체)
   * @param params.product_line_id 대분류/제품라인 필터
   * @param params.part_group_id 소분류/품목군 필터
   * @param params.level_id 레벨 필터
   * @param params.material_id 재질 필터
   * @param params.treatment_id 후처리 필터
   * @param params.skip 건너뛸 개수
   * @param params.limit 조회 개수
   */
  // ==================== BOM 엑셀 업로드 (v0.23.0) ====================

  /**
   * BOM 엑셀 파일 검증
   */
  uploadValidate: async (
    file: File,
    mode: string = 'replace'
  ): Promise<BOMUploadValidateResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post<BOMUploadValidateResponse>(
      '/bom/upload/validate',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' }, params: { mode } }
    )
    return response.data
  },

  /**
   * BOM 엑셀 파일 업로드 및 등록 (v2)
   */
  uploadExcel: async (
    file: File,
    mode: string = 'replace'
  ): Promise<BOMUploadResult> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post<BOMUploadResult>(
      '/bom/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' }, params: { mode } }
    )
    return response.data
  },

  getBomParts: (params?: {
    keyword?: string
    part_type?: string
    product_line_id?: number
    part_group_id?: number
    level_id?: number
    material_id?: number
    treatment_id?: number
    skip?: number
    limit?: number
  }) => {
    return apiClient.get<{
      items: BomPartItem[]
      total: number
      skip: number
      limit: number
      has_more: boolean
    }>('/bom/parts', { params })
  },
}

// BOM 부품 목록 아이템 (v0.20.0, v0.22.0 필터 필드 추가)
export interface BomPartItem {
  id: number
  part_number: string
  part_number_display?: string
  part_name: string
  name_ko?: string
  name_en?: string
  specification?: string
  product_line?: {
    id: number
    code: string
    name_ko: string
  }
  part_group?: {
    id: number
    code: string
    name_ko: string
  }
  level?: {
    id: number
    code: string
    name_ko: string
  }
  material?: {
    id: number
    code: string
    name_ko: string
  }
  treatment?: {
    id: number
    code: string
    name_ko: string
  }
}

// ==================== BOM 엑셀 업로드 타입 (v2) ====================

export interface BOMUploadValidationItem {
  row_number: number
  level: number
  part_number_display: string
  part_name?: string
  specification?: string
  quantity: number
  unit_name?: string
  remark?: string
  part_id?: number
  resolved_part_name?: string
  resolved_parent_part_id?: number
  is_new_part: boolean
  has_existing_bom: boolean
  status: 'valid' | 'warning' | 'error'
  messages: string[]
}

export interface BOMUploadValidateResponse {
  is_valid: boolean
  total_rows: number
  valid_count: number
  warning_count: number
  error_count: number
  new_part_count: number
  overwrite_count: number
  items: BOMUploadValidationItem[]
  parent_parts: Array<{ part_id: number; part_number: string; part_name: string }>
}

export interface BOMUploadResult {
  success: boolean
  message: string
  total: number
  created_count: number
  skipped_count: number
  overwrite_count: number
  new_part_count: number
  error_count: number
  errors: Array<{ row: number; part_no: string; error: string }>
  parent_part_ids: number[]
}
