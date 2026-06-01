import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  applyWidgetCandidates,
  fetchWidgetCandidates,
  previewWidgetCandidates,
  type WidgetCandidateSelection,
} from '@/features/collections/api/widget-candidates'

export const widgetCandidatesQueryKey = ['collection-widget-candidates'] as const

export function useWidgetCandidates(
  collectionName?: string | null,
  options: { enabled?: boolean } = {},
) {
  const queryClient = useQueryClient()
  const enabled = Boolean(collectionName) && (options.enabled ?? true)

  const query = useQuery({
    queryKey: [...widgetCandidatesQueryKey, collectionName],
    queryFn: () => fetchWidgetCandidates(collectionName || ''),
    enabled,
    staleTime: 30000,
  })

  const previewMutation = useMutation({
    mutationFn: (selections: WidgetCandidateSelection[]) =>
      previewWidgetCandidates(collectionName || '', selections),
  })

  const applyMutation = useMutation({
    mutationFn: ({
      selections,
      previewToken,
    }: {
      selections: WidgetCandidateSelection[]
      previewToken?: string | null
    }) => applyWidgetCandidates(collectionName || '', selections, previewToken),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...widgetCandidatesQueryKey, collectionName],
      })
      queryClient.invalidateQueries({ queryKey: ['collection-widget-proposals', collectionName] })
      queryClient.invalidateQueries({ queryKey: ['widget-config'] })
      queryClient.invalidateQueries({ queryKey: ['configured-widgets'] })
    },
  })

  return {
    ...query,
    preview: previewMutation.mutateAsync,
    previewState: previewMutation,
    apply: applyMutation.mutateAsync,
    applyState: applyMutation,
  }
}
