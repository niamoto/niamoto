import { useEffect, useState } from 'react'

import {
  getBootstrappedRuntimeMode,
  isRuntimeModeState,
} from '@/shared/desktop/runtime'
import type { RuntimeModeState } from '@/shared/desktop/types'

function getInitialRuntimeMode(): RuntimeModeState {
  return getBootstrappedRuntimeMode()
}

/**
 * Hook to detect the current runtime mode and active desktop shell.
 * Fetches from `/api/health/runtime-mode` to confirm the shell contract.
 */
export function useRuntimeMode() {
  const [runtimeMode, setRuntimeMode] = useState<RuntimeModeState>(() =>
    getInitialRuntimeMode()
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRuntimeMode = async () => {
      try {
        const response = await fetch('/api/health/runtime-mode')
        if (!response.ok) {
          throw new Error('Failed to fetch runtime mode')
        }

        const data: unknown = await response.json()
        if (!isRuntimeModeState(data)) {
          throw new Error('Received an invalid runtime mode payload')
        }

        setRuntimeMode(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
        console.error('Failed to fetch runtime mode:', err)
      } finally {
        setLoading(false)
      }
    }

    void fetchRuntimeMode()
  }, [])

  return {
    ...runtimeMode,
    loading,
    error,
    isDesktop: runtimeMode.mode === 'desktop',
    isWeb: runtimeMode.mode === 'web',
    isTauri: runtimeMode.shell === 'tauri',
    isElectron: runtimeMode.shell === 'electron',
  }
}
