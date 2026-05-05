// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useCollectionDataOptions } from './useCollectionDataOptions'

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

describe('useCollectionDataOptions', () => {
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

  it('loads collection-scoped data options from the encoded endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        collection: {
          name: 'occurrences publication',
          label: 'Occurrences publication',
          grain: 'occurrence',
          roles: ['api', 'standard'],
          source: { type: 'dataset', name: 'occurrences' },
          review_status: 'accepted',
        },
        state: 'recommended',
        configured_outputs: [],
        available_options: [],
        primary_action: null,
        missing_evidence: [],
        sensitivity: { metadata_available: false },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    function Probe() {
      const query = useCollectionDataOptions('occurrences publication')
      return <span>{query.data?.collection.name ?? ''}</span>
    }

    renderWithClient(<Probe />)
    await flushQueries()

    expect(container?.textContent).toBe('occurrences publication')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/collections/occurrences%20publication/data-options',
    )
  })

  it('does not load without a collection name', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    function Probe() {
      const query = useCollectionDataOptions(null)
      return <span>{query.fetchStatus}</span>
    }

    renderWithClient(<Probe />)
    await flushQueries()

    expect(fetchMock).not.toHaveBeenCalled()
    expect(container?.textContent).toBe('idle')
  })
})
