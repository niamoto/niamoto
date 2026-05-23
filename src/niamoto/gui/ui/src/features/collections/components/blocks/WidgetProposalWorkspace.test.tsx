// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { WidgetProposalGroups } from '@/features/collections/api/widget-proposals'
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

    expect(container?.textContent).toContain('Widget proposals')
    expect(container?.textContent).toContain('Dbh cm')
    expect(container?.textContent).toContain('binned_distribution')
    expect(container?.textContent).toContain('bar_plot')
  })
})
