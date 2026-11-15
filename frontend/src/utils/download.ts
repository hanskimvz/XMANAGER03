/**
 * 인증 헤더를 실어 파일을 받는 다운로드 유틸 (v0.41.0)
 *
 * RBAC 강제 적용(observe/enforce) 시 `window.open(url)` / `<a href>` / `<img src>` 는
 * 브라우저 네비게이션이라 Authorization 헤더를 보내지 못해 401 이 난다.
 * 여기 유틸은 apiClient(GET, responseType:'blob') 로 받아오므로 토큰이 항상 실린다.
 * RBAC_MODE=disabled 에서도 동일하게 동작(토큰 있으면 실어 보냄).
 */

import apiClient from '@/api/client'

function triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

function filenameFromResponse(res: { headers?: Record<string, unknown> }, fallback: string): string {
  const cd = res.headers?.['content-disposition'] as string | undefined
  if (cd) {
    const m = cd.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)/i)
    if (m && m[1]) {
      try { return decodeURIComponent(m[1]) } catch { return m[1] }
    }
  }
  return fallback
}

/** 절대/상대 URL을 인증 헤더와 함께 blob 으로 받아 파일 다운로드 */
export async function downloadAuthedUrl(url: string, fallbackName = 'download', params?: Record<string, unknown>) {
  const res = await apiClient.get(url, { responseType: 'blob', params })
  triggerDownload(res.data as Blob, filenameFromResponse(res, fallbackName))
}

/** 인증 헤더와 함께 blob 으로 받아 새 탭으로 열기(미리보기) */
export async function openAuthedUrl(url: string, params?: Record<string, unknown>) {
  const res = await apiClient.get(url, { responseType: 'blob', params })
  const objUrl = window.URL.createObjectURL(res.data as Blob)
  window.open(objUrl, '_blank')
  // 새 탭이 로드할 시간을 준 뒤 해제
  setTimeout(() => window.URL.revokeObjectURL(objUrl), 60000)
}

/** 인증 헤더와 함께 blob object URL 생성(img src / iframe 용). 호출측이 revoke 책임. */
export async function fetchAuthedObjectUrl(url: string, params?: Record<string, unknown>): Promise<string> {
  const res = await apiClient.get(url, { responseType: 'blob', params })
  return window.URL.createObjectURL(res.data as Blob)
}
