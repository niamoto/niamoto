import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export type FreshnessStatus = 'fresh' | 'stale' | 'never_run' | 'running' | 'error'

export interface EntityStatus {
  name: string
  status: FreshnessStatus
  last_run_at: string | null
  reason: string | null
}

export interface StageSummary {
  // Data stage
  entities?: Array<{ name: string; row_count: number }>
  // Groups stage
  groups?: Array<{ name: string; entity_count: number | null }>
  // Site stage
  title?: string
  page_count?: number
  language_count?: number
  languages?: string[]
  // Publication stage
  html_page_count?: number
  total_size_mb?: number
}

export interface StageStatus {
  status: FreshnessStatus
  last_run_at: string | null
  items: EntityStatus[]
  summary: StageSummary | null
  last_job_duration_s: number | null
}

export interface RunningJob {
  id: string
  type: string
  group_by: string | null
  progress: number
  message: string
  started_at: string
}

export interface PipelineStatus {
  data: StageStatus
  groups: StageStatus
  site: StageStatus
  publication: StageStatus
  running_job: RunningJob | null
}

export function usePipelineStatus(enabled = true) {
  return useQuery<PipelineStatus>({
    queryKey: ['pipeline-status'],
    queryFn: async () => {
      const response = await axios.get('/api/pipeline/status')
      return response.data
    },
    enabled,
    refetchInterval: 30_000, // Poll every 30s
    staleTime: 10_000,       // Consider fresh for 10s
    retry: 1,
  })
}
