/**
 * 파일 업로드/다운로드 API 서비스
 * 부품에 첨부되는 도면, 사진, 문서 파일을 관리합니다.
 *
 * API 엔드포인트:
 *   - POST /api/v1/parts/{part_id}/upload/drawing - 도면 업로드
 *   - POST /api/v1/parts/{part_id}/upload/photo - 사진 업로드
 *   - POST /api/v1/parts/{part_id}/upload/document - 문서 업로드
 *   - GET /api/v1/parts/{part_id}/files - 첨부파일 목록 조회
 *   - DELETE /api/v1/parts/{part_id}/files/{file_type} - 파일 삭제
 *   - GET /api/v1/files/{file_path} - 파일 다운로드/미리보기
 */

import apiClient from './client'

// 파일 타입
export type FileType = 'drawing' | 'photo' | 'document'

// 파일 정보 인터페이스
export interface FileInfo {
  file_name: string
  original_name: string
  file_type: string
  file_size: number
  file_path: string
  uploaded_at: string
  download_url: string
  preview_url: string
}

// 파일 업로드 응답
export interface FileUploadResponse {
  success: boolean
  message: string
  file_info?: FileInfo
}

// 부품 파일 목록 응답
export interface PartFilesResponse {
  part_id: number
  part_number: string
  drawing: FileInfo | null
  photo: FileInfo | null
  documents: FileInfo[]
}

// 파일 삭제 응답
export interface FileDeleteResponse {
  success: boolean
  message: string
}

// API 베이스 URL - 환경별 동적 결정
// 운영(Caddy 프록시): 같은 origin /api/v1 사용
// 개발(:5174/:5175): http://hostname:8001/api/v1 사용
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  const frontendPort = window.location.port
  if (frontendPort === '5174' || frontendPort === '5175') {
    return `http://${window.location.hostname}:8001/api/v1`
  }
  return `${window.location.origin}/api/v1`
}

// 허용 파일 형식 (config와 동기화)
export const ALLOWED_EXTENSIONS = {
  drawing: ['.pdf', '.dwg', '.dxf', '.step', '.stp', '.igs'],
  photo: ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
  document: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.hwp'],
}

// 최대 파일 크기 (200MB)
export const MAX_FILE_SIZE = 200 * 1024 * 1024

// 파일 관리 API
export const fileApi = {
  /**
   * 도면 파일 업로드
   */
  uploadDrawing: async (
    partId: number,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<FileUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<FileUploadResponse>(
      `/parts/${partId}/upload/drawing`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
          }
        },
      }
    )
    return response.data
  },

  /**
   * 사진 파일 업로드
   */
  uploadPhoto: async (
    partId: number,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<FileUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<FileUploadResponse>(
      `/parts/${partId}/upload/photo`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
          }
        },
      }
    )
    return response.data
  },

  /**
   * 문서 파일 업로드
   */
  uploadDocument: async (
    partId: number,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<FileUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<FileUploadResponse>(
      `/parts/${partId}/upload/document`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
          }
        },
      }
    )
    return response.data
  },

  /**
   * 파일 타입별 업로드 (통합)
   */
  upload: async (
    partId: number,
    fileType: FileType,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<FileUploadResponse> => {
    switch (fileType) {
      case 'drawing':
        return fileApi.uploadDrawing(partId, file, onProgress)
      case 'photo':
        return fileApi.uploadPhoto(partId, file, onProgress)
      case 'document':
        return fileApi.uploadDocument(partId, file, onProgress)
    }
  },

  /**
   * 부품 파일 목록 조회
   */
  getPartFiles: (partId: number) => {
    return apiClient.get<PartFilesResponse>(`/parts/${partId}/files`)
  },

  /**
   * 파일 삭제
   */
  delete: (partId: number, fileType: FileType, fileIndex?: number) => {
    let url = `/parts/${partId}/files/${fileType}`
    if (fileType === 'document' && fileIndex !== undefined) {
      url += `?file_index=${fileIndex}`
    }
    return apiClient.delete<FileDeleteResponse>(url)
  },

  /**
   * 다운로드 URL 생성
   */
  getDownloadUrl: (filePath: string): string => {
    return `${getApiBaseUrl()}/files/${filePath}`
  },

  /**
   * 미리보기 URL 생성
   */
  getPreviewUrl: (filePath: string): string => {
    return `${getApiBaseUrl()}/files/${filePath}?preview=true`
  },

  /**
   * 파일 다운로드 (브라우저)
   */
  downloadFile: (filePath: string, fileName?: string) => {
    const url = fileApi.getDownloadUrl(filePath)
    const link = document.createElement('a')
    link.href = url
    link.download = fileName || filePath.split('/').pop() || 'download'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  },

  /**
   * 파일 크기 포맷팅
   */
  formatFileSize: (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  },

  /**
   * 파일 확장자 추출
   */
  getFileExtension: (fileName: string): string => {
    return fileName.split('.').pop()?.toLowerCase() || ''
  },

  /**
   * 파일 확장자 유효성 검사
   */
  isValidExtension: (fileName: string, fileType: FileType): boolean => {
    const ext = '.' + fileApi.getFileExtension(fileName)
    return ALLOWED_EXTENSIONS[fileType].includes(ext.toLowerCase())
  },

  /**
   * 파일 크기 유효성 검사
   */
  isValidFileSize: (fileSize: number): boolean => {
    return fileSize <= MAX_FILE_SIZE
  },

  /**
   * 이미지 파일 여부 확인
   */
  isImageFile: (fileName: string): boolean => {
    const ext = '.' + fileApi.getFileExtension(fileName)
    return ['.jpg', '.jpeg', '.png', '.gif', '.webp'].includes(ext.toLowerCase())
  },

  /**
   * PDF 파일 여부 확인
   */
  isPdfFile: (fileName: string): boolean => {
    return fileApi.getFileExtension(fileName) === 'pdf'
  },

  /**
   * 미리보기 가능 여부 확인
   */
  canPreview: (fileName: string): boolean => {
    return fileApi.isImageFile(fileName) || fileApi.isPdfFile(fileName)
  },

  /**
   * 파일 타입별 허용 확장자 문자열 (accept 속성용)
   */
  getAcceptString: (fileType: FileType): string => {
    return ALLOWED_EXTENSIONS[fileType].join(',')
  },

  /**
   * 파일 타입별 설명
   */
  getFileTypeDescription: (fileType: FileType): string => {
    switch (fileType) {
      case 'drawing':
        return '도면 파일 (PDF, DWG, DXF, STEP, STP, IGS)'
      case 'photo':
        return '이미지 파일 (JPG, PNG, GIF, WEBP)'
      case 'document':
        return '문서 파일 (PDF, DOC, DOCX, XLS, XLSX, HWP)'
    }
  },
}
