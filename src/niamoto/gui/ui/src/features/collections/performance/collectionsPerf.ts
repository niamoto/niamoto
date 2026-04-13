const CONTENT_SWITCH_MARK_PREFIX = 'collections:content-switch'

export interface CollectionsPerfEvent {
  name: string
  at: number
  detail?: Record<string, unknown>
}

interface CollectionsPerfStore {
  events: CollectionsPerfEvent[]
  marks: Record<string, number>
}

declare global {
  interface Window {
    __NIAMOTO_COLLECTIONS_PERF__?: CollectionsPerfStore
  }
}

function isCollectionsPerfEnabled() {
  return import.meta.env.DEV && typeof window !== 'undefined' && typeof performance !== 'undefined'
}

function getCollectionsPerfStore(): CollectionsPerfStore | null {
  if (!isCollectionsPerfEnabled()) {
    return null
  }

  if (!window.__NIAMOTO_COLLECTIONS_PERF__) {
    window.__NIAMOTO_COLLECTIONS_PERF__ = {
      events: [],
      marks: {},
    }
  }

  return window.__NIAMOTO_COLLECTIONS_PERF__
}

export function recordCollectionsPerf(
  name: string,
  detail?: Record<string, unknown>,
): void {
  const store = getCollectionsPerfStore()
  if (!store) {
    return
  }

  store.events.push({
    name,
    at: performance.now(),
    detail,
  })
}

export function markCollectionsContentSwitch(groupBy: string): void {
  const store = getCollectionsPerfStore()
  if (!store) {
    return
  }

  store.marks[`${CONTENT_SWITCH_MARK_PREFIX}:${groupBy}`] = performance.now()
}

export function measureCollectionsContentSwitch(
  groupBy: string,
  detail?: Record<string, unknown>,
): number | null {
  const store = getCollectionsPerfStore()
  if (!store) {
    return null
  }

  const key = `${CONTENT_SWITCH_MARK_PREFIX}:${groupBy}`
  const startedAt = store.marks[key]
  if (typeof startedAt !== 'number') {
    return null
  }

  const durationMs = performance.now() - startedAt
  delete store.marks[key]
  recordCollectionsPerf('collections.content.ready', {
    ...detail,
    durationMs,
    groupBy,
  })
  return durationMs
}

export function extractPreviewRenderMs(
  headers: Pick<Headers, 'get'> | null | undefined,
): number | null {
  const explicitValue = headers?.get('x-preview-render-ms')
  const explicitMs = explicitValue ? Number.parseFloat(explicitValue) : Number.NaN
  if (Number.isFinite(explicitMs)) {
    return explicitMs
  }

  const serverTiming = headers?.get('server-timing')
  if (!serverTiming) {
    return null
  }

  const match = serverTiming.match(/preview;dur=([0-9.]+)/)
  if (!match) {
    return null
  }

  const parsed = Number.parseFloat(match[1])
  return Number.isFinite(parsed) ? parsed : null
}
