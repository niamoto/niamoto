/**
 * Hook for fetching dataset entities from import.yml
 *
 * Datasets are dynamically discovered from the import configuration.
 * No hardcoded entity names - everything comes from the API.
 */

import { useQuery } from '@tanstack/react-query'

export interface DatasetInfo {
  name: string
  table_name: string
  description?: string
  schema_fields: Array<{
    name: string
    type?: string
    description?: string
  }>
  entity_count?: number
}

interface DatasetsResponse {
  datasets: DatasetInfo[]
  total: number
}

async function fetchDatasets(): Promise<DatasetsResponse> {
  const response = await fetch('/api/config/datasets')
  if (!response.ok) {
    throw new Error('Failed to fetch datasets')
  }
  return response.json()
}

export function useDatasets() {
  return useQuery({
    queryKey: ['datasets'],
    queryFn: fetchDatasets,
    staleTime: 30000, // Cache for 30 seconds
  })
}

/**
 * Get a specific dataset by name
 */
export function useDataset(name: string | null) {
  const { data, ...rest } = useDatasets()

  const dataset = name
    ? data?.datasets.find((d) => d.name === name)
    : undefined

  return {
    ...rest,
    data: dataset,
    allDatasets: data?.datasets ?? [],
  }
}
