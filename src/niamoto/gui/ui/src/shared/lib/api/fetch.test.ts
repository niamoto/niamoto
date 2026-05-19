import { beforeEach, describe, expect, it, vi } from 'vitest'

const getDesktopApiAuthToken = vi.hoisted(() => vi.fn())

vi.mock('@/shared/desktop/apiAuth', () => ({
  DESKTOP_API_AUTH_HEADER: 'x-niamoto-desktop-token',
  getDesktopApiAuthToken,
}))

describe('apiFetch', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    getDesktopApiAuthToken.mockReset()
  })

  it('uses plain fetch when no desktop token is available', async () => {
    getDesktopApiAuthToken.mockResolvedValue(null)
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response('{}'))
    const { apiFetch } = await import('./fetch')

    await apiFetch('/api/health/reload-project', { method: 'POST' })

    expect(fetchSpy).toHaveBeenCalledWith('/api/health/reload-project', {
      method: 'POST',
    })
  })

  it('adds the desktop token header while preserving existing headers', async () => {
    getDesktopApiAuthToken.mockResolvedValue('desktop-token')
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response('{}'))
    const { apiFetch } = await import('./fetch')

    await apiFetch('/api/deploy/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })

    const [, init] = fetchSpy.mock.calls[0]
    const headers = new Headers(init?.headers)
    expect(headers.get('Content-Type')).toBe('application/json')
    expect(headers.get('x-niamoto-desktop-token')).toBe('desktop-token')
  })
})
