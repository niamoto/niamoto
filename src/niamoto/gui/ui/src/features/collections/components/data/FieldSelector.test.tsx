// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FieldSelector } from './FieldSelector'

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

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

describe('FieldSelector', () => {
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

  async function renderSelector(onChange = vi.fn()) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <FieldSelector
          value=""
          placeholder="Select a source field"
          emptyLabel="No fields"
          searchPlaceholder="Search fields"
          options={[
            {
              value: 'general_info.name.value',
              label: 'Name',
              description: 'general_info.name.value',
              groupKey: 'generalInfo',
              groupLabel: 'General information',
            },
            {
              value: 'stats.richness.value',
              label: 'Richness',
              description: 'stats.richness.value',
              groupKey: 'statistics',
              groupLabel: 'Statistics',
            },
          ]}
          onChange={onChange}
        />,
      )
    })
  }

  it('opens grouped searchable source fields and returns the selected value', async () => {
    const onChange = vi.fn()
    await renderSelector(onChange)

    await act(async () => {
      click(container!.querySelector('button'))
    })

    expect(document.body.textContent).toContain('General information')
    expect(document.body.textContent).toContain('Statistics')

    await act(async () => {
      click(
        Array.from(document.body.querySelectorAll('[cmdk-item]')).find((item) =>
          item.textContent?.includes('Richness'),
        ) ?? null,
      )
    })

    expect(onChange).toHaveBeenCalledWith('stats.richness.value')
  })
})
