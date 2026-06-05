// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImportInventoryList } from './ImportInventoryList'
import type { ImportInventoryItem } from './importInventory'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const translations: Record<string, string> = {
  'autoConfig.reviewReasons.referenceEnrichedDatasetSignals':
    'Référence enrichie avec mesures ou géométrie ; le ML voit aussi des signaux de jeu de données ({{confidence}}).',
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const template = translations[key] ?? key
      const translated = Object.entries(options ?? {}).reduce((value, [name, replacement]) => {
        if (name === 'count') return value
        return value.replaceAll(`{{${name}}}`, String(replacement))
      }, template)
      return options?.count === undefined ? translated : `${translated}:${options.count}`
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

const items: ImportInventoryItem[] = [
  {
    id: 'dataset:occurrences',
    name: 'occurrences',
    sourceFileName: 'occurrences.csv',
    sourcePath: 'imports/occurrences.csv',
    family: 'csv',
    role: 'occurrences',
    status: 'analysed',
    quality: 'good',
    primaryMessage: 'Headers and taxonomy detected',
    summary: 'CSV • 23 fields',
    details: [],
    badges: ['headers'],
    tips: [],
  },
  {
    id: 'layer:rainfall',
    name: 'rainfall',
    sourceFileName: 'rainfall.tif',
    sourcePath: 'imports/rainfall.tif',
    family: 'raster',
    role: 'raster_layer',
    status: 'needs_attention',
    quality: 'review',
    primaryMessage: 'Projection needs review',
    summary: 'Raster',
    details: [],
    badges: [],
    tips: ['projection'],
  },
]

describe('ImportInventoryList', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('groups inventory items by role with compact statuses', async () => {
    const harness = createHarness()

    await harness.render(<ImportInventoryList items={items} />)

    expect(harness.container.textContent).toContain('cockpit.roles.occurrences')
    expect(harness.container.textContent).toContain('cockpit.roles.raster_layer')
    expect(harness.container.textContent).toContain('occurrences')
    expect(harness.container.textContent).toContain('rainfall')
    expect(harness.container.textContent).toContain('cockpit.status.analysed')
    expect(harness.container.textContent).toContain('cockpit.status.needs_attention')

    await harness.unmount()
  })

  it('collapses a noisy group without removing the group summary', async () => {
    const harness = createHarness()

    await harness.render(<ImportInventoryList items={items} />)

    const groupButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('cockpit.roles.occurrences')
    )
    expect(groupButton).toBeTruthy()

    await act(async () => {
      groupButton?.click()
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain('cockpit.roles.occurrences')
    expect(harness.container.textContent).not.toContain('Headers and taxonomy detected')

    await harness.unmount()
  })

  it('notifies when a file row is selected', async () => {
    const harness = createHarness()
    const onSelect = vi.fn()

    await harness.render(<ImportInventoryList items={items} onSelectItem={onSelect} />)

    const fileButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('rainfall')
    )
    expect(fileButton).toBeTruthy()

    await act(async () => {
      fileButton?.click()
      await Promise.resolve()
    })

    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'layer:rainfall' }))

    await harness.unmount()
  })

  it('localizes known auto-config review reasons in row summaries', async () => {
    const harness = createHarness()
    const reviewReason =
      'Reference enriched with measurements or geometry; ML also saw dataset-like signals (100%).'

    await harness.render(
      <ImportInventoryList
        items={[
          {
            id: 'reference:plots',
            name: 'plots.csv',
            sourceFileName: 'plots.csv',
            sourcePath: 'imports/plots.csv',
            family: 'csv',
            role: 'sites',
            status: 'needs_attention',
            quality: 'review',
            primaryMessage: reviewReason,
            summary: 'CSV',
            details: [],
            badges: [reviewReason],
            tips: [],
          },
        ]}
      />
    )

    expect(harness.container.textContent).toContain(
      'Référence enrichie avec mesures ou géométrie ; le ML voit aussi des signaux de jeu de données (100%).'
    )
    expect(harness.container.textContent).not.toContain('Reference enriched')

    await harness.unmount()
  })
})
