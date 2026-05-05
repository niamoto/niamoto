// @vitest-environment jsdom

import { act } from 'react'
import type { ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DwcMappingEditor } from './DwcMappingEditor'

globalThis.IS_REACT_ACT_ENVIRONMENT = true
Element.prototype.scrollIntoView = vi.fn()
HTMLElement.prototype.hasPointerCapture = vi.fn(() => false)
HTMLElement.prototype.releasePointerCapture = vi.fn()
HTMLElement.prototype.setPointerCapture = vi.fn()
vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
)

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      key === 'collectionPanel.api.mappingTermFallback'
        ? `Term ${opts?.index}`
        : key,
  }),
}))

vi.mock('@/components/ui/select', () => ({
  Select: (props: { children: ReactNode }) => <div>{props.children}</div>,
  SelectContent: (props: { children: ReactNode }) => <div>{props.children}</div>,
  SelectItem: (props: { children: ReactNode; value: string }) => (
    <div data-value={props.value}>{props.children}</div>
  ),
  SelectTrigger: (props: { children: ReactNode }) => (
    <button type="button">{props.children}</button>
  ),
  SelectValue: (props: { placeholder?: string }) => <span>{props.placeholder}</span>,
}))

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

describe('DwcMappingEditor', () => {
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
  })

  async function renderEditor(
    value: Record<string, unknown> = {},
    sourceFields: string[] = [],
    onChange = vi.fn(),
    generatorOptions?: string[],
  ) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <DwcMappingEditor
          value={value}
          sourceFields={sourceFields}
          onChange={onChange}
          generatorOptions={generatorOptions}
        />,
      )
    })
    return { onChange }
  }

  it('shows an empty state instead of a placeholder row for empty mappings', async () => {
    await renderEditor()

    expect(container!.textContent).toContain('collectionPanel.api.dwcMappingEmpty')
    expect(container!.textContent).not.toContain('Term 1')
    expect(container!.querySelectorAll('input')).toHaveLength(0)
  })

  it('adds an empty row on demand', async () => {
    await renderEditor()

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('common:actions.add')
        ) ?? null
      )
    })

    const inputs = Array.from(container!.querySelectorAll('input'))
    expect(container!.textContent).toContain('Term 1')
    expect((inputs[0] as HTMLInputElement).value).toBe('')
    expect((inputs[1] as HTMLInputElement).value).toBe('')
  })

  it('keeps the edited row mounted while typing a term', async () => {
    await renderEditor({ scientificName: '@taxon.full_name' })

    const termInput = container!.querySelector('input') as HTMLInputElement
    termInput.focus()

    await act(async () => {
      termInput.value = 'scientificName2'
      termInput.dispatchEvent(new Event('input', { bubbles: true }))
    })

    const nextTermInput = container!.querySelector('input') as HTMLInputElement
    expect(nextTermInput).toBe(termInput)
    expect(document.activeElement).toBe(termInput)
  })

  it('shows source field options while preserving a manual reference input', async () => {
    await renderEditor({ occurrenceID: { source: 'id' } }, ['id', 'taxon_id'])

    expect(container!.textContent).toContain('collectionPanel.api.sourceField')
    expect(container!.textContent).toContain('id')
    await act(async () => {
      click(container!.querySelector('button[aria-label="collectionPanel.api.sourceField"]'))
    })

    expect(document.body.textContent).toContain('taxon_id')
    expect(container!.textContent).toContain('collectionPanel.api.customSourceReference')
    expect((container!.querySelectorAll('input')[1] as HTMLInputElement).value).toBe(
      'id',
    )
  })

  it('serializes source references explicitly for DwC exporters', async () => {
    const onChange = vi.fn()
    await renderEditor({ occurrenceID: { source: 'id' } }, ['id', 'taxon_id'], onChange)

    const manualReferenceInput = container!.querySelectorAll('input')[1] as HTMLInputElement

    await act(async () => {
      Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        'value',
      )?.set?.call(manualReferenceInput, 'taxon_id')
      manualReferenceInput.dispatchEvent(new Event('input', { bubbles: true }))
      manualReferenceInput.dispatchEvent(new Event('change', { bubbles: true }))
    })

    expect(onChange).toHaveBeenLastCalledWith({
      occurrenceID: { source: '@source.taxon_id' },
    })
  })

  it('can fill suggested generator params from available source fields', async () => {
    await renderEditor(
      { decimalLatitude: { generator: 'extract_geometry_coordinate' } },
      ['id', 'geo_pt'],
    )

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('collectionPanel.api.useSuggestedGeneratorParams'),
        ) ?? null,
      )
    })

    const params = container!.querySelector('textarea') as HTMLTextAreaElement
    expect(params.value).toContain('"source": "geo_pt"')
    expect(params.value).toContain('"coordinate": "latitude"')
  })

  it('can limit generator options for standard profile mappings', async () => {
    await renderEditor(
      { eventDate: { generator: 'current_date' } },
      [],
      vi.fn(),
      ['current_date'],
    )

    expect(container!.textContent).toContain('current_date')
    expect(container!.textContent).not.toContain('format_event_date')
  })
})
