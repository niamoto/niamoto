import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

interface ImportSummaryLight {
  alert_count: number
  dataset_count: number
  reference_count: number
  layer_count: number
}

export function useImportSummary(enabled = true) {
  return useQuery<ImportSummaryLight>({
    queryKey: ['import-summary-light'],
    queryFn: async () => {
      const res = await axios.get('/api/stats/summary')
      const entities = res.data.entities ?? []
      return {
        alert_count: res.data.alerts?.length ?? 0,
        dataset_count: entities.filter((entity: { entity_type: string }) => entity.entity_type === 'dataset').length,
        reference_count: entities.filter((entity: { entity_type: string }) => entity.entity_type === 'reference').length,
        layer_count: entities.filter((entity: { entity_type: string }) => entity.entity_type === 'layer').length,
      }
    },
    enabled,
    staleTime: 60_000,
    retry: 1,
  })
}
