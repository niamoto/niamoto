// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AutoConfigureResponse } from '@/features/import/api/smart-config'
import { AutoConfigDisplay } from './AutoConfigDisplay'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const translations: Record<string, string> = {
  'autoConfig.dataset.autoDetectedDescription':
    'This file will be imported as a primary data table.',
  'autoConfig.dataset.linkDescription': 'Detected relationship: {{field}} -> {{target}}.',
  'autoConfig.reference.autoDetectedDescription':
    'This file will be used as a reference table and aggregation target.',
  'autoConfig.reference.derivedDescription':
    'This reference will be derived from {{source}} during import.',
  'autoConfig.layer.autoDetectedDescription':
    'This file will be added as a {{type}} map layer.',
  'autoConfig.auxiliary.autoDetectedDescription':
    'This file will be used as precomputed values attached to {{target}}.',
  'autoConfig.auxiliary.joinDescription':
    'Join: {{field}} from the file -> {{refField}} in {{target}}.',
  'autoConfig.actions.moveToDatasets': 'Classify as dataset',
  'autoConfig.actions.moveToReferences': 'Classify as reference',
  'autoConfig.actions.moveToAuxiliary': 'Classify as auxiliary source',
  'autoConfig.warnings.derivedHierarchyNoDatasetRelation':
    'Derived hierarchy {{name}} needs a manual dataset link.',
  'autoConfig.reviewReasons.referenceEnrichedDatasetSignals':
    'Reference enriched translated {{confidence}}.',
  'autoConfig.reviewReasons.observationSignalsInEnrichedReference':
    'Observation reference translated.',
  'autoConfig.reviewReasons.mlObservationSignals':
    'ML observation translated.',
}

function translate(key: string, options?: Record<string, string | number>) {
  const template = translations[key] ?? key
  if (!options) return template

  return Object.entries(options).reduce(
    (value, [name, replacement]) => value.replaceAll(`{{${name}}}`, String(replacement)),
    template
  )
}

