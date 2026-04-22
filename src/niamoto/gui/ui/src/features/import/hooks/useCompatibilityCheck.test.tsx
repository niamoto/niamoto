// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useCompatibilityCheck } from './useCompatibilityCheck'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const impactCheck = vi.hoisted(() => vi.fn())

vi.mock('../api/compatibility', () => ({
  impactCheck,
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

describe('useCompatibilityCheck', () => {
  beforeEach(() => {
    impactCheck.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('returns matched impacts and unmatched files without blocking on per-file failures', async () => {
    impactCheck.mockImplementation(async (filePath: string) => {
      if (filePath.includes('plots.csv')) {
        return {
          entity_name: 'plots',
          matched_columns: [],
          impacts: [
            {
              column: 'plot_id',
              level: 'warning',
              detail: 'Column renamed',
              referenced_in: ['transform.yml'],
            },
          ],
          has_blockers: false,
          has_warnings: true,
          has_opportunities: false,
        }
      }

      throw new Error('backend unavailable')
    })

    const harness = createHookHarness(() => useCompatibilityCheck())
    await harness.render()

    let result: Awaited<ReturnType<typeof harness.current.check>> | undefined
    await act(async () => {
      result = await harness.current.check([
        { name: 'plots.csv', path: 'imports/plots.csv' },
        { name: 'unknown.csv', path: 'imports/unknown.csv' },
      ])
    })

    expect(result).toEqual({
      matched: [
        expect.objectContaining({
          entity_name: 'plots',
        }),
      ],
      unmatched: ['unknown.csv'],
    })
    expect(harness.current.isChecking).toBe(false)
    expect(harness.current.matched).toHaveLength(1)
    expect(harness.current.unmatched).toEqual(['unknown.csv'])
    expect(harness.current.error).toBeNull()

    await harness.unmount()
  })

  it('drops matched results when the check found no actionable impact', async () => {
    impactCheck.mockResolvedValue({
      entity_name: 'plots',
      matched_columns: [],
      impacts: [],
      has_blockers: false,
      has_warnings: false,
      has_opportunities: false,
    })

    const harness = createHookHarness(() => useCompatibilityCheck())
    await harness.render()

    let result: Awaited<ReturnType<typeof harness.current.check>> | undefined
    await act(async () => {
      result = await harness.current.check([
        { name: 'plots.csv', path: 'imports/plots.csv' },
      ])
    })

    expect(result).toEqual({ matched: [], unmatched: [] })
    expect(harness.current.matched).toEqual([])
    expect(harness.current.unmatched).toEqual([])

    await harness.unmount()
  })

  it('resets back to the idle state', async () => {
    impactCheck.mockResolvedValue({
      entity_name: 'plots',
      matched_columns: [],
      impacts: [],
      has_blockers: false,
      has_warnings: false,
      has_opportunities: false,
    })

    const harness = createHookHarness(() => useCompatibilityCheck())
    await harness.render()

    await act(async () => {
      await harness.current.check([{ name: 'plots.csv', path: 'imports/plots.csv' }])
    })
    act(() => {
      harness.current.reset()
    })

    expect(harness.current).toMatchObject({
      isChecking: false,
      matched: [],
      unmatched: [],
      error: null,
    })

    await harness.unmount()
  })
})
