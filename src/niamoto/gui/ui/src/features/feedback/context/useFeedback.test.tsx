// @vitest-environment jsdom

import { act, useLayoutEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FeedbackContext, type FeedbackState } from './feedbackContext'
import { useFeedback } from './useFeedback'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

function makeFeedbackState(): FeedbackState {
  return {
    isOpen: true,
    type: 'bug',
    isSending: false,
    cooldownRemaining: 0,
    screenshot: null,
    screenshotError: false,
    isPreparingScreenshot: false,
    contextData: null,
    draftTitle: 'Draft',
    draftDescription: 'Description',
    openWithType: vi.fn(async () => {}),
    close: vi.fn(),
    setType: vi.fn(),
    captureScreenshot: vi.fn(async () => {}),
    send: vi.fn(async () => {}),
  }
}

describe('useFeedback', () => {
  let container: HTMLDivElement | null = null

  afterEach(() => {
    container?.remove()
    container = null
  })

  it('returns the provider value when rendered inside FeedbackContext', async () => {
    const expected = makeFeedbackState()
    container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    const receivedRef: { current: FeedbackState | null } = { current: null }

    function Probe() {
      const feedback = useFeedback()

      useLayoutEffect(() => {
        receivedRef.current = feedback
      }, [feedback])

      return null
    }

    await act(async () => {
      root.render(
        <FeedbackContext.Provider value={expected}>
          <Probe />
        </FeedbackContext.Provider>
      )
    })

    expect(receivedRef.current).toBe(expected)

    await act(async () => {
      root.unmount()
    })
  })

  it('throws when used outside FeedbackContext', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)

    function Probe() {
      useFeedback()
      return null
    }

    expect(() => {
      act(() => {
        root.render(<Probe />)
      })
    }).toThrow('useFeedback must be used within a FeedbackProvider')

    consoleError.mockRestore()
  })
})
