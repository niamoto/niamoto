import type { DesktopShell, RuntimeModeState, RuntimeModeValue } from './types'

const KNOWN_DESKTOP_SHELLS = ['tauri', 'electron'] as const
const KNOWN_RUNTIME_MODES = ['desktop', 'web'] as const

function isDesktopShell(value: string | null): value is DesktopShell {
  return value !== null && KNOWN_DESKTOP_SHELLS.includes(value as DesktopShell)
}

function isRuntimeModeValue(value: string | null): value is RuntimeModeValue {
  return (
    value !== null && KNOWN_RUNTIME_MODES.includes(value as RuntimeModeValue)
  )
}

function getDocumentAttribute(name: string): string | null {
  if (typeof document === 'undefined') {
    return null
  }

  return document.documentElement.getAttribute(name)
}

function detectDesktopShellFromWindow(): DesktopShell | null {
  if (typeof window === 'undefined') {
    return null
  }

  if (typeof window.__NIAMOTO_ELECTRON__?.invoke === 'function') {
    return 'electron'
  }

  if (
    typeof window.__TAURI_INTERNALS__ === 'object' ||
    typeof window.__TAURI__ === 'object'
  ) {
    return 'tauri'
  }

  return null
}

export function getDesktopShell(): DesktopShell | null {
  const bootstrappedShell = getDocumentAttribute('data-shell')
  if (isDesktopShell(bootstrappedShell)) {
    return bootstrappedShell
  }

  return detectDesktopShellFromWindow()
}

export function hasDesktopShell(): boolean {
  return getDesktopShell() !== null
}

export function getBootstrappedRuntimeMode(): RuntimeModeState {
  const shell = getDesktopShell()
  const bootstrappedMode = getDocumentAttribute('data-runtime-mode')
  const mode =
    isRuntimeModeValue(bootstrappedMode)
      ? bootstrappedMode
      : shell
        ? 'desktop'
        : 'web'

  return {
    mode,
    shell,
    project: null,
    features: {
      project_switching: mode === 'desktop',
    },
  }
}

function isRuntimeFeatures(value: unknown): value is RuntimeModeState['features'] {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const candidate = value as Record<string, unknown>
  return typeof candidate.project_switching === 'boolean'
}

export function isRuntimeModeState(value: unknown): value is RuntimeModeState {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const candidate = value as Record<string, unknown>
  const shell = candidate.shell

  return (
    (candidate.mode === 'desktop' || candidate.mode === 'web') &&
    (typeof candidate.project === 'string' || candidate.project === null) &&
    (shell === 'tauri' || shell === 'electron' || shell === null) &&
    isRuntimeFeatures(candidate.features)
  )
}
