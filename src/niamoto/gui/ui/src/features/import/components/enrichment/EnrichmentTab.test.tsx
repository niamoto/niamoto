// @vitest-environment jsdom

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { EnrichmentTab } from './EnrichmentTab'
import { shouldShowEnrichmentConnectivityWarning } from './enrichmentConnectivity'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const restartSourceJobSpy = vi.hoisted(() => vi.fn())
const useEnrichmentStateSpy = vi.hoisted(() => vi.fn())

const translations: Record<string, string> = {
  'enrichmentTab.status.completed': 'Completed',
  'enrichmentTab.runtime.runProgress': 'Attempts completed',
  'enrichmentTab.runtime.restartSource': 'Restart from zero',
  'enrichmentTab.restartDialog.title': 'Restart this source from zero?',
  'enrichmentTab.restartDialog.description':
    'This relaunches {{source}} for {{count}} entities. Existing data from this source will be replaced, and removed when the API no longer returns anything.',
  'enrichmentTab.restartDialog.confirm': 'Restart from zero',
  'common:actions.cancel': 'Cancel',
  'common:actions.delete': 'Delete',
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      (translations[key] ?? key).replace(/\{\{(\w+)\}\}/g, (_match, token: string) =>
        String(options?.[token] ?? '')
      ),
  }),
}))

vi.mock('../../hooks/useEnrichmentState', () => ({
  useEnrichmentState: useEnrichmentStateSpy,
  getResultEntityName: (result: { entity_name?: string; taxon_name?: string }) =>
    result.entity_name || result.taxon_name || '-',
}))

vi.mock('./ApiEnrichmentConfig', () => ({
  ApiEnrichmentConfig: () => <div>API config</div>,
}))

vi.mock('./enrichmentRenderers', () => ({
  isStructuredSourceSummary: () => false,
  renderMappedPreview: () => null,
  renderRawPreview: () => null,
  renderStructuredSummary: () => null,
  renderValue: (value: unknown) => String(value ?? ''),
}))

vi.mock('@/components/ui/alert', () => ({
  Alert: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertTitle: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDescription: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/alert-dialog', () => ({
  AlertDialog: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDialogTrigger: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDialogContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDialogDescription: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDialogFooter: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDialogHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDialogTitle: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDialogCancel: ({
    children,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props}>
      {children}
    </button>
  ),
  AlertDialogAction: ({
    children,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props}>
      {children}
    </button>
  ),
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    variant: _variant,
    size: _size,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: string
    size?: string
  }) => (
    <button type="button" {...props}>
      {children}
    </button>
  ),
}))

vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CardContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CardDescription: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CardHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogDescription: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/input', () => ({
  Input: ({
    value,
    onChange,
    ...props
  }: InputHTMLAttributes<HTMLInputElement>) => (
    <input
      value={value}
      onChange={onChange}
      {...props}
    />
  ),
}))

vi.mock('@/components/ui/label', () => ({
  Label: ({ children }: { children: ReactNode }) => <label>{children}</label>,
}))

vi.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: { value?: number }) => <div data-progress={value} />,
}))

vi.mock('@/components/ui/resizable', () => ({
  ResizablePanelGroup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  ResizablePanel: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  ResizableHandle: () => <div />,
}))

vi.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/switch', () => ({
  Switch: ({
    checked,
    onCheckedChange,
    ...props
  }: {
    checked?: boolean
    onCheckedChange?: (checked: boolean) => void
  }) => (
    <input
      type="checkbox"
      checked={checked}
      onChange={(event) => onCheckedChange?.(event.target.checked)}
      {...props}
    />
  ),
}))

vi.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({
    children,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props}>
      {children}
    </button>
  ),
}))

vi.mock('@/components/ui/table', () => ({
  Table: ({ children }: { children: ReactNode }) => <table>{children}</table>,
  TableBody: ({ children }: { children: ReactNode }) => <tbody>{children}</tbody>,
  TableCell: ({ children }: { children: ReactNode }) => <td>{children}</td>,
  TableHead: ({ children }: { children: ReactNode }) => <th>{children}</th>,
  TableHeader: ({ children }: { children: ReactNode }) => <thead>{children}</thead>,
  TableRow: ({ children }: { children: ReactNode }) => <tr>{children}</tr>,
}))

