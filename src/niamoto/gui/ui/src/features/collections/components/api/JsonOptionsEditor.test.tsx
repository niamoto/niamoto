// @vitest-environment jsdom

import { act, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { JsonOptionsEditor } from './JsonOptionsEditor'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

function input(element: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(element),
    'value'
  )?.set
  setter?.call(element, value)
  element.dispatchEvent(new Event('input', { bubbles: true }))
  element.dispatchEvent(new Event('change', { bubbles: true }))
}

describe('JsonOptionsEditor', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    container = null
    root = null
    vi.clearAllMocks()
  })

  async function renderEditor(
    initialValue: Record<string, unknown>,
    onChange: (value: Record<string, unknown>) => void
  ) {
    function Harness() {
      const [value, setValue] = useState(initialValue)

      return (
        <JsonOptionsEditor
          value={value}
          onChange={(nextValue) => {
            onChange(nextValue)
            setValue(nextValue)
          }}
        />
      )
    }

    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(<Harness />)
    })
  }

  it('writes numeric options from the form', async () => {
    const onChange = vi.fn()
    await renderEditor({}, onChange)

    await act(async () => {
      input(container!.querySelector('input[name="indent"]') as HTMLInputElement, '2')
    })

    expect(onChange).toHaveBeenLastCalledWith({ indent: 2, minify: false })
  })

  it('keeps minify compatible with indentation', async () => {
    const onChange = vi.fn()
    await renderEditor({ indent: 2 }, onChange)

    await act(async () => {
      click(
        container!.querySelector(
          'button[aria-label="collectionPanel.api.jsonOptionsForm.minify"]'
        )
      )
    })

    expect(onChange).toHaveBeenLastCalledWith({ indent: null, minify: true })
  })
})
