import { createContext } from 'react'

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

export interface AppUpdaterValue extends UpdateInfo {
  appVersion: string
  manualUpdateUrl?: string
  checkForUpdate: () => Promise<void>
  installUpdate: () => Promise<void>
  restartApp: () => Promise<void>
}

declare const __APP_VERSION__: string

export const APP_VERSION = __APP_VERSION__

export const AppUpdaterContext = createContext<AppUpdaterValue | null>(null)

export function createStaticAppUpdaterValue(
  appVersion: string
): AppUpdaterValue {
  return {
    status: 'idle',
    appVersion,
    checkForUpdate: async () => {},
    installUpdate: async () => {},
    restartApp: async () => {},
  }
}
