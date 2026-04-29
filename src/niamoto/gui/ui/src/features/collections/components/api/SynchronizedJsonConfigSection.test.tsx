// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SynchronizedJsonConfigSection } from './SynchronizedJsonConfigSection'

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

function input(element: HTMLTextAreaElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(element),
    'value'
  )?.set
  setter?.call(element, value)
  element.dispatchEvent(new Event('input', { bubbles: true }))
  element.dispatchEvent(new Event('change', { bubbles: true }))
}

describe('SynchronizedJsonConfigSection', () => {
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

  async function renderSection(element: ReactNode) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(element)
    })
  }

  it('shows the JSON representation for the same visual value', async () => {
    await renderSection(
      <SynchronizedJsonConfigSection
        name="index-fields"
        value={[{ name: 'general_info.name.value' }]}
        onChange={vi.fn()}
        validate={(value): value is unknown[] => Array.isArray(value)}
      >
        <div>Visual editor</div>
      </SynchronizedJsonConfigSection>
    )

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('json')
        ) ?? null
      )
    })

    const textarea = container!.querySelector('textarea') as HTMLTextAreaElement
    expect(textarea.value).toContain('general_info.name.value')
  })

  it('shows a read-only JSON preview next to the visual editor', async () => {
    await renderSection(
      <SynchronizedJsonConfigSection
        name="index-fields"
        value={[{ name: 'general_info.name.value' }]}
        onChange={vi.fn()}
        validate={(value): value is unknown[] => Array.isArray(value)}
        showJsonPreview
        jsonPreviewValue={{ name: 'Araucaria columnaris' }}
      >
        <div>Visual editor</div>
      </SynchronizedJsonConfigSection>
    )

    const preview = container!.querySelector(
      'pre[aria-label="collectionPanel.api.jsonPreview"]'
    )

    expect(container!.textContent).toContain('Visual editor')
    expect(container!.textContent).toContain('collectionPanel.api.jsonPreview')
    expect(preview?.textContent).toContain('Araucaria columnaris')
  })

  it('accepts valid JSON that matches the section shape', async () => {
    const onChange = vi.fn()
    await renderSection(
      <SynchronizedJsonConfigSection
        name="index-fields"
        value={[]}
        onChange={onChange}
        validate={(value): value is unknown[] => Array.isArray(value)}
      >
        <div>Visual editor</div>
      </SynchronizedJsonConfigSection>
    )

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('json')
        ) ?? null
      )
    })

    await act(async () => {
      input(
        container!.querySelector('textarea') as HTMLTextAreaElement,
        '[{"name":"general_info.name.value"}]'
      )
    })

    expect(onChange).toHaveBeenLastCalledWith([
      { name: 'general_info.name.value' },
    ])
  })

  it('blocks valid JSON with the wrong section shape', async () => {
    const onChange = vi.fn()
    await renderSection(
      <SynchronizedJsonConfigSection
        name="index-fields"
        value={[]}
        onChange={onChange}
        validate={(value): value is unknown[] => Array.isArray(value)}
      >
        <div>Visual editor</div>
      </SynchronizedJsonConfigSection>
    )

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('json')
        ) ?? null
      )
    })

    await act(async () => {
      input(
        container!.querySelector('textarea') as HTMLTextAreaElement,
        '{"name":"general_info.name.value"}'
      )
    })

    expect(container!.textContent).toContain('collectionPanel.api.jsonShapeError')
    expect(onChange).not.toHaveBeenCalled()
  })
})
