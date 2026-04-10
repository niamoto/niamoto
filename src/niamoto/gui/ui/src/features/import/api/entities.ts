import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'

export interface DatasetInfo {
  name: string
  table_name: string
  description?: string
  schema_fields: Array<{
    name: string
    type?: string
    description?: string
  }>
  entity_count?: number
}

export interface DatasetsResponse {
  datasets: DatasetInfo[]
  total: number
}

export interface ReferenceInfo {
  name: string
  table_name: string
  kind: 'hierarchical' | 'generic' | 'spatial'
  description?: string
  schema_fields: Array<{
    name: string
    type?: string
    description?: string
  }>
  entity_count?: number
  can_enrich?: boolean
  enrichment_enabled?: boolean
}

export interface ReferencesResponse {
  references: ReferenceInfo[]
  total: number
}

export async function fetchDatasets(): Promise<DatasetsResponse> {
  try {
    const response = await apiClient.get<DatasetsResponse>('/config/datasets')
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch datasets'))
  }
}

export async function fetchReferences(): Promise<ReferencesResponse> {
  try {
    const response = await apiClient.get<ReferencesResponse>('/config/references')
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch references'))
  }
}
