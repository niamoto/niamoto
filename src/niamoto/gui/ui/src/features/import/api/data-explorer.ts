/**
 * API client for data explorer endpoints
 */

import { apiClient } from '@/shared/lib/api/client'
import type {
  ColumnInfo,
  QueryRequest,
  QueryResponse,
  TableInfo,
} from '@/shared/lib/api/data-types'

export type { ColumnInfo, QueryRequest, QueryResponse, TableInfo }

export interface TableColumnsResponse {
  table: string
  columns: ColumnInfo[]
}

/**
 * List all available database tables
 */
export async function listTables(): Promise<TableInfo[]> {
  const response = await apiClient.get<TableInfo[]>('/data/tables')
  return response.data
}

/**
 * Query a database table with pagination
 */
export async function queryTable(request: QueryRequest): Promise<QueryResponse> {
  const response = await apiClient.post<QueryResponse>('/data/query', {
    table: request.table,
    columns: request.columns,
    where: request.where,
    order_by: request.order_by,
    limit: request.limit ?? 100,
    offset: request.offset ?? 0,
  })
  return response.data
}

/**
 * Get column information for a table
 */
export async function getTableColumns(tableName: string): Promise<TableColumnsResponse> {
  const response = await apiClient.get<TableColumnsResponse>(
    `/data/tables/${tableName}/columns`
  )
  return response.data
}
