// @vitest-environment jsdom

import { act, useEffect, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  type UseWidgetConfigReturn,
  useWidgetConfig,
} from './useWidgetConfig'

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

describe('useWidgetConfig', () => {
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
        <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
      )
    })
  }

  it('rolls back transform duplication when export creation fails', async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url === '/api/config/transform' && !init) {
        return Promise.resolve(
          jsonResponse({
            content: [
              {
                group_by: 'taxons',
                widgets_data: {
                  richness: {
                    plugin: 'field_aggregator',
                    params: { field: 'id' },
                  },
                },
              },
            ],
          })
        )
      }

      if (url === '/api/config/export' && !init) {
        return Promise.resolve(
          jsonResponse({
            content: {
              exports: [
                {
                  name: 'web_pages',
                  exporter: 'html_page_exporter',
                  groups: [
                    {
                      group_by: 'taxons',
                      widgets: [
                        {
                          plugin: 'bar_plot',
                          data_source: 'richness',
                          title: { fr: 'Richesse', en: 'Richness' },
                          description: { fr: "Nombre d'espèces", en: 'Species count' },
                          params: { x_axis: 'name' },
                        },
                      ],
                    },
                  ],
                },
              ],
            },
          })
        )
      }

      if (
        url === '/api/config/transform/taxons/widgets/richness_copy' &&
        init?.method === 'PUT'
      ) {
        return Promise.resolve(jsonResponse({ success: true }))
      }

      if (
        url === '/api/config/export/taxons/widgets/richness_copy' &&
        init?.method === 'PUT'
      ) {
        return Promise.resolve(jsonResponse({ detail: 'Export failed' }, { status: 500 }))
      }

      if (
        url === '/api/config/transform/taxons/widgets/richness_copy' &&
        init?.method === 'DELETE'
      ) {
        return Promise.resolve(jsonResponse({ success: true }))
      }

      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    let hook: UseWidgetConfigReturn | null = null
    function Probe() {
      const value = useWidgetConfig('taxons')
      useEffect(() => {
        hook = value
      }, [value])
      return null
    }

    renderWithClient(<Probe />)
    await flushQueries()

    expect(hook?.configuredWidgets).toHaveLength(1)

    let duplicated = true
    await act(async () => {
      duplicated = await hook!.duplicateWidget('richness', 'richness_copy')
    })

    expect(duplicated).toBe(false)

    const exportCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        url === '/api/config/export/taxons/widgets/richness_copy' &&
        init?.method === 'PUT',
    )
    expect(exportCall).toBeDefined()
    expect(JSON.parse(exportCall?.[1]?.body as string).title).toEqual({
      fr: 'Richesse (copie)',
      en: 'Richness (copie)',
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/transform/taxons/widgets/richness_copy',
      { method: 'DELETE' },
    )
  })
})
