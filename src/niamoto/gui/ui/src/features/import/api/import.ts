import { isAxiosError } from 'axios'
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

// Estimate import duration based on entity type and data size
function calculateEstimatedDuration(entityType: string, dataSize: number): number {
  // Base durations in milliseconds per 1000 records
  // Adjusted for more realistic progress display
  const baseDurations: Record<string, number> = {
    reference: 8000,   // ~8s per 1000 reference records
    dataset: 10000,    // ~10s per 1000 dataset records
  }

  const baseTime = baseDurations[entityType] || 8000
  const estimatedTime = (dataSize / 1000) * baseTime

  // Minimum duration to show progress (at least 3 seconds)
  const minDuration = 3000

  // Add some buffer time for initialization and finalization
  return Math.max(minDuration, estimatedTime) + 1000 // +1s buffer
}

export interface FileAnalysis {
  rowCount: number
  columns: string[]
  encoding: string
  preview: Record<string, unknown>[]
  suggestions: Record<string, string[]>
  uniqueTaxonCount?: number
  error?: string
}

export interface ImportExecutionResponse {
  job_id: string
  [key: string]: unknown
}

export interface ImportExecutionResult extends ImportJobStatus {
  count: number
}

export interface ImportRequest {
  entity_name: string
  entity_type: 'reference' | 'dataset'  // 'reference' or 'dataset'
  reset_table?: boolean
  file?: File
}

export async function analyzeFile(file: File, entityType: string): Promise<FileAnalysis> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('entity_type', entityType)

  const response = await apiClient.post<FileAnalysis>('/files/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })

  return response.data
}

export async function executeImport(
  request: ImportRequest,
  file?: File
): Promise<ImportExecutionResponse> {
  const formData = new FormData()
  formData.append('reset_table', String(request.reset_table || false))
  const fileToUpload = file ?? request.file
  if (fileToUpload) {
    formData.append('file', fileToUpload)
  }

  let endpoint: string
  if (request.entity_type === 'reference') {
    endpoint = `/imports/execute/reference/${request.entity_name}`
  } else {
    endpoint = `/imports/execute/dataset/${request.entity_name}`
  }

  const response = await apiClient.post<ImportExecutionResponse>(endpoint, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })

  return response.data
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

export async function executeImportFromConfig(
  request: ImportRequest,
  pollInterval: number = 500,
  maxWaitTime: number = 300000,
  onProgress?: (progress: number) => void,
  dataSize?: number,
  onStatusUpdate?: (status: ImportJobStatus) => void
): Promise<ImportExecutionResult> {
  try {
    const response = await executeImport(request)
    const jobId = response.job_id

    // Use the same polling logic as executeImportAndWait
    const startTime = Date.now()
    const estimatedDuration = calculateEstimatedDuration(request.entity_type, dataSize || 1000)
    let currentProgress = 0
    let pollCount = 0
    const maxPolls = Math.ceil(maxWaitTime / pollInterval)

    while (pollCount < maxPolls) {
      if (Date.now() - startTime > maxWaitTime) {
        throw new Error('Import timed out')
      }

      const status = await getImportStatus(jobId)
      onStatusUpdate?.(status)

      if (onProgress) {
        if (typeof status.progress === 'number') {
          currentProgress = Math.max(currentProgress, status.progress)
          onProgress(Math.round(Math.min(100, currentProgress)))
        } else if (status.status === 'running') {
          const elapsed = Date.now() - startTime
          const rawProgress = (elapsed / estimatedDuration) * 100
          const logProgress = Math.log(rawProgress + 1) / Math.log(101) * 95
          currentProgress = Math.max(currentProgress, Math.min(95, logProgress))
          onProgress(Math.round(currentProgress))
        }
      }

      if (status.status === 'completed') {
        onProgress?.(100)
        return {
          ...status,
          count: status.processed_records || status.total_records || status.count || status.imported_count || status.result?.count || 0
        }
      } else if (status.status === 'failed') {
        throw new Error(status.errors?.join(', ') || 'Import failed')
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval))
      pollCount++
    }

    throw new Error('Import timed out')
  } catch (error) {
    if (isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export async function executeImportAndWait(
  request: ImportRequest,
  file?: File,
  pollInterval: number = 500, // Poll every 500ms for smoother progress
  maxWaitTime: number = 300000, // 5 minutes max
  onProgress?: (progress: number) => void,
  dataSize?: number // Number of rows or features to process
): Promise<ImportExecutionResult> {
  // Start the import and get the job ID
  const importResponse = await executeImport(request, file)
  const jobId = importResponse.job_id

  // Poll for completion
  const startTime = Date.now()
  let currentProgress = 0

  // Estimate processing speed based on entity type and data size
  const estimatedDuration = calculateEstimatedDuration(request.entity_type, dataSize || 1000)

  while (Date.now() - startTime < maxWaitTime) {
    const status = await getImportStatus(jobId)

    // Calculate estimated progress based on time elapsed and expected duration
    if (onProgress && status.status === 'running') {
      const elapsed = Date.now() - startTime

      // Calculate raw progress percentage
      const rawProgress = (elapsed / estimatedDuration) * 100

      // Use a logarithmic curve for more visible progress
      // This gives: 0->0%, 25->50%, 50->70%, 75->85%, 100->95%
      const logProgress = Math.log(rawProgress + 1) / Math.log(101) * 95

      // Ensure progress is always increasing and capped at 95%
      currentProgress = Math.max(currentProgress, Math.min(95, logProgress))
      onProgress(Math.round(currentProgress))
    }

    if (status.status === 'completed') {
      onProgress?.(100)
      return {
        ...status,
        count: status.processed_records || status.total_records || status.count || status.imported_count || status.result?.count || 0
      }
    } else if (status.status === 'failed') {
      throw new Error(status.errors?.join(', ') || 'Import failed')
    }

    // Wait before polling again
    await new Promise(resolve => setTimeout(resolve, pollInterval))
  }

  throw new Error('Import timed out')
}

export interface EntityInfo {
  name: string
  table_name: string
  kind?: string
  connector_type: string
  path: string
  links?: number
}

export interface EntitiesResponse {
  references: EntityInfo[]
  datasets: EntityInfo[]
}

export async function getEntities(): Promise<EntitiesResponse> {
  const response = await apiClient.get<EntitiesResponse>('/imports/entities')
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
