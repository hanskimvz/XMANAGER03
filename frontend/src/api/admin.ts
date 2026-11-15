/**
 * 관리자 API
 * DB 백업, 복원, 동기화 기능
 */

import apiClient from './client'

export interface BackupInfo {
  filename: string
  size: number
  size_display: string
  created_at: string
  is_daily: boolean
}

export interface BackupListResponse {
  backups: BackupInfo[]
  total_count: number
  total_size: string
}

export interface BackupResponse {
  success: boolean
  message: string
  filename?: string
}

// v0.12.0: 서버 정보
export interface ServerInfo {
  name: string
  environment: 'production' | 'development'
  database_name: string
  host: string
  port: string
  is_current: boolean
}

export interface SystemInfoResponse {
  environment: string
  database: string
  storage_path: string
  backup_count: number
  total_backup_size: string
  // v0.12.0: 서버 정보 추가
  servers: ServerInfo[]
  api_version: string
  backend_host: string
  backend_port: number
}

export interface BackupRequest {
  source_db: 'production' | 'development'
}

export interface RestoreRequest {
  filename: string
  target_db: 'production' | 'development'
}

export interface SyncRequest {
  direction: 'prod_to_dev' | 'dev_to_prod'
}

// 시스템 정보 조회
export const getSystemInfo = async (): Promise<SystemInfoResponse> => {
  const response = await apiClient.get('/admin/system-info')
  return response.data
}

// 백업 목록 조회
export const getBackups = async (): Promise<BackupListResponse> => {
  const response = await apiClient.get('/admin/backups')
  return response.data
}

// 백업 생성
export const createBackup = async (request: BackupRequest): Promise<BackupResponse> => {
  const response = await apiClient.post('/admin/backup', request)
  return response.data
}

// 백업 복원
export const restoreBackup = async (request: RestoreRequest): Promise<BackupResponse> => {
  const response = await apiClient.post('/admin/restore', request)
  return response.data
}

// DB 동기화
export const syncDatabases = async (request: SyncRequest): Promise<BackupResponse> => {
  const response = await apiClient.post('/admin/sync', request)
  return response.data
}

// 백업 삭제
export const deleteBackup = async (filename: string): Promise<BackupResponse> => {
  const response = await apiClient.delete(`/admin/backups/${encodeURIComponent(filename)}`)
  return response.data
}
