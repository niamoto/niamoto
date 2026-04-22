import { describe, expect, it } from 'vitest'

import { shouldSkipResultsRequest } from './useEnrichmentState'

describe('shouldSkipResultsRequest', () => {
  it('does not block append requests after the first loaded page', () => {
    expect(
      shouldSkipResultsRequest({
        append: true,
        showLoader: false,
        isResultsLoading: false,
        isSilentRefreshActive: false,
        currentPage: 1,
      })
    ).toBe(false)
  })

  it('still blocks silent refreshes while paginated history is open', () => {
    expect(
      shouldSkipResultsRequest({
        append: false,
        showLoader: false,
        isResultsLoading: false,
        isSilentRefreshActive: false,
        currentPage: 1,
      })
    ).toBe(true)
  })
})
