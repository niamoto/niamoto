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
  'cockpit.detailValues.decision.aligned': 'Décision automatique confirmée',
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) =>
      translations[key] ?? options?.defaultValue ?? key,
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
})
