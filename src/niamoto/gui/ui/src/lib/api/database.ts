import { apiClient } from './client'

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

/**
 * Get metrics for imported data
 */
export async function getImportMetrics() {
  try {
    // Fetch statistics for all key tables
    const [taxonStats, occurrencesStats, plotsStats, shapesStats] = await Promise.all([
      getTableStats('taxon_ref').catch(() => null),
      getTableStats('occurrences').catch(() => null),
      getTableStats('plot_ref').catch(() => null),
      getTableStats('shape_ref').catch(() => null)
    ])

    return {
      taxon_ref: taxonStats?.row_count || 0,
      occurrences: occurrencesStats?.row_count || 0,
      plot_ref: plotsStats?.row_count || 0,
      shape_ref: shapesStats?.row_count || 0,
      total_records: (taxonStats?.row_count || 0) +
                     (occurrencesStats?.row_count || 0) +
                     (plotsStats?.row_count || 0),
      unique_species: taxonStats?.unique_counts?.full_name || 0,
      unique_locations: plotsStats?.row_count || 0
    }
  } catch (error) {
    console.error('Failed to fetch import metrics:', error)
    return {
      taxon_ref: 0,
      occurrences: 0,
      plot_ref: 0,
      shape_ref: 0,
      total_records: 0,
      unique_species: 0,
      unique_locations: 0
    }
  }
}
