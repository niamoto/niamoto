import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  applyWidgetProposals,
  fetchWidgetProposals,
  previewWidgetProposals,
  type WidgetProposalSelection,
} from '@/features/collections/api/widget-proposals'

export const widgetProposalsQueryKey = ['collection-widget-proposals'] as const

export function useWidgetProposals(
  collectionName?: string | null,
  options: { enabled?: boolean } = {},
) {
  const queryClient = useQueryClient()
  const enabled = Boolean(collectionName) && (options.enabled ?? true)

  const query = useQuery({
    queryKey: [...widgetProposalsQueryKey, collectionName],
    queryFn: () => fetchWidgetProposals(collectionName || ''),
    enabled,
    staleTime: 30000,
  })

  const previewMutation = useMutation({
    mutationFn: (selections: WidgetProposalSelection[]) =>
      previewWidgetProposals(collectionName || '', selections),
  })

  const applyMutation = useMutation({
    mutationFn: ({
      selections,
      previewToken,
    }: {
      selections: WidgetProposalSelection[]
      previewToken?: string | null
    }) => applyWidgetProposals(collectionName || '', selections, previewToken),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...widgetProposalsQueryKey, collectionName],
      })
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
