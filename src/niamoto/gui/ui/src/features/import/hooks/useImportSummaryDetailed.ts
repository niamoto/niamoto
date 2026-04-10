import { useQuery } from '@tanstack/react-query'
import {
  fetchImportSummary,
  type ImportSummaryDetailed,
  type ImportSummaryAlert,
  type ImportSummaryEntity,
} from '@/features/import/api/summary'
import { importQueryKeys } from '@/features/import/queryKeys'

export type { ImportSummaryAlert, ImportSummaryDetailed, ImportSummaryEntity }

export const importSummaryQueryKey = importQueryKeys.summary()

export function useImportSummaryDetailed(enabled = true) {
  return useQuery<ImportSummaryDetailed>({
    queryKey: importSummaryQueryKey,
    queryFn: fetchImportSummary,
    enabled,
    staleTime: 60000,
    retry: 1,
  })
}

export { fetchImportSummary }
