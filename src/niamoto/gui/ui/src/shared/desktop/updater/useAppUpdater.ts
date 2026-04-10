import { useState, useEffect, useCallback, useRef } from 'react'
import { relaunch } from '@tauri-apps/plugin-process'
import { check } from '@tauri-apps/plugin-updater'
import { toast } from 'sonner'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { usePlatform } from '@/shared/hooks/usePlatform'
import {
  createInitialDownloadProgressState,
  reduceDownloadProgressEvent,
} from './downloadProgress'

export interface UpdateInfo {
  status: 'idle' | 'checking' | 'available' | 'downloading' | 'installing'
  version?: string
  progress?: number
}

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000 // 4 hours
const INITIAL_DELAY_MS = 5000
declare const __APP_VERSION__: string
const APP_VERSION = __APP_VERSION__

export function useAppUpdater() {
  const { isDesktop } = useRuntimeMode()
  const { isLinux } = usePlatform()
  const [info, setInfo] = useState<UpdateInfo>({ status: 'idle' })
  const updateRef = useRef<Awaited<ReturnType<typeof check>> | null>(null)
  const toastIdRef = useRef<string | number | undefined>(undefined)
  const isInstallingRef = useRef(false)

  const installUpdate = useCallback(async () => {
    const update = updateRef.current
    if (!update || isInstallingRef.current) return

    isInstallingRef.current = true
    if (toastIdRef.current !== undefined) {
      toast.dismiss(toastIdRef.current)
    }

    setInfo(prev => ({ ...prev, status: 'downloading', progress: undefined }))
    toastIdRef.current = toast.loading('Mise à jour en cours...', {
      duration: Infinity,
    })

    try {
      let downloadState = createInitialDownloadProgressState()

      await update.downloadAndInstall((event) => {
        downloadState = reduceDownloadProgressEvent(downloadState, event, { isLinux })
        setInfo(prev => ({
          ...prev,
          status: downloadState.status,
          progress: downloadState.progress,
        }))
        toast.loading(downloadState.label, {
          id: toastIdRef.current,
          duration: Infinity,
        })
      })

      updateRef.current = null
      setInfo({ status: 'idle' })

      if (isLinux) {
        toast.success('Mise à jour installée', {
          id: toastIdRef.current,
          description:
            "L'installation est terminée. Fermez puis relancez l'application pour utiliser la nouvelle version.",
          duration: 10000,
        })
        return
      }

      toast.success('Mise à jour installée, redémarrage...', {
        id: toastIdRef.current,
        duration: 2000,
      })

      try {
        await relaunch()
      } catch (err) {
        setInfo({ status: 'idle' })
        toast('Mise à jour installée', {
          id: toastIdRef.current,
          description:
            "Le redémarrage automatique a échoué. Relancez l'application manuellement.",
          duration: 10000,
        })
        console.error('Update installed but relaunch failed:', err)
      }
    } catch (err) {
      updateRef.current = null
      setInfo({ status: 'idle' })
      toast.error('Échec de la mise à jour', {
        id: toastIdRef.current,
        description: err instanceof Error ? err.message : undefined,
        duration: 8000,
      })
    } finally {
      isInstallingRef.current = false
    }
  }, [isLinux])

  const checkForUpdate = useCallback(async () => {
    if (!isDesktop || isInstallingRef.current) return

    setInfo({ status: 'checking' })
    try {
      const update = await check()

      if (update) {
        updateRef.current = update
        setInfo({ status: 'available', version: update.version })
        if (toastIdRef.current !== undefined) {
          toast.dismiss(toastIdRef.current)
        }
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
