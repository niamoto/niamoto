import { apiClient } from '@/shared/lib/api/client'

export interface TableStats {
  table_name: string
  row_count: number
  column_count: number
  null_counts: Record<string, number>
  unique_counts: Record<string, number>
  data_types: Record<string, string>
}

export interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  primary_key: boolean
  foreign_key?: string | null
}

export interface TableInfo {
  name: string
  row_count: number
  columns: ColumnInfo[]
  indexes: string[]
  is_view: boolean
}

export interface DatabaseSchema {
  tables: TableInfo[]
  views: TableInfo[]
  total_size: number | null
}

export interface TablePreview {
  table_name: string
  columns: string[]
  rows: Record<string, any>[]
  total_rows: number
  preview_limit: number
}

export interface QueryResult {
  columns: string[]
  rows: Record<string, any>[]
  row_count: number
}

/**
 * Get the complete database schema
 */
export async function getDatabaseSchema(): Promise<DatabaseSchema> {
  const response = await apiClient.get('/database/schema')
  return response.data
}

/**
 * Get statistics for a specific table
 */
export async function getTableStats(tableName: string): Promise<TableStats> {
  const response = await apiClient.get(`/database/tables/${tableName}/stats`)
  return response.data
}

/**
 * Get a preview of table data
 */
export async function getTablePreview(
  tableName: string,
  limit = 100,
  offset = 0
): Promise<TablePreview> {
  const response = await apiClient.get(`/database/tables/${tableName}/preview`, {
    params: { limit, offset }
  })
  return response.data
}

/**
 * Execute a custom SQL query (read-only)
 */
export async function executeQuery(
  query: string,
  limit = 100
): Promise<QueryResult> {
  const response = await apiClient.get('/database/query', {
    params: { query, limit }
  })
  return response.data
}
