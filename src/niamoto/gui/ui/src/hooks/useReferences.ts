/**
 * Hook for fetching reference entities from import.yml
 *
 * References are dynamically discovered from the import configuration.
 * No hardcoded entity names - everything comes from the API.
 */

import { useQuery } from '@tanstack/react-query'

export interface ReferenceInfo {
  name: string
  table_name: string
  kind: 'hierarchical' | 'generic' | 'spatial'
  description?: string
  schema_fields: Array<{
    name: string
    type?: string
    description?: string
  }>
  entity_count?: number
}

interface ReferencesResponse {
  references: ReferenceInfo[]
  total: number
}

async function fetchReferences(): Promise<ReferencesResponse> {
  const response = await fetch('/api/config/references')
  if (!response.ok) {
    throw new Error('Failed to fetch references')
  }
  return response.json()
}

export function useReferences() {
  return useQuery({
    queryKey: ['references'],
    queryFn: fetchReferences,
    staleTime: 30000, // Cache for 30 seconds
  })
}

/**
 * Get a specific reference by name
 */
export function useReference(name: string | null) {
  const { data, ...rest } = useReferences()

  const reference = name
    ? data?.references.find((r) => r.name === name)
    : undefined

  return {
    ...rest,
    data: reference,
    allReferences: data?.references ?? [],
  }
}
