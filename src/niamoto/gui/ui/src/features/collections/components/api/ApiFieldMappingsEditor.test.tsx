// @vitest-environment jsdom

import { act, useState, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ApiFieldMappingsEditor,
  type ApiFieldMappingValue,
} from './ApiFieldMappingsEditor'

globalThis.IS_REACT_ACT_ENVIRONMENT = true
Element.prototype.scrollIntoView = vi.fn()
HTMLElement.prototype.hasPointerCapture = vi.fn(() => false)
HTMLElement.prototype.releasePointerCapture = vi.fn()
HTMLElement.prototype.setPointerCapture = vi.fn()

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

function input(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(element),
    'value'
  )?.set
  setter?.call(element, value)
  element.dispatchEvent(new Event('input', { bubbles: true }))
  element.dispatchEvent(new Event('change', { bubbles: true }))
}

describe('ApiFieldMappingsEditor', () => {
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

  async function renderEditor(element: ReactNode) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(element)
    })
  }

  it('renders simple string fields as matching output and source values', async () => {
    await renderEditor(
      <ApiFieldMappingsEditor value={['general_info.name.value']} onChange={vi.fn()} />
    )

    const inputs = Array.from(container!.querySelectorAll('input'))
    expect(inputs[0].value).toBe('general_info.name.value')
    expect(container!.textContent).toContain('general_info.name.value')
  })

  it('places the add field button after the field list', async () => {
    await renderEditor(
      <ApiFieldMappingsEditor value={['general_info.name.value']} onChange={vi.fn()} />
    )

    const text = container!.textContent ?? ''
    const firstFieldPosition = text.indexOf(
      'collectionPanel.api.fieldMappings.outputField'
    )
    const addButtonPosition = text.indexOf(
      'collectionPanel.api.fieldMappings.addField'
    )

    expect(firstFieldPosition).toBeGreaterThanOrEqual(0)
    expect(addButtonPosition).toBeGreaterThan(firstFieldPosition)
  })

  it('adds field suggestions as explicit source mappings', async () => {
    const onChange = vi.fn()
    await renderEditor(
      <ApiFieldMappingsEditor
        value={[]}
        onChange={onChange}
        suggestions={[
          {
            name: 'name',
            source: 'general_info.name.value',
            label: 'Name',
          },
        ]}
      />
    )

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('Name')
        ) ?? null
      )
    })

    expect(onChange).toHaveBeenLastCalledWith([
      { name: 'general_info.name.value' },
    ])
  })

  it('keeps focus while typing in a field mapping input', async () => {
    function Harness() {
      const [value, setValue] = useState<ApiFieldMappingValue[]>([
        { name: 'general_info.name.value' },
      ])
      return <ApiFieldMappingsEditor value={value} onChange={setValue} />
    }

    await renderEditor(<Harness />)

    const outputInput = container!.querySelector('input') as HTMLInputElement
    outputInput.focus()

    await act(async () => {
      input(outputInput, 'display_name')
    })

    expect(document.activeElement).toBe(outputInput)
    expect(outputInput.value).toBe('display_name')
  })

  it('suggests value paths by their parent metric and skips unit chips', async () => {
    const onChange = vi.fn()
    await renderEditor(
      <ApiFieldMappingsEditor
        value={[]}
        onChange={onChange}
        sourceFields={[
          {
            name: 'value',
            source: 'stats.richness.value',
            label: 'Value',
          },
          {
            name: 'units',
            source: 'stats.richness.units',
            label: 'Units',
          },
        ]}
      />
    )

    const buttons = Array.from(container!.querySelectorAll('button'))
    const richnessButton = buttons.find((button) =>
      button.textContent?.includes('Richness')
    )
    const unitButtons = buttons.filter((button) =>
      button.textContent?.includes('Units')
    )

    expect(richnessButton).toBeDefined()
    expect(unitButtons).toHaveLength(0)

    await act(async () => {
      click(richnessButton ?? null)
    })

    expect(onChange).toHaveBeenLastCalledWith([
      { richness: 'stats.richness.value' },
    ])
  })

  it('distinguishes full object options from value options', async () => {
    await renderEditor(
      <ApiFieldMappingsEditor
        value={[]}
        onChange={vi.fn()}
        sourceFields={[
          {
            name: 'basal_area',
            source: 'basal_area',
            label: 'Basal Area',
          },
          {
            name: 'value',
            source: 'basal_area.value',
            label: 'Value',
          },
        ]}
      />
    )

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes(
            'collectionPanel.api.fieldMappings.selectSourcePath'
          )
        ) ?? null
      )
    })

    expect(document.body.textContent).toContain(
      'Basal Area (collectionPanel.api.fieldMappings.allFields)'
    )
    expect(document.body.textContent).toContain('Basal Area value')
  })

  it('groups source path options by logical section', async () => {
    await renderEditor(
      <ApiFieldMappingsEditor
        value={[]}
        onChange={vi.fn()}
        sourceFields={[
          {
            name: 'name',
            source: 'general_info.name.value',
            label: 'Name',
          },
          {
            name: 'value',
            source: 'stats.richness.value',
            label: 'Value',
          },
          {
            name: 'value',
            source: 'extra_data.gbif.score.value',
            label: 'Value',
          },
        ]}
      />
    )

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes(
            'collectionPanel.api.fieldMappings.selectSourcePath'
          )
        ) ?? null
      )
    })

    expect(document.body.textContent).toContain(
      'collectionPanel.api.fieldMappings.sourceGroups.generalInfo'
    )
    expect(document.body.textContent).toContain(
      'collectionPanel.api.fieldMappings.sourceGroups.statistics'
    )
    expect(document.body.textContent).toContain(
      'collectionPanel.api.fieldMappings.sourceGroups.externalData'
    )
  })

  it('keeps generated mapping params visible and blocks invalid JSON params', async () => {
    const onChange = vi.fn()
    await renderEditor(
      <ApiFieldMappingsEditor
        value={[
          {
            occurrenceID: {
              generator: 'unique_occurrence_id',
              params: { prefix: 'NIAOCC-' },
            },
          },
        ]}
        onChange={onChange}
      />
    )

    const textarea = container!.querySelector('textarea') as HTMLTextAreaElement
    expect(textarea.value).toContain('NIAOCC-')

    await act(async () => {
      input(textarea, '{')
    })

    expect(container!.textContent).toContain('Invalid JSON in params')
    expect(onChange).not.toHaveBeenCalled()
  })
})
