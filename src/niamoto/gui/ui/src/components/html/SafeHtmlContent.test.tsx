// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it } from 'vitest'

import { SafeHtmlContent } from './SafeHtmlContent'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('SafeHtmlContent', () => {
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

  function render(element: ReactNode) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    act(() => {
      root?.render(element)
    })
  }

  it('renders supported documentation markup without unsafe attributes', () => {
    render(
      <SafeHtmlContent
        html={'<h2 id="intro" onclick="alert(1)">Intro</h2><p>An <strong>outlier</strong>.</p><script>alert(1)</script>'}
      />
    )

    expect(container?.querySelector('h2')?.id).toBe('intro')
    expect(container?.querySelector('h2')?.getAttribute('onclick')).toBeNull()
    expect(container?.querySelector('strong')?.textContent).toBe('outlier')
    expect(container?.querySelector('script')).toBeNull()
  })

  it('keeps safe links and rejects unsafe protocols', () => {
    render(
      <SafeHtmlContent
        html={'<a href="https://example.org">External</a><a href="javascript:alert(1)">Unsafe</a><a href="/help/start">Internal</a>'}
      />
    )

    const links = Array.from(container?.querySelectorAll('a') ?? [])
    expect(links[0].getAttribute('href')).toBe('https://example.org')
    expect(links[0].getAttribute('target')).toBe('_blank')
    expect(links[0].getAttribute('rel')).toBe('noreferrer noopener')
    expect(links[1].getAttribute('href')).toBeNull()
    expect(links[2].getAttribute('href')).toBe('/help/start')
    expect(links[2].getAttribute('target')).toBeNull()
  })

  it('renders image tags from documentation html without passing children to img', () => {
    expect(() => {
      render(
        <SafeHtmlContent
          html={'<p><a href="https://example.org"><img src="https://example.org/logo.png" alt="Logo" height="52" /></a></p>'}
        />
      )
    }).not.toThrow()

    const image = container?.querySelector('img')
    expect(image?.getAttribute('src')).toBe('https://example.org/logo.png')
    expect(image?.getAttribute('alt')).toBe('Logo')
    expect(image?.getAttribute('height')).toBe('52')
  })
})
