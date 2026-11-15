/**
 * API 클라이언트 설정
 * Axios를 사용하여 백엔드 API와 통신합니다.
 *
 * v0.12.0: 네트워크 에러 재시도 및 에러 처리 강화
 */

import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

// 재시도 설정
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // ms

// 재시도 가능한 HTTP 메서드 (읽기 전용 요청만)
const RETRYABLE_METHODS = ['get', 'head', 'options']

// 재시도 가능한 네트워크 에러 코드
const RETRYABLE_ERROR_CODES = ['ECONNABORTED', 'ETIMEDOUT', 'ENOTFOUND', 'ENETUNREACH', 'ERR_NETWORK']

// 재시도 가능한 HTTP 상태 코드
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504]

// 동적 API URL 설정: 브라우저가 접속한 호스트 기준으로 API URL 생성
// 같은 네트워크의 다른 컴퓨터에서 접속 시 자동으로 해당 서버 IP 사용
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  const frontendPort = window.location.port
  // 개발 서버(5174/5175)는 백엔드 직접 연결, 운영(도메인/Caddy)은 같은 origin의 /api/v1 사용
  if (frontendPort === '5174' || frontendPort === '5175') {
    const hostname = window.location.hostname
    return `http://${hostname}:8001/api/v1`
  }
  // 운영: Caddy가 /api/* 를 프록시하므로 같은 origin 사용
  return '/api/v1'
}

const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30초 타임아웃
})

// 재시도 가능 여부 확인
const shouldRetry = (error: AxiosError, retryCount: number): boolean => {
  // 최대 재시도 횟수 초과
  if (retryCount >= MAX_RETRIES) return false

  // 요청이 취소된 경우
  if (axios.isCancel(error)) return false

  // 읽기 전용 요청만 재시도 (POST, PUT, DELETE는 재시도 안함)
  const method = error.config?.method?.toLowerCase()
  if (method && !RETRYABLE_METHODS.includes(method)) return false

  // 네트워크 에러 확인
  if (!error.response && error.code && RETRYABLE_ERROR_CODES.includes(error.code)) {
    return true
  }

  // 재시도 가능한 HTTP 상태 코드 확인
  if (error.response && RETRYABLE_STATUS_CODES.includes(error.response.status)) {
    return true
  }

  return false
}

// 재시도 대기
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

// 요청 인터셉터 (인증 토큰 추가 등)
apiClient.interceptors.request.use(
  (config) => {
    // 재시도 카운트 초기화 (커스텀 속성)
    if (!(config as any).__retryCount) {
      (config as any).__retryCount = 0
    }
    // 인증 토큰 추가 (v0.28.0)
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 사용자 이름 헤더 추가 (v0.31.0 - 변경 이력 추적용)
    try {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        const user = JSON.parse(userStr)
        if (user?.name) {
          config.headers['X-User-Name'] = encodeURIComponent(user.name)
        }
      }
    } catch { /* ignore */ }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 응답 인터셉터 (에러 처리 및 재시도)
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  async (error: AxiosError) => {
    const config = error.config as InternalAxiosRequestConfig & { __retryCount?: number }

    if (!config) {
      return Promise.reject(error)
    }

    const retryCount = config.__retryCount || 0

    // 재시도 가능 여부 확인
    if (shouldRetry(error, retryCount)) {
      config.__retryCount = retryCount + 1

      // 지수 백오프 적용 (1초, 2초, 4초...)
      const backoffDelay = RETRY_DELAY * Math.pow(2, retryCount)
      console.warn(`API 요청 재시도 (${config.__retryCount}/${MAX_RETRIES}): ${config.url}`)

      await delay(backoffDelay)
      return apiClient(config)
    }

    // 에러 처리
    if (error.response?.status === 401 && !(config as any).__isRefresh) {
      // 토큰 갱신 시도 (v0.28.0)
      const refreshTokenStr = localStorage.getItem('refresh_token')
      if (refreshTokenStr && !config.url?.includes('/auth/')) {
        try {
          (config as any).__isRefresh = true
          const refreshRes = await apiClient.post('/auth/refresh', { refresh_token: refreshTokenStr })
          localStorage.setItem('access_token', refreshRes.data.access_token)
          localStorage.setItem('refresh_token', refreshRes.data.refresh_token)
          localStorage.setItem('user', JSON.stringify(refreshRes.data.user))
          config.headers.Authorization = `Bearer ${refreshRes.data.access_token}`
          return apiClient(config)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
        }
      }
    }

    // 네트워크 에러 콘솔 로깅
    if (!error.response) {
      console.error('네트워크 에러:', error.message)
    }

    return Promise.reject(error)
  }
)

export default apiClient

// API 상태 확인 유틸리티
export const checkApiHealth = async (): Promise<boolean> => {
  try {
    await apiClient.get('/health', { timeout: 5000 })
    return true
  } catch {
    return false
  }
}
