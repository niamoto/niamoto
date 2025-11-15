/**
 * API client for smart configuration endpoints
 */

import { apiClient } from './client'

export interface FileInfo {
  name: string
  path: string
  full_path: string
  size: number
  size_mb: number
  modified: number
  file_type: string
  importable: boolean
  extension: string
}

export interface DirectoryInfo {
  name: string
  path: string
  full_path: string
  file_count: number
}

export interface ScanResult {
  exists: boolean
  path: string
  files: FileInfo[]
  directories: DirectoryInfo[]
  summary: {
    total_files: number
    importable_files: number
    total_directories: number
    total_size_mb: number
    file_types: Record<string, number>
  }
}

export interface HierarchyInfo {
  detected: boolean
  levels: string[]
  column_mapping: Record<string, string>
  is_valid: boolean
  confidence: number
  level_count: number
  stats_per_level?: Record<string, {
    column: string
    unique_count: number
    sample_values: string[]
  }>
}

export interface FileAnalysis {
  filename: string
  filepath: string
  row_count: number
  columns: string[]
  column_count: number
  hierarchy: HierarchyInfo
  id_columns: string[]
  geometry_columns: string[]
  name_columns: string[]
  date_columns: string[]
  suggested_entity_type: string
  suggested_connector_type: string
  confidence: number
  extract_hierarchy_as_reference?: boolean
}

export interface AutoConfigureRequest {
  files: string[]
}

export interface AutoConfigureResponse {
  success: boolean
  entities: {
    datasets: Record<string, any>
    references: Record<string, any>
    detected_links?: Record<string, Array<{
      entity: string
      field: string
      target_field: string
      confidence?: number
      match_type?: string
    }>>
    referenced_by?: Record<string, Array<{
      from: string
      field: string
      confidence: number
    }>>
    metadata?: {
      layers?: Array<{
        name: string
        type: string
        path: string
        format?: string
        description?: string
      }>
    }
  }
  confidence: number
  warnings: string[]
}

/**
 * Scan the imports/ directory for files
 */
export async function scanImportsDirectory(): Promise<ScanResult> {
  const response = await apiClient.get<ScanResult>('/files/scan')
  return response.data
}

/**
 * Analyze a single file with smart pattern detection
 */
export async function analyzeFile(filepath: string): Promise<FileAnalysis> {
  const response = await apiClient.post<FileAnalysis>('/smart/analyze-file', {
    filepath
  })
  return response.data
}

/**
 * Detect hierarchy in a file
 */
export async function detectHierarchy(filepath: string): Promise<HierarchyInfo> {
  const response = await apiClient.post<HierarchyInfo>('/smart/detect-hierarchy', {
    filepath
  })
  return response.data
}

/**
 * Auto-configure entities from multiple files
 */
export async function autoConfigureEntities(
  request: AutoConfigureRequest
): Promise<AutoConfigureResponse> {
  const response = await apiClient.post<AutoConfigureResponse>('/smart/auto-configure', request)
  return response.data
}

/**
 * Create multiple entities at once
 */
export async function createEntitiesBulk(entities: {
  datasets?: Record<string, any>
  references?: Record<string, any>
}): Promise<any> {
  const response = await apiClient.post('/smart/management/entities/bulk', { entities })
  return response.data
}
