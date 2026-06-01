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

vi.mock('./WidgetListPanel', () => ({
  WidgetListPanel: () => <div data-testid="widget-list" />,
}))

vi.mock('./ContentRightPanel', () => ({
  ContentRightPanel: () => <div data-testid="content-right-panel" />,
}))

vi.mock('@/components/widgets/AddWidgetModal', () => ({
  AddWidgetModal: ({
    defaultTab,
    onOpenChange,
    onWidgetAdded,
  }: {
    defaultTab?: string
    onOpenChange: (open: boolean) => void
    onWidgetAdded: () => void
  }) => (
    <div data-testid="add-widget-modal">
      {defaultTab}
      <button type="button" onClick={() => onOpenChange(false)}>
        close modal
      </button>
      <button type="button" onClick={onWidgetAdded}>
        add widget from modal
      </button>
    </div>
  ),
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
    widgetConfigState.refetch.mockClear()
  })

  it('opens the add widget modal when requested by the route panel marker', async () => {
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

    expect(container.querySelector('[data-testid="add-widget-modal"]')).toBeTruthy()
    expect(container.querySelector('[data-testid="add-widget-modal"]')?.textContent).toContain('suggestions')
  })

  it('keeps the normal widget layout visible behind route-opened suggestions', async () => {
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

    expect(container.querySelector('[data-testid="add-widget-modal"]')).toBeTruthy()
    expect(container.querySelector('[data-testid="widget-list"]')).toBeTruthy()
    expect(container.querySelector('[data-testid="content-right-panel"]')).toBeTruthy()
  })

  it('opens the add widget modal when the route panel marker is added after mount', async () => {
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
    expect(container.querySelector('[data-testid="add-widget-modal"]')).toBeNull()

    await act(async () => {
      navigateToPanel?.()
    })

    expect(container.querySelector('[data-testid="add-widget-modal"]')).toBeTruthy()
    expect(container.querySelector('[data-testid="content-right-panel"]')).toBeTruthy()
  })

  it('dismisses a route-opened add widget modal without reopening it immediately', async () => {
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

    expect(container.querySelector('[data-testid="add-widget-modal"]')).toBeTruthy()

    const closeButton = [...container.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('close modal'),
    )
    expect(closeButton).toBeDefined()

    await act(async () => {
      closeButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(container.querySelector('[data-testid="add-widget-modal"]')).toBeNull()
    expect(container.querySelector('[data-testid="content-right-panel"]')).toBeTruthy()
  })

  it('refreshes widgets and closes the route-opened modal after a widget is added', async () => {
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

    const addFromModalButton = [...container.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('add widget from modal'),
    )
    expect(addFromModalButton).toBeDefined()

    await act(async () => {
      addFromModalButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(widgetConfigState.refetch).toHaveBeenCalledTimes(1)
    expect(container.querySelector('[data-testid="add-widget-modal"]')).toBeNull()
    expect(container.querySelector('[data-testid="content-right-panel"]')).toBeTruthy()
  })

  it('opens the add widget modal directly from the add button', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <MemoryRouter initialEntries={['/groups/taxons']}>
          <ContentTab reference={reference} />
        </MemoryRouter>,
      )
    })

    const addButton = [...container.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('Ajouter un widget') ||
      button.textContent?.includes('Add widget') ||
      button.textContent?.includes('actions.addWidget'),
    )
    expect(addButton).toBeDefined()
    expect(container.textContent).not.toContain('Auto proposals')
    expect(container.textContent).not.toContain('From suggestions')

    await act(async () => {
      addButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(container.querySelector('[data-testid="add-widget-modal"]')).toBeTruthy()
  })
})
