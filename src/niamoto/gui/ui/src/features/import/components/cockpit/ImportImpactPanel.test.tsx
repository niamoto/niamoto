// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImportImpactPanel } from './ImportImpactPanel'
import type { ImpactCheckResult } from '@/features/import/api/compatibility'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const translations: Record<string, string> = {
  'impact.details.missingColumn': 'Colonne {{column}} absente du nouveau fichier.',
  'impact.details.newColumn': 'Nouvelle colonne {{column}} pas encore dans la configuration.',
  'impact.details.typeChanged': 'Type modifié : {{from}} -> {{to}}.',
  'impact.widgetDetails.incomingFieldUnused':
    'Le champ entrant n’est pas utilisé par les widgets configurés.',
  'impact.widgetDetails.barRequiresRanking':
    'La cardinalité entrante demande un classement, un regroupement ou du défilement avant affichage.',
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, string | number>) => {
      if (options?.count !== undefined) return `${key}:${options.count}`
      const template = translations[key] ?? key
      return Object.entries(options ?? {}).reduce(
        (value, [name, replacement]) =>
          value.replaceAll(`{{${name}}}`, String(replacement)),
        template
      )
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

  it('localizes known widget impact details returned by compatibility checks', async () => {
    const harness = createHarness()

    await harness.render(<ImportImpactPanel reports={[report]} />)

    expect(harness.container.textContent).toContain(
      'Le champ entrant n’est pas utilisé par les widgets configurés.'
    )
    expect(harness.container.textContent).toContain(
      'La cardinalité entrante demande un classement, un regroupement ou du défilement avant affichage.'
    )
    expect(harness.container.textContent).not.toContain(
      'Incoming field is not used by current widget recipes.'
    )
    expect(harness.container.textContent).not.toContain(
      'Incoming cardinality is high enough to require ranking.'
    )

    await harness.unmount()
  })

  it('localizes known pipeline impact details returned by compatibility checks', async () => {
    const harness = createHarness()
    const pipelineReport: ImpactCheckResult = {
      ...report,
      widget_impacts: [],
      widget_impact_summary: {},
      impacts: [
        {
          column: 'plot_id',
          level: 'breaks_transform',
          detail: "Column 'plot_id' missing in new file",
          referenced_in: ['transform.yml'],
        },
        {
          column: 'class_value',
          level: 'opportunity',
          detail: "New column 'class_value' not yet in config",
          referenced_in: [],
        },
        {
          column: 'height',
          level: 'warning',
          detail: 'Type changed: integer → float',
          referenced_in: ['import.yml'],
        },
      ],
    }

    await harness.render(<ImportImpactPanel reports={[pipelineReport]} />)

    expect(harness.container.textContent).toContain(
      'Colonne plot_id absente du nouveau fichier.'
    )
    expect(harness.container.textContent).toContain(
      'Nouvelle colonne class_value pas encore dans la configuration.'
    )
    expect(harness.container.textContent).toContain('Type modifié : integer -> float.')
    expect(harness.container.textContent).not.toContain("Column 'plot_id' missing in new file")
    expect(harness.container.textContent).not.toContain(
      "New column 'class_value' not yet in config"
    )
    expect(harness.container.textContent).not.toContain('Type changed: integer')

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
