import { useQuery } from '@tanstack/react-query'
import {
  fetchImportSummary,
  importSummaryQueryKey,
  type ImportSummaryDetailed,
} from '@/features/import/hooks/useImportSummaryDetailed'

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
        dataset_count: entities.filter((entity) => entity.entity_type === 'dataset').length,
        reference_count: entities.filter((entity) => entity.entity_type === 'reference').length,
        layer_count: entities.filter((entity) => entity.entity_type === 'layer').length,
      }
    },
    enabled,
    staleTime: 60000,
    retry: 1,
  })
}
