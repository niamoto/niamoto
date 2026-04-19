import fs from 'node:fs/promises'
import path from 'node:path'
import readline from 'node:readline'

import {
  DESKTOP_PROBE_HEADER,
  DESKTOP_TOKEN_HEADER,
  generateStartupToken,
  resolveDesktopApiPort,
  resolveSidecarPath,
  spawnSidecar,
  terminateChildProcess,
} from './sidecar.mjs'

const DEFAULT_HEALTH_TIMEOUT_MS = 750
const DEFAULT_STARTUP_TIMEOUT_MS = 90_000
const DEFAULT_POLL_INTERVAL_MS = 500

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

export function newStartupSession(options = {}) {
  const now = options.now ?? Date.now
  const pid = options.pid ?? process.pid
  return `desktop-startup-${pid}-${now()}`
}

export async function writeStartupLog(logPath, session, source, message, options = {}) {
  const appendFileImpl = options.appendFileImpl ?? fs.appendFile
  const now = options.now ?? Date.now
  const timestamp = (now() / 1000).toFixed(3)
  const line = `[${timestamp}] [${session}] [${source}] ${message}\n`
  await appendFileImpl(logPath, line, 'utf8')
}

export function createStartupLogger(options) {
  return async (source, message) => {
    await writeStartupLog(options.logPath, options.session, source, message, options)
  }
}

export function healthProbeIsAuthenticated(status, returnedToken, expectedToken) {
  return status >= 200 && status < 300 && returnedToken === expectedToken
}

function getResponseHeader(response, headerName) {
  if (!response?.headers) {
    return null
  }

  if (typeof response.headers.get === 'function') {
    return response.headers.get(headerName)
  }

  return response.headers[headerName] ?? null
}

export function monitorChildStream(stream, log, source) {
  if (!stream || typeof stream.on !== 'function') {
    return null
  }

  const reader = readline.createInterface({ input: stream })
  reader.on('line', (line) => {
    void log(source, line)
  })
  reader.on('error', (error) => {
    void log(source, `failed to read child stream: ${error.message}`)
  })
  return reader
}

