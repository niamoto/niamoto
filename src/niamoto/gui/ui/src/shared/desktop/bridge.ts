import { getDesktopShell } from './runtime'
import type { DesktopBridge, DesktopInvokeArgs } from './types'

let cachedBridgePromise: Promise<DesktopBridge | null> | null = null

function resolveElectronBridge(): DesktopBridge | null {
  if (typeof window === 'undefined') {
    return null
  }

  const electronBridge = window.__NIAMOTO_ELECTRON__
  if (!electronBridge || typeof electronBridge.invoke !== 'function') {
    return null
  }

  return {
    shell: 'electron',
    invoke: <T,>(command: string, args?: DesktopInvokeArgs) =>
      electronBridge.invoke<T>(command, args),
  }
}

async function loadDesktopBridge(): Promise<DesktopBridge | null> {
  const shell = getDesktopShell()
  if (shell === 'electron') {
    return resolveElectronBridge()
  }

  if (shell === 'tauri') {
    const { createTauriDesktopBridge } = await import('./providers/tauri')
    return createTauriDesktopBridge()
  }

  return null
}

export async function getDesktopBridge(): Promise<DesktopBridge | null> {
  if (!cachedBridgePromise) {
    const shell = getDesktopShell()
    if (!shell) {
      return null
    }

    cachedBridgePromise = loadDesktopBridge()
  }

  return cachedBridgePromise
}

export function hasDesktopBridge(): boolean {
  return getDesktopShell() !== null
}

export async function invokeDesktop<T>(
  command: string,
  args?: DesktopInvokeArgs
): Promise<T> {
  const bridge = await getDesktopBridge()
  if (!bridge) {
    throw new Error('Desktop bridge is unavailable in this runtime')
  }

  return bridge.invoke<T>(command, args)
}

export function isDesktopTauri(): boolean {
  return getDesktopShell() === 'tauri'
}

export function isDesktopElectron(): boolean {
  return getDesktopShell() === 'electron'
}

export function resetDesktopBridgeForTests(): void {
  cachedBridgePromise = null
}
