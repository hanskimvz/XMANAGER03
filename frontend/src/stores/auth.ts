/**
 * 인증 상태 관리
 * v0.28.0
 */

import { ref, computed } from 'vue'
import apiClient from '@/api/client'

export interface AuthUser {
  id: number
  username: string
  name: string
  email?: string
  role: string
  department?: string
  position?: string
  approver_id?: number | null   // v0.42.0: 디폴트 결재자 1차(기안 자동 채움)
  approver2_id?: number | null  // v0.42.0: 디폴트 결재자 2차
  leave_approver_ids?: number[] | null   // v0.51.0: 휴가 전용 결재선(휴가 기안 자동 채움)
  leave_reference_ids?: number[] | null  // v0.51.0: 휴가 전용 참조자
  permissions?: string[]   // v0.41.0: RBAC 유효 권한(와일드카드면 ['*'])
  rbac_enforced?: boolean  // v0.41.0: 서버 enforce 모드 여부
}

// 부서 코드 → 한글 라벨: 부서 마스터 캐시(api/department) 기준 + 시드 폴백.
// (빈 값은 '-' 대신 ''로 — 헤더 표시용)
import { departmentLabel as deptMasterLabel } from '@/api/department'
function departmentLabel(dept?: string): string {
  if (!dept) return ''
  return deptMasterLabel(dept)
}

const user = ref<AuthUser | null>(null)
const accessToken = ref<string | null>(null)
const refreshToken = ref<string | null>(null)

/**
 * 권한 검사 헬퍼 (컴포넌트 밖에서도 사용 가능 — 라우터 가드 등).
 * - 관리자(role ADMIN 또는 권한 '*') → 항상 true
 * - 서버가 enforce 모드가 아니면 → 항상 true (메뉴/기능을 가리지 않음)
 * - enforce 모드 → 권한 보유 여부
 */
export function can(perm: string): boolean {
  const u = user.value
  if (!u) return false
  if (u.role === 'ADMIN') return true
  const perms = u.permissions || []
  if (perms.includes('*')) return true
  if (!u.rbac_enforced) return true
  return perms.includes(perm)
}

export function canAny(perms: string[]): boolean {
  return perms.some((p) => can(p))
}

/**
 * 실제 권한 보유 여부(전역 모드 무관) — 항상 enforce되는 민감 모듈(연차 등) 메뉴 게이팅용.
 * can()은 비enforce 시 true를 반환하지만, 이 함수는 보유 권한만으로 판정한다.
 */
export function hasPermStrict(perm: string): boolean {
  const u = user.value
  if (!u) return false
  if (u.role === 'ADMIN') return true
  const perms = u.permissions || []
  return perms.includes('*') || perms.includes(perm)
}

export function hasAnyPermStrict(perms: string[]): boolean {
  return perms.some((p) => hasPermStrict(p))
}

// 초기화: localStorage에서 복원
function init() {
  const savedToken = localStorage.getItem('access_token')
  const savedRefresh = localStorage.getItem('refresh_token')
  const savedUser = localStorage.getItem('user')
  if (savedToken) accessToken.value = savedToken
  if (savedRefresh) refreshToken.value = savedRefresh
  if (savedUser) {
    try { user.value = JSON.parse(savedUser) } catch { /* ignore */ }
  }
}
init()

export function useAuth() {
  const isLoggedIn = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'ADMIN')
  const userName = computed(() => user.value?.name || '')
  const userPosition = computed(() => user.value?.position || '')
  const userDepartment = computed(() => departmentLabel(user.value?.department))
  // 이름 + 직급 (예: 홍길동 과장)
  const userDisplay = computed(() =>
    [user.value?.name, user.value?.position].filter(Boolean).join(' ')
  )

  // 최신 사용자 정보 동기화 (직급/부서 등 신규 필드 반영 — 재로그인 불필요)
  async function fetchMe() {
    if (!accessToken.value) return
    try {
      const res = await apiClient.get('/auth/me')
      user.value = res.data
      localStorage.setItem('user', JSON.stringify(res.data))
    } catch { /* 무시 */ }
  }

  async function login(username: string, password: string) {
    const res = await apiClient.post('/auth/login', { username, password })
    const data = res.data
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('user', JSON.stringify(data.user))
  }

  async function refresh() {
    if (!refreshToken.value) throw new Error('No refresh token')
    try {
      const res = await apiClient.post('/auth/refresh', { refresh_token: refreshToken.value })
      const data = res.data
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token
      user.value = data.user
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))
    } catch {
      logout()
      throw new Error('Token refresh failed')
    }
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  }

  function getAccessToken() {
    return accessToken.value
  }

  return { user, isLoggedIn, isAdmin, userName, userPosition, userDepartment, userDisplay, login, refresh, logout, fetchMe, getAccessToken }
}