export async function probeHealth(options) {
  const fetchImpl = options.fetchImpl ?? globalThis.fetch
  if (typeof fetchImpl !== 'function') {
    return false
  }

  const timeoutMs = options.timeoutMs ?? DEFAULT_HEALTH_TIMEOUT_MS
  const controller = new AbortController()
  const timer = setTimeout(() => {
    controller.abort()
  }, timeoutMs)

  try {
    const response = await fetchImpl(`http://127.0.0.1:${options.port}/api/health`, {
      headers: {
        [DESKTOP_PROBE_HEADER]: '1',
      },
      signal: controller.signal,
    })

    return healthProbeIsAuthenticated(
      response.status,
      getResponseHeader(response, DESKTOP_TOKEN_HEADER),
      options.expectedToken
    )
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

export async function waitForSidecarReady(options) {
  const timeoutMs = options.timeoutMs ?? DEFAULT_STARTUP_TIMEOUT_MS
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS
  const sleep = options.sleep ?? delay
  const maxAttempts = Math.max(1, Math.ceil(timeoutMs / pollIntervalMs))

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const isReady = await probeHealth({
      port: options.port,
      expectedToken: options.expectedToken,
      fetchImpl: options.fetchImpl,
      timeoutMs: options.healthTimeoutMs,
    })

    if (isReady) {
      return { status: 'ready', attempts: attempt + 1 }
    }

    if (options.childProcess && options.childProcess.exitCode !== null) {
      return {
        status: 'exited',
        attempts: attempt + 1,
        exitCode: options.childProcess.exitCode,
        signalCode: options.childProcess.signalCode ?? null,
      }
    }

    if (attempt < maxAttempts - 1) {
      if (typeof options.onProgress === 'function' && (attempt + 1) % 10 === 0) {
        await options.onProgress({ attempt: attempt + 1, maxAttempts })
      }

      await sleep(pollIntervalMs)
    }
  }

  return { status: 'timeout', attempts: maxAttempts }
}

export function resolveStartupUrl(options) {
  if (options.hotReloadEnabled) {
    if (!options.rendererUrl) {
      throw new Error('Missing renderer URL for Electron hot reload mode')
    }

    return options.rendererUrl
  }

  return `http://127.0.0.1:${options.readyPort}`
}

export async function startSidecarSession(options) {
  const hotReloadEnabled = options.hotReloadEnabled ?? false
  const logDir = options.logDir
  const startupTimeoutMs = options.startupTimeoutMs ?? DEFAULT_STARTUP_TIMEOUT_MS
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS
  const now = options.now ?? Date.now
  const startupSession = newStartupSession({
    now,
    pid: options.pid,
  })
  const startupLogPath = path.join(logDir, `${startupSession}.log`)
  const mkdirImpl = options.mkdirImpl ?? fs.mkdir

  await mkdirImpl(logDir, { recursive: true })

  const log = createStartupLogger({
    logPath: startupLogPath,
    session: startupSession,
    appendFileImpl: options.appendFileImpl,
    now,
  })

  await log('electron', 'desktop startup started')

  const port = await resolveDesktopApiPort({
    hotReloadEnabled,
    env: options.env,
    findFreePortImpl: options.findFreePortImpl,
  })
  const desktopAuthToken = generateStartupToken({
    randomBytesImpl: options.randomBytesImpl,
  })
  const sidecarPath = await resolveSidecarPath({
    isPackaged: options.isPackaged,
    platform: options.platform,
    arch: options.arch,
    resourcesPath: options.resourcesPath,
    execPath: options.execPath,
    projectRoot: options.projectRoot,
  })

  await log('electron', `resolved sidecar path ${sidecarPath}`)
  await log('electron', `selected API port ${port}`)

  let childProcess
  try {
    childProcess = spawnSidecar({
      sidecarPath,
      port,
      projectPath: options.projectPath,
      desktopAuthToken,
      startupSession,
      startupLogPath,
      logDir,
      env: options.env,
      platform: options.platform,
      spawnImpl: options.spawnImpl,
    })
  } catch (error) {
    await log('electron', `failed to spawn sidecar: ${error.message}`)
    throw new Error(
      `Electron failed to launch the Python sidecar: ${error.message}\n\nStartup log: ${startupLogPath}`
    )
  }

  await log(
    'electron',
    `sidecar spawned with pid=${childProcess.pid ?? 'unknown'} on port ${port}`
  )

  monitorChildStream(childProcess.stdout, log, 'sidecar:stdout')
  monitorChildStream(childProcess.stderr, log, 'sidecar:stderr')

  const readiness = await waitForSidecarReady({
    port,
    expectedToken: desktopAuthToken,
    childProcess,
    fetchImpl: options.fetchImpl,
    timeoutMs: startupTimeoutMs,
    pollIntervalMs,
    sleep: options.sleep,
    onProgress: async ({ attempt, maxAttempts }) => {
      await log(
        'electron',
        `still waiting for authenticated health probe (${attempt}/${maxAttempts})`
      )

      if (typeof options.onProgress === 'function') {
        await options.onProgress({ attempt, maxAttempts })
      }
    },
  })

  if (readiness.status === 'ready') {
    const readyUrl = resolveStartupUrl({
      hotReloadEnabled,
      rendererUrl: options.rendererUrl,
      readyPort: port,
    })

    await log('electron', `desktop ready at ${readyUrl}`)
    return {
      childProcess,
      desktopAuthToken,
      port,
      readyUrl,
      sidecarPath,
      startupLogPath,
      startupSession,
    }
  }

  if (readiness.status === 'exited') {
    await log(
      'electron',
      `sidecar exited before readiness (exitCode=${readiness.exitCode ?? 'null'})`
    )
    throw new Error(
      `Electron sidecar exited before becoming ready on port ${port}.\n\nStartup log: ${startupLogPath}`
    )
  }

  await log(
    'electron',
    `startup timed out after ${Math.round(startupTimeoutMs / 1000)}s on port ${port}`
  )
  await terminateChildProcess(childProcess, {
    platform: options.platform,
    execFileImpl: options.execFileImpl,
    killImpl: options.killImpl,
    delayImpl: options.sleep,
  })

  throw new Error(
    `Electron sidecar failed to become ready within ${Math.round(startupTimeoutMs / 1000)}s.\n\nStartup log: ${startupLogPath}`
  )
}
