import { afterEach, describe, expect, it, vi } from 'vitest'

import { hasDesktopBridge, invokeDesktop } from './bridge'
import { reloadDesktopProject } from './projectReload'

vi.mock('./bridge', () => ({
  hasDesktopBridge: vi.fn(() => false),
  invokeDesktop: vi.fn(),
}))

const hasDesktopBridgeMock = vi.mocked(hasDesktopBridge)
const invokeDesktopMock = vi.mocked(invokeDesktop)

describe('reloadDesktopProject', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    hasDesktopBridgeMock.mockReturnValue(false)
    invokeDesktopMock.mockReset()
  })

  it('returns a valid loaded response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          state: 'loaded',
          project: '/tmp/demo',
          message: null,
        })
      )
    )

    await expect(
      reloadDesktopProject({
        allowStates: ['loaded'],
        expectedProject: '/tmp/demo',
      })
    ).resolves.toEqual({
      success: true,
      state: 'loaded',
      project: '/tmp/demo',
      message: null,
    })
  })

  it('uses the native desktop bridge when available', async () => {
    hasDesktopBridgeMock.mockReturnValue(true)
    invokeDesktopMock.mockResolvedValue({
      success: true,
      state: 'loaded',
      project: '/tmp/demo',
      message: null,
    })
    const fetchSpy = vi.spyOn(globalThis, 'fetch')

    await expect(
      reloadDesktopProject({
        allowStates: ['loaded'],
        expectedProject: '/tmp/demo',
      })
    ).resolves.toEqual({
      success: true,
      state: 'loaded',
      project: '/tmp/demo',
      message: null,
    })
    expect(invokeDesktopMock).toHaveBeenCalledWith('reload_desktop_project')
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('rejects an unexpected reload state', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          state: 'welcome',
          project: null,
          message: null,
        })
      )
    )

    await expect(
      reloadDesktopProject({
        allowStates: ['loaded'],
      })
    ).rejects.toThrow(
      'Unexpected project reload state returned by the server: welcome'
    )
  })

  it('rejects a mismatched expected project', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          state: 'loaded',
          project: '/tmp/other',
          message: null,
        })
      )
    )

    await expect(
      reloadDesktopProject({
        allowStates: ['loaded'],
        expectedProject: '/tmp/demo',
      })
    ).rejects.toThrow('Server failed to load the selected project')
  })

  it('rejects an invalid payload', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          state: 'loaded',
          project: '/tmp/demo',
        })
      )
    )

    await expect(reloadDesktopProject()).rejects.toThrow(
      'Received an invalid reload-project response'
    )
  })
})
