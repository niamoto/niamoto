import { useSyncExternalStore } from 'react'

function subscribe(callback: () => void): () => void {
  window.addEventListener('online', callback)
  window.addEventListener('offline', callback)
  return () => {
    window.removeEventListener('online', callback)
    window.removeEventListener('offline', callback)
  }
}

function getSnapshot(): boolean {
  return navigator.onLine
}

/**
 * Lightweight hook for browser online/offline detection.
 * Intentionally does NOT check the local backend — the feedback
 * POST goes directly to the CF Worker and should work even when
 * the local FastAPI backend is down.
 */
export function useBrowserOnline(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot)
}