vi.mock('react-i18next', () => ({
  initReactI18next: {
    type: '3rdParty',
    init: vi.fn(),
  },
  useTranslation: () => ({
    t: translate,
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

const auxiliaryAutoConfig: AutoConfigureResponse = {
  success: true,
  entities: {
    datasets: {
      occurrences: {
        connector: {
          type: 'file',
          format: 'csv',
          path: 'imports/occurrences.csv',
        },
      },
    },
    references: {
      plots: {
        kind: 'generic',
        connector: {
          type: 'file',
          format: 'csv',
          path: 'imports/plots.csv',
        },
        schema: {
          id_field: 'id',
          fields: [],
        },
      },
    },
    metadata: {},
  },
  auxiliary_sources: [
    {
      name: 'plot_stats',
      data: 'imports/raw_plot_stats.csv',
      grouping: 'plots',
      relation: {
        plugin: 'stats_loader',
        key: 'id',
        ref_field: 'id',
        match_field: 'plot_id',
      },
      source_entity: 'raw_plot_stats',
    },
  ],
  detected_columns: {
    raw_plot_stats: ['plot_id', 'class_object', 'class_name', 'class_value'],
  },
  confidence: 0.91,
  warnings: [],
}

const mixedAutoConfig: AutoConfigureResponse = {
  success: true,
  entities: {
    datasets: {
      occurrences: {
        connector: {
          type: 'file',
          format: 'csv',
          path: 'imports/occurrences.csv',
        },
        links: [
          {
            field: 'plot_id',
            entity: 'plots',
            target_field: 'id',
          },
        ],
      },
    },
    references: {
      plots: {
        kind: 'generic',
        connector: {
          type: 'file',
          format: 'csv',
          path: 'imports/plots.csv',
        },
        schema: {
          id_field: 'id',
          fields: [],
        },
      },
      taxons: {
        kind: 'hierarchical',
        connector: {
          type: 'derived',
          source: 'occurrences',
          extraction: {
            levels: [
              { name: 'family', column: 'family' },
              { name: 'genus', column: 'genus' },
              { name: 'species', column: 'species' },
            ],
          },
        },
        hierarchy: {
          strategy: 'taxonomy',
          levels: ['family', 'genus', 'species'],
        },
      },
    },
    metadata: {
      layers: [
        {
          name: 'rainfall',
          type: 'raster',
          format: 'geotiff',
          path: 'imports/rainfall.tif',
          description: 'Annual rainfall',
        },
      ],
    },
  },
  detected_columns: {
    occurrences: ['id', 'plot_id', 'family', 'genus', 'species'],
    plots: ['id', 'name'],
  },
  confidence: 0.94,
  warnings: [],
}

describe('AutoConfigDisplay', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('explains auxiliary source decisions without exposing raw reclassification actions', async () => {
    const harness = createHarness()

    await harness.render(
      <AutoConfigDisplay
        result={auxiliaryAutoConfig}
        editable
        detectedColumns={auxiliaryAutoConfig.detected_columns}
        onReclassify={vi.fn()}
      />
    )

    const buttons = Array.from(harness.container.querySelectorAll('button'))
    const toggleButton = buttons.at(-1)
    expect(toggleButton).toBeTruthy()

    await act(async () => {
      toggleButton?.click()
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain(
      'This file will be used as precomputed values attached to plots.'
    )
    expect(harness.container.textContent).toContain('Join: plot_id from the file -> id in plots.')
    expect(harness.container.textContent).not.toContain('Classify as dataset')
    expect(harness.container.textContent).not.toContain('Classify as reference')
    expect(harness.container.textContent).not.toContain('Classify as auxiliary source')

    await harness.unmount()
  })

  it('explains dataset, reference, derived reference, and layer decisions', async () => {
    const harness = createHarness()

    await harness.render(
      <AutoConfigDisplay
        result={mixedAutoConfig}
        detectedColumns={mixedAutoConfig.detected_columns}
      />
    )

    const toggleButtons = Array.from(harness.container.querySelectorAll('button'))

    await act(async () => {
      toggleButtons.forEach((button) => button.click())
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain(
      'This file will be imported as a primary data table.'
    )
    expect(harness.container.textContent).toContain('Detected relationship: plot_id -> plots.')
    expect(harness.container.textContent).toContain(
      'This file will be used as a reference table and aggregation target.'
    )
    expect(harness.container.textContent).toContain(
      'This reference will be derived from occurrences during import.'
    )
    expect(harness.container.textContent).toContain(
      'This file will be added as a raster map layer.'
    )

    await harness.unmount()
  })

  it('localizes backend warnings for derived hierarchies without dataset relations', async () => {
    const harness = createHarness()

    await harness.render(
      <AutoConfigDisplay
        result={{
          ...mixedAutoConfig,
          warnings: [
            'Derived hierarchy "plots_hierarchy" has no inferred dataset relation. Preview and transform links will require manual configuration.',
          ],
        }}
        detectedColumns={mixedAutoConfig.detected_columns}
      />
    )

    expect(harness.container.textContent).toContain(
      'Derived hierarchy plots_hierarchy needs a manual dataset link.'
    )
    expect(harness.container.textContent).not.toContain('no inferred dataset relation')

    await harness.unmount()
  })

  it('localizes backend review reasons in entity decision insights', async () => {
    const harness = createHarness()

    await harness.render(
      <AutoConfigDisplay
        result={{
          ...mixedAutoConfig,
          decision_summary: {
            plots: {
              final_entity_type: 'reference',
              heuristic_entity_type: 'reference',
              heuristic_confidence: 0.9,
              ml_entity_type: 'dataset',
              ml_confidence: 1,
              alignment: 'conflict',
              review_required: false,
              review_level: 'notice',
              review_reasons: [
                'Reference enriched with measurements or geometry; ML also saw dataset-like signals (100%).',
                'Observation-like signals were detected, but the file still behaves like an enriched reference.',
                'ML found observation-oriented signals such as measurements, time, or geometry.',
              ],
            },
          },
        }}
        detectedColumns={mixedAutoConfig.detected_columns}
      />
    )

    const toggleButtons = Array.from(harness.container.querySelectorAll('button'))

    await act(async () => {
      toggleButtons.forEach((button) => button.click())
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain('Reference enriched translated 100%.')
    expect(harness.container.textContent).toContain('Observation reference translated.')
    expect(harness.container.textContent).toContain('ML observation translated.')
    expect(harness.container.textContent).not.toContain('Reference enriched with measurements')
    expect(harness.container.textContent).not.toContain('Observation-like signals were detected')
    expect(harness.container.textContent).not.toContain('ML found observation-oriented signals')

    await harness.unmount()
  })
})
