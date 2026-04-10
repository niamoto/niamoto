import { useQuery } from '@tanstack/react-query'
import { fetchReferences, type ReferenceInfo } from '@/features/import/api/entities'
import { importQueryKeys } from '@/features/import/queryKeys'

export type { ReferenceInfo }

export function useReferences() {
  return useQuery({
    queryKey: importQueryKeys.entities.references(),
    queryFn: fetchReferences,
    staleTime: 30000,
  })
}

export function useReference(name: string | null) {
  const { data, ...rest } = useReferences()

  const reference = name ? data?.references.find((item) => item.name === name) : undefined

  return {
    ...rest,
    data: reference,
    allReferences: data?.references ?? [],
  }
}
