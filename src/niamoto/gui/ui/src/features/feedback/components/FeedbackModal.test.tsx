// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FeedbackContext, type FeedbackState } from '../context/feedbackContext'
import { FeedbackModal } from './FeedbackModal'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, string>) => {
      if (!options) return key
      return `${key}: ${Object.values(options).join(' ')}`
    },
  }),
}))

globalThis.IS_REACT_ACT_ENVIRONMENT = true

function makeFeedbackState(overrides: Partial<FeedbackState> = {}): FeedbackState {
  return {
    isOpen: true,
    type: 'bug',
    isSending: false,
    cooldownRemaining: 0,
    screenshot: null,
    screenshotError: false,
    isPreparingScreenshot: false,
    contextData: null,
    draftTitle: 'Broken feedback',
    draftDescription: '',
    generatedReport: {
      success: true,
      report_downloaded: false,
      report_format: 'markdown',
      report_filename: 'niamoto-feedback-broken.md',
      report_content: '# Broken feedback',
      screenshot_included: false,
      github_issue_url: 'https://github.com/niamoto/niamoto/issues/new?title=Broken',
    },
    reportDownloadState: { status: 'idle' },
    openWithType: vi.fn(async () => {}),
    close: vi.fn(),
    setType: vi.fn(),
    captureScreenshot: vi.fn(async () => {}),
    send: vi.fn(async () => {}),
    clearGeneratedReport: vi.fn(),
    downloadGeneratedReport: vi.fn(async () => {}),
    openGeneratedReportIssue: vi.fn(),
    ...overrides,
  }
}

describe('FeedbackModal', () => {
  let container: HTMLDivElement | null = null

  afterEach(() => {
    container?.remove()
    container = null
    document.body.replaceChildren()
    vi.clearAllMocks()
  })

  it('shows a persistent local report explanation and download action', async () => {
    const feedback = makeFeedbackState()
    container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)

    await act(async () => {
      root.render(
        <FeedbackContext.Provider value={feedback}>
          <FeedbackModal />
        </FeedbackContext.Provider>
      )
    })

    expect(document.body.textContent).toContain('report_ready_title')
    expect(document.body.textContent).toContain('report_ready_description')
    expect(document.body.textContent).toContain('niamoto-feedback-broken.md')

    const buttons = Array.from(document.body.querySelectorAll('button'))
    const downloadButton = buttons.find((button) => (
      button.textContent?.includes('download_report')
    ))
    const githubButton = buttons.find((button) => (
      button.textContent?.includes('open_github_issue')
    ))

    expect(downloadButton).toBeTruthy()
    expect(githubButton).toBeTruthy()

    await act(async () => {
      downloadButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      githubButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(feedback.downloadGeneratedReport).toHaveBeenCalledTimes(1)
    expect(feedback.openGeneratedReportIssue).toHaveBeenCalledTimes(1)

    await act(async () => {
      root.unmount()
    })
  })

  it('shows the saved report path after a native desktop save', async () => {
    const feedback = makeFeedbackState({
      reportDownloadState: {
        status: 'saved',
        filename: 'niamoto-feedback-broken.md',
        path: '/Users/julien/Desktop/niamoto-feedback-broken.md',
      },
    })
    container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)

    await act(async () => {
      root.render(
        <FeedbackContext.Provider value={feedback}>
          <FeedbackModal />
        </FeedbackContext.Provider>
      )
    })

    expect(document.body.textContent).toContain('download_saved_path')
    expect(document.body.textContent).toContain('/Users/julien/Desktop/niamoto-feedback-broken.md')
    expect(document.body.textContent).toContain('download_again')

    await act(async () => {
      root.unmount()
    })
  })

  it('closes directly without discard confirmation when a report is generated', async () => {
    const feedback = makeFeedbackState()
    container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)

    await act(async () => {
      root.render(
        <FeedbackContext.Provider value={feedback}>
          <FeedbackModal />
        </FeedbackContext.Provider>
      )
    })

    const closeButton = Array.from(document.body.querySelectorAll('button')).find((button) => (
      button.textContent?.includes('Close')
    ))

    await act(async () => {
      closeButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(feedback.close).toHaveBeenCalledTimes(1)
    expect(document.body.textContent).not.toContain('confirm_close_title')

    await act(async () => {
      root.unmount()
    })
  })

  it('keeps the discard confirmation for an unsent draft', async () => {
    const feedback = makeFeedbackState({
      generatedReport: null,
    })
    container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)

    await act(async () => {
      root.render(
        <FeedbackContext.Provider value={feedback}>
          <FeedbackModal />
        </FeedbackContext.Provider>
      )
    })

    const closeButton = Array.from(document.body.querySelectorAll('button')).find((button) => (
      button.textContent?.includes('Close')
    ))

    await act(async () => {
      closeButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(feedback.close).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('confirm_close_title')

    await act(async () => {
      root.unmount()
    })
  })
})
