/**
 * RBAC(역할/권한) 관리 API (ADMIN 전용)
 * 권한 카탈로그, 역할 CRUD, 역할 권한 교체, 사용자 역할 배정
 */

import apiClient from './client'

// 단일 권한(동작)
export interface PermissionAction {
  code: string
  action: string
  label: string
}

// 권한 그룹(모듈)
export interface PermissionGroup {
  module: string
  label: string
  actions: PermissionAction[]
}

// 역할
export interface Role {
  id: number
  code: string
  name: string
  is_system: boolean
  is_admin: boolean
  description?: string | null
  sort_order: number
  permission_codes: string[]
}

// 역할 생성 payload
export interface RoleCreatePayload {
  code: string
  name: string
  description?: string
  sort_order?: number
}

// 역할 수정 payload
export interface RoleUpdatePayload {
  name?: string
  description?: string
  sort_order?: number
}

// 사용자 역할 응답
export interface UserRolesResp {
  roles: Role[]
}

export const rbacApi = {
  // 권한 카탈로그(16모듈/54권한)
  permissions: async (): Promise<PermissionGroup[]> => {
    const res = await apiClient.get('/admin/permissions')
    return res.data
  },

  // 역할 목록
  roles: async (): Promise<Role[]> => {
    const res = await apiClient.get('/admin/roles')
    return res.data
  },

  // 역할 생성
  createRole: async (payload: RoleCreatePayload): Promise<Role> => {
    const res = await apiClient.post('/admin/roles', payload)
    return res.data
  },

  // 역할 수정 (코드/시스템역할 제약 있음)
  updateRole: async (id: number, payload: RoleUpdatePayload): Promise<Role> => {
    const res = await apiClient.put(`/admin/roles/${id}`, payload)
    return res.data
  },

  // 역할 삭제 (is_system 삭제 불가)
  deleteRole: async (id: number): Promise<void> => {
    await apiClient.delete(`/admin/roles/${id}`)
  },

  // 역할 권한 전체 교체
  setRolePermissions: async (id: number, codes: string[]): Promise<Role> => {
    const res = await apiClient.put(`/admin/roles/${id}/permissions`, {
      permission_codes: codes,
    })
    return res.data
  },

  // 사용자 역할 조회
  userRoles: async (userId: number): Promise<Role[]> => {
    const res = await apiClient.get(`/admin/users/${userId}/roles`)
    // 응답이 배열 또는 { roles: [...] } 형태 모두 허용
    const data = res.data
    return Array.isArray(data) ? data : (data?.roles ?? [])
  },

  // 사용자 역할 교체
  setUserRoles: async (userId: number, roleIds: number[]): Promise<void> => {
    await apiClient.put(`/admin/users/${userId}/roles`, { role_ids: roleIds })
  },

  // v0.47.0 모듈별 enforce 토글
  modulePolicy: async (): Promise<ModulePolicyResp> => {
    const res = await apiClient.get('/admin/module-policy')
    return res.data
  },
  setModulePolicy: async (module: string, enforced: boolean): Promise<ModulePolicyResp> => {
    const res = await apiClient.put(`/admin/module-policy/${module}`, null, { params: { enforced } })
    return res.data
  },
}

export interface ModulePolicyRow {
  module: string
  label: string
  enforced: boolean
  locked: boolean
}
export interface ModulePolicyResp {
  global_mode: string
  modules: ModulePolicyRow[]
}
