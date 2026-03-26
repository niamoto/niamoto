import { apiClient } from '@/shared/lib/api/client'
import type {
  ColumnInfo,
  QueryRequest,
  QueryResponse,
  TableInfo,
} from '@/shared/lib/api/data-types'

export type { ColumnInfo, QueryRequest, QueryResponse, TableInfo }

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

export interface EnrichmentPreviewRequest {
  taxon_name: string
  table?: string
}

export interface EnrichmentPreviewResponse {
  success: boolean
  taxon_name: string
  api_enrichment: Record<string, any>
  config_used: {
    api_url: string
    query_field: string
  }
}

/**
 * Preview API enrichment for a taxon name without saving to database
 */
export async function previewEnrichment(request: EnrichmentPreviewRequest): Promise<EnrichmentPreviewResponse> {
  const response = await apiClient.post<EnrichmentPreviewResponse>('/data/enrichment/preview', request)
  return response.data
}
