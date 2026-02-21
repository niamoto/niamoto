/**
 * Queue de chargement des previews avec concurrence limitée.
 *
 * Architecture :
 * - Un singleton module-level gère la queue et la concurrence (max 2)
 * - Le hook `usePreviewHtml` permet à chaque composant de s'abonner à l'état d'une URL
 * - Le cache LRU global (`previewHtmlCache`) déduplique miniature ↔ preview large
 */
import { useState, useEffect } from 'react'
import { previewHtmlCache } from '@/lib/lru-cache'

// Keep network/HTML parse pressure very low in the modal.
const MAX_CONCURRENT = 2
const MAX_DURATION_SAMPLES = 200

type Listener = () => void
type StatsListener = () => void

interface PendingRequest {
  url: string
  controller: AbortController
}

export interface PreviewQueueStats {
  active: number
  queued: number
  loading: number
  listeners: number
  cacheSize: number
  completed: number
  failed: number
  aborted: number
  avgMs: number
  p95Ms: number
  maxMs: number
}

/** État global de la queue (singleton) */
const listeners = new Map<string, Set<Listener>>()
const loadingUrls = new Set<string>()
const errorUrls = new Set<string>()
const queue: string[] = []
let active = 0
let completedCount = 0
let failedCount = 0
let abortedCount = 0
const durationsMs: number[] = []
const fetchStartedAt = new Map<string, number>()
const statsListeners = new Set<StatsListener>()
let latestStats: PreviewQueueStats

function nowMs(): number {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now()
  }
  return Date.now()
}

function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const idx = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1)
  return sorted[Math.max(0, idx)]
}

function computeStats(): PreviewQueueStats {
  const avgMs =
    durationsMs.length > 0
      ? durationsMs.reduce((sum, value) => sum + value, 0) / durationsMs.length
      : 0
  const totalListeners = Array.from(listeners.values()).reduce(
    (sum, group) => sum + group.size,
    0
  )
  return {
    active,
    queued: queue.length,
    loading: loadingUrls.size,
    listeners: totalListeners,
    cacheSize: previewHtmlCache.size,
    completed: completedCount,
    failed: failedCount,
    aborted: abortedCount,
    avgMs,
    p95Ms: percentile(durationsMs, 95),
    maxMs: durationsMs.length > 0 ? Math.max(...durationsMs) : 0,
  }
}

function notifyStats() {
  latestStats = computeStats()
  statsListeners.forEach(fn => fn())
}

function notify(url: string) {
  listeners.get(url)?.forEach(fn => fn())
}

latestStats = computeStats()

function processQueue() {
  while (active < MAX_CONCURRENT && queue.length > 0) {
    const url = queue.shift()!
    notifyStats()
    // No active subscribers (e.g. card scrolled out): skip this preview.
    if (!listeners.has(url)) {
      continue
    }
    // Déjà en cache ou en cours ? Passer
    if (previewHtmlCache.has(url)) {
      loadingUrls.delete(url)
      notify(url)
      notifyStats()
      continue
    }
    if (loadingUrls.has(url)) {
      notifyStats()
      continue
    }

    active++
    loadingUrls.add(url)
    notify(url)
    fetchStartedAt.set(url, nowMs())
    notifyStats()

    const controller = new AbortController()
    activeFetches.set(url, { url, controller })
    let wasSuccessful = false

    fetch(url, { signal: controller.signal, cache: 'no-store' })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.text()
      })
      .then(html => {
        wasSuccessful = true
        completedCount++
        previewHtmlCache.set(url, html)
        errorUrls.delete(url)
      })
      .catch(err => {
        if (err.name === 'AbortError') {
          abortedCount++
        } else {
          failedCount++
          errorUrls.add(url)
        }
      })
      .finally(() => {
        const startedAt = fetchStartedAt.get(url)
        fetchStartedAt.delete(url)
        if (wasSuccessful && startedAt !== undefined) {
          durationsMs.push(nowMs() - startedAt)
          if (durationsMs.length > MAX_DURATION_SAMPLES) {
            durationsMs.shift()
          }
        }
        active--
        loadingUrls.delete(url)
        activeFetches.delete(url)
        notify(url)
        notifyStats()
        processQueue()
      })
  }
}

const activeFetches = new Map<string, PendingRequest>()

/** Demander le chargement d'une preview */
function enqueue(url: string) {
  if (previewHtmlCache.has(url) || loadingUrls.has(url) || queue.includes(url)) {
    return
  }
  queue.push(url)
  notifyStats()
  processQueue()
}

/**
 * Hook pour s'abonner à l'état d'une preview HTML.
 * Déclenche le chargement quand visible (via isVisible).
 */
export function usePreviewHtml(url: string | null, isVisible: boolean) {
  const [, forceUpdate] = useState(0)

  useEffect(() => {
    if (!url || !isVisible) return
    const listener = () => forceUpdate(n => n + 1)
    if (!listeners.has(url)) listeners.set(url, new Set())
    listeners.get(url)!.add(listener)

    // Lancer le chargement si visible
    enqueue(url)

    return () => {
      listeners.get(url)!.delete(listener)
      if (listeners.get(url)!.size === 0) {
        listeners.delete(url)
        // If nobody needs this preview anymore, drop queued work and abort
        // in-flight fetch to keep the UI responsive while scrolling.
        const queuedIdx = queue.indexOf(url)
        if (queuedIdx !== -1) {
          queue.splice(queuedIdx, 1)
        }
        const activeReq = activeFetches.get(url)
        if (activeReq) {
          activeReq.controller.abort()
        }
        notifyStats()
      }
    }
  }, [url, isVisible])

  if (!url) return { html: null, loading: false, error: false }

  const cached = previewHtmlCache.get(url)
  if (cached) return { html: cached, loading: false, error: false }

  return {
    html: null,
    loading: loadingUrls.has(url),
    error: errorUrls.has(url),
  }
}

/** Forcer le rechargement d'une preview (invalider le cache puis re-fetcher) */
export function refreshPreview(url: string) {
  errorUrls.delete(url)
  previewHtmlCache.delete(url)
  notifyStats()
  enqueue(url)
}

/** Annuler toutes les requêtes en attente (utile quand la modale se ferme) */
export function cancelAllPreviews() {
  queue.length = 0
  activeFetches.forEach(req => req.controller.abort())
  activeFetches.clear()
  loadingUrls.clear()
  notifyStats()
}

export function usePreviewQueueStats(): PreviewQueueStats {
  const [, forceUpdate] = useState(0)

  useEffect(() => {
    const listener = () => forceUpdate(n => n + 1)
    statsListeners.add(listener)
    return () => {
      statsListeners.delete(listener)
    }
  }, [])

  return latestStats
}
