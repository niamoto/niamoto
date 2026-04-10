/**
 * API client for smart configuration endpoints
 */

import { apiClient } from '@/shared/lib/api/client'

type SmartConfiguredEntity = Record<string, unknown>

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

export interface AutoConfigureJobStartResponse {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export interface AutoConfigureProgressEvent {
  kind: 'stage' | 'detail' | 'finding' | 'complete' | 'error'
  message: string
  timestamp: number
  file?: string | null
  entity?: string | null
  details?: Record<string, unknown>
}

export interface AutoConfigureJobStatusResponse {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  events: AutoConfigureProgressEvent[]
  result?: AutoConfigureResponse | null
  error?: string | null
}

export type DecisionAlignment =
  | 'aligned'
  | 'heuristic_only'
  | 'ml_override'
  | 'conflict'
  | 'mixed'

export type ReviewLevel = 'stable' | 'info' | 'notice' | 'review'

export interface DecisionSummary {
  final_entity_type: string
  heuristic_entity_type: string
  heuristic_confidence: number
  ml_entity_type?: string | null
  ml_confidence?: number
  alignment?: DecisionAlignment
  review_required?: boolean
  review_level?: ReviewLevel
  review_reasons?: string[]
  review_priority?: 'normal' | 'high'
  analysis_snapshot?: {
    row_count: number
    date_columns: string[]
    geometry_columns: string[]
  }
  referenced_by?: Array<{
    from: string
    field: string
    target_field?: string
    confidence: number
    match_type?: string
  }>
  row_count?: number
  heuristic_flags?: Record<string, unknown>
  auxiliary_target?: string
  auxiliary_relation?: {
    plugin: string
    key: string
    ref_field: string
    match_field: string
  }
}

export interface AuxiliarySource {
  name: string
  data: string
  grouping: string
  relation: {
    plugin: string
    key: string
    ref_field: string
    match_field: string
  }
  source_entity?: string
}

export interface AutoConfigureResponse {
  success: boolean
  entities: {
    datasets: Record<string, SmartConfiguredEntity>
    references: Record<string, SmartConfiguredEntity>
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
  auxiliary_sources?: AuxiliarySource[]
  /** Detected columns per entity name */
  detected_columns?: Record<string, string[]>
  /** ML semantic predictions per entity, computed from sampled columns */
  ml_predictions?: Record<string, Array<{
    column: string
    concept: string
    confidence: number
    source: string
  }>>
  decision_summary?: Record<string, DecisionSummary>
  semantic_evidence?: Record<string, {
    top_predictions?: Array<{
      column: string
      concept: string
      confidence: number
      source: string
    }>
    top_roles?: Array<{
      role: string
      score: number
    }>
    top_concepts?: Array<{
      concept: string
      score: number
    }>
    date_columns?: string[]
    geometry_columns?: string[]
    hierarchy?: {
      detected?: boolean
      hierarchy_type?: string
      levels?: string[]
    }
    relationship_candidates?: Array<{
      from: string
      field: string
      target_field?: string
      confidence: number
      match_type?: string
    }>
    inferred_ml_entity_type?: string | null
    inferred_ml_confidence?: number
  }>
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

export async function startAutoConfigureJob(
  request: AutoConfigureRequest
): Promise<AutoConfigureJobStartResponse> {
  const response = await apiClient.post<AutoConfigureJobStartResponse>(
    '/smart/auto-configure/jobs',
    request
  )
  return response.data
}

export async function getAutoConfigureJob(
  jobId: string
): Promise<AutoConfigureJobStatusResponse> {
  const response = await apiClient.get<AutoConfigureJobStatusResponse>(
    `/smart/auto-configure/jobs/${jobId}`
  )
  return response.data
}

export function subscribeToAutoConfigureJobEvents(
  jobId: string,
  onEvent: (event: AutoConfigureProgressEvent) => void
): EventSource {
  const eventSource = new EventSource(`/api/smart/auto-configure/jobs/${jobId}/events`)
  eventSource.onmessage = (message) => {
    try {
      const parsed = JSON.parse(message.data) as AutoConfigureProgressEvent
      onEvent(parsed)
    } catch (error) {
      console.error('Failed to parse auto-config event:', error)
    }
  }
  return eventSource
}

/**
 * Create multiple entities at once
 */
export async function createEntitiesBulk(entities: {
  entities: {
    datasets?: Record<string, SmartConfiguredEntity>
    references?: Record<string, SmartConfiguredEntity>
    metadata?: Record<string, unknown>
  }
  auxiliary_sources?: AuxiliarySource[]
}): Promise<Record<string, unknown>> {
  const response = await apiClient.post<Record<string, unknown>>('/smart/management/entities/bulk', entities)
  return response.data
}
