// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DisplayFieldEditorPanel } from './DisplayFieldEditorPanel'
import type { IndexDisplayField } from './useIndexConfig'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'fr', resolvedLanguage: 'fr' },
  }),
}))

vi.mock('./FieldSourcePicker', () => ({
  FieldSourcePicker: () => <div data-testid="field-source-picker" />,
}))

const baseField: IndexDisplayField = {
  name: 'occurrences_count',
  source: 'general_info.occurrences_count.value',
  type: 'text',
  searchable: false,
  dynamic_options: false,
  display: 'normal',
  is_title: false,
  inline_badge: false,
}

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

describe('DisplayFieldEditorPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('does not render a local save action', async () => {
    const harness = createHarness()

    await harness.render(
      <DisplayFieldEditorPanel
        field={baseField}
        fieldIndex={5}
        onChange={vi.fn()}
        onClose={vi.fn()}
      />
    )

    expect(harness.container.textContent).not.toContain('common:actions.save')

    await harness.unmount()
  })

  it('emits title changes immediately', async () => {
    const onChange = vi.fn()
    const harness = createHarness()

    await harness.render(
      <DisplayFieldEditorPanel
        field={baseField}
        fieldIndex={5}
        onChange={onChange}
        onClose={vi.fn()}
      />
    )

    const useAsTitleSwitch = harness.container.querySelector('[role="switch"]') as HTMLButtonElement

    await act(async () => {
      useAsTitleSwitch.click()
      await Promise.resolve()
    })

    expect(onChange).toHaveBeenCalledWith({
      is_title: true,
      searchable: true,
    })

    await harness.unmount()
  })
})
