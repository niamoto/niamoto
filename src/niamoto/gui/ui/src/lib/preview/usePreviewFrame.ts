/**
 * Hook unifié pour le chargement de previews widgets via TanStack Query.
 *
 * Remplace usePreviewQueue (queue manuelle + LRU cache) par TanStack Query
 * (cache, déduplication, invalidation, retry, garbage collection).
 *
 * SYNC : le contrat backend est dans
 * src/niamoto/gui/api/services/preview_engine/models.py
 */

import { useRef, useEffect } from 'react'
import { useQuery, type QueryClient } from '@tanstack/react-query'
import type { PreviewDescriptor, PreviewState } from './types'
import {
  extractPreviewRenderMs,
  recordCollectionsPerf,
} from '@/features/collections/performance/collectionsPerf'

// --- Constantes ---

/** En dev, pas de cache pour voir les changements immédiatement */
const IS_DEV = import.meta.env.DEV

/** Données écologiques : stables entre imports explicites */
const STALE_TIME = IS_DEV ? 0 : Infinity

/** Garder en cache 5min après démontage du dernier observateur (0 en dev) */
const GC_TIME = IS_DEV ? 0 : 5 * 60_000

/**
 * Limite les iframes Plotly en cours de rendu simultané.
 * TanStack Query gère la déduplication réseau, mais ne borne PAS
 * le parsing/rendu JS de Plotly dans les iframes (~200ms thread principal).
 */
const MAX_CONCURRENT_RENDERS = 3

// --- Sémaphore de rendu Plotly ---

interface RenderQueueEntry {
  resolve: () => void
  reject: (error: Error) => void
  signal?: AbortSignal
  abortListener?: () => void
}

const renderQueue: RenderQueueEntry[] = []
let activeRenders = 0

function createAbortError(): Error {
  const error = new Error('Preview render cancelled')
  error.name = 'AbortError'
  return error
}

function removeQueuedRender(entry: RenderQueueEntry): void {
  const index = renderQueue.indexOf(entry)
  if (index >= 0) {
    renderQueue.splice(index, 1)
  }
}

function cleanupQueuedRender(entry: RenderQueueEntry): void {
  if (entry.signal && entry.abortListener) {
    entry.signal.removeEventListener('abort', entry.abortListener)
  }
}

function acquireRenderSlot(signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) {
    return Promise.reject(createAbortError())
  }

  if (activeRenders < MAX_CONCURRENT_RENDERS) {
    activeRenders++
    return Promise.resolve()
  }

  return new Promise((resolve, reject) => {
    const entry: RenderQueueEntry = {
      resolve: () => {
        cleanupQueuedRender(entry)
        resolve()
      },
      reject,
      signal,
    }

    entry.abortListener = () => {
      removeQueuedRender(entry)
      cleanupQueuedRender(entry)
      reject(createAbortError())
    }

    signal?.addEventListener('abort', entry.abortListener, { once: true })
    renderQueue.push(entry)
  })
}

function releaseRenderSlot(): void {
  if (activeRenders <= 0) return
  activeRenders--

  while (renderQueue.length > 0) {
    const next = renderQueue.shift()
    if (!next) return

    if (next.signal?.aborted) {
      cleanupQueuedRender(next)
      next.reject(createAbortError())
      continue
    }

    activeRenders++
    next.resolve()
    return
  }
}

// --- Helpers ---

function stableHash(obj: unknown): string {
  return JSON.stringify(obj, (_key, value) =>
    value && typeof value === 'object' && !Array.isArray(value)
      ? Object.keys(value as Record<string, unknown>).sort().reduce((sorted, k) => {
          sorted[k] = (value as Record<string, unknown>)[k]
          return sorted
        }, {} as Record<string, unknown>)
      : value
  )
}

/** Dependances primitives d'un PreviewDescriptor pour useMemo. */
export function descriptorDeps(d: PreviewDescriptor): unknown[] {
  return [
    d.templateId, d.groupBy, d.source, d.entityId,
    d.inline ? stableHash(d.inline) : null,
  ]
}

