// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FieldAggregatorBuilder } from './FieldAggregatorBuilder'
import type { SourceInfo } from '@/lib/api/recipes'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/lib/api/recipes', () => ({
  useSourceColumns: () => ({ columns: [], loading: false }),
}))

const sources: SourceInfo[] = [
  {
    type: 'reference',
    name: 'taxons',
    columns: [],
    transformers: [],
  },
]

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

describe('FieldAggregatorBuilder', () => {
  afterEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('opens advanced field options without rendering an empty SelectItem value', async () => {
    const harness = createHarness()

    await harness.render(
      <FieldAggregatorBuilder
        groupBy="taxons"
        sources={sources}
        value={[
          {
            source: 'taxons',
            field: 'general_info.name.value',
            target: 'name',
            transformation: 'direct',
          },
        ]}
        onChange={vi.fn()}
      />
    )

    const iconButtons = Array.from(
      harness.container.querySelectorAll<HTMLButtonElement>('button.h-8.w-8')
    )
    const advancedButton = iconButtons[0]

    expect(advancedButton).toBeTruthy()

    await act(async () => {
      advancedButton?.click()
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain('recipe.none')

    await harness.unmount()
  })
})
