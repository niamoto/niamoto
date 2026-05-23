// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ContentTab } from './ContentTab'
import type { ReferenceInfo } from '@/hooks/useReferences'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

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
    refetch: vi.fn(),
  }),
  useSuggestions: () => ({ suggestions: [], loading: false }),
}))

vi.mock('@/features/collections/components/blocks/WidgetProposalWorkspace', () => ({
  WidgetProposalWorkspace: ({ collectionName }: { collectionName: string }) => (
    <div data-testid="widget-proposal-workspace">{collectionName}</div>
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
})
