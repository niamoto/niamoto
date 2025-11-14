import { apiClient } from './client'

export interface EntitySummary {
  id: string  // Changed to string to preserve large integer precision
  name: string
  display_name?: string
}

export interface EntityDetail {
  id: string  // Changed to string to preserve large integer precision
  name: string
  group_by: string
  widgets_data: Record<string, any>
}

export interface TransformationPreview {
  entity_id: string  // Changed to string to preserve large integer precision
  entity_name: string
  group_by: string
  transformation_key: string
  transformation_data: Record<string, any>
  widget_plugin?: string
}

export interface EntityInfo {
  name: string
  kind: string
  entity_type: string
}

export interface EntityListResponse {
  datasets: string[]
  references: string[]
  all: EntityInfo[]
}

/**
 * Get available entities from EntityRegistry
 */
export async function getAvailableEntities(
  kind?: 'dataset' | 'reference'
): Promise<EntityListResponse> {
  const params = kind ? { kind } : {}
  const response = await apiClient.get<EntityListResponse>(
    `/entities/available`,
    { params }
  )
  return response.data
}

/**
 * List entities for a specific group_by (taxon, plot, or shape)
 */
export async function listEntities(
  groupBy: string,
  limit?: number
): Promise<EntitySummary[]> {
  const params = limit !== undefined ? { limit } : {}
  const response = await apiClient.get<EntitySummary[]>(
    `/entities/entities/${groupBy}`,
    { params }
  )
  return response.data
}

/**
 * Get detailed information about a specific entity including all widgets_data
 */
export async function getEntityDetail(
  groupBy: string,
  entityId: string
): Promise<EntityDetail> {
  const response = await apiClient.get<EntityDetail>(
    `/entities/entity/${groupBy}/${entityId}`
  )
  return response.data
}

/**
 * Get preview of a specific transformation for an entity
 */
export async function getTransformationPreview(
  groupBy: string,
  entityId: string,
  transformKey: string
): Promise<TransformationPreview> {
  const response = await apiClient.get<TransformationPreview>(
    `/entities/transformation/${groupBy}/${entityId}/${transformKey}`
  )
  return response.data
}
