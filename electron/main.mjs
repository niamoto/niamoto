import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs/promises'

import {
  attachMainWindow,
  clearBackendSession,
  createShellState,
  detachMainWindow,
  setBackendSession,
} from './shell/appState.mjs'
import {
  createDesktopCommandRouter,
} from './shell/commands.mjs'
import {
  DESKTOP_CONFIG_ENV,
  DESKTOP_LOG_DIR_ENV,
  DESKTOP_RUNTIME_MODE_ENV,
  DESKTOP_SHELL_ENV,
  resolveElectronLogDir,
  resolveElectronSettingsPath,
  resolveRendererUrl,
  resolveSharedDesktopConfigPath,
  resolveWindowOptions,
} from './shell/config.mjs'
import { terminateChildProcess } from './shell/sidecar.mjs'
import { startSidecarSession } from './shell/startup.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const IPC_CHANNEL = 'niamoto:desktop-command'

function resolvePreloadPath() {
  return path.join(__dirname, 'preload.mjs')
}

function createPaths() {
  return {
    sharedDesktopConfigPath: resolveSharedDesktopConfigPath(),
    electronSettingsPath: resolveElectronSettingsPath(),
    electronLogDir: resolveElectronLogDir(),
  }
}

async function ensureShellDirectories(paths) {
  await fs.mkdir(path.dirname(paths.sharedDesktopConfigPath), { recursive: true })
  await fs.mkdir(path.dirname(paths.electronSettingsPath), { recursive: true })
  await fs.mkdir(paths.electronLogDir, { recursive: true })
}

function shellPageHtml({ title, message, tone = 'loading' }) {
  const accent = tone === 'error' ? '#dc2626' : '#2d7a3a'
  const background = tone === 'error' ? '#18181b' : '#ffffff'
  const foreground = tone === 'error' ? '#fafafa' : '#18181b'
  const messageBg =
    tone === 'error' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(24, 24, 27, 0.05)'

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${title}</title>
    <style>
      :root {
        color-scheme: ${tone === 'error' ? 'dark' : 'light'};
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: ${background};
        color: ${foreground};
        user-select: none;
      }
      main {
        width: min(640px, calc(100vw - 48px));
        text-align: center;
      }
      h1 {
        margin: 0 0 16px;
        font-size: 30px;
      }
      p {
        margin: 0 auto;
        padding: 16px 18px;
        border-radius: 12px;
        background: ${messageBg};
        font: 15px/1.6 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        white-space: pre-wrap;
      }
      .spinner {
        width: 40px;
        height: 40px;
        margin: 0 auto 18px;
        border: 3px solid rgba(127, 127, 127, 0.18);
        border-top-color: ${accent};
        border-radius: 999px;
        animation: spin 0.9s linear infinite;
      }
      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }
    </style>
  </head>
  <body>
    <main>
      <div class="spinner" aria-hidden="true"></div>
      <h1>${title}</h1>
      <p>${message}</p>
    </main>
  </body>
</html>`
}

async function loadShellPage(mainWindow, options) {
  const html = shellPageHtml(options)
  await mainWindow.loadURL(
    `data:text/html;charset=utf-8,${encodeURIComponent(html)}`
  )
}

async function readStartupProjectPath(sharedDesktopConfigPath) {
  const envProject = process.env.NIAMOTO_HOME?.trim()
  if (envProject) {
    return envProject
  }

  try {
    const raw = JSON.parse(await fs.readFile(sharedDesktopConfigPath, 'utf8'))
    return typeof raw.current_project === 'string' && raw.current_project.trim()
      ? raw.current_project
      : null
  } catch (error) {
    if (error && typeof error === 'object' && error.code === 'ENOENT') {
      return null
    }

    throw error
  }
}

function backendSessionIsAlive(state) {
  return Boolean(state.readyUrl && state.serverProcess && state.serverProcess.exitCode === null)
}

async function createMainWindow(state) {
  const mainWindow = new BrowserWindow(resolveWindowOptions(resolvePreloadPath()))
  attachMainWindow(state, mainWindow)
  mainWindow.on('closed', () => {
    detachMainWindow(state, mainWindow)
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  if (backendSessionIsAlive(state)) {
    await mainWindow.loadURL(state.readyUrl)
  } else {
    await loadShellPage(mainWindow, {
      title: 'Starting Niamoto',
      message: 'Waiting for the local backend to become ready…',
    })
  }

  return mainWindow
}

async function ensureRendererReady(state, paths) {
  if (backendSessionIsAlive(state)) {
    if (state.mainWindow && !state.mainWindow.isDestroyed()) {
      await state.mainWindow.loadURL(state.readyUrl)
    }

    return state.readyUrl
  }

  if (state.startupPromise) {
    return state.startupPromise
  }

  clearBackendSession(state)
  state.startupPromise = (async () => {
    const projectPath = await readStartupProjectPath(paths.sharedDesktopConfigPath)

    if (state.mainWindow && !state.mainWindow.isDestroyed()) {
      await loadShellPage(state.mainWindow, {
        title: 'Starting Niamoto',
        message: projectPath
          ? `Booting the local desktop backend for:\n${projectPath}`
          : 'Booting the local desktop backend…',
      })
    }

    try {
      const session = await startSidecarSession({
        hotReloadEnabled: !app.isPackaged,
        isPackaged: app.isPackaged,
        rendererUrl: resolveRendererUrl(),
        logDir: paths.electronLogDir,
        projectPath,
      })

      setBackendSession(state, session)

      if (state.mainWindow && !state.mainWindow.isDestroyed()) {
        await state.mainWindow.loadURL(session.readyUrl)
      }

      return session.readyUrl
    } catch (error) {
      clearBackendSession(state)

      if (state.mainWindow && !state.mainWindow.isDestroyed()) {
        await loadShellPage(state.mainWindow, {
          title: 'Failed to Start Niamoto',
          message: error.message,
          tone: 'error',
        })
      }

      throw error
    } finally {
      state.startupPromise = null
    }
  })()

  return state.startupPromise
}

async function bootstrap() {
  const paths = createPaths()
  await ensureShellDirectories(paths)

  process.env[DESKTOP_CONFIG_ENV] = paths.sharedDesktopConfigPath
  process.env[DESKTOP_LOG_DIR_ENV] = paths.electronLogDir
  process.env[DESKTOP_RUNTIME_MODE_ENV] = 'desktop'
  process.env[DESKTOP_SHELL_ENV] = 'electron'

  const state = createShellState(paths)

  const invokeDesktopCommand = createDesktopCommandRouter({
    paths,
    shellApi: {
      pickDirectory: async ({ title }) => {
        const result = await dialog.showOpenDialog({
          title,
          properties: ['openDirectory'],
        })

        if (result.canceled || result.filePaths.length === 0) {
          return null
        }

        return result.filePaths[0]
      },
      openExternalUrl: (url) => shell.openExternal(url),
      openDevTools: () => state.mainWindow?.webContents.openDevTools(),
    },
    isDev: !app.isPackaged,
  })

  ipcMain.handle(IPC_CHANNEL, async (_event, payload) => {
    return invokeDesktopCommand(payload?.command, payload?.args ?? {})
  })

  await createMainWindow(state)
  void ensureRendererReady(state, paths).catch(() => {})

  app.on('activate', async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createMainWindow(state)
      void ensureRendererReady(state, paths).catch(() => {})
    }
  })

  app.on('before-quit', () => {
    if (state.serverProcess) {
      void terminateChildProcess(state.serverProcess)
      clearBackendSession(state)
    }
  })
}

app.whenReady().then(() => {
  void bootstrap()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
