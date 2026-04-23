// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useRuntimeMode } from './useRuntimeMode'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const getBootstrappedRuntimeMode = vi.hoisted(() => vi.fn())
const isRuntimeModeState = vi.hoisted(() => vi.fn())

vi.mock('@/shared/desktop/runtime', () => ({
  getBootstrappedRuntimeMode,
  isRuntimeModeState,
}))

function createHookHarness<T>(useHook: () => T) {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  let currentValue: T

  function Probe() {
    currentValue = useHook()
    return null
  }

  return {
    async render() {
      await act(async () => {
        root.render(<Probe />)
        await Promise.resolve()
      })
    },
    async flush() {
      await act(async () => {
        await Promise.resolve()
        await Promise.resolve()
      })
    },
    get current() {
      return currentValue!
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

describe('useRuntimeMode', () => {
  beforeEach(() => {
    getBootstrappedRuntimeMode.mockReset()
    isRuntimeModeState.mockReset()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('hydrates runtime flags from the backend contract', async () => {
    getBootstrappedRuntimeMode.mockReturnValue({
      mode: 'web',
      shell: null,
      project: null,
      features: { project_switching: false },
    })
    isRuntimeModeState.mockImplementation(
      (value: unknown) =>
        typeof value === 'object' &&
        value !== null &&
        (value as { mode?: string }).mode === 'desktop'
    )
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        mode: 'desktop',
        shell: 'tauri',
        project: '/tmp/project',
        features: { project_switching: true },
      }),
    } as Response)

    const harness = createHookHarness(() => useRuntimeMode())
    await harness.render()
    await harness.flush()

    expect(harness.current.loading).toBe(false)
    expect(harness.current.error).toBeNull()
    expect(harness.current.mode).toBe('desktop')
    expect(harness.current.shell).toBe('tauri')
    expect(harness.current.project).toBe('/tmp/project')
    expect(harness.current.isDesktop).toBe(true)
    expect(harness.current.isWeb).toBe(false)
    expect(harness.current.isTauri).toBe(true)
    expect(harness.current.isElectron).toBe(false)

    await harness.unmount()
  })

  it('keeps the bootstrapped state and surfaces an error on invalid payloads', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    getBootstrappedRuntimeMode.mockReturnValue({
      mode: 'web',
      shell: null,
      project: null,
      features: { project_switching: false },
    })
    isRuntimeModeState.mockReturnValue(false)
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ mode: 'desktop', shell: 'invalid-shell' }),
    } as Response)

    const harness = createHookHarness(() => useRuntimeMode())
    await harness.render()
    await harness.flush()

    expect(harness.current.mode).toBe('web')
    expect(harness.current.loading).toBe(false)
    expect(harness.current.error).toBe('Received an invalid runtime mode payload')
    expect(consoleError).toHaveBeenCalled()

    await harness.unmount()
    consoleError.mockRestore()
  })
})
