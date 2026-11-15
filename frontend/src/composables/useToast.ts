/**
 * Toast 알림 Composable
 * 사용자에게 성공/에러/정보 메시지를 토스트로 표시
 */

import { ref, reactive } from 'vue'

export interface Toast {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration: number
}

// 전역 상태
const toasts = ref<Toast[]>([])
let toastId = 0

export function useToast() {
  const addToast = (type: Toast['type'], message: string, duration = 3000): number => {
    const id = ++toastId
    toasts.value.push({ id, type, message, duration })

    // 자동 제거
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  const removeToast = (id: number) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  const success = (message: string, duration = 3000) => addToast('success', message, duration)
  const error = (message: string, duration = 5000) => addToast('error', message, duration)
  const warning = (message: string, duration = 4000) => addToast('warning', message, duration)
  const info = (message: string, duration = 3000) => addToast('info', message, duration)

  const clearAll = () => {
    toasts.value = []
  }

  // showToast 래퍼 — showToast(message, type) 형태로 호출 가능
  const showToast = (message: string, type: Toast['type'] = 'info', duration?: number) => {
    return addToast(type, message, duration)
  }

  return {
    toasts,
    addToast,
    removeToast,
    showToast,
    success,
    error,
    warning,
    info,
    clearAll
  }
}
