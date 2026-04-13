import {
  createElement,
  createContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  useContext,
  type ReactNode,
} from 'react'
import { relaunch } from '@tauri-apps/plugin-process'
import { check } from '@tauri-apps/plugin-updater'
import { toast } from 'sonner'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { usePlatform } from '@/shared/hooks/usePlatform'
import { openExternalUrl } from '@/shared/desktop/openExternalUrl'
import {
  createInitialDownloadProgressState,
  reduceDownloadProgressEvent,
} from './downloadProgress'
import { isInAppUpdateInstallSupported, WINDOWS_MANUAL_UPDATE_URL } from './support'

export interface UpdateInfo {
  status:
    | 'idle'
    | 'checking'
    | 'available'
    | 'downloading'
    | 'installing'
    | 'restart_required'
  version?: string
  progress?: number
}

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000 // 4 hours
const INITIAL_DELAY_MS = 5000
declare const __APP_VERSION__: string
const APP_VERSION = __APP_VERSION__

interface AppUpdaterValue extends UpdateInfo {
  appVersion: string
  manualUpdateUrl?: string
  checkForUpdate: () => Promise<void>
  installUpdate: () => Promise<void>
  restartApp: () => Promise<void>
}

const AppUpdaterContext = createContext<AppUpdaterValue | null>(null)

function useAppUpdaterController(): AppUpdaterValue {
  const { isDesktop } = useRuntimeMode()
  const { platform, isLinux, isWindows } = usePlatform()
  const [info, setInfo] = useState<UpdateInfo>({ status: 'idle' })
  const updateRef = useRef<Awaited<ReturnType<typeof check>> | null>(null)
  const toastIdRef = useRef<string | number | undefined>(undefined)
  const isInstallingRef = useRef(false)
  const inAppUpdateInstallSupported = isInAppUpdateInstallSupported(platform)

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
            label: inAppUpdateInstallSupported ? 'Installer' : 'Télécharger',
            onClick: () => {
              if (inAppUpdateInstallSupported) {
                void installUpdate()
                return
              }

              void openExternalUrl(WINDOWS_MANUAL_UPDATE_URL)
            },
          },
        })
      } else {
        setInfo({ status: 'idle' })
      }
    } catch {
      setInfo({ status: 'idle' })
    }
  }, [inAppUpdateInstallSupported, isDesktop, installUpdate])

  useEffect(() => {
    if (!isDesktop) return

    const initialTimeout = setTimeout(checkForUpdate, INITIAL_DELAY_MS)
    const interval = setInterval(checkForUpdate, CHECK_INTERVAL_MS)

    return () => {
      clearTimeout(initialTimeout)
      clearInterval(interval)
    }
  }, [checkForUpdate, isDesktop])

  return {
    ...info,
    appVersion: APP_VERSION,
    manualUpdateUrl: inAppUpdateInstallSupported ? undefined : WINDOWS_MANUAL_UPDATE_URL,
    checkForUpdate,
    installUpdate,
    restartApp,
  }
}

export function AppUpdaterProvider({ children }: { children: ReactNode }) {
  const value = useAppUpdaterController()
  return createElement(AppUpdaterContext.Provider, { value }, children)
}

export function useAppUpdater() {
  const value = useContext(AppUpdaterContext)
  if (!value) {
    throw new Error('useAppUpdater must be used within an AppUpdaterProvider')
  }
  return value
}
