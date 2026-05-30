// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ContentTab } from './ContentTab'
import type { ReferenceInfo } from '@/hooks/useReferences'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const widgetConfigState = vi.hoisted(() => ({
  refetch: vi.fn(),
}))

vi.mock('@/components/ui/resizable', () => ({
  ResizableHandle: () => <div />,
  ResizablePanel: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  ResizablePanelGroup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/widgets', () => ({
  useConfiguredWidgets: () => ({ loading: false }),
  useWidgetConfig: () => ({
    configuredWidgets: [],
    loading: false,
    updateWidget: vi.fn(),
    deleteWidget: vi.fn(),
    duplicateWidget: vi.fn(),
    reorderWidgets: vi.fn(),
    refetch: widgetConfigState.refetch,
  }),
  useSuggestions: () => ({ suggestions: [], loading: false }),
}))

vi.mock('@/features/collections/components/blocks/WidgetProposalWorkspace', () => ({
  WidgetProposalWorkspace: ({
    collectionName,
    onApplied,
  }: {
    collectionName: string
    onApplied: () => void | Promise<void>
  }) => (
    <div data-testid="widget-proposal-workspace">
      {collectionName}
      <button type="button" onClick={() => { void onApplied() }}>
        apply proposals
      </button>
    </div>
  ),
}))

vi.mock('./WidgetListPanel', () => ({
  WidgetListPanel: () => <div data-testid="widget-list" />,
}))

vi.mock('./ContentRightPanel', () => ({
  ContentRightPanel: () => <div data-testid="content-right-panel" />,
}))

vi.mock('@/components/widgets/AddWidgetModal', () => ({
  AddWidgetModal: () => <div />,
}))

vi.mock('@/shared/performance/devRenderMetrics', () => ({
  useDevListRenderMetric: () => undefined,
}))

const reference: ReferenceInfo = {
  name: 'taxons',
  table_name: 'entity_taxons',
  kind: 'hierarchical',
  schema_fields: [],
}

function deferred<T = void>() {
  let resolve: (value: T | PromiseLike<T>) => void = () => undefined
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve
  })
  return { promise, resolve }
}

function ContentTabRouteHarness({
  onNavigateReady,
}: {
  onNavigateReady: (navigateToPanel: () => void) => void
}) {
  const navigate = useNavigate()
  onNavigateReady(() => navigate('/groups/taxons?panel=widget-proposals'))

  return <ContentTab reference={reference} />
}

describe('ContentTab', () => {
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
    widgetConfigState.refetch.mockClear()
  })

  it('opens widget proposals when requested by the route panel marker', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <MemoryRouter initialEntries={['/groups/taxons?panel=widget-proposals']}>
          <ContentTab reference={reference} />
        </MemoryRouter>,
      )
    })

    expect(container.querySelector('[data-testid="widget-proposal-workspace"]')).toBeTruthy()
    expect(container.textContent).toContain('taxons')
  })

  it('opens widget proposals when the route panel marker is added after mount', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    let navigateToPanel: (() => void) | undefined

    await act(async () => {
      root?.render(
        <MemoryRouter initialEntries={['/groups/taxons']}>
          <ContentTabRouteHarness
            onNavigateReady={(navigate) => {
              navigateToPanel = navigate
            }}
          />
        </MemoryRouter>,
      )
    })

    expect(container.querySelector('[data-testid="content-right-panel"]')).toBeTruthy()
    expect(container.querySelector('[data-testid="widget-proposal-workspace"]')).toBeNull()

    await act(async () => {
      navigateToPanel?.()
    })

    expect(container.querySelector('[data-testid="widget-proposal-workspace"]')).toBeTruthy()
    expect(container.textContent).toContain('taxons')
  })

  it('returns to the normal blocks preview after widget proposals are applied', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <MemoryRouter initialEntries={['/groups/taxons?panel=widget-proposals']}>
          <ContentTab reference={reference} />
        </MemoryRouter>,
      )
    })

    expect(container.querySelector('[data-testid="widget-proposal-workspace"]')).toBeTruthy()

    const applyButton = [...container.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('apply proposals'),
    )
    expect(applyButton).toBeDefined()

    await act(async () => {
      applyButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(widgetConfigState.refetch).toHaveBeenCalledTimes(1)
    expect(container.querySelector('[data-testid="widget-proposal-workspace"]')).toBeNull()
    expect(container.querySelector('[data-testid="content-right-panel"]')).toBeTruthy()
  })

  it('keeps widget proposals visible until the refreshed blocks data is ready', async () => {
    const pendingRefresh = deferred()
    widgetConfigState.refetch.mockReturnValueOnce(pendingRefresh.promise)
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <MemoryRouter initialEntries={['/groups/taxons?panel=widget-proposals']}>
          <ContentTab reference={reference} />
        </MemoryRouter>,
      )
    })

    const applyButton = [...container.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('apply proposals'),
    )
    expect(applyButton).toBeDefined()

    await act(async () => {
      applyButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(widgetConfigState.refetch).toHaveBeenCalledTimes(1)
    expect(container.querySelector('[data-testid="widget-proposal-workspace"]')).toBeTruthy()
    expect(container.querySelector('[data-testid="content-right-panel"]')).toBeNull()

    await act(async () => {
      pendingRefresh.resolve()
      await pendingRefresh.promise
    })

    expect(container.querySelector('[data-testid="widget-proposal-workspace"]')).toBeNull()
    expect(container.querySelector('[data-testid="content-right-panel"]')).toBeTruthy()
  })
})
