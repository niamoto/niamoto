// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SourcesOverview } from './SourcesOverview'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const navigateSpy = vi.hoisted(() => vi.fn())
const invalidateQueriesSpy = vi.hoisted(() => vi.fn())

const summaryState = vi.hoisted(() => ({
  value: {
    data: {
      total_entities: 2,
      total_rows: 67,
      entities: [
        {
          name: 'entity_places',
          entity_type: 'reference',
          row_count: 12,
          column_count: 3,
          columns: ['id', 'name', 'geometry'],
        },
        {
          name: 'places',
          entity_type: 'dataset',
          row_count: 55,
          column_count: 1,
          columns: ['places_id'],
        },
      ],
      alerts: [
        {
          level: 'warning',
          entity: 'places',
          message: "Table 'places' is empty",
        },
      ],
    },
    isLoading: false,
    isFetching: false,
    error: null,
  },
}))

const referencesState = vi.hoisted(() => ({
  value: {
    data: {
      references: [
        {
          name: 'places',
          table_name: 'entity_places',
          kind: 'spatial',
          schema_fields: [
            { name: 'id' },
            { name: 'name' },
            { name: 'geometry' },
          ],
          entity_count: 12,
          can_enrich: false,
          enrichment_enabled: false,
        },
      ],
      total: 1,
    },
    isFetching: false,
  },
}))

const datasetsState = vi.hoisted(() => ({
  value: {
    data: {
      datasets: [],
      total: 0,
    },
    isFetching: false,
  },
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
      if (
        defaultValue &&
        typeof defaultValue === 'object' &&
        typeof defaultValue.defaultValue === 'string'
      ) {
        return defaultValue.defaultValue
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

vi.mock('@/features/import/hooks/useImportSummaryDetailed', () => ({
  useImportSummaryDetailed: () => summaryState.value,
}))

vi.mock('@/features/import/hooks/useReferences', () => ({
  useReferences: () => referencesState.value,
}))

vi.mock('@/features/import/hooks/useDatasets', () => ({
  useDatasets: () => datasetsState.value,
}))

vi.mock('@/features/import/queryUtils', () => ({
  datasetConfigQueryOptions: vi.fn(),
  prefetchImportEntityDetail: vi.fn(),
}))

vi.mock('@/shared/lib/api/client', () => ({
  apiClient: {
    put: vi.fn(),
  },
}))

vi.mock('@/components/ui/alert', () => ({
  Alert: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertDescription: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertTitle: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: (props: { children: ReactNode }) => <span>{props.children}</span>,
}))

vi.mock('@/components/ui/button', () => ({
  Button: (props: { children: ReactNode; onClick?: () => void }) => (
    <button type="button" onClick={props.onClick}>
      {props.children}
    </button>
  ),
}))

vi.mock('./MetricCard', () => ({
  MetricCard: (props: { label: string; value: string | number }) => (
    <div>
      {props.label}:{props.value}
    </div>
  ),
}))

vi.mock('./SourceRow', () => ({
  SourceRow: (props: {
    name: string
    statusBadge?: { label: string }
    actions: Array<{ label: string }>
  }) => (
    <div data-testid={`source-row-${props.name}`}>
      <span>{props.name}</span>
      {props.statusBadge ? <span>{props.statusBadge.label}</span> : null}
      {props.actions.map((action, index) => (
        <span key={`${action.label}-${index}`}>{action.label}</span>
      ))}
    </div>
  ),
}))

vi.mock('./DashboardConfigEditorSheet', () => ({
  DashboardConfigEditorSheet: () => null,
}))

vi.mock('./EnrichmentWorkspaceSheet', () => ({
  EnrichmentWorkspaceSheet: () => null,
}))

describe('SourcesOverview', () => {
  let container: HTMLDivElement
  let root: Root

  async function renderOverview() {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root.render(
        <SourcesOverview
          onExploreDataset={vi.fn()}
          onExploreReference={vi.fn()}
          onOpenGroups={vi.fn()}
          onOpenGroup={vi.fn()}
          onReimport={vi.fn()}
          onOpenVerification={vi.fn()}
          onOpenEnrichment={vi.fn()}
        />
      )
    })
  }

  afterEach(async () => {
    navigateSpy.mockReset()
    invalidateQueriesSpy.mockReset()

    if (root) {
      await act(async () => {
        root.unmount()
      })
    }

    container?.remove()
  })

  it('ignores empty transformed tables that share a reference name', async () => {
    await renderOverview()

    const row = container.querySelector('[data-testid="source-row-places"]')

    expect(container.textContent).toContain('Known alerts:0')
    expect(container.textContent).toContain('Rows imported:12')
    expect(row?.textContent).toContain('Imported')
    expect(row?.textContent).not.toContain('Structural alert')
    expect(row?.textContent).not.toContain('Open verification')
  })
})
