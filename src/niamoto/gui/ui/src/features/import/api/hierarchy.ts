import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'

export type HierarchyMode = 'roots' | 'children' | 'search'

export interface HierarchyLevelSummary {
  level: string
  count: number
  orphan_count: number
}

export interface HierarchyNode {
  id: string | number
  parent_id: string | number | null
  label: string
  rank: string | null
  level: number | null
  child_count: number
  has_children: boolean
  path: string | null
}

export interface HierarchyInspection {
  reference_name: string
  table_name: string | null
  is_hierarchical: boolean
  metadata_available: boolean
  mode: HierarchyMode
  search: string | null
  parent_id: string | number | null
  total_nodes: number
  root_count: number
  orphan_count: number
  levels: HierarchyLevelSummary[]
  nodes: HierarchyNode[]
  limit: number
  offset: number
  result_count: number
  has_more: boolean
  next_offset: number | null
}

export interface HierarchyInspectionParams {
  mode?: HierarchyMode
  parentId?: string | number | null
  search?: string | null
  limit?: number
  offset?: number
}

export async function getHierarchyInspection(
  referenceName: string,
  params: HierarchyInspectionParams = {}
): Promise<HierarchyInspection> {
  try {
    const searchParams = new URLSearchParams()
    if (params.mode) searchParams.set('mode', params.mode)
    if (params.parentId != null) searchParams.set('parent_id', String(params.parentId))
    if (params.search) searchParams.set('search', params.search)
    if (params.limit) searchParams.set('limit', String(params.limit))
    if (params.offset != null) searchParams.set('offset', String(params.offset))

    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : ''
    const response = await apiClient.get<HierarchyInspection>(
      `/stats/hierarchy/${encodeURIComponent(referenceName)}${suffix}`
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to load hierarchy data'))
  }
}
