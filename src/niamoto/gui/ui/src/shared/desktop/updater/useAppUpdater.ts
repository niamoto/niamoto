import { useState, useEffect, useCallback, useRef } from 'react'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'

interface UpdateState {
  status: 'idle' | 'checking' | 'available' | 'downloading' | 'error'
  version?: string
  progress?: number
  error?: string
}

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000 // 4 hours
const INITIAL_DELAY_MS = 5000

export function useAppUpdater() {
  const { isDesktop } = useRuntimeMode()
  const [state, setState] = useState<UpdateState>({ status: 'idle' })
  const [dismissed, setDismissed] = useState(false)
  const updateRef = useRef<Awaited<ReturnType<typeof import('@tauri-apps/plugin-updater').check>> | null>(null)

  const checkForUpdate = useCallback(async () => {
    if (!isDesktop) return

    setState({ status: 'checking' })
    try {
      const { check } = await import('@tauri-apps/plugin-updater')
      const update = await check()

      if (update) {
        updateRef.current = update
        setState({ status: 'available', version: update.version })
        setDismissed(false)
      } else {
        setState({ status: 'idle' })
      }
    } catch (err) {
      // Network errors and 404 (no release yet) are not user-facing errors
      console.warn('Update check skipped:', err)
      setState({ status: 'idle' })
    }
  }, [isDesktop])

  const installUpdate = useCallback(async () => {
    const update = updateRef.current
    if (!update) return

    setState(prev => ({ ...prev, status: 'downloading', progress: 0 }))
    try {
      let downloaded = 0
      let total = 0

      await update.downloadAndInstall((event) => {
        if (event.event === 'Started') {
          total = (event.data as { contentLength?: number }).contentLength ?? 0
        } else if (event.event === 'Progress') {
          downloaded += (event.data as { chunkLength: number }).chunkLength
          if (total > 0) {
            setState(prev => ({
              ...prev,
              progress: Math.min(100, Math.round((downloaded / total) * 100)),
            }))
          }
        }
      })

      const { relaunch } = await import('@tauri-apps/plugin-process')
      await relaunch()
    } catch (err) {
      setState({
        status: 'error',
        error: err instanceof Error ? err.message : 'Update failed',
      })
    }
  }, [])

  const dismiss = useCallback(() => setDismissed(true), [])
  const retry = useCallback(() => checkForUpdate(), [checkForUpdate])

  useEffect(() => {
    if (!isDesktop) return

    const initialTimeout = setTimeout(checkForUpdate, INITIAL_DELAY_MS)
    const interval = setInterval(checkForUpdate, CHECK_INTERVAL_MS)

    return () => {
      clearTimeout(initialTimeout)
      clearInterval(interval)
    }
  }, [isDesktop, checkForUpdate])

  return {
    ...state,
    dismissed,
    installUpdate,
    dismiss,
    retry,
  }
}
