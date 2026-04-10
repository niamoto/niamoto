import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'

export interface ColumnCompleteness {
  column: string
  type: string
  total_count: number
  null_count: number
  non_null_count: number
  completeness: number
  unique_count: number
}

export interface EntityCompleteness {
  entity: string
  columns: ColumnCompleteness[]
  overall_completeness: number
}

export interface ShapeInfo {
  table_name: string
  display_name: string
  shape_count: number
  has_geometry: boolean
  shape_types: string[]
}

export interface GeoCoverage {
  total_occurrences: number
  occurrences_with_geo: number
  geo_column: string | null
  available_shapes: ShapeInfo[]
  ready_for_analysis: boolean
}

export interface ShapeCoverageDetail {
  shape_type: string
  shape_table: string
  total_shapes: number
  occurrences_covered: number
  coverage_percent: number
}

export interface SpatialAnalysisResult {
  total_occurrences: number
  occurrences_with_geo: number
  occurrences_without_geo: number
  shape_coverage: ShapeCoverageDetail[]
  analysis_time_seconds: number
  geo_column: string | null
  status: 'success' | 'no_geo_column' | 'no_shapes' | 'error'
  message: string | null
}

export interface ShapeOccurrenceCount {
  shape_id: number
  shape_name: string
  shape_type: string
  occurrence_count: number
  percent_of_total: number
}

export interface ShapeDistributionResult {
  total_occurrences_with_geo: number
  shapes: ShapeOccurrenceCount[]
  analysis_time_seconds: number
  status: string
  message: string | null
}

export async function getEntityCompleteness(
  entityName: string
): Promise<EntityCompleteness> {
  try {
    const response = await apiClient.get<EntityCompleteness>(
      `/stats/completeness/${entityName}`
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to load completeness data'))
  }
}

export async function getGeoCoverage(): Promise<GeoCoverage> {
  try {
    const response = await apiClient.get<GeoCoverage>('/stats/geo-coverage')
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to load coverage data'))
  }
}

export async function runGeoCoverageAnalysis(): Promise<SpatialAnalysisResult> {
  try {
    const response = await apiClient.post<SpatialAnalysisResult>(
      '/stats/geo-coverage/analyze'
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Analysis failed'))
  }
}

export async function getGeoCoverageDistribution(): Promise<ShapeDistributionResult> {
  try {
    const response = await apiClient.post<ShapeDistributionResult>(
      '/stats/geo-coverage/distribution'
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to load distribution'))
  }
}
