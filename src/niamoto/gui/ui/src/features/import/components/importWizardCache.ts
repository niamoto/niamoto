import type { QueryClient } from '@tanstack/react-query'

import { buildCollectionsPath } from '@/features/collections/routing'
import { widgetCandidatesQueryKey } from '@/features/collections/hooks/useWidgetCandidates'
import { importQueryKeys } from '@/features/import/queryKeys'

export async function refreshImportDependentQueries(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: importQueryKeys.all() }),
    queryClient.invalidateQueries({ queryKey: ['pipeline-status'] }),
  ])
  queryClient.removeQueries({ queryKey: ['suggestions'] })
  queryClient.removeQueries({ queryKey: ['configured-widgets'] })
  queryClient.removeQueries({ queryKey: ['widget-config'] })
  queryClient.removeQueries({ queryKey: widgetCandidatesQueryKey })
}

export function buildCollectionWidgetReviewPath(collection: string): string {
  const path = buildCollectionsPath({ type: 'collection', name: collection }, 'content')
  const separator = path.includes('?') ? '&' : '?'
  const tabParam = path.includes('tab=') ? '' : `${separator}tab=content`
  const panelSeparator = tabParam ? '&' : separator
  return `${path}${tabParam}${panelSeparator}panel=add-widget`
}
