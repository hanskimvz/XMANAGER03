/**
 * 사용자(계정) 관리 API (ADMIN 전용)
 * 직원 계정의 역할/부서/직급/기본결재자/활성 설정 + 생성/수정/비밀번호초기화/삭제
 */

import apiClient from './client'

export type UserRole = 'ADMIN' | 'USER'

// 부서 코드 → 한글 라벨
export const DEPARTMENT_LABELS: Record<string, string> = {
  SALES: '영업팀',
  PRODUCTION: '생산팀',
  MANAGEMENT: '경영지원팀',
}

// 부서 select 옵션 (코드 저장, 한글 표시)
export const DEPARTMENT_OPTIONS: { value: string; label: string }[] = [
  { value: 'SALES', label: '영업팀' },
  { value: 'PRODUCTION', label: '생산팀' },
  { value: 'MANAGEMENT', label: '경영지원팀' },
]

// 직급 추천 목록 (자유 입력 + datalist)
export const POSITION_SUGGESTIONS: string[] = [
  '사원', '대리', '과장', '차장', '부장', '팀장', '이사', '대표',
]

export function departmentLabel(dept?: string | null): string {
  if (!dept) return '-'
  return DEPARTMENT_LABELS[dept] || dept
}

export interface ManagedUser {
  id: number
  username: string
  name: string
  name_en?: string | null
  email?: string | null
  role: UserRole
  department?: string | null
  position?: string | null
  approver_id?: number | null
  approver2_id?: number | null
  leave_approver_ids?: number[] | null
  leave_reference_ids?: number[] | null
  hire_date?: string | null
  resign_date?: string | null
  is_active: boolean
  last_login_at?: string | null
  created_at?: string | null
}

export interface UserCreatePayload {
  username: string
  password: string
  name: string
  name_en?: string
  email?: string
  role: UserRole
  department?: string
  position?: string
  approver_id?: number | null
  approver2_id?: number | null
  leave_approver_ids?: number[] | null
  leave_reference_ids?: number[] | null
  hire_date?: string | null
  resign_date?: string | null
}

export interface UserUpdatePayload {
  name?: string
  name_en?: string
  email?: string
  role?: UserRole
  department?: string
  position?: string
  approver_id?: number | null
  approver2_id?: number | null
  leave_approver_ids?: number[] | null
  leave_reference_ids?: number[] | null
  hire_date?: string | null
  resign_date?: string | null
  is_active?: boolean
}

export const userApi = {
  list: async (): Promise<ManagedUser[]> => {
    const res = await apiClient.get('/users')
    return res.data
  },
  create: async (payload: UserCreatePayload): Promise<ManagedUser> => {
    const res = await apiClient.post('/users', payload)
    return res.data
  },
  update: async (id: number, payload: UserUpdatePayload): Promise<ManagedUser> => {
    const res = await apiClient.put(`/users/${id}`, payload)
    return res.data
  },
  resetPassword: async (id: number, newPassword: string): Promise<void> => {
    await apiClient.post(`/users/${id}/reset-password`, { new_password: newPassword })
  },
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/users/${id}`)
  },
}
