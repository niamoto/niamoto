// @vitest-environment jsdom

import { act, useLayoutEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useCurrentProjectScope } from './useCurrentProjectScope'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const useRuntimeMode = vi.hoisted(() => vi.fn())
const useProjectInfo = vi.hoisted(() => vi.fn())

vi.mock('./useRuntimeMode', () => ({
  useRuntimeMode,
}))

vi.mock('@/hooks/useProjectInfo', () => ({
  useProjectInfo,
}))

function createHookHarness<T>(useHook: () => T) {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  const currentRef: { current: T | undefined } = { current: undefined }

  function Probe() {
    const value = useHook()

    useLayoutEffect(() => {
      currentRef.current = value
    }, [value])

    return null
  }

  return {
    async render() {
      await act(async () => {
        root.render(<Probe />)
        await Promise.resolve()
      })
    },
    get current() {
      return currentRef.current!
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

describe('useCurrentProjectScope', () => {
  beforeEach(() => {
    useRuntimeMode.mockReset()
    useProjectInfo.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('prefers the desktop project path when available', async () => {
    useRuntimeMode.mockReturnValue({
      project: '/tmp/niamoto-desktop',
    })
    useProjectInfo.mockReturnValue({
      data: {
        name: 'Fallback project',
        created_at: '2026-04-23T10:00:00',
      },
    })

    const harness = createHookHarness(() => useCurrentProjectScope())
    await harness.render()

    expect(harness.current.projectScope).toBe(
      'desktop:/tmp/niamoto-desktop',
    )

    await harness.unmount()
  })

  it('falls back to stable project info when no desktop path is available', async () => {
    useRuntimeMode.mockReturnValue({
      project: null,
    })
    useProjectInfo.mockReturnValue({
      data: {
        name: 'Niamoto subset',
        created_at: '2026-04-23T10:00:00',
      },
    })

    const harness = createHookHarness(() => useCurrentProjectScope())
    await harness.render()

    expect(harness.current.projectScope).toBe(
      'project:Niamoto subset:2026-04-23T10:00:00',
    )

    await harness.unmount()
  })

  it('returns null when no project identity is available', async () => {
    useRuntimeMode.mockReturnValue({
      project: null,
    })
    useProjectInfo.mockReturnValue({
      data: null,
    })

    const harness = createHookHarness(() => useCurrentProjectScope())
    await harness.render()

    expect(harness.current.projectScope).toBeNull()

    await harness.unmount()
  })
})
