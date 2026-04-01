import { useQuery } from '@tanstack/react-query'
import {
  fetchImportSummary,
  importSummaryQueryKey,
  type ImportSummaryDetailed,
} from '@/hooks/useImportSummaryDetailed'

interface ImportSummaryLight {
  alert_count: number
  dataset_count: number
  reference_count: number
  layer_count: number
}

export function useImportSummary(enabled = true) {
  return useQuery<ImportSummaryDetailed, Error, ImportSummaryLight>({
    queryKey: importSummaryQueryKey,
    queryFn: fetchImportSummary,
    select: (data: ImportSummaryDetailed) => {
      const entities = data.entities ?? []
      return {
        alert_count: data.alerts?.length ?? 0,
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
