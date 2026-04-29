// @vitest-environment jsdom

import { act } from 'react'
import type { ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DwcMappingEditor } from './DwcMappingEditor'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

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

  async function renderEditor(value: Record<string, unknown> = {}) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(<DwcMappingEditor value={value} onChange={vi.fn()} />)
    })
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
})
