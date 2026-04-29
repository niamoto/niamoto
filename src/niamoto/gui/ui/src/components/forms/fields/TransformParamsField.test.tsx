// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TransformParamsField from './TransformParamsField'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key,
  }),
}))

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('TransformParamsField', () => {
  let root: Root | null = null
  let container: HTMLDivElement | null = null

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    root = null
    container = null
  })

  function render(ui: ReactNode) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    act(() => {
      root?.render(ui)
    })
  }

  function setInputValue(input: HTMLInputElement, value: string) {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }

  it('does not emit params on initial mount', () => {
    const onChange = vi.fn()

    render(
      <TransformParamsField
        name="transform_params"
        selectedTransform="bins_to_df"
        transformSchemas={{
          bins_to_df: {
            bin_field: { type: 'string', default: 'bins' },
            count_field: { type: 'string', default: 'counts' },
          },
        }}
        value={{ bin_field: 'bins', percentage_field: 'percentages' }}
        onChange={onChange}
      />,
    )

    expect(onChange).not.toHaveBeenCalled()
  })

  it('preserves existing params outside the schema when a field changes', () => {
    const onChange = vi.fn()

    render(
      <TransformParamsField
        name="transform_params"
        selectedTransform="bins_to_df"
        transformSchemas={{
          bins_to_df: {
            bin_field: { type: 'string', default: 'bins' },
            count_field: { type: 'string', default: 'counts' },
          },
        }}
        value={{ bin_field: 'bins', count_field: 'counts', percentage_field: 'percentages' }}
        onChange={onChange}
      />,
    )

    const inputs = container?.querySelectorAll('input')
    expect(inputs?.length).toBe(2)

    act(() => {
      setInputValue(inputs?.[1] as HTMLInputElement, 'total')
    })

    expect(onChange).toHaveBeenCalledWith({
      bin_field: 'bins',
      count_field: 'total',
      percentage_field: 'percentages',
    })
  })
})
