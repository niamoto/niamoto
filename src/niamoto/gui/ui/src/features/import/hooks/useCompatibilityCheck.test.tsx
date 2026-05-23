// @vitest-environment jsdom

import { act, useLayoutEffect } from 'react'
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

describe('useCompatibilityCheck', () => {
  beforeEach(() => {
    impactCheck.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('returns matched impacts and exposes per-file failures', async () => {
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
          widget_impacts: [],
          widget_impact_summary: {},
          widget_repair_context: {},
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
      unmatched: [],
      failed: [{ file: 'unknown.csv', error: 'backend unavailable' }],
    })
    expect(harness.current.isChecking).toBe(false)
    expect(harness.current.matched).toHaveLength(1)
    expect(harness.current.unmatched).toEqual([])
    expect(harness.current.failed).toEqual([
      { file: 'unknown.csv', error: 'backend unavailable' },
    ])
    expect(harness.current.error).toBe('1 compatibility check failed')

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
      widget_impacts: [],
      widget_impact_summary: {},
      widget_repair_context: {},
    })

    const harness = createHookHarness(() => useCompatibilityCheck())
    await harness.render()

    let result: Awaited<ReturnType<typeof harness.current.check>> | undefined
    await act(async () => {
      result = await harness.current.check([
        { name: 'plots.csv', path: 'imports/plots.csv' },
      ])
    })

    expect(result).toEqual({ matched: [], unmatched: [], failed: [] })
    expect(harness.current.matched).toEqual([])
    expect(harness.current.unmatched).toEqual([])

    await harness.unmount()
  })

  it('keeps matched results when widget compatibility has impacts', async () => {
    impactCheck.mockResolvedValue({
      entity_name: 'plots',
      matched_columns: [],
      impacts: [],
      has_blockers: false,
      has_warnings: false,
      has_opportunities: false,
      widget_impacts: [
        {
          widget_id: 'plots_by_habitat',
          collection: 'plots',
          status: 'degraded',
          detail: 'Incoming cardinality is high enough to require ranking.',
          affected_columns: ['habitat'],
          transformer_plugin: 'categorical_distribution',
          widget_plugin: 'bar_plot',
        },
      ],
      widget_impact_summary: { degraded: 1 },
      widget_repair_context: { entity: 'plots' },
    })

    const harness = createHookHarness(() => useCompatibilityCheck())
    await harness.render()

    let result: Awaited<ReturnType<typeof harness.current.check>> | undefined
    await act(async () => {
      result = await harness.current.check([{ name: 'plots.csv', path: 'imports/plots.csv' }])
    })

    expect(result?.matched).toHaveLength(1)
    expect(harness.current.matched[0]?.widget_impacts).toHaveLength(1)

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
      widget_impacts: [],
      widget_impact_summary: {},
      widget_repair_context: {},
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
      failed: [],
      error: null,
    })

    await harness.unmount()
  })
})
