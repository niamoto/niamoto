// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { usePublishBootstrap } from './usePublishBootstrap'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const listExportJobs = vi.hoisted(() => vi.fn())
const apiGet = vi.hoisted(() => vi.fn())
const setProjectScope = vi.hoisted(() => vi.fn())
const hydrateBuildState = vi.hoisted(() => vi.fn())

vi.mock('@/features/publish/api/export', () => ({
  listExportJobs,
}))

vi.mock('@/shared/lib/api/client', () => ({
  apiClient: {
    get: apiGet,
  },
}))

vi.mock('@/features/publish/store/publishStore', () => ({
  usePublishStore: () => ({
    setProjectScope,
    hydrateBuildState,
  }),
}))

function mountHook() {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  function Probe() {
    usePublishBootstrap()
    return null
  }

  return {
    async render() {
      await act(async () => {
        root.render(<Probe />)
        await Promise.resolve()
        await Promise.resolve()
      })
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

describe('usePublishBootstrap', () => {
  beforeEach(() => {
    listExportJobs.mockReset()
    apiGet.mockReset()
    setProjectScope.mockReset()
    hydrateBuildState.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('hydrates the publish store from project config and export jobs', async () => {
    apiGet.mockResolvedValue({ data: { working_directory: '/tmp/project' } })
    listExportJobs.mockResolvedValue({
      jobs: [
        {
          job_id: 'job-running',
          status: 'running',
          progress: 45,
          message: 'Building pages',
          started_at: '2026-04-22T10:00:00Z',
          completed_at: null,
          result: null,
          error: null,
        },
        {
          job_id: 'job-completed',
          status: 'completed',
          progress: 100,
          message: 'Done',
          started_at: '2026-04-22T09:00:00Z',
          completed_at: '2026-04-22T09:05:00Z',
          result: {
            exports: {
              web_pages: {
                data: {
                  files_generated: 12,
                },
              },
            },
            metrics: {
              execution_time: 12.345,
            },
          },
          error: null,
        },
      ],
    })

    const hook = mountHook()
    await hook.render()

    expect(setProjectScope).toHaveBeenCalledWith('/tmp/project')
    expect(hydrateBuildState).toHaveBeenCalledWith({
      currentBuild: {
        id: 'job-running',
        status: 'running',
        progress: 45,
        message: 'Building pages',
        startedAt: '2026-04-22T10:00:00Z',
        completedAt: undefined,
        metrics: undefined,
        error: undefined,
      },
      buildHistory: [
        {
          id: 'job-completed',
          status: 'completed',
          progress: 100,
          message: 'Done',
          startedAt: '2026-04-22T09:00:00Z',
          completedAt: '2026-04-22T09:05:00Z',
          metrics: {
            totalFiles: 12,
            duration: 12.3,
            targets: [{ name: 'web_pages', files: 12 }],
          },
          error: undefined,
        },
      ],
    })

    await hook.unmount()
  })

  it('falls back to an empty hydrated state when bootstrap fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    apiGet.mockRejectedValue(new Error('config endpoint failed'))

    const hook = mountHook()
    await hook.render()

    expect(setProjectScope).not.toHaveBeenCalled()
    expect(hydrateBuildState).toHaveBeenCalledWith({
      currentBuild: null,
      buildHistory: [],
    })

    await hook.unmount()
    consoleError.mockRestore()
  })
})
