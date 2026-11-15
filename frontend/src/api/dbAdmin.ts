/**
 * DB관리자 API (설정 > DB관리자)
 * DB/테이블 목록과 레코드 원본(raw data) 조회 — 읽기 전용, 관리자 전용
 */

import apiClient from './client'

export interface DatabaseInfo {
  name: string
  is_current: boolean
  size_display: string
}

export interface TableInfo {
  schema_name: string
  name: string
  kind: 'table' | 'view' | 'matview'
  estimated_rows: number | null
}

export interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  is_pk: boolean
}

export type FilterOp =
  | 'contains' | 'not_contains' | 'starts' | 'ends'
  | 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte'
  | 'is_null' | 'not_null'

export interface SortSpec {
  column: string
  direction: 'asc' | 'desc'
}

export interface FilterSpec {
  column: string
  op: FilterOp
  value?: string | null
}

export interface RowsRequest {
  database: string
  schema_name: string
  table: string
  limit: number
  offset: number
  sort: SortSpec[]
  filters: FilterSpec[]
}

export interface RowsResponse {
  columns: ColumnInfo[]
  rows: unknown[][]
  total: number
  limit: number
  offset: number
}

// 데이터베이스 목록
export const getDatabases = async (): Promise<DatabaseInfo[]> => {
  const response = await apiClient.get('/admin/db/databases')
  return response.data
}

// 테이블 목록
export const getTables = async (database: string): Promise<TableInfo[]> => {
  const response = await apiClient.get('/admin/db/tables', { params: { database } })
  return response.data
}

// 레코드 조회(제한/정렬/필터)
export const queryRows = async (request: RowsRequest): Promise<RowsResponse> => {
  const response = await apiClient.post('/admin/db/rows', request)
  return response.data
}
