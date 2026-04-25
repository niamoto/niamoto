import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/lib/api/client'

export interface JobHistoryEntry {
  id: string
  type: 'import' | 'transform' | 'export' | string
  status: 'completed' | 'failed' | 'cancelled' | string
  group_by?: string | null
  group_bys?: string[] | null
  started_at: string
  completed_at?: string | null
  updated_at?: string | null
  progress?: number
  message?: string
  phase?: string | null
  error?: string | null
  result?: Record<string, unknown> | null
}

export function usePipelineHistory(limit = 10) {
  return useQuery<JobHistoryEntry[]>({
    queryKey: ['pipeline-history', limit],
    queryFn: async () => {
      const response = await apiClient.get('/pipeline/history', { params: { limit } })
      const data = response.data
      return Array.isArray(data) ? data : []
    },
    staleTime: 30_000,
    refetchOnMount: 'always',
    retry: 1,
  })
}
