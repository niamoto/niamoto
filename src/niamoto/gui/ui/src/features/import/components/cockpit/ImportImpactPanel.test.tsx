// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImportImpactPanel } from './ImportImpactPanel'
import type { ImpactCheckResult } from '@/features/import/api/compatibility'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { count?: number }) => {
      if (options?.count !== undefined) return `${key}:${options.count}`
      return key
    },
  }),
}))

function createHarness() {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  return {
    container,
    async render(element: ReactNode) {
      await act(async () => {
        root.render(element)
        await Promise.resolve()
      })
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

const report: ImpactCheckResult = {
  entity_name: 'plots',
  matched_columns: [],
  impacts: [
    {
      column: 'plot_id',
      level: 'breaks_transform',
      detail: 'Column type changed.',
      referenced_in: ['transform.yml'],
    },
  ],
  has_blockers: false,
  has_warnings: true,
  has_opportunities: false,
  widget_impacts: [
    {
      widget_id: 'plots_by_habitat',
      collection: 'plots',
      status: 'degraded',
      detail: 'Incoming cardinality is high enough to require ranking.',
      affected_columns: ['habitat'],
      transformer_plugin: 'categorical_distribution',
      widget_plugin: 'bar_plot',
    },
    {
      widget_id: 'new:plots:elevation',
      collection: 'plots',
      status: 'newly_available',
      detail: 'Incoming field is not used by current widget recipes.',
      affected_columns: ['elevation'],
    },
  ],
  widget_impact_summary: {
    degraded: 1,
    newly_available: 1,
  },
  widget_repair_context: { entity: 'plots' },
}

describe('ImportImpactPanel', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('summarizes pipeline and widget impacts', async () => {
    const onReviewCollection = vi.fn()
    const harness = createHarness()

    await harness.render(
      <ImportImpactPanel reports={[report]} onReviewCollection={onReviewCollection} />
    )

    expect(harness.container.textContent).toContain('impact.title')
    expect(harness.container.textContent).toContain('plots_by_habitat')
    expect(harness.container.textContent).toContain('new:plots:elevation')
    expect(harness.container.textContent).toContain('Column type changed.')

    const reviewButtons = Array.from(harness.container.querySelectorAll('button')).filter((button) =>
      button.textContent?.includes('impact.reviewWidgets')
    )
    expect(reviewButtons).toHaveLength(2)

    await act(async () => {
      reviewButtons[1]?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    expect(onReviewCollection).toHaveBeenCalledWith('plots')

    await harness.unmount()
  })

  it('renders the checking state without reports', async () => {
    const harness = createHarness()

    await harness.render(<ImportImpactPanel reports={[]} isChecking />)

    expect(harness.container.textContent).toContain('impact.checking')

    await harness.unmount()
  })

  it('shows failed compatibility checks instead of hiding them', async () => {
    const harness = createHarness()

    await harness.render(
      <ImportImpactPanel
        reports={[]}
        failedChecks={[{ file: 'occurrences.csv', error: 'backend unavailable' }]}
      />,
    )

    expect(harness.container.textContent).toContain('impact.failedChecksTitle')
    expect(harness.container.textContent).toContain('occurrences.csv')
    expect(harness.container.textContent).toContain('backend unavailable')

    await harness.unmount()
  })
})
