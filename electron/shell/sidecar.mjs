import { spawn, execFile } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import fs from 'node:fs/promises'
import net from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DEFAULT_PROJECT_ROOT = path.resolve(__dirname, '../..')

export const DEV_API_PORT = 8080
export const DESKTOP_PROBE_HEADER = 'x-niamoto-desktop-probe'
export const DESKTOP_TOKEN_HEADER = 'x-niamoto-desktop-token'

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath)
    return true
  } catch {
    return false
  }
}

export function sidecarExeName(platform = process.platform) {
  return platform === 'win32' ? 'niamoto.exe' : 'niamoto'
}

export function sidecarTargetTriple(
  platform = process.platform,
  arch = process.arch
) {
  const triples = {
    'darwin:aarch64': 'aarch64-apple-darwin',
    'darwin:arm64': 'aarch64-apple-darwin',
    'darwin:x64': 'x86_64-apple-darwin',
    'linux:aarch64': 'aarch64-unknown-linux-gnu',
    'linux:arm64': 'aarch64-unknown-linux-gnu',
    'linux:x64': 'x86_64-unknown-linux-gnu',
    'win32:aarch64': 'aarch64-pc-windows-msvc',
    'win32:arm64': 'aarch64-pc-windows-msvc',
    'win32:x64': 'x86_64-pc-windows-msvc',
  }

  const triple = triples[`${platform}:${arch}`]
  if (!triple) {
    throw new Error(`Unsupported Electron sidecar target: ${platform}/${arch}`)
  }

  return triple
}

export function resolveDevSidecarPath(options = {}) {
  const projectRoot = options.projectRoot ?? DEFAULT_PROJECT_ROOT
  const platform = options.platform ?? process.platform
  const exeName = sidecarExeName(platform)

  return platform === 'win32'
    ? path.join(projectRoot, '.venv', 'Scripts', exeName)
    : path.join(projectRoot, '.venv', 'bin', exeName)
}

export function resolvePackagedSidecarPath(options = {}) {
  const resourcesPath = options.resourcesPath ?? process.resourcesPath
  const platform = options.platform ?? process.platform
  const arch = options.arch ?? process.arch

  if (!resourcesPath) {
    throw new Error('Missing Electron resourcesPath for packaged sidecar resolution')
  }

  return path.join(
    resourcesPath,
    'sidecar',
    sidecarTargetTriple(platform, arch),
    'niamoto',
    sidecarExeName(platform)
  )
}

export async function resolveSidecarPath(options = {}) {
  const isPackaged = options.isPackaged ?? false
  const platform = options.platform ?? process.platform
  const projectRoot = options.projectRoot ?? DEFAULT_PROJECT_ROOT
  const resourcesPath = options.resourcesPath ?? process.resourcesPath
  const arch = options.arch ?? process.arch
  const execPath = options.execPath ?? process.execPath

  const devSidecar = resolveDevSidecarPath({ projectRoot, platform })
  if (!isPackaged && (await pathExists(devSidecar))) {
    return devSidecar
  }

  if (resourcesPath) {
    const packagedSidecar = resolvePackagedSidecarPath({
      resourcesPath,
      platform,
      arch,
    })
    if (await pathExists(packagedSidecar)) {
      return packagedSidecar
    }
  }

  if (await pathExists(devSidecar)) {
    return devSidecar
  }

  return path.join(path.dirname(execPath), sidecarExeName(platform))
}

export async function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()

    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      server.close((error) => {
        if (error) {
          reject(error)
          return
        }

        if (!address || typeof address === 'string') {
          reject(new Error('Failed to resolve an ephemeral API port'))
          return
        }

        resolve(address.port)
      })
    })
  })
}

export async function resolveDesktopApiPort(options = {}) {
  const hotReloadEnabled = options.hotReloadEnabled ?? false
  const env = options.env ?? process.env
  const findFreePortImpl = options.findFreePortImpl ?? findFreePort

  if (hotReloadEnabled) {
    const configuredPort = Number.parseInt(env.NIAMOTO_DESKTOP_API_PORT ?? '', 10)
    return Number.isFinite(configuredPort) ? configuredPort : DEV_API_PORT
  }

  return findFreePortImpl()
}

export function generateStartupToken(options = {}) {
  const randomBytesImpl = options.randomBytesImpl ?? randomBytes
  return Buffer.from(randomBytesImpl(32)).toString('hex')
}

export function buildSidecarEnvironment(options) {
  const env = { ...(options.env ?? process.env) }
  const nextEnv = {
    ...env,
    NIAMOTO_RUNTIME_MODE: 'desktop',
    NIAMOTO_DESKTOP_SHELL: 'electron',
    NIAMOTO_DESKTOP_AUTH_TOKEN: options.desktopAuthToken,
    NIAMOTO_STARTUP_SESSION: options.startupSession,
    NIAMOTO_STARTUP_LOG: options.startupLogPath,
    PYTHONUNBUFFERED: '1',
  }

  if (options.projectPath) {
    nextEnv.NIAMOTO_HOME = options.projectPath
    delete nextEnv.NIAMOTO_LOGS
  } else if (options.logDir) {
    nextEnv.NIAMOTO_LOGS = options.logDir
    delete nextEnv.NIAMOTO_HOME
  }

  return nextEnv
}

export function createSidecarSpawnOptions(options) {
  const platform = options.platform ?? process.platform

  return {
    detached: platform !== 'win32',
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    env: buildSidecarEnvironment(options),
  }
}

export function spawnSidecar(options) {
  const spawnImpl = options.spawnImpl ?? spawn
  const args = ['gui', '--port', String(options.port), '--no-browser', '--host', '127.0.0.1']

  return spawnImpl(
    options.sidecarPath,
    args,
    createSidecarSpawnOptions(options)
  )
}

export async function terminateChildProcess(childProcess, options = {}) {
  if (!childProcess?.pid) {
    return
  }

  const platform = options.platform ?? process.platform
  const execFileImpl = options.execFileImpl ?? execFileAsync
  const killImpl = options.killImpl ?? process.kill
  const delayImpl = options.delayImpl ?? delay

  if (platform === 'win32') {
    try {
      await execFileImpl('taskkill', ['/F', '/T', '/PID', String(childProcess.pid)])
    } catch {
      // Ignore shutdown cleanup failures.
    }
  } else {
    try {
      killImpl(-childProcess.pid, 'SIGTERM')
    } catch {
      // Ignore process-group cleanup failures.
    }

    await delayImpl(500)
  }

  try {
    childProcess.kill?.('SIGTERM')
  } catch {
    // Ignore direct child cleanup failures.
  }
}
