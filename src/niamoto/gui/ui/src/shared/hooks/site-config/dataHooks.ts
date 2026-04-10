import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchDataContent, updateDataContent } from './siteConfigApi'
import { siteConfigQueryKeys } from './queryKeys'

export function useDataContent(path: string | null | undefined) {
  return useQuery({
    queryKey: siteConfigQueryKeys.dataContent(path),
    queryFn: () => fetchDataContent(path!),
    enabled: Boolean(path),
    staleTime: 10000,
  })
}

export function useUpdateDataContent() {
  const queryClient = useQueryClient()

  return useMutation({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mutationFn: ({ path, data }: { path: string; data: any[] }) => updateDataContent(path, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: siteConfigQueryKeys.dataContent(variables.path),
      })
    },
  })
}
