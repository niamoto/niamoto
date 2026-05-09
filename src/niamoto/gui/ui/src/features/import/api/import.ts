import { apiClient } from '@/shared/lib/api/client'

export interface ImportJobEvent {
  timestamp: string
  kind: 'stage' | 'detail' | 'finding' | 'complete' | 'error'
  message: string
  phase?: string | null
  entity_name?: string | null
  entity_type?: string | null
  details?: ImportErrorDetails | Record<string, unknown> | null
}

export interface ImportErrorDetails {
  message: string
  error_type?: string
  user_message?: string
  traceback?: string | null
  details?: Record<string, unknown>
  cause?: {
    error_type?: string
    message?: string
    traceback?: string | null
  } | null
}

export interface ImportJobStatus {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  message?: string
  phase?: string | null
  total_entities?: number
  processed_entities?: number
  current_entity?: string | null
  current_entity_type?: string | null
  errors?: string[]
  error_details?: ImportErrorDetails | null
  warnings?: string[]
  events?: ImportJobEvent[]
  processed_records?: number
  total_records?: number
  count?: number
  imported_count?: number
  result?: Record<string, unknown> & { count?: number }
}

export interface ImportExecutionResponse {
  job_id: string
  [key: string]: unknown
}

export async function executeImportAll(resetTable: boolean = false): Promise<ImportExecutionResponse> {
  const formData = new FormData()
  formData.append('reset_table', String(resetTable))

  const response = await apiClient.post<ImportExecutionResponse>('/imports/execute/all', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })

  return response.data
}

export async function getImportStatus(jobId: string): Promise<ImportJobStatus> {
  const response = await apiClient.get<ImportJobStatus>(`/imports/jobs/${jobId}`)
  return response.data
}

export interface DeleteEntityResponse {
  success: boolean
  message: string
  table_dropped: boolean
}

export async function deleteEntity(
  entityType: 'dataset' | 'reference',
  entityName: string,
  deleteTable: boolean = false
): Promise<DeleteEntityResponse> {
  const response = await apiClient.delete<DeleteEntityResponse>(
    `/imports/entities/${entityType}/${entityName}`,
    { params: { delete_table: deleteTable } }
  )
  return response.data
}
