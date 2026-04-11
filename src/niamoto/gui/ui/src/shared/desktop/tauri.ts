import {
  invoke as tauriInvoke,
  isTauri as tauriIsTauri,
} from '@tauri-apps/api/core'

export function isDesktopTauri(): boolean {
  return typeof window !== 'undefined' && tauriIsTauri()
}

export function invokeDesktop<T>(
  command: string,
  args?: Record<string, unknown>
): Promise<T> {
  return tauriInvoke<T>(command, args)
}
