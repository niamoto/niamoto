// @vitest-environment jsdom

import { act, useLayoutEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FeedbackProvider } from './FeedbackProvider'
import { useFeedback } from './useFeedback'
import type { FeedbackContext as FeedbackContextData } from '../types'

const mocks = vi.hoisted(() => ({
  sendFeedback: vi.fn(),
  downloadFeedbackReport: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  openExternalUrl: vi.fn(),
  capture: vi.fn(async () => {}),
  clear: vi.fn(),
  collect: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: mocks.toastSuccess,
    error: mocks.toastError,
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('../lib/feedback-api', () => ({
  sendFeedback: mocks.sendFeedback,
  downloadFeedbackReport: mocks.downloadFeedbackReport,
}))

vi.mock('../hooks/useScreenshot', () => ({
  useScreenshot: () => ({
    screenshot: null,
    isCapturing: false,
    error: false,
    capture: mocks.capture,
    clear: mocks.clear,
  }),
}))

vi.mock('../hooks/useContextData', () => ({
  useContextData: () => ({
    collect: mocks.collect,
  }),
}))

vi.mock('@/shared/desktop/openExternalUrl', () => ({
  openExternalUrl: mocks.openExternalUrl,
}))

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const contextData: FeedbackContextData = {
  app_version: '0.0.0',
  os: 'linux',
  current_page: '/settings',
  runtime_mode: 'desktop',
  theme: 'forest (light)',
  language: 'fr',
  window_size: '1280x900',
  timestamp: '2026-06-06T10:00:00.000Z',
}

describe('FeedbackProvider', () => {
  let container: HTMLDivElement | null = null

  afterEach(() => {
    container?.remove()
    container = null
    vi.clearAllMocks()
  })

  it('keeps the modal open and exposes the generated report actions', async () => {
    const githubIssueUrl = 'https://github.com/niamoto/niamoto/issues/new?title=Broken'
    mocks.collect.mockResolvedValue(contextData)
    mocks.sendFeedback.mockResolvedValue({
      success: true,
      report_downloaded: false,
      report_format: 'markdown',
      report_filename: 'niamoto-feedback-broken.md',
      report_content: '# Broken feedback',
      screenshot_included: false,
      github_issue_url: githubIssueUrl,
    })
    mocks.downloadFeedbackReport.mockResolvedValue({
      status: 'saved',
      filename: 'niamoto-feedback-broken.md',
      path: '/Users/julien/Desktop/niamoto-feedback-broken.md',
    })

    container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    const feedbackRef: { current: ReturnType<typeof useFeedback> | null } = { current: null }

    function Probe() {
      const feedback = useFeedback()

      useLayoutEffect(() => {
        feedbackRef.current = feedback
      }, [feedback])

      return null
    }

    await act(async () => {
      root.render(
        <FeedbackProvider>
          <Probe />
        </FeedbackProvider>
      )
    })

    await act(async () => {
      await feedbackRef.current?.openWithType('bug')
    })
    await act(async () => {
      await feedbackRef.current?.send('Broken feedback', 'The report is ready.', false)
    })

    expect(mocks.toastSuccess).not.toHaveBeenCalled()
    expect(feedbackRef.current?.isOpen).toBe(true)
    expect(feedbackRef.current?.generatedReport).toMatchObject({
      report_filename: 'niamoto-feedback-broken.md',
      report_content: '# Broken feedback',
      github_issue_url: githubIssueUrl,
    })

    await act(async () => {
      await feedbackRef.current?.downloadGeneratedReport()
    })
    expect(mocks.downloadFeedbackReport).toHaveBeenCalledWith(expect.objectContaining({
      report_filename: 'niamoto-feedback-broken.md',
    }))
    expect(feedbackRef.current?.reportDownloadState).toEqual({
      status: 'saved',
      filename: 'niamoto-feedback-broken.md',
      path: '/Users/julien/Desktop/niamoto-feedback-broken.md',
    })

    await act(async () => {
      feedbackRef.current?.openGeneratedReportIssue()
    })
    expect(mocks.openExternalUrl).toHaveBeenCalledWith(githubIssueUrl)

    await act(async () => {
      root.unmount()
    })
  })
})
