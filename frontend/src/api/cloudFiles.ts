/**
 * 파일 허브 (Nextcloud 동기화 폴더 브라우저) API — v0.81.0 / Phase 1b
 *
 * 백엔드 `/cloud-files` 라우터와 통신. 모든 경로는 NEXTCLOUD_BASE_PATH 내부(../ 차단).
 * 접근 통제는 백엔드 _guard("sales") — 영업 권한 상속.
 */
import apiClient from './client'

export interface CloudItem {
  name: string
  is_dir: boolean
  size: number
  mtime: number // epoch seconds
}

export interface CloudEntry {
  scope: 'customer' | 'order'
  path: string
  items: CloudItem[]
  managed?: boolean // true=전용 트리(자동), false=수동 링크된 레거시 폴더
}

export interface CloudListing {
  path: string
  items: CloudItem[]
}

export const cloudFilesApi = {
  // 거래처 루트 폴더 보장(ensure)·반환 + 목록
  entryCustomer: (customerId: number) =>
    apiClient.get<CloudEntry>('/cloud-files/entry', {
      params: { scope: 'customer', customer_id: customerId },
    }),

  // 주문(PI) 폴더(01~06) 보장·반환 + 목록
  entryOrder: (documentId: number) =>
    apiClient.get<CloudEntry>('/cloud-files/entry', {
      params: { scope: 'order', document_id: documentId },
    }),

  // 하위 폴더 목록(탐색·브레드크럼)
  list: (path: string) =>
    apiClient.get<CloudListing>('/cloud-files/list', { params: { path } }),

  // 폴더에 파일 업로드(동일명 자동 (n) 접미사)
  upload: (path: string, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return apiClient.post<{ message: string; name: string; path: string }>(
      '/cloud-files/upload',
      fd,
      { params: { path }, headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },

  // 하위 폴더 생성
  mkdir: (path: string, name: string) =>
    apiClient.post<{ message: string; path: string }>('/cloud-files/mkdir', null, {
      params: { path, name },
    }),

  // 파일 삭제(폴더 삭제 불가)
  remove: (path: string) => apiClient.delete('/cloud-files', { params: { path } }),

  // 레거시(기존) 폴더 수동 연결 — 파일함이 이 경로를 가리키게
  link: (scope: 'customer' | 'order', id: number, path: string) =>
    apiClient.post<CloudEntry>('/cloud-files/link', null, {
      params: {
        scope,
        path,
        ...(scope === 'customer' ? { customer_id: id } : { document_id: id }),
      },
    }),

  // 수동 연결 해제 — 다음 진입 시 전용 트리(자동)로 복귀
  unlink: (scope: 'customer' | 'order', id: number) =>
    apiClient.post<{ ok: boolean }>('/cloud-files/unlink', null, {
      params: { scope, ...(scope === 'customer' ? { customer_id: id } : { document_id: id }) },
    }),

  // 인증 헤더 실은 blob 미리보기 URL (사용 후 revoke 필수)
  previewBlobUrl: async (path: string): Promise<{ url: string; mimetype: string }> => {
    const res = await apiClient.get('/cloud-files/preview', {
      params: { path },
      responseType: 'blob',
    })
    const mimetype =
      (res.headers['content-type'] as string) || 'application/octet-stream'
    const blob = new Blob([res.data], { type: mimetype })
    return { url: URL.createObjectURL(blob), mimetype }
  },

  // 다운로드(파일로 저장)
  download: async (path: string, filename: string) => {
    const res = await apiClient.get('/cloud-files/download', {
      params: { path },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
}
