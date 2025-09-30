import { apiClient } from './client'

export interface TableInfo {
  name: string
  count: number
  description: string
  columns: string[]
}

export interface QueryRequest {
  table: string
  columns?: string[]
  where?: string
  order_by?: string
  limit?: number
  offset?: number
}

export interface QueryResponse {
  columns: string[]
  rows: Array<Record<string, any>>
  total_count: number
  page_count: number
}

export interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  default: string | null
}

/**
 * Get list of all database tables with metadata
 */
export async function getTables(): Promise<TableInfo[]> {
  const response = await apiClient.get<TableInfo[]>('/data/tables')
  return response.data
}

/**
 * Query a database table
 */
export async function queryTable(request: QueryRequest): Promise<QueryResponse> {
  const response = await apiClient.post<QueryResponse>('/data/query', request)
  return response.data
}

/**
 * Get column information for a specific table
 */
export async function getTableColumns(tableName: string): Promise<{ table: string; columns: ColumnInfo[] }> {
  const response = await apiClient.get<{ table: string; columns: ColumnInfo[] }>(`/data/tables/${tableName}/columns`)
  return response.data
}
