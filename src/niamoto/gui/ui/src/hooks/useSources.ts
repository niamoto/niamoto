/**
 * Hook for managing pre-calculated data sources.
 *
 * Provides functions to:
 * - List configured sources for a group
 * - Upload and validate new CSV sources
 * - Save source configuration
 * - Remove source configuration
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_BASE = '/api/sources'

// =============================================================================
// TYPES
// =============================================================================

export interface ClassObjectInfo {
  name: string
  cardinality: number
  class_names: string[]
  value_type: 'numeric' | 'categorical'
  suggested_plugin: string | null
  confidence: number
}

export interface UploadValidationResponse {
  success: boolean
  source_name: string
  file_name: string
  path: string
  delimiter: string
  row_count: number
  entity_column: string | null
  entity_count: number
  columns: string[]
  class_objects: ClassObjectInfo[]
  validation_errors: string[]
}

export interface ConfiguredSource {
  name: string
  data_path: string
  grouping: string
  relation_plugin: string
  class_object_count?: number
  is_builtin?: boolean  // True for reference entity sources
  source_type?: 'csv' | 'reference' | 'occurrences'  // Type of source
  columns?: string[]  // Available columns for reference sources
}

export interface SourcesListResponse {
  group_name: string
  sources: ConfiguredSource[]
  total: number
}

export interface SaveSourceRequest {
  source_name: string
  file_path: string
  entity_id_column: string
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

async function fetchSources(referenceName: string): Promise<SourcesListResponse> {
  const response = await fetch(`${API_BASE}/${referenceName}/sources`)
  if (!response.ok) {
    throw new Error(`Failed to fetch sources: ${response.statusText}`)
  }
  return response.json()
}

async function uploadSource(
  referenceName: string,
  file: File,
  sourceName: string
): Promise<UploadValidationResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(
    `${API_BASE}/${referenceName}/upload?source_name=${encodeURIComponent(sourceName)}`,
    {
      method: 'POST',
      body: formData,
    }
  )

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

async function saveSource(
  referenceName: string,
  request: SaveSourceRequest
): Promise<{ success: boolean; message: string; source_name: string }> {
  const response = await fetch(`${API_BASE}/${referenceName}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Save failed')
  }

  return response.json()
}

async function removeSource(
  referenceName: string,
  sourceName: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${API_BASE}/${referenceName}/sources/${encodeURIComponent(sourceName)}`,
    { method: 'DELETE' }
  )

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Remove failed')
  }

  return response.json()
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook to fetch configured sources for a reference group.
 */
export function useSources(referenceName: string) {
  return useQuery({
    queryKey: ['sources', referenceName],
    queryFn: () => fetchSources(referenceName),
    staleTime: 30000,
    enabled: !!referenceName,
  })
}

/**
 * Hook to upload and validate a pre-calculated CSV file.
 */
export function useUploadSource(referenceName: string) {
  return useMutation({
    mutationFn: ({ file, sourceName }: { file: File; sourceName: string }) =>
      uploadSource(referenceName, file, sourceName),
    // Don't invalidate on success - user needs to confirm save first
  })
}

/**
 * Hook to save a source configuration to transform.yml.
 */
export function useSaveSource(referenceName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: SaveSourceRequest) => saveSource(referenceName, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', referenceName] })
    },
  })
}

/**
 * Hook to remove a source configuration.
 */
export function useRemoveSource(referenceName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sourceName: string) => removeSource(referenceName, sourceName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', referenceName] })
    },
  })
}
