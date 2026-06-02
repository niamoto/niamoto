import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import {
  InlineRefreshIndicator,
  StablePageSkeleton,
  StablePanelSkeleton,
} from './StableLoadingState'
import { getStableQueryState } from './stableQueryState'

describe('StableLoadingState', () => {
  it('separates the first load from background refreshes', () => {
    expect(getStableQueryState({ isLoading: true, isFetching: true, hasData: false }))
      .toEqual({ isInitialLoading: true, isRefreshing: false })
    expect(getStableQueryState({ isLoading: false, isFetching: true, hasData: true }))
      .toEqual({ isInitialLoading: false, isRefreshing: true })
  })

  it('renders stable skeleton surfaces without spinner motion', () => {
    const html = renderToStaticMarkup(
      <>
        <StablePageSkeleton />
        <StablePanelSkeleton />
      </>,
    )

    expect(html).toContain('data-stable-loading="page"')
    expect(html).toContain('data-stable-loading="panel"')
    expect(html).not.toContain('animate-spin')
  })

  it('keeps refresh motion inline and opt-in', () => {
    const inactiveHtml = renderToStaticMarkup(<InlineRefreshIndicator />)
    const activeHtml = renderToStaticMarkup(<InlineRefreshIndicator active />)

    expect(inactiveHtml).toBe('')
    expect(activeHtml).toContain('Actualisation')
    expect(activeHtml).toContain('animate-spin')
  })
})
