import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()

describe('feedback-api', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.unstubAllEnvs()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  it('posts to the feedback proxy even when client feedback config is missing', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, screenshot_uploaded: false }),
    })

    const mod = await import('../feedback-api')

    const result = await mod.sendFeedback({
      payload: {
        type: 'bug',
        title: 'Broken feedback',
        context: {
          app_version: '0.0.0',
          os: 'linux',
          current_page: '/settings',
          runtime_mode: 'desktop',
          theme: 'forest (light)',
          language: 'fr',
          window_size: '1280×900',
          timestamp: new Date().toISOString(),
        },
      },
    })

    expect(result.success).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/feedback/submit',
      expect.objectContaining({
        method: 'POST',
      })
    )
    const formData = fetchMock.mock.calls[0]?.[1]?.body as FormData
    expect(formData.has('worker_url')).toBe(false)
    expect(formData.has('api_key')).toBe(false)
  })

  it('does not send client feedback config when Vite env values are present', async () => {
    vi.stubEnv('VITE_FEEDBACK_WORKER_URL', 'https://feedback.example.com')
    vi.stubEnv('VITE_FEEDBACK_API_KEY', 'secret')
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, screenshot_uploaded: false }),
    })

    const mod = await import('../feedback-api')

    const result = await mod.sendFeedback({
      payload: {
        type: 'bug',
        title: 'Broken feedback',
        context: {
          app_version: '0.0.0',
          os: 'linux',
          current_page: '/settings',
          runtime_mode: 'desktop',
          theme: 'forest (light)',
          language: 'fr',
          window_size: '1280×900',
          timestamp: new Date().toISOString(),
        },
      },
    })

    expect(result.success).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/feedback/submit',
      expect.objectContaining({
        method: 'POST',
      })
    )
    const formData = fetchMock.mock.calls[0]?.[1]?.body as FormData
    expect(formData.has('worker_url')).toBe(false)
    expect(formData.has('api_key')).toBe(false)
  })
})
