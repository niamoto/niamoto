import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchGroups,
  fetchProjectFiles,
  fetchSiteConfig,
  fetchTemplates,
  previewGroupIndex,
  previewMarkdown,
  previewTemplate,
  updateGroupIndexConfig,
  updateSiteConfig,
} from './siteConfigApi'
import { siteConfigQueryKeys } from './queryKeys'
import type { GroupIndexConfig, GroupIndexPreviewRequest, SiteConfigUpdate } from './types'

export function useSiteConfig() {
  return useQuery({
    queryKey: siteConfigQueryKeys.config(),
    queryFn: fetchSiteConfig,
    staleTime: 30000,
  })
}

export function useGroups() {
  return useQuery({
    queryKey: siteConfigQueryKeys.groups(),
    queryFn: fetchGroups,
    staleTime: 30000,
  })
}

export function useUpdateSiteConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (config: SiteConfigUpdate) => updateSiteConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteConfigQueryKeys.config() })
    },
  })
}

export function useUpdateGroupIndexConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ groupName, config }: { groupName: string; config: GroupIndexConfig }) =>
      updateGroupIndexConfig(groupName, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteConfigQueryKeys.groups() })
    },
  })
}

export function useTemplates() {
  return useQuery({
    queryKey: siteConfigQueryKeys.templates(),
    queryFn: fetchTemplates,
    staleTime: 60000,
  })
}

export function useProjectFiles(folder: string) {
  return useQuery({
    queryKey: siteConfigQueryKeys.projectFiles(folder),
    queryFn: () => fetchProjectFiles(folder),
    staleTime: 30000,
    enabled: Boolean(folder),
  })
}

export function useMarkdownPreview() {
  return useMutation({
    mutationFn: (content: string) => previewMarkdown(content),
  })
}

export function useTemplatePreview() {
  return useMutation({
    mutationFn: previewTemplate,
  })
}

export function useGroupIndexPreview() {
  return useMutation({
    mutationFn: ({ groupName, request }: { groupName: string; request?: GroupIndexPreviewRequest }) =>
      previewGroupIndex(groupName, request),
  })
}
