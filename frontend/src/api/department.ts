/**
 * 부서 마스터 API + 라벨/옵션 캐시 (v0.43.0)
 * - departmentApi: CRUD (목록은 공용, 생성/수정/삭제는 ADMIN)
 * - departments(ref) + loadDepartments(): 앱 전역에서 코드→이름 라벨 해석에 사용
 */
import { ref } from 'vue'
import apiClient from './client'

export type OrgType = 'EXECUTIVE' | 'DIVISION' | 'DEPARTMENT' | 'TEAM'

// 조직 유형 코드/라벨/색 — 백엔드 models/department.py 의 ORG_TYPES 와 동일하게 유지
export const ORG_TYPES: { value: OrgType; label: string; badge: string }[] = [
  { value: 'EXECUTIVE', label: '경영진', badge: 'bg-purple-600 text-white' },
  { value: 'DIVISION', label: '본부', badge: 'bg-teal-600 text-white' },
  { value: 'DEPARTMENT', label: '부서', badge: 'bg-amber-500 text-white' },
  { value: 'TEAM', label: '팀', badge: 'bg-blue-600 text-white' },
]

export function orgTypeLabel(code: string): string {
  return ORG_TYPES.find((t) => t.value === code)?.label || code
}

export function orgTypeBadge(code: string): string {
  return ORG_TYPES.find((t) => t.value === code)?.badge || 'bg-gray-500 text-white'
}

export interface Department {
  id: number
  code: string
  name: string
  is_active: boolean
  sort_order: number
  created_at?: string | null
  // 조직도 필드 (v1.04.0)
  name_en?: string | null
  org_type: OrgType
  parent_id?: number | null // null = 최상위
  manager_user_id?: number | null
  manager_name?: string | null
  description?: string | null
  member_count: number
}

export interface DepartmentCreatePayload {
  code: string
  name: string
  sort_order?: number
  name_en?: string | null
  org_type?: OrgType
  parent_id?: number | null
  manager_user_id?: number | null
  description?: string | null
}

// 상위 조직/책임자/영문명/설명은 null 을 보내면 비운다
export interface DepartmentUpdatePayload {
  name?: string
  is_active?: boolean
  sort_order?: number
  name_en?: string | null
  org_type?: OrgType
  parent_id?: number | null
  manager_user_id?: number | null
  description?: string | null
}

// 시드 부서 폴백(마스터 로드 전/실패 시)
const FALLBACK_LABELS: Record<string, string> = {
  SALES: '영업팀',
  PRODUCTION: '생산팀',
  MANAGEMENT: '경영지원팀',
}

// 전역 캐시(활성 부서)
export const departments = ref<Department[]>([])
let loaded = false

/** 활성 부서 목록 로드(1회 캐시). force 로 강제 갱신. */
export async function loadDepartments(force = false): Promise<void> {
  if (loaded && !force) return
  try {
    const res = await apiClient.get<Department[]>('/departments')
    departments.value = res.data
    loaded = true
  } catch {
    /* 로드 실패 시 폴백 라벨 사용 */
  }
}

/** 부서 코드 → 표시 이름. 마스터 우선, 없으면 시드 폴백, 그래도 없으면 코드 그대로. */
export function departmentLabel(code?: string | null): string {
  if (!code) return '-'
  const d = departments.value.find((x) => x.code === code)
  return d?.name || FALLBACK_LABELS[code] || code
}

export const departmentApi = {
  list: async (): Promise<Department[]> => (await apiClient.get('/departments')).data,
  listAll: async (): Promise<Department[]> => (await apiClient.get('/departments/all')).data,
  create: async (payload: DepartmentCreatePayload): Promise<Department> =>
    (await apiClient.post('/departments', payload)).data,
  update: async (id: number, payload: DepartmentUpdatePayload): Promise<Department> =>
    (await apiClient.put(`/departments/${id}`, payload)).data,
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/departments/${id}`)
  },
}
