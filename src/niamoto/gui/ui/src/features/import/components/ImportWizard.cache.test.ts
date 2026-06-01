import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'

import {
  buildCollectionWidgetReviewPath,
  refreshImportDependentQueries,
} from './importWizardCache'
import { widgetCandidatesQueryKey } from '@/features/collections/hooks/useWidgetCandidates'

describe('ImportWizard cache and collection review helpers', () => {
  it('clears widget candidate queries after an import completes', async () => {
    const queryClient = new QueryClient()
    queryClient.setQueryData(widgetCandidatesQueryKey, { collection: 'taxons' })
    queryClient.setQueryData(['suggestions'], [{ id: 'old' }])
    queryClient.setQueryData(['widget-config'], { old: true })

    await refreshImportDependentQueries(queryClient)

    expect(queryClient.getQueryData(widgetCandidatesQueryKey)).toBeUndefined()
    expect(queryClient.getQueryData(['suggestions'])).toBeUndefined()
    expect(queryClient.getQueryData(['widget-config'])).toBeUndefined()
  })

  it('opens the collection content tab before the add-widget panel', () => {
    expect(buildCollectionWidgetReviewPath('taxons')).toBe(
      '/groups/taxons?tab=content&panel=add-widget',
    )
  })
})
