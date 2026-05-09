import { apiClient } from '@/shared/lib/api/client'

interface ExportRequest {
  config_path?: string
  export_types?: string[]
  include_transform?: boolean
}

interface ExportResponse {
  job_id: string
  status: string
  message: string
  started_at: string
}

interface ExportMetrics {
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

async function executeExport(
  request: ExportRequest = {}
): Promise<ExportResponse> {
  const response = await apiClient.post('/export/execute', request)
  return response.data
}

async function getExportStatus(jobId: string): Promise<ExportStatus> {
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

export async function getActiveExportJob(): Promise<ExportStatus | null> {
  const response = await apiClient.get('/export/active')
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
