/**
 * 작업지시서 공정 작업 API
 * v0.29.0
 */

import apiClient from './client'

export interface WorkOrderTask {
  id: number
  work_order_id: number
  task_name: string
  assigned_team?: string
  status: string
  sort_order: number
  started_at?: string
  completed_at?: string
  remarks?: string
  created_at: string
}

export interface WorkOrderTaskCreate {
  task_name: string
  assigned_team?: string
  sort_order?: number
  remarks?: string
}

export const taskStatusLabels: Record<string, string> = {
  PENDING: '대기',
  IN_PROGRESS: '진행중',
  COMPLETED: '완료',
}

export const taskStatusStyles: Record<string, string> = {
  PENDING: 'bg-gray-100 text-gray-600',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  COMPLETED: 'bg-green-100 text-green-700',
}

export const workOrderTaskApi = {
  getTasks: (woId: number) =>
    apiClient.get<WorkOrderTask[]>(`/work-orders/${woId}/tasks`),

  createTask: (woId: number, data: WorkOrderTaskCreate) =>
    apiClient.post<WorkOrderTask>(`/work-orders/${woId}/tasks`, data),

  updateTask: (woId: number, taskId: number, data: Partial<WorkOrderTaskCreate & { status: string }>) =>
    apiClient.put<WorkOrderTask>(`/work-orders/${woId}/tasks/${taskId}`, data),

  startTask: (woId: number, taskId: number) =>
    apiClient.post<WorkOrderTask>(`/work-orders/${woId}/tasks/${taskId}/start`),

  completeTask: (woId: number, taskId: number) =>
    apiClient.post<WorkOrderTask>(`/work-orders/${woId}/tasks/${taskId}/complete`),

  deleteTask: (woId: number, taskId: number) =>
    apiClient.delete(`/work-orders/${woId}/tasks/${taskId}`),
}
