import apiClient from './client'

export type NotificationType =
  | 'APPROVAL_REQUEST'
  | 'APPROVAL_APPROVED'
  | 'APPROVAL_REJECTED'
  | 'APPROVAL_REFERENCE'
  | 'APPROVAL_RECALLED'
  | 'APPROVAL_COMMENT'
  | 'APPROVAL_EXECUTION'
  | 'APPROVAL_EXECUTED'
  | string

export interface NotificationItem {
  id: number
  type: NotificationType
  title: string
  message?: string | null
  link?: string | null
  related_type?: string | null
  related_id?: number | null
  actor_name?: string | null
  is_read: boolean
  created_at: string
}

export interface NotificationListResponse {
  items: NotificationItem[]
  total: number
  unread: number
}

export const notificationApi = {
  // 알림 목록 (+ 미읽음 수)
  list: async (params?: { limit?: number; offset?: number; unread_only?: boolean }): Promise<NotificationListResponse> =>
    (await apiClient.get('/notifications', { params })).data,

  // 미읽음 배지용 카운트
  unreadCount: async (): Promise<number> =>
    (await apiClient.get('/notifications/unread-count')).data.count,

  // 단건 읽음 처리
  markRead: async (id: number): Promise<void> => {
    await apiClient.post(`/notifications/${id}/read`)
  },

  // 전체 읽음 처리
  markAllRead: async (): Promise<void> => {
    await apiClient.post('/notifications/read-all')
  },
}
