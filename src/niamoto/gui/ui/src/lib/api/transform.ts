import { apiClient } from './client'

export interface TransformRequest {
  config_path?: string
  transformations?: string[]
}

export interface TransformResponse {
  job_id: string
  status: string
  message: string
  started_at: string
}

export interface TransformStatus {
  job_id: string
  status: string
  progress: number
  message: string
  started_at: string
  completed_at?: string | null
  result?: {
    metrics: TransformMetrics
    transformations: Record<string, any>
  } | null
  error?: string | null
}

export interface TransformMetrics {
  total_transformations: number
  completed_transformations: number
  failed_transformations: number
  total_widgets: number
  generated_files: string[]
  execution_time: number
}

export interface TransformConfig {
  config: any
  summary: {
    total_widgets: number
    widget_types: Record<string, number>
  }
}

/**
 * Execute transformations
 */
export async function executeTransform(
  request: TransformRequest = {}
): Promise<TransformResponse> {
  const response = await apiClient.post('/transform/execute', request)
  return response.data
}

/**
 * Get transform job status
 */
export async function getTransformStatus(jobId: string): Promise<TransformStatus> {
  const response = await apiClient.get(`/transform/status/${jobId}`)
  return response.data
}

/**
 * List all transform jobs
 */
export async function listTransformJobs(): Promise<{
  jobs: Array<{
    job_id: string
    status: string
    started_at: string
    completed_at?: string | null
    progress: number
    message: string
  }>
}> {
  const response = await apiClient.get('/transform/jobs')
  return response.data
}

/**
 * Cancel a transform job
 */
export async function cancelTransformJob(jobId: string): Promise<{ message: string }> {
  const response = await apiClient.delete(`/transform/jobs/${jobId}`)
  return response.data
}

/**
 * Get transform configuration
 */
export async function getTransformConfig(): Promise<TransformConfig> {
  const response = await apiClient.get('/transform/config')
  return response.data
}

/**
 * Get metrics from last completed transform
 */
export async function getTransformMetrics(): Promise<{
  metrics: TransformMetrics
  last_run?: string | null
  job_id?: string
}> {
  const response = await apiClient.get('/transform/metrics')
  return response.data
}

/**
 * Execute transform and wait for completion
 */
export async function executeTransformAndWait(
  request: TransformRequest = {},
  onProgress?: (progress: number, message: string) => void
): Promise<TransformStatus> {
  // Start the transform
  const { job_id } = await executeTransform(request)

  // Poll for status
  return new Promise((resolve, reject) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await getTransformStatus(job_id)

        if (onProgress) {
          onProgress(status.progress, status.message)
        }

        if (status.status === 'completed') {
          clearInterval(pollInterval)
          resolve(status)
        } else if (status.status === 'failed') {
          clearInterval(pollInterval)
          reject(new Error(status.error || 'Transform failed'))
        }
      } catch (error) {
        clearInterval(pollInterval)
        reject(error)
      }
    }, 1000)
  })
}
