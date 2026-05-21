// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImportCockpit } from './ImportCockpit'
import type { ImportInventoryItem } from './importInventory'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { count?: number; progress?: number }) => {
      if (options?.count !== undefined) return `${key}:${options.count}`
      if (options?.progress !== undefined) return `${key}:${options.progress}`
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

const inventory: ImportInventoryItem[] = [
  {
    id: 'dataset:occurrences',
    name: 'occurrences',
    sourceName: 'occurrences.csv',
    sourcePath: 'imports/occurrences.csv',
    family: 'csv',
    role: 'occurrences',
    status: 'analysed',
    quality: 'good',
    primaryMessage: 'Ready',
    summary: 'CSV',
    details: [{ label: 'source', value: 'imports/occurrences.csv' }],
    badges: ['headers'],
    tips: [],
  },
  {
    id: 'layer:rainfall',
    name: 'rainfall',
    sourceName: 'rainfall.tif',
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

describe('ImportCockpit', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('renders a workflow rail, inventory summary, and context panel', async () => {
    const harness = createHarness()

    await harness.render(
      <ImportCockpit
        phase="reviewing"
        items={inventory}
        selectedItemId="dataset:occurrences"
        introGuidance={<div>Guidance</div>}
      />
    )

    expect(harness.container.textContent).toContain('cockpit.workflow.title')
    expect(harness.container.textContent).toContain('cockpit.inventory.title')
    expect(harness.container.textContent).toContain('cockpit.summary.total:2')
    expect(harness.container.textContent).toContain('occurrences')
    expect(harness.container.textContent).toContain('imports/occurrences.csv')

    await harness.unmount()
  })

  it('switches context when a row is selected', async () => {
    const harness = createHarness()
    const onSelect = vi.fn()

    await harness.render(
      <ImportCockpit
        phase="reviewing"
        items={inventory}
        selectedItemId="dataset:occurrences"
        onSelectItem={onSelect}
      />
    )

    const rainfallButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('rainfall')
    )
    expect(rainfallButton).toBeTruthy()

    await act(async () => {
      rainfallButton?.click()
      await Promise.resolve()
    })

    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'layer:rainfall' }))

    await harness.unmount()
  })

  it('keeps completed workflow step counts stable as files advance', async () => {
    const harness = createHarness()

    await harness.render(
      <ImportCockpit
        phase="reviewing"
        items={inventory}
        selectedItemId="dataset:occurrences"
      />
    )

    const steps = Array.from(harness.container.querySelectorAll('nav li')).map((step) =>
      step.textContent || ''
    )

    expect(steps[0]).toContain('cockpit.workflow.files')
    expect(steps[0]).toContain('cockpit.workflow.itemCount:2')
    expect(steps[1]).toContain('cockpit.workflow.analysis')
    expect(steps[1]).toContain('cockpit.workflow.itemCount:2')
    expect(steps[2]).toContain('cockpit.workflow.import')
    expect(steps[2]).toContain('cockpit.workflow.itemCount:2')

    await harness.unmount()
  })

  it('does not treat pre-upload ready files as analysed progress', async () => {
    const harness = createHarness()
    const selectedInventory: ImportInventoryItem[] = [
      {
        id: 'selected:occurrences.csv',
        name: 'occurrences.csv',
        family: 'csv',
        role: 'occurrences',
        status: 'ready',
        quality: 'good',
        primaryMessage: 'ready',
        summary: 'CSV',
        details: [],
        badges: [],
        tips: [],
      },
      {
        id: 'selected:plots.csv',
        name: 'plots.csv',
        family: 'csv',
        role: 'sites',
        status: 'selected',
        quality: 'info',
        primaryMessage: 'selected',
        summary: 'CSV',
        details: [],
        badges: [],
        tips: [],
      },
    ]

    await harness.render(
      <ImportCockpit
        phase="idle"
        items={selectedInventory}
        selectedItemId="selected:occurrences.csv"
      />
    )

    expect(harness.container.textContent).toContain('cockpit.inventory.readyToUpload:2')
    expect(harness.container.textContent).not.toContain('cockpit.inventory.progress')

    await harness.unmount()
  })

  it('does not show a spinner while waiting for file selection', async () => {
    const harness = createHarness()

    await harness.render(
      <ImportCockpit
        phase="idle"
        items={[]}
      />
    )

    const firstStep = harness.container.querySelector('nav li')
    expect(firstStep?.textContent).toContain('cockpit.workflow.files')
    expect(firstStep?.querySelector('.animate-spin')).toBeNull()

    await harness.unmount()
  })

  it('marks analysis as done while the import step is active', async () => {
    const harness = createHarness()

    await harness.render(
      <ImportCockpit
        phase="reviewing"
        items={inventory}
        selectedItemId="dataset:occurrences"
      />
    )

    const steps = Array.from(harness.container.querySelectorAll('nav li'))
    expect(steps[1].textContent).toContain('cockpit.workflow.analysis')
    expect(steps[1].querySelector('svg')?.classList.toString()).not.toContain('animate-spin')
    expect(steps[2].textContent).toContain('cockpit.workflow.import')
    expect(steps[2].querySelector('.animate-spin')).toBeNull()

    await harness.unmount()
  })

  it('uses backend import progress instead of visible inventory counts', async () => {
    const harness = createHarness()
    const importingInventory = inventory.map((item, index) => ({
      ...item,
      status: index === 0 ? 'imported' as const : 'analysed' as const,
      quality: 'good' as const,
    }))

    await harness.render(
      <ImportCockpit
        phase="importing"
        items={importingInventory}
        progress={47}
        selectedItemId="dataset:occurrences"
      />
    )

    expect(harness.container.textContent).toContain('cockpit.inventory.importProgress:47')

    await harness.unmount()
  })
})
