// @vitest-environment jsdom

import { act, useLayoutEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAutoConfigureJob } from './useAutoConfigureJob'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const getAutoConfigureJob = vi.hoisted(() => vi.fn())
const startAutoConfigureJob = vi.hoisted(() => vi.fn())
const subscribeToAutoConfigureJobEvents = vi.hoisted(() => vi.fn())

vi.mock('@/features/import/api/smart-config', () => ({
  getAutoConfigureJob,
  startAutoConfigureJob,
  subscribeToAutoConfigureJobEvents,
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

describe('useAutoConfigureJob', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    getAutoConfigureJob.mockReset()
    startAutoConfigureJob.mockReset()
    subscribeToAutoConfigureJobEvents.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('completes successfully and keeps the latest streamed stage', async () => {
    const close = vi.fn()
    const result = {
      success: true,
      entities: { datasets: {}, references: {} },
      confidence: 0.91,
      warnings: [],
    }

    startAutoConfigureJob.mockResolvedValue({ job_id: 'job-1', status: 'running' })
    subscribeToAutoConfigureJobEvents.mockImplementation((jobId, onEvent) => {
      onEvent({ kind: 'stage', message: 'Analyzing files', timestamp: Date.now() })
      return { close }
    })
    getAutoConfigureJob
      .mockResolvedValueOnce({ status: 'running' })
      .mockResolvedValueOnce({ status: 'completed', result })

    const harness = createHookHarness(() =>
      useAutoConfigureJob({ timeoutMs: 100, pollIntervalMs: 1 })
    )
    await harness.render()

    let resolved: typeof result | undefined
    await act(async () => {
      const startPromise = harness.current.start(['imports/plots.csv'])
      await vi.runAllTimersAsync()
      resolved = await startPromise
    })

    expect(startAutoConfigureJob).toHaveBeenCalledWith({ files: ['imports/plots.csv'] })
    expect(subscribeToAutoConfigureJobEvents).toHaveBeenCalledWith(
      'job-1',
      expect.any(Function)
    )
    expect(resolved).toEqual(result)
    expect(harness.current.status).toBe('completed')
    expect(harness.current.result).toEqual(result)
    expect(harness.current.error).toBeNull()
    expect(harness.current.stage).toBe('Analyzing files')
    expect(harness.current.events).toEqual([
      expect.objectContaining({ message: 'Analyzing files' }),
    ])
    expect(close).toHaveBeenCalled()

    await harness.unmount()
  })

  it('surfaces failures and preserves the failed state', async () => {
    const close = vi.fn()

    startAutoConfigureJob.mockResolvedValue({ job_id: 'job-2', status: 'running' })
    subscribeToAutoConfigureJobEvents.mockReturnValue({ close })
    getAutoConfigureJob.mockResolvedValue({ status: 'failed', error: null })

    const harness = createHookHarness(() =>
      useAutoConfigureJob({ timeoutMs: 100, pollIntervalMs: 1 })
    )
    await harness.render()

    let caughtError: unknown
    await act(async () => {
      const startPromise = harness.current
        .start(['imports/broken.csv'], {
          failed: 'Job failed',
        })
        .catch((error) => {
          caughtError = error
        })
      await vi.runAllTimersAsync()
      await startPromise
    })

    expect(caughtError).toBeInstanceOf(Error)
    expect((caughtError as Error).message).toBe('Job failed')
    expect(harness.current.status).toBe('failed')
    expect(harness.current.error).toBe('Job failed')
    expect(harness.current.result).toBeNull()
    expect(close).toHaveBeenCalled()

    await harness.unmount()
  })
})
