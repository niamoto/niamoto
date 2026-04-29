// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  type ApiExportGroupConfig,
  updateApiExportGroupConfig,
  useApiExportAutoConfig,
  useApiExportPreview,
} from './useApiExportConfigs'

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

describe('useApiExportConfigs', () => {
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

  it('posts group config updates to the encoded group endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        enabled: true,
        group_by: 'plots',
        detail: { pass_through: true },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const config: ApiExportGroupConfig = {
      enabled: true,
      group_by: 'plots',
      detail: { pass_through: true },
      index: { fields: [] },
    }
    const result = await updateApiExportGroupConfig('json api', 'plots', config)

    expect(result.detail?.pass_through).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/export/api-targets/json%20api/groups/plots',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify(config),
      })
    )
  })

  it('loads auto-config proposals only when enabled', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        export_name: 'json_api',
        group_by: 'taxons',
        total_entities: 12,
        proposal: { enabled: true, group_by: 'taxons' },
        sections: {},
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    function Probe() {
      const query = useApiExportAutoConfig('json_api', 'taxons', true)
      return <span>{query.data?.export_name ?? ''}</span>
    }

    renderWithClient(<Probe />)
    await flushQueries()

    expect(container?.textContent).toBe('json_api')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/export/api-targets/json_api/groups/taxons/auto-config'
    )
  })

  it('posts preview drafts with the selected section', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        export_name: 'json_api',
        group_by: 'taxons',
        section: 'detail',
        item_id: 1,
        preview: { name: 'Araucaria columnaris' },
        source: {},
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const config: ApiExportGroupConfig = {
      enabled: true,
      group_by: 'taxons',
      detail: { pass_through: false, fields: [{ name: 'general_info.name.value' }] },
      index: { fields: [] },
    }
    function Probe() {
      const query = useApiExportPreview('json_api', 'taxons', 'detail', config, true)
      return <span>{JSON.stringify(query.data?.preview ?? null)}</span>
    }

    renderWithClient(<Probe />)
    await flushQueries()

    expect(container?.textContent).toBe(
      JSON.stringify({ name: 'Araucaria columnaris' })
    )
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/export/api-targets/json_api/groups/taxons/preview',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ ...config, section: 'detail' }),
      })
    )
  })
})
