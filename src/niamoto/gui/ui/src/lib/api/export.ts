import { apiClient } from './client'

export interface ExportRequest {
  config_path?: string
  export_types?: string[]
}

export interface ExportResponse {
  job_id: string
  status: string
  message: string
  started_at: string
}

export interface ExportStatus {
  job_id: string
  status: string
  progress: number
  message: string
  started_at: string
  completed_at?: string | null
  result?: {
    metrics: ExportMetrics
    exports: Record<string, any>
    generated_paths: string[]
  } | null
  error?: string | null
}

export interface ExportMetrics {
  total_exports: number
  completed_exports: number
  failed_exports: number
  generated_pages: number
  static_site_path?: string | null
  execution_time: number
}

export interface ExportConfig {
  config: any
  summary: {
    total_exports: number
    export_types: Record<string, number>
  }
}

/**
 * Execute exports
 */
export async function executeExport(
  request: ExportRequest = {}
): Promise<ExportResponse> {
  const response = await apiClient.post('/export/execute', request)
  return response.data
}

/**
 * Get export job status
 */
export async function getExportStatus(jobId: string): Promise<ExportStatus> {
  const response = await apiClient.get(`/export/status/${jobId}`)
  return response.data
}

/**
 * List all export jobs
 */
export async function listExportJobs(): Promise<{
  jobs: Array<{
    job_id: string
    status: string
    started_at: string
    completed_at?: string | null
    progress: number
    message: string
  }>
}> {
  const response = await apiClient.get('/export/jobs')
  return response.data
}

/**
 * Cancel an export job
 */
export async function cancelExportJob(jobId: string): Promise<{ message: string }> {
  const response = await apiClient.delete(`/export/jobs/${jobId}`)
  return response.data
}

/**
 * Get export configuration
 */
export async function getExportConfig(): Promise<ExportConfig> {
  const response = await apiClient.get('/export/config')
  return response.data
}

/**
 * Get metrics from last completed export
 */
export async function getExportMetrics(): Promise<{
  metrics: ExportMetrics
  last_run?: string | null
  job_id?: string
}> {
  const response = await apiClient.get('/export/metrics')
  return response.data
}

/**
 * Execute export using CLI command
 */
export async function executeExportCLI(): Promise<{
  job_id: string
  status: string
  message: string
}> {
  const response = await apiClient.post('/export/execute-cli')
  return response.data
}

/**
 * Execute export and wait for completion
 */
export async function executeExportAndWait(
  request: ExportRequest = {},
  onProgress?: (progress: number, message: string) => void
): Promise<ExportStatus> {
  // Start the export
  const { job_id } = await executeExport(request)

  // Poll for status
  return new Promise((resolve, reject) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await getExportStatus(job_id)

        if (onProgress) {
          onProgress(status.progress, status.message)
        }

        if (status.status === 'completed') {
          clearInterval(pollInterval)
          resolve(status)
        } else if (status.status === 'failed') {
          clearInterval(pollInterval)
          reject(new Error(status.error || 'Export failed'))
        }
      } catch (error) {
        clearInterval(pollInterval)
        reject(error)
      }
    }, 1000)
  })
}