function createMockState() {
  const activeSource = {
    id: 'endemia',
    label: 'Endemia NC',
    plugin: 'api_taxonomy_enricher',
    enabled: true,
    config: {
      api_url: 'https://api.endemia.nc/v1/taxons',
    },
  }

  return {
    referenceConfig: { enrichment: [] },
    configLoading: false,
    configSaving: false,
    configError: null,
    configSaved: false,
    stats: {
      entity_total: 1667,
      source_total: 1,
      total: 1667,
      enriched: 1608,
      pending: 59,
      sources: [
        {
          source_id: 'endemia',
          label: 'Endemia NC',
          enabled: true,
          total: 1667,
          enriched: 1608,
          pending: 59,
          status: 'completed',
        },
      ],
    },
    statsLoading: false,
    job: {
      id: 'job-reset-1',
      reference_name: 'taxons',
      mode: 'single',
      strategy: 'reset',
      status: 'completed',
      total: 1667,
      processed: 1667,
      successful: 1608,
      failed: 0,
      already_completed: 1608,
      pending_total: 59,
      pending_processed: 59,
      started_at: '2026-04-22T15:00:00',
      updated_at: '2026-04-22T15:05:00',
      source_ids: ['endemia'],
      source_id: 'endemia',
      source_label: 'Endemia NC',
      current_source_id: 'endemia',
      current_source_label: 'Endemia NC',
      current_source_processed: 1667,
      current_source_total: 1667,
      current_source_already_completed: 1608,
      current_source_pending_total: 59,
      current_source_pending_processed: 59,
      error: null,
      current_entity: null,
    },
    jobLoadingScope: null,
    jobRunProgress: {
      total: 59,
      processed: 59,
      percentage: 100,
      alreadyCompleted: 1608,
    },
    isTerminalJob: true,
    resultsLoading: false,
    resultsLoadingMore: false,
    resultsTotal: 0,
    resultsHasMore: false,
    recentResults: [],
    entities: [],
    entitiesLoading: false,
    entitySearch: '',
    setEntitySearch: vi.fn(),
    previewQuery: '',
    setPreviewQuery: vi.fn(),
    previewData: null,
    previewLoading: false,
    previewError: null,
    previewResultMode: 'mapped',
    setPreviewResultMode: vi.fn(),
    sources: [activeSource],
    enabledSources: [activeSource],
    activeSource,
    setActiveSourceId: vi.fn(),
    activeSourceStats: {
      source_id: 'endemia',
      label: 'Endemia NC',
      enabled: true,
      total: 1667,
      enriched: 1608,
      pending: 59,
      status: 'completed',
    },
    activeSourceResults: [],
    activeSourceProgress: {
      total: 1667,
      processed: 1608,
      percentage: 96.46070785842832,
    },
    activeSourceIndex: 0,
    activePreviewResult: null,
    isRunningSingleSource: false,
    canStartActiveSource: false,
    canRestartActiveSource: true,
    quickSelectedSource: activeSource,
    selectedResult: null,
    setSelectedResult: vi.fn(),
    isRefreshing: false,
    isSpatialReference: false,
    apiCategory: 'taxonomy',
    workspacePane: 'config',
    setWorkspacePane: vi.fn(),
    enrichmentAvailability: 'available',
    addSource: vi.fn(),
    updateSourceLabel: vi.fn(),
    updateSourceConfig: vi.fn(),
    applyPresetLabel: vi.fn(),
    toggleSourceEnabled: vi.fn(),
    duplicateSource: vi.fn(),
    moveSource: vi.fn(),
    removeSource: vi.fn(),
    saveEnrichmentConfig: vi.fn(),
    startGlobalJob: vi.fn(),
    startSourceJob: vi.fn(),
    restartSourceJob: restartSourceJobSpy,
    pauseJob: vi.fn(),
    resumeJob: vi.fn(),
    cancelJob: vi.fn(),
    handleRefresh: vi.fn(),
    loadMoreResults: vi.fn(),
    previewEnrichment: vi.fn(),
    resetPreviewState: vi.fn(),
    loadEntities: vi.fn(),
    getSourceProgress: vi.fn(() => ({
      total: 1667,
      processed: 1608,
      percentage: 96.46070785842832,
    })),
  }
}

function normalizeText(value: string) {
  return value.replace(/\s+/g, ' ').trim()
}

describe('EnrichmentTab', () => {
  let container: HTMLDivElement
  let root: Root

  beforeEach(() => {
    restartSourceJobSpy.mockReset()
    useEnrichmentStateSpy.mockReturnValue(createMockState())

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root.unmount()
      })
    }
    container?.remove()
    vi.clearAllMocks()
  })

  it('shows a restart-from-zero action and labels run progress explicitly', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root.render(<EnrichmentTab referenceName="taxons" hasEnrichment />)
    })

    const text = normalizeText(container.textContent ?? '')
    expect(text).toContain('Completed · Attempts completed: 59 / 59')
    expect(text).toContain('Restart this source from zero?')
    expect(text).toContain('This relaunches Endemia NC for 1667 entities.')

    const confirmButton = Array.from(container.querySelectorAll('button')).find(
      (button) => normalizeText(button.textContent ?? '') === 'Restart from zero'
    )
    expect(confirmButton).toBeDefined()

    await act(async () => {
      confirmButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(restartSourceJobSpy).toHaveBeenCalledWith('endemia')
  })

  it('does not show the generic connectivity warning while a job is starting or running', () => {
    expect(
      shouldShowEnrichmentConnectivityWarning({
        enrichmentAvailability: 'unavailable',
        jobStatus: 'running',
        jobLoadingScope: null,
      })
    ).toBe(false)
    expect(
      shouldShowEnrichmentConnectivityWarning({
        enrichmentAvailability: 'unavailable',
        jobStatus: null,
        jobLoadingScope: 'endemia',
      })
    ).toBe(false)
    expect(
      shouldShowEnrichmentConnectivityWarning({
        enrichmentAvailability: 'unavailable',
        jobStatus: 'completed',
        jobLoadingScope: null,
      })
    ).toBe(true)
  })
})
