import { afterEach, describe, expect, it, vi } from 'vitest'

import { reloadDesktopProject } from './projectReload'

describe('reloadDesktopProject', () => {
  afterEach(() => {
    vi.restoreAllMocks()
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
