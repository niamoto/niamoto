export type DesktopShell = 'tauri' | 'electron'
export type RuntimeModeValue = 'desktop' | 'web'

export interface RuntimeFeatures {
  project_switching: boolean
}

export interface RuntimeModeState {
  mode: RuntimeModeValue
  shell: DesktopShell | null
  project: string | null
  features: RuntimeFeatures
}

export interface DesktopInvokeArgs {
  [key: string]: unknown
}

export interface DesktopBridge {
  shell: DesktopShell
  invoke<T>(command: string, args?: DesktopInvokeArgs): Promise<T>
}

export interface ElectronDesktopApi {
  invoke<T>(command: string, args?: DesktopInvokeArgs): Promise<T>
}

declare global {
  interface Window {
    __NIAMOTO_ELECTRON__?: ElectronDesktopApi
    __TAURI__?: unknown
    __TAURI_INTERNALS__?: unknown
  }
}
