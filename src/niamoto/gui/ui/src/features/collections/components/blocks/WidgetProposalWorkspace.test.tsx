// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  WidgetProposal,
  WidgetProposalGroups,
} from '@/features/collections/api/widget-proposals'
import { WidgetProposalWorkspace } from './WidgetProposalWorkspace'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const queryState = vi.hoisted(() => ({
  value: {
    data: undefined as WidgetProposalGroups | undefined,
    isLoading: false,
    error: null as Error | null,
    refetch: vi.fn(),
    preview: vi.fn(),
    apply: vi.fn(),
    previewState: { isPending: false, error: null },
    applyState: { isPending: false, error: null },
  },
}))

vi.mock('@/features/collections/hooks/useWidgetProposals', () => ({
  useWidgetProposals: () => queryState.value,
}))

vi.mock('@/components/preview', () => ({
  PreviewTile: ({ descriptor }: { descriptor: { templateId?: string } }) => (
    <div data-testid={`preview-${descriptor.templateId ?? 'inline'}`} />
  ),
}))

describe('WidgetProposalWorkspace', () => {
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
    queryState.value.data = undefined
    queryState.value.isLoading = false
    queryState.value.error = null
  })

  async function renderWorkspace() {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <WidgetProposalWorkspace
          collectionName="taxons"
          onClose={() => undefined}
          onApplied={() => undefined}
        />,
      )
    })
  }

  function makeProposal(
    overrides: Partial<WidgetProposal> & Pick<WidgetProposal, 'id' | 'title'>,
  ): WidgetProposal {
    const widget = overrides.primary_fit?.widget ?? 'bar_plot'
    return {
      id: overrides.id,
      collection: 'taxons',
      title: overrides.title,
      status: overrides.status ?? 'recommended',
      candidate: overrides.candidate ?? {
        id: `${overrides.id}_candidate`,
        collection: 'taxons',
        origin: 'raw_field',
        intent: `Show ${overrides.title}`,
        source_name: 'occurrences',
        field_names: [overrides.title.toLowerCase().replace(/\s+/g, '_')],
        transformer_plugin: 'binned_distribution',
        reconstructability: 'full',
        freshness: 'current',
        warnings: [],
        skip_reasons: [],
      },
      shape: overrides.shape ?? {
        kind: 'binned_numeric_distribution',
        bin_count: 10,
        has_labels: true,
        columns: [],
        metadata: {},
      },
      primary_fit: overrides.primary_fit ?? {
        widget,
        status: 'primary',
        score: 0.9,
        reason: 'Readable summary',
        warnings: [],
        params: {},
        rank: 1,
      },
      alternatives: overrides.alternatives ?? [],
      suppressed_fits: overrides.suppressed_fits ?? [],
      missing_chart: overrides.missing_chart ?? null,
      score: overrides.score ?? { dimensions: { utility: 0.9 }, weights: {} },
      warnings: overrides.warnings ?? [],
      skip_reasons: overrides.skip_reasons ?? [],
      applyability: overrides.applyability ?? 'applicable',
      fingerprint: overrides.fingerprint ?? overrides.id,
      recipe: overrides.recipe ?? {
        transformer: {
          plugin: 'binned_distribution',
          params: { source: 'occurrences', field: 'dbh_cm' },
        },
        widget: {
          plugin: widget,
          params: { title: overrides.title },
        },
      },
    }
  }

  it('renders grouped recommended proposals and details', async () => {
    queryState.value.data = {
      collection: 'taxons',
      recommended: [
        {
          id: 'wp_1',
          collection: 'taxons',
          title: 'Dbh cm',
          status: 'recommended',
          candidate: {
            id: 'candidate_1',
            collection: 'taxons',
            origin: 'raw_field',
            intent: 'Bin numeric values from dbh_cm',
            source_name: 'occurrences',
            field_names: ['dbh_cm'],
            transformer_plugin: 'binned_distribution',
            reconstructability: 'full',
            freshness: 'current',
            warnings: [],
            skip_reasons: [],
          },
          shape: {
            kind: 'binned_numeric_distribution',
            bin_count: 10,
            has_labels: true,
            columns: ['dbh_cm'],
            metadata: {},
          },
          primary_fit: {
            widget: 'bar_plot',
            status: 'primary',
            score: 0.9,
            reason: 'Readable',
            warnings: [],
            params: {},
            rank: 1,
          },
          alternatives: [],
          suppressed_fits: [],
          missing_chart: null,
          score: { dimensions: { utility: 0.9 }, weights: {} },
          warnings: [],
          skip_reasons: [],
          applyability: 'applicable',
          fingerprint: 'wp_1',
          recipe: {},
        },
      ],
      warnings: [],
      missing_chart: [],
      skipped: [],
      already_configured: [],
      review_only: [],
      partial: false,
      messages: [],
    }

    await renderWorkspace()

    expect(container?.textContent).toContain('Review proposed page')
    expect(container?.textContent).toContain('Dbh cm')
    expect(container?.textContent).toContain('binned_distribution')
    expect(container?.textContent).toContain('bar_plot')
  })

  it('renders a future page preview whose cards toggle selected proposals', async () => {
    queryState.value.data = {
      collection: 'taxons',
      recommended: [
        makeProposal({ id: 'wp_1', title: 'Dbh cm' }),
        makeProposal({ id: 'wp_2', title: 'Elevation' }),
      ],
      warnings: [],
      missing_chart: [],
      skipped: [],
      already_configured: [],
      review_only: [],
      partial: false,
      messages: [],
    }

    await renderWorkspace()

    expect(container?.textContent).toContain('Future page preview')
    expect(container?.textContent).toContain('2 selected')
    expect(container?.textContent).toContain('Review and add')
    expect(
      container?.querySelector(
        '[data-testid="preview-dbh_cm_binned_distribution_bar_plot"]',
      ),
    ).not.toBeNull()

    const removeElevation = container?.querySelector(
      '[aria-label="Remove Elevation from the future page"]',
    ) as HTMLButtonElement | null
    expect(removeElevation).not.toBeNull()

    await act(async () => {
      removeElevation?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(container?.textContent).toContain('1 selected')
    expect(container?.textContent).toContain('Available but not selected')

    const addElevation = container?.querySelector(
      '[aria-label="Add Elevation to the future page"]',
    ) as HTMLButtonElement | null
    expect(addElevation).not.toBeNull()

    await act(async () => {
      addElevation?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(container?.textContent).toContain('2 selected')
  })

  it('keeps selected preview cards in a single responsive column', async () => {
    queryState.value.data = {
      collection: 'taxons',
      recommended: [
        makeProposal({ id: 'wp_1', title: 'Rainfall' }),
        makeProposal({ id: 'wp_2', title: 'Elevation' }),
        makeProposal({ id: 'wp_3', title: 'Geo pt', primary_fit: {
          widget: 'interactive_map',
          status: 'primary',
          score: 0.9,
          reason: 'Readable map',
          warnings: [],
          params: {},
          rank: 1,
        } }),
      ],
      warnings: [],
      missing_chart: [],
      skipped: [],
      already_configured: [],
      review_only: [],
      partial: false,
      messages: [],
    }

    await renderWorkspace()

    const rainfallCard = container?.querySelector(
      '[aria-label="Remove Rainfall from the future page"]',
    ) as HTMLButtonElement | null
    expect(rainfallCard).not.toBeNull()

    expect(rainfallCard?.parentElement?.className).toContain('grid-cols-1')
    expect(rainfallCard?.parentElement?.className).toContain('min-[1800px]:grid-cols-2')
    expect(rainfallCard?.parentElement?.className).not.toContain('2xl:grid-cols-2')
    expect(rainfallCard?.className).toContain('grid-cols-1')
    expect(rainfallCard?.className).not.toContain('grid-cols-[280px_minmax')
  })
})
