// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useWidgetProposals } from './useWidgetProposals'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

async function flushQueries() {
  for (let index = 0; index < 5; index += 1) {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0))
    })
  }
}

describe('useWidgetProposals', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    container = null
    root = null
    vi.unstubAllGlobals()
  })

  function renderWithClient(ui: ReactNode) {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    act(() => {
      root?.render(
        <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
      )
    })
  }

  it('loads widget proposals from the encoded collection endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        collection: 'taxons with spaces',
        recommended: [],
        warnings: [],
        missing_chart: [],
        skipped: [],
        already_configured: [],
        review_only: [],
        partial: false,
        messages: [],
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    function Probe() {
      const query = useWidgetProposals('taxons with spaces')
      return <span>{query.data?.collection ?? ''}</span>
    }

    renderWithClient(<Probe />)
    await flushQueries()

    expect(container?.textContent).toBe('taxons with spaces')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/collections/taxons%20with%20spaces/widget-proposals',
      {},
    )
  })
})
