import { useState, useEffect, useCallback, useRef } from 'react'

export interface NetworkStatus {
  /** Browser reports as online (fast but unreliable) */
  isOnline: boolean
  /** Backend confirmed internet connectivity (reliable, on-demand) */
  isInternetAvailable: boolean | null
  /** Currently checking connectivity */
  isChecking: boolean
  /** Last connectivity check timestamp */
  lastChecked: Date | null
}

const CONNECTIVITY_TIMEOUT_MS = 5000
const FOREGROUND_RECHECK_DEBOUNCE_MS = 5000

let inFlightConnectivityProbe: Promise<boolean> | null = null
let lastConnectivityProbeAt = 0

export function applyConnectivityResult(
  status: NetworkStatus,
  online: boolean,
  checkedAt: Date
): NetworkStatus {
  return {
    ...status,
    // A successful backend probe heals stale navigator.onLine=false states after resume.
    isOnline: online ? true : status.isOnline,
    isInternetAvailable: online,
    isChecking: false,
    lastChecked: checkedAt,
  }
}

export function getIsOffline(
  status: Pick<NetworkStatus, 'isOnline' | 'isInternetAvailable'>
): boolean {
  if (status.isInternetAvailable === true) {
    return false
  }

  if (status.isInternetAvailable === false) {
    return true
  }

  return !status.isOnline
}

async function probeConnectivity(): Promise<boolean> {
  if (inFlightConnectivityProbe) {
    return inFlightConnectivityProbe
  }

  lastConnectivityProbeAt = Date.now()
  inFlightConnectivityProbe = (async () => {
    try {
      const response = await fetch('/api/health/connectivity', {
        signal: AbortSignal.timeout(CONNECTIVITY_TIMEOUT_MS),
      })
      if (!response.ok) {
        return false
      }

      const data = await response.json()
      return data.online === true
    } catch {
      return false
    } finally {
      inFlightConnectivityProbe = null
    }
  })()

  return inFlightConnectivityProbe
}

/**
 * Hook to detect network and internet connectivity status.
 *
 * Uses two layers:
 * 1. `navigator.onLine` + browser events for fast (but unreliable) detection
 * 2. Backend `/api/health/connectivity` for reliable on-demand checks
 *
 * The `checkConnectivity()` function can be called before operations
 * that require internet (enrichment, deploy).
 */
export function useNetworkStatus() {
  const [status, setStatus] = useState<NetworkStatus>({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    isInternetAvailable: null,
    isChecking: false,
    lastChecked: null,
  })
  const isMountedRef = useRef(true)

  // On-demand connectivity check via backend
  const checkConnectivity = useCallback(async (): Promise<boolean> => {
    setStatus((prev) => ({ ...prev, isChecking: true }))
    const online = await probeConnectivity()
    const checkedAt = new Date()

    if (isMountedRef.current) {
      setStatus((prev) => applyConnectivityResult(prev, online, checkedAt))
    }

    return online
  }, [])

  // Listen to browser online/offline events
  useEffect(() => {
    isMountedRef.current = true

    const handleOnline = () => {
      // Clear stale offline state immediately, then confirm via backend.
      setStatus((prev) => ({
        ...prev,
        isOnline: true,
        isInternetAvailable: null,
      }))
      void checkConnectivity()
    }
    const handleOffline = () => {
      setStatus((prev) => ({
        ...prev,
        isOnline: false,
        isInternetAvailable: prev.isInternetAvailable === true ? true : null,
      }))
      void checkConnectivity()
    }

    const handleForegroundResume = () => {
      if (document.visibilityState === 'hidden') {
        return
      }

      const now = Date.now()
      if (now - lastConnectivityProbeAt < FOREGROUND_RECHECK_DEBOUNCE_MS) {
        return
      }

      void checkConnectivity()
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    window.addEventListener('focus', handleForegroundResume)
    document.addEventListener('visibilitychange', handleForegroundResume)

    return () => {
      isMountedRef.current = false
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('focus', handleForegroundResume)
      document.removeEventListener('visibilitychange', handleForegroundResume)
    }
  }, [checkConnectivity])

  return {
    ...status,
    /** Trigger an on-demand connectivity check via backend */
    checkConnectivity,
    /** Convenience: is the app likely offline? */
    isOffline: getIsOffline(status),
  }
}
