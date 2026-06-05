// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImportContextPanel } from './ImportContextPanel'
import type { ImportInventoryItem } from './importInventory'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const translations: Record<string, string> = {
  'cockpit.detailLabels.path': 'Chemin',
  'cockpit.detailLabels.type': 'Type',
  'cockpit.detailLabels.decision': 'Décision',
  'cockpit.detailLabels.review': 'À vérifier',
  'cockpit.detailLabels.notice': 'À noter',
  'cockpit.detailValues.decision.aligned': 'Décision automatique confirmée',
  'autoConfig.reviewReasons.referenceEnrichedDatasetSignals':
    'Référence enrichie avec mesures ou géométrie ; le ML voit aussi des signaux de jeu de données ({{confidence}}).',
  'autoConfig.reviewReasons.observationSignalsInEnrichedReference':
    'Des signaux d’observation ont été détectés, mais le fichier se comporte encore comme une référence enrichie.',
  'autoConfig.reviewReasons.mlObservationSignals':
    'Le ML a détecté des signaux orientés observation, comme des mesures, une date ou une géométrie.',
}

function translate(key: string, options?: { defaultValue?: string; [key: string]: unknown }) {
  const template = translations[key] ?? options?.defaultValue ?? key
  return Object.entries(options ?? {}).reduce((value, [name, replacement]) => {
    if (name === 'defaultValue') return value
    return value.replaceAll(`{{${name}}}`, String(replacement))
  }, template)
}

vi.mock('react-i18next', () => ({
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

const itemWithDuplicateEventDetails: ImportInventoryItem = {
  id: 'layer:substrate',
  name: 'substrate.gpkg',
  sourceFileName: 'substrate.gpkg',
  sourcePath: 'imports/substrate.gpkg',
  sourcePaths: ['imports/substrate.gpkg'],
  family: 'vector',
  role: 'shape_layer',
  status: 'checking',
  quality: 'info',
  primaryMessage: 'Analyzing substrate.gpkg',
  summary: 'GPKG',
  details: [
    { label: 'event', value: 'Analyzing substrate.gpkg' },
    { label: 'event', value: 'Analyzing substrate.gpkg' },
  ],
  badges: [],
  tips: [],
}

const itemWithTechnicalDetails: ImportInventoryItem = {
  id: 'selected:occurrences.csv',
  name: 'occurrences.csv',
  sourceFileName: 'occurrences.csv',
  sourcePath: 'imports/occurrences.csv',
  family: 'csv',
  role: 'occurrences',
  status: 'analysed',
  quality: 'good',
  primaryMessage: 'analysed',
  summary: 'CSV',
  details: [
    { label: 'path', value: 'imports/occurrences.csv' },
    { label: 'type', value: 'csv' },
    { label: 'decision', value: 'aligned' },
  ],
  badges: [],
  tips: [],
}

const enrichedReferenceReason =
  'Reference enriched with measurements or geometry; ML also saw dataset-like signals (100%).'
const observationReferenceReason =
  'Observation-like signals were detected, but the file still behaves like an enriched reference.'
const mlObservationReason =
  'ML found observation-oriented signals such as measurements, time, or geometry.'

const itemWithReviewReasons: ImportInventoryItem = {
  id: 'reference:plots',
  name: 'plots.csv',
  sourceFileName: 'plots.csv',
  sourcePath: 'imports/plots.csv',
  family: 'csv',
  role: 'sites',
  status: 'needs_attention',
  quality: 'review',
  primaryMessage: enrichedReferenceReason,
  summary: 'CSV',
  details: [
      {
      label: 'notice',
      value: [
        enrichedReferenceReason,
        observationReferenceReason,
        mlObservationReason,
      ].join(', '),
      tone: 'info',
    },
  ],
  badges: [
    enrichedReferenceReason,
    observationReferenceReason,
    mlObservationReason,
  ],
  tips: [],
}

describe('ImportContextPanel', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('renders repeated event details without duplicate React keys', async () => {
    const harness = createHarness()
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    await harness.render(
      <ImportContextPanel
        item={itemWithDuplicateEventDetails}
        phase="importing"
      />
    )

    expect(harness.container.textContent).toContain('Analyzing substrate.gpkg')
    expect(
      consoleError.mock.calls.some((call) =>
        call.some((value) =>
          String(value).includes('Encountered two children with the same key')
        )
      )
    ).toBe(false)

    await harness.unmount()
  })

  it('localizes known detail labels and decision values', async () => {
    const harness = createHarness()

    await harness.render(
      <ImportContextPanel
        item={itemWithTechnicalDetails}
        phase="reviewing"
      />
    )

    expect(harness.container.textContent).toContain('Chemin')
    expect(harness.container.textContent).toContain('Type')
    expect(harness.container.textContent).toContain('Décision')
    expect(harness.container.textContent).toContain('Décision automatique confirmée')
    expect(harness.container.textContent).not.toContain('aligned')

    await harness.unmount()
  })

  it('localizes known auto-config review reasons in messages, details, and badges', async () => {
    const harness = createHarness()

    await harness.render(
      <ImportContextPanel
        item={itemWithReviewReasons}
        phase="reviewing"
      />
    )

    expect(harness.container.textContent).toContain(
      'Référence enrichie avec mesures ou géométrie ; le ML voit aussi des signaux de jeu de données (100%).'
    )
    expect(harness.container.textContent).toContain('À noter')
    expect(harness.container.textContent).not.toContain('À vérifier')
    expect(harness.container.textContent).toContain(
      'Des signaux d’observation ont été détectés, mais le fichier se comporte encore comme une référence enrichie.'
    )
    expect(harness.container.textContent).toContain(
      'Le ML a détecté des signaux orientés observation, comme des mesures, une date ou une géométrie.'
    )
    expect(harness.container.textContent).not.toContain('Reference enriched')
    expect(harness.container.textContent).not.toContain('Observation-like signals')
    expect(harness.container.textContent).not.toContain('ML found observation-oriented signals')

    await harness.unmount()
  })
})
