// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it } from 'vitest'

import { Input } from './input'
import { Textarea } from './textarea'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('text input defaults', () => {
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

  async function render(element: ReactNode) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(element)
    })
  }

  it('disables browser text rewriting by default on inputs and textareas', async () => {
    await render(
      <>
        <Input />
        <Textarea />
      </>
    )

    const input = container!.querySelector('input') as HTMLInputElement
    const textarea = container!.querySelector('textarea') as HTMLTextAreaElement

    expect(input.getAttribute('autocapitalize')).toBe('none')
    expect(input.getAttribute('autocorrect')).toBe('off')
    expect(input.getAttribute('spellcheck')).toBe('false')
    expect(textarea.getAttribute('autocapitalize')).toBe('none')
    expect(textarea.getAttribute('autocorrect')).toBe('off')
    expect(textarea.getAttribute('spellcheck')).toBe('false')
  })

  it('allows explicit overrides for prose fields', async () => {
    await render(<Textarea autoCapitalize="sentences" autoCorrect="on" spellCheck />)

    const textarea = container!.querySelector('textarea') as HTMLTextAreaElement

    expect(textarea.getAttribute('autocapitalize')).toBe('sentences')
    expect(textarea.getAttribute('autocorrect')).toBe('on')
    expect(textarea.getAttribute('spellcheck')).toBe('true')
  })
})
