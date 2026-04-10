import { useQuery } from '@tanstack/react-query'
import { fetchDatasets, type DatasetInfo } from '@/features/import/api/entities'
import { importQueryKeys } from '@/features/import/queryKeys'

export type { DatasetInfo }

export function useDatasets() {
  return useQuery({
    queryKey: importQueryKeys.entities.datasets(),
    queryFn: fetchDatasets,
    staleTime: 30000,
  })
}

export function useDataset(name: string | null) {
  const { data, ...rest } = useDatasets()

  const dataset = name ? data?.datasets.find((item) => item.name === name) : undefined

  return {
    ...rest,
    data: dataset,
    allDatasets: data?.datasets ?? [],
  }
}
