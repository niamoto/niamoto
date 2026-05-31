// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImportContextPanel } from './ImportContextPanel'
import type { ImportInventoryItem } from './importInventory'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key,
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
})
