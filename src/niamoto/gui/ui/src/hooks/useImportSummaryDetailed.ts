import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/lib/api/client'

export const importSummaryQueryKey = ['import-summary'] as const

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

export async function fetchImportSummary(): Promise<ImportSummaryDetailed> {
  const response = await apiClient.get<ImportSummaryDetailed>('/stats/summary')
  return response.data
}

export function useImportSummaryDetailed(enabled = true) {
  return useQuery<ImportSummaryDetailed>({
    queryKey: importSummaryQueryKey,
    queryFn: fetchImportSummary,
    enabled,
    staleTime: 60_000,
    retry: 1,
  })
}
