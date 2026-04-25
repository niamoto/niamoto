// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  clearStoredDevRenderMetrics,
  createDevRenderMetric,
  recordDevRenderMetric,
  readStoredDevRenderMetrics,
  shouldRecordListRenderMetric,
} from './devRenderMetrics'

describe('devRenderMetrics', () => {
  it('records list metrics only after the configured item threshold', () => {
    expect(shouldRecordListRenderMetric(49)).toBe(false)
    expect(shouldRecordListRenderMetric(50)).toBe(true)
    expect(shouldRecordListRenderMetric(10, 10)).toBe(true)
    expect(shouldRecordListRenderMetric(9, 10)).toBe(false)
  })

  it('creates a non-negative duration metric', () => {
    expect(createDevRenderMetric({
      name: 'tools.dataExplorer.rows',
      itemCount: 100,
      startedAt: 12,
      endedAt: 32.5,
      detail: { table: 'taxon_ref' },
    })).toEqual({
      name: 'tools.dataExplorer.rows',
      at: 32.5,
      itemCount: 100,
      durationMs: 20.5,
      detail: { table: 'taxon_ref' },
    })

    expect(createDevRenderMetric({
      name: 'collections.tree.references',
      itemCount: 3,
      startedAt: 30,
      endedAt: 20,
    }).durationMs).toBe(0)
  })

  it('persists metrics in localStorage for manual test sessions', () => {
    clearStoredDevRenderMetrics()

    recordDevRenderMetric(createDevRenderMetric({
      name: 'collections.tree.references',
      itemCount: 30,
      startedAt: 10,
      endedAt: 18,
    }))

    expect(readStoredDevRenderMetrics()).toMatchObject([
      {
        name: 'collections.tree.references',
        itemCount: 30,
        durationMs: 8,
      },
    ])

    clearStoredDevRenderMetrics()
    expect(readStoredDevRenderMetrics()).toEqual([])
  })
})
