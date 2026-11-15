import apiClient from './client'

export type FreeBoardCategory = 'CHAT' | 'SUGGESTION' | 'COMPLAINT' | 'HEART'

// 분류 코드/라벨 — 백엔드 models/free_board.py 의 FREE_BOARD_CATEGORIES 와 동일하게 유지
export const FREE_BOARD_CATEGORIES: { value: FreeBoardCategory; label: string }[] = [
  { value: 'CHAT', label: '잡담' },
  { value: 'SUGGESTION', label: '건의' },
  { value: 'COMPLAINT', label: '불만' },
  { value: 'HEART', label: '속마음' },
]

export function freeBoardCategoryLabel(code: string): string {
  return FREE_BOARD_CATEGORIES.find((c) => c.value === code)?.label || code
}

export interface FreeBoardComment {
  id: number
  parent_id?: number | null
  content: string
  is_anonymous: boolean
  author_name?: string | null // 익명/삭제 시 null
  is_post_author: boolean
  is_mine: boolean
  can_delete: boolean
  is_deleted: boolean
  created_at: string
}

export interface FreeBoardListItem {
  id: number
  category: FreeBoardCategory
  title: string
  is_anonymous: boolean
  author_name?: string | null // 익명이면 null
  is_mine: boolean
  view_count: number
  comment_count: number
  created_at: string
}

export interface FreeBoardListResponse {
  items: FreeBoardListItem[]
  total: number
  page: number
  size: number
}

export interface FreeBoardDetail extends FreeBoardListItem {
  body: string
  can_edit: boolean
  can_delete: boolean
  updated_at?: string | null
  comments: FreeBoardComment[]
}

export interface FreeBoardPostPayload {
  category: FreeBoardCategory
  title: string
  body: string
  is_anonymous: boolean
}

export interface FreeBoardCommentPayload {
  content: string
  is_anonymous: boolean
  parent_id?: number | null
}

export const freeBoardApi = {
  list: async (params: { page?: number; size?: number; category?: FreeBoardCategory; q?: string } = {}): Promise<FreeBoardListResponse> =>
    (await apiClient.get('/free-board', { params })).data,

  // countView=false: 수정 직후 재조회처럼 조회수를 올리면 안 되는 경우
  detail: async (id: number, countView = true): Promise<FreeBoardDetail> =>
    (await apiClient.get(`/free-board/${id}`, { params: { count_view: countView } })).data,

  create: async (payload: FreeBoardPostPayload): Promise<FreeBoardDetail> =>
    (await apiClient.post('/free-board', payload)).data,

  update: async (id: number, payload: Partial<FreeBoardPostPayload>): Promise<FreeBoardDetail> =>
    (await apiClient.put(`/free-board/${id}`, payload)).data,

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/free-board/${id}`)
  },

  // 댓글 등록/삭제는 갱신된 글 상세(댓글 목록 포함)를 돌려준다
  addComment: async (id: number, payload: FreeBoardCommentPayload): Promise<FreeBoardDetail> =>
    (await apiClient.post(`/free-board/${id}/comments`, payload)).data,

  removeComment: async (id: number, commentId: number): Promise<FreeBoardDetail> =>
    (await apiClient.delete(`/free-board/${id}/comments/${commentId}`)).data,
}
