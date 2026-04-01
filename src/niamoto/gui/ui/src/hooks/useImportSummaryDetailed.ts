import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/lib/api/client'

export interface ImportSummaryEntity {
  name: string
  entity_type: 'dataset' | 'reference' | 'layer' | string
  row_count: number
  column_count: number
  columns: string[]
}

export interface ImportSummaryAlert {
  level: string
  entity: string
  message: string
}

export interface ImportSummaryDetailed {
  total_entities: number
  total_rows: number
  entities: ImportSummaryEntity[]
  alerts: ImportSummaryAlert[]
}

export function useImportSummaryDetailed(enabled = true) {
  return useQuery<ImportSummaryDetailed>({
    queryKey: ['import-summary-detailed'],
    queryFn: async () => {
      const response = await apiClient.get<ImportSummaryDetailed>('/stats/summary')
      return response.data
    },
    enabled,
    staleTime: 60_000,
    retry: 1,
  })
}
