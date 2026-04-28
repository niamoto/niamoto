import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'

export type SpatialGeometryKind = 'point' | 'polygon' | 'line' | 'mixed' | 'unknown'

export interface SpatialBoundingBox {
  min_x: number
  min_y: number
  max_x: number
  max_y: number
}

export type GeoJsonPosition = [number, number, ...number[]]

export interface GeoJsonGeometry {
  type: string
  coordinates: unknown
}

export interface SpatialMapFeature {
  type: 'Feature'
  id?: string | number | null
  geometry: GeoJsonGeometry | null
  properties: {
    id?: string | number | null
    label?: string | null
    name?: string | null
    type?: string | null
    layer?: string | null
    geometry_type?: string | null
  }
}

export interface SpatialMapLayer {
  value: string
  label: string
  feature_count: number
  with_geometry: number
}

export interface SpatialMapInspection {
  reference_name: string
  table_name: string | null
  is_mappable: boolean
  reason: string | null
  geometry_column: string | null
  geometry_storage: string | null
  geometry_kind: SpatialGeometryKind
  geometry_types: string[]
  id_column: string | null
  name_column: string | null
  type_column: string | null
  layer_column: string | null
  selected_layer: string | null
  layers: SpatialMapLayer[]
  total_features: number
  with_geometry: number
  without_geometry: number
  bounding_box: SpatialBoundingBox | null
  feature_collection: {
    type: 'FeatureCollection'
    features: SpatialMapFeature[]
  }
  limit: number
  offset: number
  result_count: number
  has_more: boolean
  next_offset: number | null
}

export interface SpatialMapParams {
  limit?: number
  offset?: number
  layer?: string | null
}

export async function getSpatialMapInspection(
  referenceName: string,
  params: SpatialMapParams = {}
): Promise<SpatialMapInspection> {
  try {
    const searchParams = new URLSearchParams()
    if (params.limit != null) searchParams.set('limit', String(params.limit))
    if (params.offset != null) searchParams.set('offset', String(params.offset))
    if (params.layer) searchParams.set('layer', params.layer)

    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : ''
    const response = await apiClient.get<SpatialMapInspection>(
      `/stats/spatial-map/${encodeURIComponent(referenceName)}${suffix}`
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to load spatial map data'))
  }
}

export function getSpatialMapRenderUrl(referenceName: string, params: SpatialMapParams = {}) {
  const searchParams = new URLSearchParams()
  if (params.limit != null) searchParams.set('limit', String(params.limit))
  if (params.layer) searchParams.set('layer', params.layer)

  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : ''
  return `/api/stats/spatial-map/${encodeURIComponent(referenceName)}/render${suffix}`
}
