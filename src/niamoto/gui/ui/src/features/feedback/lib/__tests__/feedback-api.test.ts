import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()

describe('feedback-api', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.unstubAllEnvs()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  it('fails explicitly when the worker endpoint is missing', async () => {
    vi.stubEnv('VITE_FEEDBACK_WORKER_URL', '')
    vi.stubEnv('VITE_FEEDBACK_API_KEY', 'secret')

    const mod = await import('../feedback-api')

    await expect(
      mod.sendFeedback({
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
    ).rejects.toThrow('Feedback endpoint not configured')

    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('posts to the configured worker when configuration is present', async () => {
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
  })
})
