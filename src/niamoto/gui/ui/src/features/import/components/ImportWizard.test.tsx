// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ImportWizard } from './ImportWizard'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const navigateSpy = vi.hoisted(() => vi.fn())
const autoConfigureStart = vi.hoisted(() => vi.fn())
const autoConfigureReset = vi.hoisted(() => vi.fn())
const compatibilityCheck = vi.hoisted(() => vi.fn())
const compatibilityReset = vi.hoisted(() => vi.fn())
const compatibilityState = vi.hoisted(() => ({
  isChecking: false,
  matched: [] as Array<Record<string, unknown>>,
  failed: [] as Array<{ file: string; error: string }>,
}))
const importReset = vi.hoisted(() => vi.fn())
const importStart = vi.hoisted(() => vi.fn())

vi.mock('react-i18next', () => ({
  initReactI18next: {
    type: '3rdParty',
    init: vi.fn(),
  },
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options?.count === undefined ? key : `${key}:${options.count}`,
  }),
}))

vi.mock('react-router-dom', () => ({
  useLocation: () => ({
    pathname: '/sources/import',
    state: {
      autoStart: true,
      filePaths: ['imports/occurrences.csv'],
      uploadedFiles: [{ name: 'occurrences.csv', path: 'imports/occurrences.csv' }],
    },
  }),
  useNavigate: () => navigateSpy,
}))

vi.mock('@/features/import/components/cockpit/ImportCockpit', () => ({
  ImportCockpit: ({ detailPanel, footer }: { detailPanel?: ReactNode; footer?: ReactNode }) => (
    <div data-testid="import-cockpit">
      {detailPanel}
      {footer}
    </div>
  ),
}))

vi.mock('@/features/import/components/upload/PreImportGuidance', () => ({
  PreImportGuidance: () => <div data-testid="pre-import-guidance" />,
}))

vi.mock('@/features/import/components/upload/ExistingFilesSection', () => ({
  ExistingFilesSection: () => <div data-testid="existing-files" />,
}))

vi.mock('@/features/import/components/upload/FileUploadZone', async () => {
  const React = await import('react')

  return {
    FileUploadZone: React.forwardRef(() => <div data-testid="file-upload-zone" />),
  }
})

vi.mock('@/features/import/components/review/AutoConfigDisplay', () => ({
  AutoConfigDisplay: () => <div data-testid="auto-config-display" />,
}))

vi.mock('@/features/import/components/review/YamlPreview', () => ({
  YamlPreview: () => <div data-testid="yaml-preview" />,
}))

vi.mock('@/features/import/hooks/useAutoConfigureJob', () => ({
  useAutoConfigureJob: () => ({
    start: autoConfigureStart,
    reset: autoConfigureReset,
    stage: null,
    events: [],
    error: null,
  }),
}))

vi.mock('@/features/import/hooks/useCompatibilityCheck', () => ({
  useCompatibilityCheck: () => ({
    check: compatibilityCheck,
    reset: compatibilityReset,
    isChecking: compatibilityState.isChecking,
    matched: compatibilityState.matched,
    failed: compatibilityState.failed,
  }),
}))

vi.mock('@/features/import/hooks/useImportJob', () => ({
  useImportJob: () => ({
    reset: importReset,
    start: importStart,
    state: {
      status: 'idle',
      message: null,
      progress: null,
      phase: null,
      events: [],
      processedEntities: 0,
      totalEntities: 0,
      currentEntity: null,
      currentEntityType: null,
      error: null,
      errorDetails: null,
    },
  }),
}))

vi.mock('@/features/import/hooks/useDatasets', () => ({
  useDatasets: () => ({ data: { datasets: [] } }),
}))

vi.mock('@/features/import/hooks/useReferences', () => ({
  useReferences: () => ({ data: { references: [] } }),
}))

vi.mock('@/features/feedback', () => ({
  requestBugReport: vi.fn(),
}))

vi.mock('@/lib/preview/usePreviewFrame', () => ({
  invalidateAllPreviews: vi.fn(),
}))

function createHarness() {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  const queryClient = new QueryClient()

  return {
    container,
    async render(element: ReactNode) {
      await act(async () => {
        root.render(
          <QueryClientProvider client={queryClient}>
            {element}
          </QueryClientProvider>
        )
        await Promise.resolve()
      })
    },
    async flush() {
      for (let i = 0; i < 5; i += 1) {
        await act(async () => {
          await Promise.resolve()
        })
      }
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      queryClient.clear()
      container.remove()
    },
  }
}

describe('ImportWizard', () => {
  beforeEach(() => {
    navigateSpy.mockReset()
    autoConfigureStart.mockReset()
    autoConfigureReset.mockReset()
    compatibilityCheck.mockReset()
    compatibilityReset.mockReset()
    importReset.mockReset()
    importStart.mockReset()
    compatibilityState.isChecking = false
    compatibilityState.matched = [
      {
        entity_name: 'occurrences',
        matched_columns: [],
        impacts: [],
        has_blockers: false,
        has_warnings: true,
        has_opportunities: false,
        widget_impacts: [
          {
            widget_id: 'occurrences_by_plot',
            collection: 'occurrences',
            status: 'degraded',
            detail: 'Incoming cardinality is high enough to require ranking.',
            affected_columns: ['plot_name'],
          },
        ],
        widget_impact_summary: { degraded: 1 },
        widget_repair_context: {},
      },
    ]
    compatibilityState.failed = []

    compatibilityCheck.mockResolvedValue(undefined)
    autoConfigureStart.mockResolvedValue({
      success: true,
      entities: {
        datasets: {
          occurrences: {
            connector: { path: 'imports/occurrences.csv' },
          },
        },
        references: {},
      },
      detected_columns: {
        occurrences: ['id', 'plot_name'],
      },
      confidence: 1,
      warnings: [],
    })
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('hides widget readability-only impacts in the review cockpit', async () => {
    const harness = createHarness()

    await harness.render(<ImportWizard />)
    await harness.flush()

    expect(autoConfigureStart).toHaveBeenCalledWith(['imports/occurrences.csv'], expect.any(Object))
    expect(harness.container.querySelector('[data-testid="import-impact-panel"]')).toBeNull()

    await harness.unmount()
  })
})
