/**
 * 공급업체 관리 API 서비스
 */

import apiClient from './client'

// 공급업체 인터페이스
export interface Supplier {
  id: number
  supplier_code: string
  supplier_name: string
  supplier_name_en?: string
  business_number?: string
  representative?: string
  business_type?: string
  business_item?: string
  address?: string
  tel?: string
  fax?: string
  email?: string
  manager_name?: string
  manager_tel?: string
  manager_email?: string
  payment_terms?: string
  delivery_terms?: string
  credit_rating?: string
  is_active: boolean
  remark?: string
  created_at: string
  updated_at: string
}

export interface SupplierListItem {
  id: number
  supplier_code: string
  supplier_name: string
  supplier_name_en?: string
  tel?: string
  manager_name?: string
  is_active: boolean
  created_at: string
}

export interface SupplierCreate {
  supplier_code: string
  supplier_name: string
  supplier_name_en?: string
  business_number?: string
  representative?: string
  business_type?: string
  business_item?: string
  address?: string
  tel?: string
  fax?: string
  email?: string
  manager_name?: string
  manager_tel?: string
  manager_email?: string
  payment_terms?: string
  delivery_terms?: string
  credit_rating?: string
  is_active?: boolean
  remark?: string
}

export interface SupplierUpdate extends Partial<SupplierCreate> {}

export interface SupplierSearchParams {
  keyword?: string
  is_active?: boolean
  skip?: number
  limit?: number
}

// API 서비스
export const supplierApi = {
  /**
   * 공급업체 목록 조회
   */
  getAll: (params?: SupplierSearchParams) => {
    return apiClient.get<SupplierListItem[]>('/suppliers', { params })
  },

  /**
   * 공급업체 단건 조회
   */
  getById: (id: number) => {
    return apiClient.get<Supplier>(`/suppliers/${id}`)
  },

  /**
   * 공급업체 코드로 조회
   */
  getByCode: (code: string) => {
    return apiClient.get<Supplier>(`/suppliers/code/${code}`)
  },

  /**
   * 공급업체 생성
   */
  create: (data: SupplierCreate) => {
    return apiClient.post<Supplier>('/suppliers', data)
  },

  /**
   * 공급업체 수정
   */
  update: (id: number, data: SupplierUpdate) => {
    return apiClient.put<Supplier>(`/suppliers/${id}`, data)
  },

  /**
   * 공급업체 삭제
   */
  delete: (id: number) => {
    return apiClient.delete(`/suppliers/${id}`)
  },

  /**
   * 공급업체 활성화
   */
  activate: (id: number) => {
    return apiClient.patch<Supplier>(`/suppliers/${id}/activate`)
  },

  /**
   * 공급업체 비활성화
   */
  deactivate: (id: number) => {
    return apiClient.patch<Supplier>(`/suppliers/${id}/deactivate`)
  },
}
