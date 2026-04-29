// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import JsonSchemaForm from './JsonSchemaForm'

interface MockSelectOption {
  value: string | number | boolean
  label: string
}

interface MockSelectFieldProps {
  name: string
  value?: string | number | boolean
  onChange?: (value: string | number | boolean | undefined) => void
  options: MockSelectOption[]
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key,
  }),
}))

vi.mock('@/lib/api/recipes', () => ({
  useSourceColumns: () => ({ columns: [] }),
}))

vi.mock('./fields/SelectField', () => ({
  default: ({ name, value, onChange, options }: MockSelectFieldProps) => (
    <select
      data-testid={name}
      value={value?.toString() ?? ''}
      onChange={(event) => {
        const option = options.find(
          (selectOption) => selectOption.value.toString() === event.target.value
        )
        onChange?.(option?.value)
      }}
    >
      <option value="">Select</option>
      {options.map((option) => (
        <option key={option.value.toString()} value={option.value.toString()}>
          {option.label}
        </option>
      ))}
    </select>
  ),
}))

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('JsonSchemaForm', () => {
  let root: Root | null = null
  let container: HTMLDivElement | null = null

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          plugin_type: 'widget',
          has_params: true,
          schema: {
            properties: {
              transform: {
                type: 'string',
                title: 'Transform',
                'ui:widget': 'select',
                'ui:options': [
                  { value: 'known_transform', label: 'Known transform' },
                  { value: 'other_transform', label: 'Other transform' },
                ],
              },
              transform_params: {
                type: 'object',
                title: 'Transform params',
                'ui:widget': 'json',
                'ui:condition': 'transform',
                'ui:transform_schemas': {
                  known_transform: {
                    x_field: { type: 'string', default: 'x' },
                  },
                  other_transform: {
                    y_field: { type: 'string', default: 'y' },
                  },
                },
              },
            },
          },
        }),
      }),
    )
  })

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    root = null
    container = null
    vi.unstubAllGlobals()
  })

  async function render(ui: ReactNode) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(ui)
    })
    await act(async () => {
      await Promise.resolve()
    })
  }

  it('falls back to raw JSON editing when transform params have no dedicated schema', async () => {
    const onChange = vi.fn()

    await render(
      <JsonSchemaForm
        pluginId="bar_plot"
        showTitle={false}
        initialValues={{
          transform: 'custom_transform',
          transform_params: {
            x_field: 'class_name',
            y_field: 'value',
          },
        }}
        onChange={onChange}
      />,
    )

    const textarea = container?.querySelector('textarea')

    expect(textarea?.value).toContain('"x_field": "class_name"')
    expect(textarea?.value).toContain('"y_field": "value"')
    expect(onChange).not.toHaveBeenCalled()
  })

  it('resets transform params when the selected transform changes', async () => {
    const onChange = vi.fn()

    await render(
      <JsonSchemaForm
        pluginId="bar_plot"
        showTitle={false}
        initialValues={{
          transform: 'known_transform',
          transform_params: {
            x_field: 'class_name',
            stale_field: 'stale',
          },
        }}
        onChange={onChange}
      />,
    )

    const select = container?.querySelector('[data-testid="transform"]') as HTMLSelectElement

    act(() => {
      select.value = 'other_transform'
      select.dispatchEvent(new Event('change', { bubbles: true }))
    })

    expect(onChange).toHaveBeenLastCalledWith({
      transform: 'other_transform',
      transform_params: {
        y_field: 'y',
      },
    })
  })
})
