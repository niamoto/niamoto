import { apiClient } from './client'

export interface EntitySummary {
  id: number
  name: string
  display_name?: string
}

export interface EntityDetail {
  id: number
  name: string
  group_by: string
  widgets_data: Record<string, any>
}

export interface TransformationPreview {
  entity_id: number
  entity_name: string
  group_by: string
  transformation_key: string
  transformation_data: Record<string, any>
  widget_plugin?: string
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
  entityId: number
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
  entityId: number,
  transformKey: string
): Promise<TransformationPreview> {
  const response = await apiClient.get<TransformationPreview>(
    `/entities/transformation/${groupBy}/${entityId}/${transformKey}`
  )
  return response.data
}
