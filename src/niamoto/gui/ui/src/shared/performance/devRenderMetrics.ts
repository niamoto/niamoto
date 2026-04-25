import { useEffect } from 'react'

const DEFAULT_LIST_ITEM_THRESHOLD = 50
const STORAGE_KEY = 'niamoto:dev-render-metrics'

export interface DevRenderMetric {
  name: string
  at: number
  itemCount: number
  durationMs: number
  detail?: Record<string, string | number | boolean | null | undefined>
}

interface DevRenderMetricsStore {
  events: DevRenderMetric[]
}

declare global {
  interface Window {
    __NIAMOTO_RENDER_METRICS__?: DevRenderMetricsStore
  }
}

export function isDevRenderMetricsEnabled(): boolean {
  return (import.meta.env.DEV || import.meta.env.MODE === 'test')
    && typeof window !== 'undefined'
    && typeof performance !== 'undefined'
}

export function shouldRecordListRenderMetric(
  itemCount: number,
  itemThreshold = DEFAULT_LIST_ITEM_THRESHOLD,
): boolean {
  return itemCount >= itemThreshold
}

export function createDevRenderMetric({
  name,
  itemCount,
  startedAt,
  endedAt,
  detail,
}: {
  name: string
  itemCount: number
  startedAt: number
  endedAt: number
  detail?: DevRenderMetric['detail']
}): DevRenderMetric {
  return {
    name,
    at: endedAt,
    itemCount,
    durationMs: Math.max(0, endedAt - startedAt),
    detail,
  }
}

export function getDevRenderMetricsStore(): DevRenderMetricsStore | null {
  if (!isDevRenderMetricsEnabled()) {
    return null
  }

  if (!window.__NIAMOTO_RENDER_METRICS__) {
    window.__NIAMOTO_RENDER_METRICS__ = {
      events: readStoredDevRenderMetrics(),
    }
  }

  return window.__NIAMOTO_RENDER_METRICS__
}

export function readStoredDevRenderMetrics(): DevRenderMetric[] {
  if (!isDevRenderMetricsEnabled()) {
    return []
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter(isDevRenderMetric) : []
  } catch {
    return []
  }
}

export function clearStoredDevRenderMetrics(): void {
  const store = getDevRenderMetricsStore()
  if (!store) {
    return
  }

  store.events = []
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Dev-only metrics must never affect the application runtime.
  }
}

export function recordDevRenderMetric(metric: DevRenderMetric): void {
  const store = getDevRenderMetricsStore()
  if (!store) {
    return
  }

  store.events.push(metric)
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store.events.slice(-200)))
  } catch {
    // Keep the in-memory store even if persistent storage is unavailable.
  }
}

export function useDevListRenderMetric(
  name: string,
  itemCount: number,
  options: {
    itemThreshold?: number
    detail?: DevRenderMetric['detail']
  } = {},
): void {
  const itemThreshold = options.itemThreshold ?? DEFAULT_LIST_ITEM_THRESHOLD
  const shouldRecord = isDevRenderMetricsEnabled()
    && shouldRecordListRenderMetric(itemCount, itemThreshold)
  const startedAt = shouldRecord ? performance.now() : null

  useEffect(() => {
    if (startedAt === null) {
      return
    }

    recordDevRenderMetric(createDevRenderMetric({
      name,
      itemCount,
      startedAt,
      endedAt: performance.now(),
      detail: options.detail,
    }))
  })
}

function isDevRenderMetric(value: unknown): value is DevRenderMetric {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const candidate = value as Partial<DevRenderMetric>
  return typeof candidate.name === 'string'
    && typeof candidate.at === 'number'
    && typeof candidate.itemCount === 'number'
    && typeof candidate.durationMs === 'number'
}
