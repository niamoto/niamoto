import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchFileContent, updateFileContent, uploadFile } from './siteConfigApi'
import { siteConfigQueryKeys } from './queryKeys'

export function useUploadFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, folder }: { file: File; folder?: string }) => uploadFile(file, folder),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: siteConfigQueryKeys.projectFiles(variables.folder || 'files'),
      })
    },
  })
}

export function useFileContent(path: string | null | undefined) {
  return useQuery({
    queryKey: siteConfigQueryKeys.fileContent(path),
    queryFn: () => fetchFileContent(path!),
    enabled: Boolean(path),
    staleTime: 10000,
  })
}

export function useUpdateFileContent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ path, content }: { path: string; content: string }) =>
      updateFileContent(path, content),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: siteConfigQueryKeys.fileContent(variables.path),
      })
    },
  })
}
