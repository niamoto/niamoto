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
  created_at?: number
  started_at?: number | null
  completed_at?: number | null
  elapsed_seconds?: number
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
  mode?: 'merge' | 'replace'
}): Promise<Record<string, unknown>> {
  const response = await apiClient.post<Record<string, unknown>>('/smart/management/entities/bulk', entities)
  return response.data
}
