// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useWidgetCandidates } from './useWidgetCandidates'

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

describe('useWidgetCandidates', () => {
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

  it('loads widget candidates from the encoded collection endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        collection: 'taxons with spaces',
        recommended: [],
        available: [],
        needs_review: [],
        missing_chart: [],
        skipped: [],
        configured: [],
        partial: false,
        messages: [],
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    function Probe() {
      const query = useWidgetCandidates('taxons with spaces')
      return <span>{query.data?.collection ?? ''}</span>
    }

    renderWithClient(<Probe />)
    await flushQueries()

    expect(container?.textContent).toBe('taxons with spaces')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/collections/taxons%20with%20spaces/widget-candidates',
      {},
    )
  })

  it('previews and applies candidates through the candidate endpoints', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          collection: 'taxons',
          recommended: [],
          available: [],
          needs_review: [],
          missing_chart: [],
          skipped: [],
          configured: [],
          partial: false,
          messages: [],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          collection: 'taxons',
          writes_files: false,
          preview_token: 'token-1',
          changes: [],
          conflicts: [],
          invalid: [],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          collection: 'taxons',
          success: true,
          applied: [],
          skipped: [],
          message: 'Applied',
          preview_token: 'token-1',
          written_files: [],
          backup_files: [],
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    function Probe() {
      const query = useWidgetCandidates('taxons')
      return (
        <button
          type="button"
          onClick={async () => {
            await query.preview([{ candidate_id: 'candidate-1' }])
            await query.apply({
              selections: [{ candidate_id: 'candidate-1' }],
              previewToken: 'token-1',
            })
          }}
        >
          run
        </button>
      )
    }

    renderWithClient(<Probe />)
    await flushQueries()

    const button = container?.querySelector('button')
    await act(async () => {
      button?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/collections/taxons/widget-candidates/preview',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/collections/taxons/widget-candidates/apply',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
