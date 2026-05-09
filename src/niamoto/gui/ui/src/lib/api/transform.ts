import { apiClient } from '@/shared/lib/api/client'

export interface TransformRequest {
  config_path?: string
  transformations?: string[]
  group_by?: string
  group_bys?: string[]
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
  phase?: string | null
  group_by?: string | null
  group_bys?: string[] | null
  started_at: string
  completed_at?: string | null
  result?: {
    metrics: {
      total_transformations: number
      completed_transformations: number
      failed_transformations: number
      total_widgets: number
      generated_files: string[]
      execution_time: number
    }
    transformations: Record<string, unknown>
  } | null
  error?: string | null
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
 * Get the currently active transform job (running or recently completed)
 */
export async function getActiveTransformJob(): Promise<TransformStatus | null> {
  const response = await apiClient.get('/transform/active')
  return response.data
}
