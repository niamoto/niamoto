import { beforeEach, describe, expect, it, vi } from 'vitest'

const promptServerErrorBugReport = vi.hoisted(() => vi.fn())

vi.mock('@/features/feedback/lib/server-error-feedback', () => ({
  promptServerErrorBugReport,
}))

function getRejectedResponseHandler(apiClient: {
  interceptors: { response: { handlers: Array<{ rejected?: (error: unknown) => Promise<never> }> } }
}) {
  const handler = apiClient.interceptors.response.handlers[0]?.rejected
  if (!handler) {
    throw new Error('Expected a registered response error interceptor')
  }
  return handler
}

describe('apiClient', () => {
  beforeEach(() => {
    vi.resetModules()
    promptServerErrorBugReport.mockReset()
  })

  it('uses the expected API defaults', async () => {
    const { apiClient } = await import('./client')

    expect(apiClient.defaults.baseURL).toBe('/api')
    expect(apiClient.defaults.timeout).toBe(180000)
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('reports 500 responses for bug-report feedback', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { apiClient } = await import('./client')
    const rejected = getRejectedResponseHandler(apiClient as never)
    const error = {
      response: { status: 500, data: { detail: 'Database unavailable' } },
      config: { url: '/publish/start' },
      message: 'Request failed',
    }

    await expect(rejected(error)).rejects.toBe(error)

    expect(consoleError).toHaveBeenCalledWith('Server error:', 'Database unavailable')
    expect(promptServerErrorBugReport).toHaveBeenCalledWith(
      '/publish/start',
      'Database unavailable'
    )

    consoleError.mockRestore()
  })

  it('logs 404 responses without prompting bug-report feedback', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { apiClient } = await import('./client')
    const rejected = getRejectedResponseHandler(apiClient as never)
    const error = {
      response: { status: 404, data: {} },
      config: { url: '/missing-resource' },
      message: 'Not found',
    }

    await expect(rejected(error)).rejects.toBe(error)

    expect(consoleError).toHaveBeenCalledWith('Resource not found:', '/missing-resource')
    expect(promptServerErrorBugReport).not.toHaveBeenCalled()

    consoleError.mockRestore()
  })
})
