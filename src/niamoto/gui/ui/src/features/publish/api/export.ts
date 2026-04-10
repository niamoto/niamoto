import { apiClient } from '@/shared/lib/api/client'

export interface ExportRequest {
  config_path?: string
  export_types?: string[]
  include_transform?: boolean
}

export interface ExportResponse {
  job_id: string
  status: string
  message: string
  started_at: string
}

export interface ExportMetrics {
  total_exports: number
  completed_exports: number
  failed_exports: number
  generated_pages: number
  static_site_path?: string | null
  execution_time: number
}

export interface ExportStatus {
  job_id: string
  status: string
  progress: number
  message: string
  phase?: string | null
  started_at: string
  completed_at?: string | null
  result?: {
    metrics: ExportMetrics
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    exports: Record<string, any>
    generated_paths: string[]
  } | null
  error?: string | null
}

export interface ExportJobListItem {
  job_id: string
  status: string
  started_at: string
  completed_at?: string | null
  progress: number
  message: string
  phase?: string | null
  result?: ExportStatus['result']
  error?: string | null
}

export interface ExportConfig {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  config: any
  summary: {
    total_exports: number
    export_types: Record<string, number>
  }
}

export async function executeExport(
  request: ExportRequest = {}
): Promise<ExportResponse> {
  const response = await apiClient.post('/export/execute', request)
  return response.data
}

export async function getExportStatus(jobId: string): Promise<ExportStatus> {
  const response = await apiClient.get(`/export/status/${jobId}`)
  return response.data
}

export async function listExportJobs(): Promise<{ jobs: ExportJobListItem[] }> {
  const response = await apiClient.get('/export/jobs')
  return response.data
}

export async function clearExportHistory(): Promise<{ removed: number }> {
  const response = await apiClient.delete('/export/history')
  return response.data
}

export async function cancelExportJob(jobId: string): Promise<{ message: string }> {
  const response = await apiClient.delete(`/export/jobs/${jobId}`)
  return response.data
}

export async function getExportConfig(): Promise<ExportConfig> {
  const response = await apiClient.get('/export/config')
  return response.data
}

export async function getExportMetrics(): Promise<{
  metrics: ExportMetrics
  last_run?: string | null
  job_id?: string
}> {
  const response = await apiClient.get('/export/metrics')
  return response.data
}

export async function getActiveExportJob(): Promise<ExportStatus | null> {
  const response = await apiClient.get('/export/active')
  return response.data
}

export async function executeExportCLI(): Promise<{
  job_id: string
  status: string
  message: string
}> {
  const response = await apiClient.post('/export/execute-cli')
  return response.data
}

export async function executeExportAndWait(
  request: ExportRequest = {},
  onProgress?: (progress: number, message: string, phase?: string | null) => void
): Promise<ExportStatus> {
  const { job_id } = await executeExport(request)

  return new Promise((resolve, reject) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await getExportStatus(job_id)

        if (onProgress) {
          onProgress(status.progress, status.message, status.phase)
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
