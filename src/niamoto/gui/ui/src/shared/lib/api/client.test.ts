import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosHeaders } from 'axios'

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

function getRequestFulfilledHandler(apiClient: {
  interceptors: {
    request: {
      handlers: Array<{
        fulfilled?: (config: { headers: AxiosHeaders }) => Promise<{ headers: AxiosHeaders }>
      }>
    }
  }
}) {
  const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
  if (!handler) {
    throw new Error('Expected a registered request interceptor')
  }
  return handler
}

describe('apiClient', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.doMock('@/shared/desktop/apiAuth', () => ({
      DESKTOP_API_AUTH_HEADER: 'x-niamoto-desktop-token',
      getDesktopApiAuthToken: vi.fn(async () => null),
    }))
    promptServerErrorBugReport.mockReset()
  })

  it('uses the expected API defaults', async () => {
    const { apiClient } = await import('./client')

    expect(apiClient.defaults.baseURL).toBe('/api')
    expect(apiClient.defaults.timeout).toBe(180000)
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('leaves requests unchanged outside desktop auth mode', async () => {
    const { apiClient } = await import('./client')
    const fulfilled = getRequestFulfilledHandler(apiClient as never)
    const config = { headers: new AxiosHeaders() }

    const result = await fulfilled(config)

    expect(result.headers.has('x-niamoto-desktop-token')).toBe(false)
  })

  it('attaches the desktop API token when available', async () => {
    vi.doMock('@/shared/desktop/apiAuth', () => ({
      DESKTOP_API_AUTH_HEADER: 'x-niamoto-desktop-token',
      getDesktopApiAuthToken: vi.fn(async () => 'desktop-token'),
    }))
    const { apiClient } = await import('./client')
    const fulfilled = getRequestFulfilledHandler(apiClient as never)
    const config = { headers: new AxiosHeaders() }

    const result = await fulfilled(config)

    expect(result.headers.get('x-niamoto-desktop-token')).toBe('desktop-token')
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
