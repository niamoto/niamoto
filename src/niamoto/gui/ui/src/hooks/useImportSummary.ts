import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

interface ImportSummaryLight {
  quality_score: number
  alert_count: number
}

export function useImportSummary(enabled = true) {
  return useQuery<ImportSummaryLight>({
    queryKey: ['import-summary-light'],
    queryFn: async () => {
      const res = await axios.get('/api/stats/summary')
      return {
        quality_score: res.data.quality_score ?? 1,
        alert_count: res.data.alerts?.length ?? 0,
      }
    },
    enabled,
    staleTime: 60_000,
    retry: 1,
  })
}
