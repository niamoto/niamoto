// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ConfiguredWidget } from './useWidgetConfig'
import { WidgetConfigForm } from './WidgetConfigForm'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
  }),
}))

vi.mock('@/components/forms/JsonSchemaForm', () => ({
  default: ({ onChange }: { onChange?: (data: Record<string, unknown>) => void }) => (
    <button
      type="button"
      data-testid="json-schema-change"
      onClick={() => onChange?.({ color: 'blue' })}
    >
      JSON change
    </button>
  ),
}))

vi.mock('@/components/ui/localized-input', () => ({
  LocalizedInput: ({
    label,
    value,
    onChange,
  }: {
    label?: string
    value?: string | Record<string, string>
    onChange: (value: string | undefined) => void
  }) => (
    <div>
      <input
        aria-label={label}
        value={typeof value === 'string' ? value : value?.fr ?? ''}
        readOnly
      />
      <button
        type="button"
        data-testid={`change-${label}`}
        onClick={() => onChange('Richesse modifiée')}
      >
        Modifier
      </button>
    </div>
  ),
}))

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const baseWidget: ConfiguredWidget = {
  id: 'richness',
  transformerPlugin: 'field_aggregator',
  widgetPlugin: 'bar_plot',
  title: 'Richesse',
  description: "Nombre d'espèces",
  dataSource: 'richness',
  transformerParams: { field: 'id' },
  widgetParams: { color: 'green' },
  category: 'chart',
  hasTransformConfig: true,
}

describe('WidgetConfigForm', () => {
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
    vi.useRealTimers()
  })

  function render(ui: ReactNode) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    act(() => {
      root?.render(ui)
    })
  }

  it('does not emit a live preview draft on initial mount', async () => {
    vi.useFakeTimers()
    const onChange = vi.fn()

    render(
      <WidgetConfigForm
        widget={baseWidget}
        groupBy="taxons"
        onSave={vi.fn()}
        onCancel={vi.fn()}
        onChange={onChange}
      />,
    )

    await act(async () => {
      vi.advanceTimersByTime(400)
    })

    expect(onChange).not.toHaveBeenCalled()
  })

  it('emits a live preview draft after a user edit', async () => {
    vi.useFakeTimers()
    const onChange = vi.fn()

    render(
      <WidgetConfigForm
        widget={baseWidget}
        groupBy="taxons"
        onSave={vi.fn()}
        onCancel={vi.fn()}
        onChange={onChange}
      />,
    )

    act(() => {
      container
        ?.querySelector<HTMLButtonElement>('[data-testid="change-Titre"]')
        ?.click()
    })

    await act(async () => {
      vi.advanceTimersByTime(400)
    })

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Richesse modifiée',
        transformerParams: baseWidget.transformerParams,
        widgetParams: baseWidget.widgetParams,
      }),
    )
  })
})
