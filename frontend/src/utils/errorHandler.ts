/**
 * API 에러 핸들링 유틸리티
 * 서버 에러를 사용자 친화적인 메시지로 변환
 */

export interface ApiError {
  response?: {
    status: number
    data?: {
      detail?: string | { msg: string }[] | { code?: string; message?: string; details?: any }
    }
  }
  request?: any
  message?: string
}

/**
 * detail에서 메시지 추출
 * @param detail - 에러 상세 정보 (문자열, 배열, 또는 객체)
 * @returns 사용자에게 표시할 메시지
 */
function extractDetailMessage(detail: any): string | null {
  if (!detail) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((err) => err.msg).join(', ')
  }
  // 객체 형태: { code, message, details }
  if (typeof detail === 'object') {
    if (detail.message) return detail.message
    if (detail.msg) return detail.msg
  }
  return null
}

/**
 * API 에러를 사용자 친화적인 메시지로 변환
 * @param error - Axios 에러 객체
 * @returns 사용자에게 표시할 에러 메시지
 */
export function handleApiError(error: ApiError): string {
  // 서버 응답이 있는 경우
  if (error.response) {
    const status = error.response.status
    const detail = error.response.data?.detail
    const detailMessage = extractDetailMessage(detail)

    // FastAPI validation error 형식 처리 (배열)
    if (Array.isArray(detail)) {
      const messages = detail.map((err) => err.msg).join(', ')
      return `입력 오류: ${messages}`
    }

    // HTTP 상태 코드별 처리
    switch (status) {
      case 400:
        return `입력 오류: ${detailMessage || '잘못된 요청입니다'}`
      case 401:
        return '인증이 필요합니다. 다시 로그인해주세요'
      case 403:
        return '이 작업을 수행할 권한이 없습니다'
      case 404:
        return detailMessage || '요청한 데이터를 찾을 수 없습니다'
      case 409:
        return `충돌 오류: ${detailMessage || '이미 존재하는 데이터입니다'}`
      case 422:
        return detailMessage || '유효성 검증 실패: 입력 데이터를 확인해주세요'
      case 500:
        return '서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요'
      case 502:
        return '서버에 연결할 수 없습니다'
      case 503:
        return '서버가 일시적으로 사용할 수 없습니다'
      default:
        return detailMessage || `오류가 발생했습니다 (코드: ${status})`
    }
  }

  // 요청이 전송되었지만 응답이 없는 경우 (네트워크 오류)
  if (error.request) {
    return '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요'
  }

  // 요청 설정 중 오류가 발생한 경우
  return error.message || '알 수 없는 오류가 발생했습니다'
}

/**
 * 에러 타입 확인
 */
export function isNetworkError(error: ApiError): boolean {
  return !!error.request && !error.response
}

export function isValidationError(error: ApiError): boolean {
  return error.response?.status === 422 || error.response?.status === 400
}

export function isNotFoundError(error: ApiError): boolean {
  return error.response?.status === 404
}

export function isServerError(error: ApiError): boolean {
  const status = error.response?.status
  return status !== undefined && status >= 500
}
