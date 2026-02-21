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

const MAX_CONCURRENT = 2

type Listener = () => void

interface PendingRequest {
  url: string
  controller: AbortController
}

/** État global de la queue (singleton) */
const listeners = new Map<string, Set<Listener>>()
const loadingUrls = new Set<string>()
const errorUrls = new Set<string>()
const queue: string[] = []
let active = 0

function notify(url: string) {
  listeners.get(url)?.forEach(fn => fn())
}

function processQueue() {
  while (active < MAX_CONCURRENT && queue.length > 0) {
    const url = queue.shift()!
    // Déjà en cache ou en cours ? Passer
    if (previewHtmlCache.has(url)) {
      loadingUrls.delete(url)
      notify(url)
      continue
    }
    if (loadingUrls.has(url)) continue

    active++
    loadingUrls.add(url)
    notify(url)

    const controller = new AbortController()
    activeFetches.set(url, { url, controller })

    fetch(url, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.text()
      })
      .then(html => {
        previewHtmlCache.set(url, html)
        errorUrls.delete(url)
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          errorUrls.add(url)
        }
      })
      .finally(() => {
        active--
        loadingUrls.delete(url)
        activeFetches.delete(url)
        notify(url)
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
  processQueue()
}

/**
 * Hook pour s'abonner à l'état d'une preview HTML.
 * Déclenche le chargement quand visible (via isVisible).
 */
export function usePreviewHtml(url: string | null, isVisible: boolean) {
  const [, forceUpdate] = useState(0)

  useEffect(() => {
    if (!url) return
    const listener = () => forceUpdate(n => n + 1)
    if (!listeners.has(url)) listeners.set(url, new Set())
    listeners.get(url)!.add(listener)

    // Lancer le chargement si visible
    if (isVisible) {
      enqueue(url)
    }

    return () => {
      listeners.get(url)!.delete(listener)
      if (listeners.get(url)!.size === 0) {
        listeners.delete(url)
      }
    }
  }, [url, isVisible])

  // Enqueue quand le composant devient visible
  useEffect(() => {
    if (url && isVisible) {
      enqueue(url)
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
  enqueue(url)
}

/** Annuler toutes les requêtes en attente (utile quand la modale se ferme) */
export function cancelAllPreviews() {
  queue.length = 0
  activeFetches.forEach(req => req.controller.abort())
  activeFetches.clear()
  loadingUrls.clear()
}