export function buildQueryKey(d: PreviewDescriptor): readonly unknown[] {
  const base = [
    'preview', d.mode,
    d.groupBy ?? '__default',
    d.source ?? '__default',
    d.entityId ?? '__default',
  ]
  if (d.inline) {
    return [...base, 'inline', stableHash(d.inline as unknown as Record<string, unknown>)] as const
  }
  return [...base, d.templateId ?? '__default'] as const
}

function buildPreviewUrl(d: PreviewDescriptor): string {
  const params = new URLSearchParams()
  if (d.groupBy) params.set('group_by', d.groupBy)
  if (d.source) params.set('source', d.source)
  if (d.entityId) params.set('entity_id', d.entityId)
  if (d.mode) params.set('mode', d.mode)
  const qs = params.toString()
  return `/api/preview/${d.templateId}${qs ? `?${qs}` : ''}`
}

// --- Hook principal ---

/**
 * Hook pour charger et afficher une preview widget.
 *
 * @param descriptor - Identifiant du widget (template_id ou inline config)
 * @param visible - true quand le conteneur est dans le viewport
 * @returns PreviewState avec html, loading, error
 */
export function usePreviewFrame(
  descriptor: PreviewDescriptor | null,
  visible: boolean,
): PreviewState {
  const abortRef = useRef<AbortController | null>(null)

  // Annuler les requêtes en vol quand la visibilité change
  useEffect(() => {
    if (!visible) {
      abortRef.current?.abort()
    }
  }, [visible])

  const query = useQuery({
    queryKey: descriptor ? buildQueryKey(descriptor) : ['preview', 'none'],
    queryFn: async ({ signal }) => {
      if (!descriptor) throw new Error('Descriptor requis')

      // Signal combiné : TanStack (unmount) + visibilité
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      const combinedSignal = AbortSignal.any([signal, controller.signal])

      // Sémaphore : limite les rendus Plotly concurrents
      let slotAcquired = false
      await acquireRenderSlot(combinedSignal)
      slotAcquired = true
      if (combinedSignal.aborted) {
        throw createAbortError()
      }
      try {
        if (descriptor.inline) {
          const res = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              template_id: descriptor.templateId,
              group_by: descriptor.groupBy,
              source: descriptor.source,
              entity_id: descriptor.entityId,
              mode: descriptor.mode,
              inline: descriptor.inline,
            }),
            signal: combinedSignal,
          })
          if (!res.ok) throw new Error(`Preview ${res.status}`)
          const html = await res.text()
          const timingMs = extractPreviewRenderMs(res.headers)
          recordCollectionsPerf('collections.preview.request', {
            descriptor: descriptor.inline?.widget_plugin ?? descriptor.templateId ?? 'inline',
            mode: descriptor.mode,
            timingMs,
          })
          return { html, timingMs }
        }

        const url = buildPreviewUrl(descriptor)
        const res = await fetch(url, { signal: combinedSignal, cache: 'no-store' })
        if (!res.ok) throw new Error(`Preview ${res.status}`)
        const html = await res.text()
        const timingMs = extractPreviewRenderMs(res.headers)
        recordCollectionsPerf('collections.preview.request', {
          descriptor: descriptor.templateId ?? 'inline',
          mode: descriptor.mode,
          timingMs,
        })
        return { html, timingMs }
      } finally {
        if (slotAcquired) releaseRenderSlot()
      }
    },
    enabled: visible && descriptor !== null,
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    retry: 1,
    refetchOnWindowFocus: false,
  })

  return {
    html: query.data?.html ?? null,
    loading: query.isLoading || query.isFetching,
    error: query.error?.message ?? null,
    timingMs: query.data?.timingMs ?? null,
  }
}

// --- Invalidation globale ---

let invalidationTimer: ReturnType<typeof setTimeout> | null = null

/**
 * Invalide toutes les previews en cache.
 * Appelée dans le callback de succès d'import ou de save config.
 * Debouncée (300ms) pour éviter le thundering herd.
 */
export function invalidateAllPreviews(queryClient: QueryClient) {
  if (invalidationTimer) clearTimeout(invalidationTimer)
  invalidationTimer = setTimeout(() => {
    invalidationTimer = null
    queryClient.invalidateQueries({
      queryKey: ['preview'],
      refetchType: 'active',
    })
  }, 300)
}
