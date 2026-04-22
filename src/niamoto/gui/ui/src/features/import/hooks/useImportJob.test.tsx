// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useImportJob } from './useImportJob'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const createEntitiesBulk = vi.hoisted(() => vi.fn())
const executeImportAll = vi.hoisted(() => vi.fn())
const getImportStatus = vi.hoisted(() => vi.fn())

vi.mock('@/features/import/api/smart-config', () => ({
  createEntitiesBulk,
}))

vi.mock('@/features/import/api/import', () => ({
  executeImportAll,
  getImportStatus,
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

const autoConfigureResponse = {
  success: true,
  entities: {
    datasets: {
      occurrences: { connector: { type: 'csv' } },
    },
    references: {},
  },
  auxiliary_sources: [],
  confidence: 0.95,
  warnings: [],
}

describe('useImportJob', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    createEntitiesBulk.mockReset()
    executeImportAll.mockReset()
    getImportStatus.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('runs the import workflow to completion and updates the state', async () => {
    createEntitiesBulk.mockResolvedValue(undefined)
    executeImportAll.mockResolvedValue({ job_id: 'job-1' })
    getImportStatus
      .mockResolvedValueOnce({
        status: 'running',
        total_entities: 2,
        processed_entities: 1,
        current_entity: 'occurrences',
        current_entity_type: 'dataset',
        phase: 'importing',
        message: 'Importing occurrences',
        progress: 50,
        events: [],
      })
      .mockResolvedValueOnce({
        status: 'completed',
        total_entities: 2,
        processed_entities: 2,
        current_entity: null,
        current_entity_type: null,
        phase: 'completed',
        message: 'Import complete',
        progress: 100,
        events: [],
      })

    const harness = createHookHarness(() =>
      useImportJob({ timeoutMs: 100, pollIntervalMs: 1 })
    )
    await harness.render()

    await act(async () => {
      const startPromise = harness.current.start(autoConfigureResponse)
      await vi.runAllTimersAsync()
      await startPromise
    })

    expect(createEntitiesBulk).toHaveBeenCalledWith({
      entities: autoConfigureResponse.entities,
      auxiliary_sources: [],
    })
    expect(executeImportAll).toHaveBeenCalledWith(false)
    expect(harness.current.state.status).toBe('completed')
    expect(harness.current.state.totalEntities).toBe(2)
    expect(harness.current.state.processedEntities).toBe(2)
    expect(harness.current.state.phase).toBe('completed')
    expect(harness.current.state.error).toBeNull()

    await harness.unmount()
  })

  it('captures failure details from the backend status payload', async () => {
    createEntitiesBulk.mockResolvedValue(undefined)
    executeImportAll.mockResolvedValue({ job_id: 'job-2' })
    getImportStatus.mockResolvedValue({
      status: 'failed',
      errors: ['Import failed badly'],
      error_details: {
        message: 'Constraint violation',
        error_type: 'ValidationError',
      },
      events: [],
    })

    const harness = createHookHarness(() =>
      useImportJob({ timeoutMs: 100, pollIntervalMs: 1 })
    )
    await harness.render()

    let caughtError: unknown
    await act(async () => {
      const startPromise = harness.current
        .start(autoConfigureResponse, {
          importFailed: 'Custom failure',
        })
        .catch((error) => {
          caughtError = error
        })
      await vi.runAllTimersAsync()
      await startPromise
    })

    expect(caughtError).toBeInstanceOf(Error)
    expect((caughtError as Error).message).toBe('Import failed badly')
    expect(harness.current.state.status).toBe('failed')
    expect(harness.current.state.error).toBe('Import failed badly')
    expect(harness.current.state.errorDetails).toEqual({
      message: 'Constraint violation',
      error_type: 'ValidationError',
    })

    await harness.unmount()
  })
})
