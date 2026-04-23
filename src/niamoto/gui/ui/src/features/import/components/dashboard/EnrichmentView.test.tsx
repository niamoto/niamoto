// @vitest-environment jsdom

import { act, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EnrichmentView } from './EnrichmentView'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const navigateSpy = vi.hoisted(() => vi.fn())
const invalidateQueriesSpy = vi.hoisted(() => vi.fn())
const trackJobSpy = vi.hoisted(() => vi.fn())
const apiGetSpy = vi.hoisted(() => vi.fn())
const apiPostSpy = vi.hoisted(() => vi.fn())

const referencesState = vi.hoisted(() => ({
  value: {
    data: {
      references: [
        {
          name: 'taxons',
          table_name: 'taxons',
          kind: 'hierarchical',
          can_enrich: true,
          enrichment_enabled: true,
          entity_count: 12,
        },
      ],
    },
    isLoading: false,
    error: null,
  },
}))

const summaryState = vi.hoisted(() => ({
  value: {
    data: {
      entities: [{ name: 'taxons', row_count: 12 }],
    },
  },
}))

const notificationStoreState = vi.hoisted(() => ({
  trackedJobs: [] as Array<{
    jobType: string
    meta?: { referenceName?: string }
  }>,
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (
      key: string,
      defaultValue?: string | Record<string, unknown>,
      options?: Record<string, unknown>
    ) => {
      if (typeof defaultValue === 'string') {
        return defaultValue.replace(/\{\{(\w+)\}\}/g, (_match, token: string) =>
          String(options?.[token] ?? '')
        )
      }
      return key
    },
  }),
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigateSpy,
}))

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    invalidateQueries: invalidateQueriesSpy,
  }),
}))

vi.mock('@/features/import/hooks/useReferences', () => ({
  useReferences: () => referencesState.value,
}))

vi.mock('@/features/import/hooks/useImportSummaryDetailed', () => ({
  useImportSummaryDetailed: () => summaryState.value,
}))

vi.mock('@/stores/notificationStore', () => ({
  useNotificationStore: Object.assign(
    (selector?: (state: typeof notificationStoreState) => unknown) =>
      selector ? selector(notificationStoreState) : notificationStoreState,
    {
      getState: () => ({
        trackJob: trackJobSpy,
      }),
    }
  ),
}))

vi.mock('@/shared/lib/api/client', () => ({
  apiClient: {
    get: apiGetSpy,
    post: apiPostSpy,
  },
}))

vi.mock('@/shared/lib/api/errors', () => ({
  getApiErrorMessage: (error: unknown, fallback: string) =>
    error instanceof Error ? error.message : fallback,
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('./EnrichmentWorkspaceSheet', () => ({
  EnrichmentWorkspaceSheet: () => <div>Workspace sheet</div>,
}))

vi.mock('@/components/ui/alert', () => ({
  Alert: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertTitle: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertDescription: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/button', () => ({
  Button: (props: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props} />
  ),
}))

vi.mock('@/components/ui/card', () => ({
  Card: (props: { children: ReactNode }) => <div>{props.children}</div>,
  CardContent: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/progress', () => ({
  Progress: (props: { value?: number }) => <div data-progress={props.value} />,
}))

describe('EnrichmentView', () => {
  let container: HTMLDivElement
  let root: Root

  const renderView = async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root.render(<EnrichmentView />)
    })
  }

  const flushEffects = async () => {
    await act(async () => {
      await Promise.resolve()
    })
  }

  afterEach(async () => {
    vi.useRealTimers()
    navigateSpy.mockReset()
    invalidateQueriesSpy.mockReset()
    trackJobSpy.mockReset()
    apiGetSpy.mockReset()
    apiPostSpy.mockReset()
    notificationStoreState.trackedJobs = []
    referencesState.value = {
      data: {
        references: [
          {
            name: 'taxons',
            table_name: 'taxons',
            kind: 'hierarchical',
            can_enrich: true,
            enrichment_enabled: true,
            entity_count: 12,
          },
        ],
      },
      isLoading: false,
      error: null,
    }
    summaryState.value = {
      data: {
        entities: [{ name: 'taxons', row_count: 12 }],
      },
    }

    if (root) {
      await act(async () => {
        root.unmount()
      })
    }

    container?.remove()
  })

  it('polls the job endpoint on first load even when no local job is known', async () => {
    vi.useFakeTimers()

    apiGetSpy.mockImplementation(async (url: string) => {
      if (url === '/enrichment/stats/taxons') {
        return { data: { total: 12, enriched: 4, pending: 8, sources: [] } }
      }
      if (url === '/enrichment/job/taxons') {
        const error = new Error('Not found') as Error & {
          response?: { status: number }
        }
        error.response = { status: 404 }
        throw error
      }
      throw new Error(`Unexpected GET ${url}`)
    })

    await renderView()
    await flushEffects()

    expect(apiGetSpy).toHaveBeenCalledWith('/enrichment/stats/taxons')
    expect(apiGetSpy).toHaveBeenCalledWith('/enrichment/job/taxons')

    apiGetSpy.mockClear()

    await act(async () => {
      vi.advanceTimersByTime(3000)
    })

    await flushEffects()

    expect(apiGetSpy).toHaveBeenCalledWith('/enrichment/stats/taxons')
    expect(apiGetSpy).not.toHaveBeenCalledWith('/enrichment/job/taxons')
  })

  it('polls the job endpoint even when the stats request fails', async () => {
    vi.useFakeTimers()

    apiGetSpy.mockImplementation(async (url: string) => {
      if (url === '/enrichment/stats/taxons') {
        throw new Error('Stats unavailable')
      }
      if (url === '/enrichment/job/taxons') {
        return {
          data: {
            id: 'job-taxons',
            mode: 'single',
            status: 'running',
            total: 12,
            processed: 3,
            pending_total: 12,
            pending_processed: 3,
            current_source_label: 'GBIF',
          },
        }
      }
      throw new Error(`Unexpected GET ${url}`)
    })

    await renderView()
    await flushEffects()

    expect(apiGetSpy).toHaveBeenCalledWith('/enrichment/stats/taxons')
    expect(apiGetSpy).toHaveBeenCalledWith('/enrichment/job/taxons')
    expect(container.textContent).toContain('enrichmentTab.status.running')
    expect(container.textContent).toContain('GBIF')
  })

  it('preserves a terminal job state when background polling is skipped', async () => {
    vi.useFakeTimers()

    apiGetSpy.mockImplementation(async (url: string) => {
      if (url === '/enrichment/stats/taxons') {
        return { data: { total: 12, enriched: 12, pending: 0, sources: [] } }
      }
      if (url === '/enrichment/job/taxons') {
        return {
          data: {
            id: 'job-taxons',
            mode: 'single',
            status: 'completed',
            total: 12,
            processed: 12,
            current_source_label: 'GBIF',
          },
        }
      }
      throw new Error(`Unexpected GET ${url}`)
    })

    await renderView()
    await flushEffects()

    expect(container.textContent).toContain('enrichmentTab.status.completed')

    apiGetSpy.mockClear()

    await act(async () => {
      vi.advanceTimersByTime(3000)
    })

    await flushEffects()

    expect(apiGetSpy).toHaveBeenCalledWith('/enrichment/stats/taxons')
    expect(apiGetSpy).not.toHaveBeenCalledWith('/enrichment/job/taxons')
    expect(container.textContent).toContain('enrichmentTab.status.completed')
  })
})
