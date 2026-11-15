import apiClient from './client'

export interface AnnouncementAttachment {
  id: number
  original_name: string
  file_size: number
  content_type?: string | null
  download_url: string
  created_at: string
}

export interface AnnouncementListItem {
  id: number
  title: string
  is_pinned: boolean
  target_departments?: string[] | null
  published_at: string
  is_active: boolean
  created_by: number
  author_name?: string | null
  attachment_count: number
  read_count: number
  is_unread: boolean
}

export interface AnnouncementListResponse {
  items: AnnouncementListItem[]
  total: number
  page: number
  size: number
  unread_total: number
}

export interface AnnouncementDetail {
  id: number
  title: string
  body: string
  is_pinned: boolean
  target_departments?: string[] | null
  published_at: string
  is_active: boolean
  created_by: number
  author_name?: string | null
  created_at: string
  updated_at?: string | null
  attachments: AnnouncementAttachment[]
  is_unread: boolean
  read_count: number
}

export interface ReadReceipt {
  user_id: number
  name?: string | null
  department?: string | null
  read_at: string
}

export interface UnreadUser {
  user_id: number
  name?: string | null
  department?: string | null
}

export interface ReadReceiptList {
  announcement_id: number
  total_targeted: number
  read_count: number
  read: ReadReceipt[]
  unread: UnreadUser[]
}

export interface AnnouncementPayload {
  title: string
  body: string
  is_pinned: boolean
  target_departments?: string[] | null
}

export const announcementApi = {
  list: async (params: { page?: number; size?: number; q?: string; include_inactive?: boolean } = {}): Promise<AnnouncementListResponse> =>
    (await apiClient.get('/announcements', { params })).data,

  unreadCount: async (): Promise<number> =>
    (await apiClient.get('/announcements/unread-count')).data.unread_total,

  detail: async (id: number): Promise<AnnouncementDetail> =>
    (await apiClient.get(`/announcements/${id}`)).data,

  create: async (payload: AnnouncementPayload): Promise<AnnouncementDetail> =>
    (await apiClient.post('/announcements', payload)).data,

  update: async (id: number, payload: Partial<AnnouncementPayload> & { is_active?: boolean }): Promise<AnnouncementDetail> =>
    (await apiClient.put(`/announcements/${id}`, payload)).data,

  remove: async (id: number, hard = false): Promise<void> => {
    await apiClient.delete(`/announcements/${id}`, { params: { hard } })
  },

  uploadAttachment: async (id: number, file: File, onProgress?: (p: number) => void): Promise<AnnouncementAttachment> => {
    const form = new FormData()
    form.append('file', file)
    const res = await apiClient.post(`/announcements/${id}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
    return res.data
  },

  deleteAttachment: async (id: number, attId: number): Promise<void> => {
    await apiClient.delete(`/announcements/${id}/attachments/${attId}`)
  },

  // 인증 토큰을 실어 blob 으로 받는다(일반 링크는 토큰 미포함 → 401)
  downloadAttachment: async (id: number, attId: number) =>
    apiClient.get(`/announcements/${id}/attachments/${attId}/download`, { responseType: 'blob' }),

  reads: async (id: number): Promise<ReadReceiptList> =>
    (await apiClient.get(`/announcements/${id}/reads`)).data,
}
