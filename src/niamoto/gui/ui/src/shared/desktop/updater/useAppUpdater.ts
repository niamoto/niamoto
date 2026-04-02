import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'

export interface UpdateInfo {
  status: 'idle' | 'checking' | 'available' | 'downloading'
  version?: string
  progress?: number
}

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000 // 4 hours
const INITIAL_DELAY_MS = 5000
const APP_VERSION = '__APP_VERSION__' // replaced by Vite define

export function useAppUpdater() {
  const { isDesktop } = useRuntimeMode()
  const [info, setInfo] = useState<UpdateInfo>({ status: 'idle' })
  const updateRef = useRef<Awaited<ReturnType<typeof import('@tauri-apps/plugin-updater').check>> | null>(null)
  const toastIdRef = useRef<string | number | undefined>(undefined)

  const installUpdate = useCallback(async () => {
    const update = updateRef.current
    if (!update) return

    const id = toastIdRef.current
    setInfo(prev => ({ ...prev, status: 'downloading', progress: 0 }))
    toast.loading('Mise à jour en cours...', { id, duration: Infinity })

    try {
      let downloaded = 0
      let total = 0

      await update.downloadAndInstall((event) => {
        if (event.event === 'Started') {
          total = (event.data as { contentLength?: number }).contentLength ?? 0
        } else if (event.event === 'Progress') {
          downloaded += (event.data as { chunkLength: number }).chunkLength
          if (total > 0) {
            const pct = Math.min(100, Math.round((downloaded / total) * 100))
            setInfo(prev => ({ ...prev, progress: pct }))
            toast.loading(`Mise à jour en cours... ${pct}%`, { id, duration: Infinity })
          }
        }
      })

      toast.success('Mise à jour installée, redémarrage...', { id, duration: 2000 })

      const { relaunch } = await import('@tauri-apps/plugin-process')
      await relaunch()
    } catch (err) {
      setInfo({ status: 'idle' })
      toast.error('Échec de la mise à jour', {
        id,
        description: err instanceof Error ? err.message : undefined,
        duration: 8000,
      })
    }
  }, [])

  const checkForUpdate = useCallback(async () => {
    if (!isDesktop) return

    setInfo({ status: 'checking' })
    try {
      const { check } = await import('@tauri-apps/plugin-updater')
      const update = await check()

      if (update) {
        updateRef.current = update
        setInfo({ status: 'available', version: update.version })
        toastIdRef.current = toast('Mise à jour disponible', {
          description: `Version ${update.version}`,
          duration: Infinity,
          action: {
            label: 'Installer',
            onClick: () => installUpdate(),
          },
        })
      } else {
        setInfo({ status: 'idle' })
      }
    } catch {
      setInfo({ status: 'idle' })
    }
  }, [isDesktop, installUpdate])

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
    ...info,
    appVersion: APP_VERSION,
    checkForUpdate,
    installUpdate,
  }
}
