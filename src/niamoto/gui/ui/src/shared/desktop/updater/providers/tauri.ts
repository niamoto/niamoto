import {
  createElement,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { relaunch } from '@tauri-apps/plugin-process'
import { check } from '@tauri-apps/plugin-updater'
import { toast } from 'sonner'

import { openExternalUrl } from '@/shared/desktop/openExternalUrl'
import { usePlatform } from '@/shared/hooks/usePlatform'

import {
  AppUpdaterContext,
  APP_VERSION,
  type AppUpdaterValue,
  type UpdateInfo,
} from '../context'
import {
  createInitialDownloadProgressState,
  reduceDownloadProgressEvent,
} from '../downloadProgress'
import { getManualUpdateUrl, isInAppUpdateInstallSupported } from '../support'

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000
const INITIAL_DELAY_MS = 5000

function useTauriAppUpdaterController(): AppUpdaterValue {
  const { platform, isLinux, isWindows } = usePlatform()
  const [info, setInfo] = useState<UpdateInfo>({ status: 'idle' })
  const updateRef = useRef<Awaited<ReturnType<typeof check>> | null>(null)
  const toastIdRef = useRef<string | number | undefined>(undefined)
  const isInstallingRef = useRef(false)
  const inAppUpdateInstallSupported = isInAppUpdateInstallSupported(platform)
  const manualUpdateUrl = inAppUpdateInstallSupported
    ? undefined
    : getManualUpdateUrl(platform, updateRef.current?.rawJson)

  const restartApp = useCallback(async () => {
    try {
      await relaunch()
    } catch (err) {
      toast.error('Redémarrage impossible', {
        id: toastIdRef.current,
        description:
          err instanceof Error
            ? err.message
            : "Fermez puis relancez l'application manuellement.",
        duration: Infinity,
      })
      throw err
    }
  }, [])

  const installUpdate = useCallback(async () => {
    const update = updateRef.current
    if (!update || isInstallingRef.current || !inAppUpdateInstallSupported) return

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
        downloadState = reduceDownloadProgressEvent(downloadState, event, {
          isLinux,
          isWindows,
        })
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
      setInfo({ status: 'installing', version: update.version })

      toast.success('Mise à jour installée, redémarrage...', {
        id: toastIdRef.current,
        duration: 2000,
      })

      try {
        await restartApp()
      } catch (err) {
        setInfo({ status: 'restart_required', version: update.version })
        toast('Mise à jour installée', {
          id: toastIdRef.current,
          description:
            "Le redémarrage automatique a échoué. Relancez l'application manuellement.",
          duration: Infinity,
          action: {
            label: 'Réessayer',
            onClick: () => {
              void restartApp()
            },
          },
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
  }, [inAppUpdateInstallSupported, isLinux, isWindows, restartApp])

  const checkForUpdate = useCallback(async () => {
    if (isInstallingRef.current) return

    setInfo({ status: 'checking' })
    try {
      const update = await check()

      if (update) {
        updateRef.current = update
        setInfo({ status: 'available', version: update.version })
        const updateDownloadUrl = getManualUpdateUrl(platform, update.rawJson)
        if (toastIdRef.current !== undefined) {
          toast.dismiss(toastIdRef.current)
        }
        toastIdRef.current = toast('Mise à jour disponible', {
          description: `Version ${update.version}`,
          duration: Infinity,
          action: {
            label: inAppUpdateInstallSupported ? 'Installer' : 'Télécharger',
            onClick: () => {
              if (inAppUpdateInstallSupported) {
                void installUpdate()
                return
              }

              if (updateDownloadUrl) {
                void openExternalUrl(updateDownloadUrl)
              }
            },
          },
        })
      } else {
        updateRef.current = null
        setInfo({ status: 'idle' })
      }
    } catch {
      updateRef.current = null
      setInfo({ status: 'idle' })
    }
  }, [inAppUpdateInstallSupported, installUpdate, platform])

  useEffect(() => {
    const initialTimeout = setTimeout(checkForUpdate, INITIAL_DELAY_MS)
    const interval = setInterval(checkForUpdate, CHECK_INTERVAL_MS)

    return () => {
      clearTimeout(initialTimeout)
      clearInterval(interval)
    }
  }, [checkForUpdate])

  return {
    ...info,
    appVersion: APP_VERSION,
    manualUpdateUrl,
    checkForUpdate,
    installUpdate,
    restartApp,
  }
}

export function TauriAppUpdaterProvider({ children }: { children: ReactNode }) {
  const value = useTauriAppUpdaterController()
  return createElement(AppUpdaterContext.Provider, { value }, children)
}
