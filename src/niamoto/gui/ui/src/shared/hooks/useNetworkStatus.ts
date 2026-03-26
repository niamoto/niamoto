import { useState, useEffect, useCallback } from 'react'

interface NetworkStatus {
  /** Browser reports as online (fast but unreliable) */
  isOnline: boolean
  /** Backend confirmed internet connectivity (reliable, on-demand) */
  isInternetAvailable: boolean | null
  /** Currently checking connectivity */
  isChecking: boolean
  /** Last connectivity check timestamp */
  lastChecked: Date | null
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

  // Listen to browser online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setStatus((prev) => ({ ...prev, isOnline: true }))
    }
    const handleOffline = () => {
      setStatus((prev) => ({ ...prev, isOnline: false, isInternetAvailable: false }))
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // On-demand connectivity check via backend
  const checkConnectivity = useCallback(async (): Promise<boolean> => {
    setStatus((prev) => ({ ...prev, isChecking: true }))
    try {
      const response = await fetch('/api/health/connectivity', {
        signal: AbortSignal.timeout(5000),
      })
      if (!response.ok) {
        setStatus((prev) => ({
          ...prev,
          isInternetAvailable: false,
          isChecking: false,
          lastChecked: new Date(),
        }))
        return false
      }
      const data = await response.json()
      const online = data.online === true
      setStatus((prev) => ({
        ...prev,
        isInternetAvailable: online,
        isChecking: false,
        lastChecked: new Date(),
      }))
      return online
    } catch {
      setStatus((prev) => ({
        ...prev,
        isInternetAvailable: false,
        isChecking: false,
        lastChecked: new Date(),
      }))
      return false
    }
  }, [])

  return {
    ...status,
    /** Trigger an on-demand connectivity check via backend */
    checkConnectivity,
    /** Convenience: is the app likely offline? */
    isOffline: !status.isOnline || status.isInternetAvailable === false,
  }
}
