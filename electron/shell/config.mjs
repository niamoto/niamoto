import os from 'node:os'
import path from 'node:path'

export const DESKTOP_CONFIG_ENV = 'NIAMOTO_DESKTOP_CONFIG'
export const DESKTOP_LOG_DIR_ENV = 'NIAMOTO_DESKTOP_LOG_DIR'
export const DESKTOP_RUNTIME_MODE_ENV = 'NIAMOTO_RUNTIME_MODE'
export const DESKTOP_SHELL_ENV = 'NIAMOTO_DESKTOP_SHELL'
export const ELECTRON_RENDERER_URL_ENV = 'NIAMOTO_ELECTRON_RENDERER_URL'

const SHARED_APP_IDENTIFIER = 'com.niamoto.desktop'
const ELECTRON_APP_IDENTIFIER = 'com.niamoto.desktop.electron'

function resolveConfigRoot(platform = process.platform, env = process.env) {
  if (platform === 'darwin') {
    return path.join(os.homedir(), 'Library', 'Application Support')
  }

  if (platform === 'win32') {
    return env.APPDATA ?? path.join(os.homedir(), 'AppData', 'Roaming')
  }

  return env.XDG_CONFIG_HOME ?? path.join(os.homedir(), '.config')
}

function resolveDataRoot(platform = process.platform, env = process.env) {
  if (platform === 'darwin') {
    return path.join(os.homedir(), 'Library', 'Application Support')
  }

  if (platform === 'win32') {
    return env.LOCALAPPDATA ?? env.APPDATA ?? path.join(os.homedir(), 'AppData', 'Local')
  }

  return env.XDG_DATA_HOME ?? path.join(os.homedir(), '.local', 'share')
}

export function resolveSharedDesktopConfigPath(options = {}) {
  const env = options.env ?? process.env
  const platform = options.platform ?? process.platform

  if (env[DESKTOP_CONFIG_ENV]) {
    return env[DESKTOP_CONFIG_ENV]
  }

  return path.join(
    resolveConfigRoot(platform, env),
    SHARED_APP_IDENTIFIER,
    'desktop-config.json'
  )
}

export function resolveElectronSettingsPath(options = {}) {
  const env = options.env ?? process.env
  const platform = options.platform ?? process.platform

  return path.join(
    resolveConfigRoot(platform, env),
    ELECTRON_APP_IDENTIFIER,
    'settings.json'
  )
}

export function resolveElectronLogDir(options = {}) {
  const env = options.env ?? process.env
  const platform = options.platform ?? process.platform

  return path.join(resolveDataRoot(platform, env), ELECTRON_APP_IDENTIFIER, 'logs')
}

export function resolveRendererUrl(options = {}) {
  const env = options.env ?? process.env
  return env[ELECTRON_RENDERER_URL_ENV] ?? 'http://127.0.0.1:5173'
}

export function resolveWindowOptions(preloadPath) {
  return {
    title: 'Niamoto',
    width: 1280,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  }
}
