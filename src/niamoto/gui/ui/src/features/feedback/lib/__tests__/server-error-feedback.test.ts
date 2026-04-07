import { beforeEach, describe, expect, it, vi } from 'vitest'

const toastError = vi.fn()
const requestBugReport = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    error: toastError,
  },
}))

vi.mock('../bug-report-bridge', () => ({
  requestBugReport,
}))

describe('server-error-feedback', () => {
  beforeEach(async () => {
    vi.resetModules()
    toastError.mockReset()
    requestBugReport.mockReset()
  })

  it('shows a reportable toast for a 500 error', async () => {
    const mod = await import('../server-error-feedback')

    mod.promptServerErrorBugReport(
      '/api/stats/summary',
      'Catalog Error: Table with name pg_collation does not exist'
    )

    expect(toastError).toHaveBeenCalledTimes(1)
    const [, options] = toastError.mock.calls[0]
    expect(options.description).toContain('pg_collation')
    expect(options.action.label).toBeTruthy()

    options.action.onClick()

    expect(requestBugReport).toHaveBeenCalledWith(
      expect.objectContaining({
        title: expect.stringContaining('/api/stats/summary'),
        description: expect.stringContaining('pg_collation'),
      })
    )
  })

  it('deduplicates repeated prompts for the same failing endpoint', async () => {
    const mod = await import('../server-error-feedback')

    mod.promptServerErrorBugReport('/api/stats/summary', 'same error')
    mod.promptServerErrorBugReport('/api/stats/summary', 'same error')

    expect(toastError).toHaveBeenCalledTimes(1)
    mod.resetServerErrorFeedbackForTests()
  })
})
