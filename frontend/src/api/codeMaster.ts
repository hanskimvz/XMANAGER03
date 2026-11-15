/**
 * 코드 마스터 API 서비스
 *
 * v0.10.0: 품번 구조 변경 (부품코드 관리기준서 적용)
 * - 품번 구성요소: ProductLine, PartGroup
 * - 분류 속성: DevelopmentType, PartType (다중선택), DrawingType
 * - 공통 속성: Material, Treatment, Level, ProcurementType, Unit
 */

import apiClient from './client'

export interface CodeMaster {
  id: number
  code: string
  name_ko: string
  name_en?: string
  description?: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at?: string
}

// v0.12.0: Level 전용 인터페이스 (is_assembly, cost_calculation 포함)
export interface LevelCodeMaster extends CodeMaster {
  bom_level?: number
  default_unit?: string
  is_assembly: boolean  // 조립품 여부 (True: BOM관리, False: 부품관리)
  cost_calculation: string  // 단가계산방식 (MANUAL: 직접입력, BOM: 하위합산)
}

export interface CodeMasterCreate {
  code: string
  name_ko: string
  name_en?: string
  description?: string
  sort_order?: number
  is_active?: boolean
}

// ============================================================
// 품번 구성요소 API
// ============================================================

// 제품라인 (ProductLine) - 품번 구성요소
export const productLineApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/product-lines'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/product-lines/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/product-lines', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/product-lines/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/product-lines/${id}`),
}

// 품목군 (PartGroup) - 품번 구성요소
export const partGroupApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/part-groups'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/part-groups/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/part-groups', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/part-groups/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/part-groups/${id}`),
}

// ============================================================
// 분류 속성 API
// ============================================================

// 개발구분 (DevelopmentType) - 분류 속성
export const developmentTypeApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/development-types'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/development-types/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/development-types', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/development-types/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/development-types/${id}`),
}

// 부품유형 (PartType) - 분류 속성 (다중선택)
export const partTypeApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/part-types'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/part-types/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/part-types', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/part-types/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/part-types/${id}`),
}

// 도면여부 (DrawingType) - 분류 속성
export const drawingTypeApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/drawing-types'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/drawing-types/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/drawing-types', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/drawing-types/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/drawing-types/${id}`),
}

// ============================================================
// 공통 속성 API
// ============================================================

// 재질 (Material)
export const materialApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/materials'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/materials/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/materials', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/materials/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/materials/${id}`),
}

// 후처리 (Treatment)
export const treatmentApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/treatments'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/treatments/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/treatments', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/treatments/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/treatments/${id}`),
}

// 레벨 (Level) - v0.12.0: LevelCodeMaster 타입 사용
export const levelApi = {
  getAll: () => apiClient.get<LevelCodeMaster[]>('/codes/levels'),
  getById: (id: number) => apiClient.get<LevelCodeMaster>(`/codes/levels/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<LevelCodeMaster>('/codes/levels', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<LevelCodeMaster>(`/codes/levels/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/levels/${id}`),
}

// 조달구분 (ProcurementType)
export const procurementTypeApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/procurement-types'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/procurement-types/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/procurement-types', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/procurement-types/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/procurement-types/${id}`),
}

// 공급업체 구분 (SupplierType)
export const supplierTypeApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/supplier-types'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/supplier-types/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/supplier-types', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/supplier-types/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/supplier-types/${id}`),
}

// 단위 (Unit)
export const unitApi = {
  getAll: () => apiClient.get<CodeMaster[]>('/codes/units'),
  getById: (id: number) => apiClient.get<CodeMaster>(`/codes/units/${id}`),
  create: (data: CodeMasterCreate) => apiClient.post<CodeMaster>('/codes/units', data),
  update: (id: number, data: Partial<CodeMasterCreate>) =>
    apiClient.put<CodeMaster>(`/codes/units/${id}`, data),
  delete: (id: number) => apiClient.delete(`/codes/units/${id}`),
}

// ============================================================
// 코드 변경 시 품번 일괄 업데이트 API
// ============================================================

export interface AffectedPart {
  id: number
  part_number: string
  part_number_display: string
  part_name: string
}

export interface AffectedPartsResponse {
  code_type: string
  current_code: string
  affected_count: number
  parts: AffectedPart[]
  message?: string
}

export interface UpdatedPart {
  id: number
  part_name: string
  old_part_number: string
  new_part_number: string
  old_part_number_display: string
  new_part_number_display: string
}

export interface BatchUpdateResponse {
  updated_count: number
  parts: UpdatedPart[]
  message?: string
}

// 코드 타입별 테이블명 매핑
export const CODE_TYPE_TABLE_MAP: Record<string, string> = {
  'productLine': 'product-lines',
  'partGroup': 'part-groups',
  'material': 'materials',
  'treatment': 'treatments',
  'developmentType': 'development-types',
  'partType': 'part-types',
  'drawingType': 'drawing-types',
  'level': 'levels',
  'procurementType': 'procurement-types',
  'unit': 'units',
}

// 품번에 영향을 주는 코드 타입 (v0.20.0: 레벨 추가)
export const PART_NUMBER_AFFECTING_TYPES = [
  'productLine',
  'partGroup',
  'material',
  'treatment',
  'level',
]

export const codeUpdateApi = {
  /**
   * 코드 변경 시 영향받는 부품 목록 조회
   */
  getAffectedParts: (codeType: string, itemId: number) => {
    const tableName = CODE_TYPE_TABLE_MAP[codeType] || codeType
    return apiClient.get<AffectedPartsResponse>(`/codes/${tableName}/${itemId}/affected-parts`)
  },

  /**
   * 코드 변경에 따른 품번 일괄 업데이트
   */
  batchUpdatePartNumbers: (codeType: string, itemId: number, newCode: string) => {
    const tableName = CODE_TYPE_TABLE_MAP[codeType] || codeType
    return apiClient.post<BatchUpdateResponse>(
      `/codes/${tableName}/${itemId}/batch-update-part-numbers`,
      null,
      { params: { new_code: newCode } }
    )
  },

  /**
   * 해당 코드 타입이 품번에 영향을 주는지 확인
   */
  affectsPartNumber: (codeType: string): boolean => {
    return PART_NUMBER_AFFECTING_TYPES.includes(codeType)
  },
}
