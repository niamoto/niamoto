import { invoke, isTauri } from '@tauri-apps/api/core'

import type { DesktopBridge, DesktopInvokeArgs } from '../types'

export function createTauriDesktopBridge(): DesktopBridge | null {
  if (!isTauri()) {
    return null
  }

  return {
    shell: 'tauri',
    invoke: <T,>(command: string, args?: DesktopInvokeArgs) =>
      invoke<T>(command, args),
  }
}
