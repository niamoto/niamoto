import assert from 'node:assert/strict'
import path from 'node:path'
import os from 'node:os'
import fs from 'node:fs/promises'
import test from 'node:test'

import {
  buildSidecarEnvironment,
  createSidecarSpawnOptions,
  DEV_API_PORT,
  generateStartupToken,
  resolveDesktopApiPort,
  resolveDevSidecarPath,
  resolvePackagedSidecarPath,
  resolveSidecarPath,
  sidecarTargetTriple,
  spawnSidecar,
  terminateChildProcess,
} from '../shell/sidecar.mjs'

test('sidecarTargetTriple maps supported desktop targets', () => {
  assert.equal(sidecarTargetTriple('darwin', 'arm64'), 'aarch64-apple-darwin')
  assert.equal(sidecarTargetTriple('darwin', 'x64'), 'x86_64-apple-darwin')
  assert.equal(sidecarTargetTriple('linux', 'x64'), 'x86_64-unknown-linux-gnu')
  assert.equal(sidecarTargetTriple('win32', 'x64'), 'x86_64-pc-windows-msvc')
})

test('resolvePackagedSidecarPath uses the documented shell-neutral resource layout', () => {
  const resolved = resolvePackagedSidecarPath({
    resourcesPath: '/Applications/Niamoto.app/Contents/Resources',
    platform: 'darwin',
    arch: 'arm64',
  })

  assert.equal(
    resolved,
    '/Applications/Niamoto.app/Contents/Resources/sidecar/aarch64-apple-darwin/niamoto/niamoto'
  )
})

test('resolveSidecarPath prefers the repository virtualenv in development', async () => {
  const projectRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'niamoto-electron-sidecar-'))
  const sidecarPath = resolveDevSidecarPath({ projectRoot, platform: 'darwin' })

  await fs.mkdir(path.dirname(sidecarPath), { recursive: true })
  await fs.writeFile(sidecarPath, '', 'utf8')

  const resolved = await resolveSidecarPath({
    isPackaged: false,
    projectRoot,
    platform: 'darwin',
    arch: 'arm64',
    resourcesPath: '/tmp/unused',
  })

  assert.equal(resolved, sidecarPath)
})

test('resolveSidecarPath falls back to packaged resources when present', async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'niamoto-electron-resources-'))
  const packagedPath = resolvePackagedSidecarPath({
    resourcesPath: tempRoot,
    platform: 'darwin',
    arch: 'arm64',
  })

  await fs.mkdir(path.dirname(packagedPath), { recursive: true })
  await fs.writeFile(packagedPath, '', 'utf8')

  const resolved = await resolveSidecarPath({
    isPackaged: true,
    projectRoot: '/tmp/missing-project-root',
    platform: 'darwin',
    arch: 'arm64',
    resourcesPath: tempRoot,
  })

  assert.equal(resolved, packagedPath)
})

test('resolveDesktopApiPort uses the fixed desktop dev port in hot reload mode', async () => {
  const port = await resolveDesktopApiPort({
    hotReloadEnabled: true,
    env: {},
  })

  assert.equal(port, DEV_API_PORT)
})

test('resolveDesktopApiPort honors NIAMOTO_DESKTOP_API_PORT in hot reload mode', async () => {
  const port = await resolveDesktopApiPort({
    hotReloadEnabled: true,
    env: { NIAMOTO_DESKTOP_API_PORT: '9042' },
  })

  assert.equal(port, 9042)
})

test('generateStartupToken returns a stable hexadecimal token with injected entropy', () => {
  const token = generateStartupToken({
    randomBytesImpl: (size) => Uint8Array.from({ length: size }, (_, index) => index),
  })

  assert.equal(token.length, 64)
  assert.match(token, /^[0-9a-f]+$/)
  assert.ok(token.startsWith('00010203'))
})

test('spawnSidecar forwards the expected command and desktop environment', () => {
  let command = null
  let args = null
  let options = null

  const child = spawnSidecar({
    sidecarPath: '/tmp/niamoto',
    port: 8080,
    projectPath: '/tmp/project',
    desktopAuthToken: 'secret',
    startupSession: 'desktop-startup-1',
    startupLogPath: '/tmp/startup.log',
    logDir: '/tmp/logs',
    env: { EXISTING_ENV: '1' },
    platform: 'darwin',
    spawnImpl: (nextCommand, nextArgs, nextOptions) => {
      command = nextCommand
      args = nextArgs
      options = nextOptions
      return {
        pid: 4242,
        stdout: null,
        stderr: null,
      }
    },
  })

  assert.equal(child.pid, 4242)
  assert.equal(command, '/tmp/niamoto')
  assert.deepEqual(args, ['gui', '--port', '8080', '--no-browser', '--host', '127.0.0.1'])
  assert.equal(options.detached, true)
  assert.equal(options.env.NIAMOTO_RUNTIME_MODE, 'desktop')
  assert.equal(options.env.NIAMOTO_DESKTOP_SHELL, 'electron')
  assert.equal(options.env.NIAMOTO_DESKTOP_AUTH_TOKEN, 'secret')
  assert.equal(options.env.NIAMOTO_HOME, '/tmp/project')
  assert.equal(options.env.EXISTING_ENV, '1')
})

test('buildSidecarEnvironment falls back to NIAMOTO_LOGS when no project is selected', () => {
  const env = buildSidecarEnvironment({
    env: {},
    desktopAuthToken: 'secret',
    startupSession: 'desktop-startup-2',
    startupLogPath: '/tmp/startup.log',
    logDir: '/tmp/logs',
  })

  assert.equal(env.NIAMOTO_LOGS, '/tmp/logs')
  assert.equal(env.NIAMOTO_HOME, undefined)
})

test('createSidecarSpawnOptions keeps Unix sidecars detached for process-group cleanup', () => {
  const options = createSidecarSpawnOptions({
    env: {},
    desktopAuthToken: 'secret',
    startupSession: 'desktop-startup-3',
    startupLogPath: '/tmp/startup.log',
    logDir: '/tmp/logs',
    platform: 'darwin',
  })

  assert.equal(options.detached, true)
  assert.deepEqual(options.stdio, ['ignore', 'pipe', 'pipe'])
})

test('terminateChildProcess uses process-group shutdown on Unix', async () => {
  const calls = []

  await terminateChildProcess(
    {
      pid: 987,
      kill: (signal) => calls.push(['child.kill', signal]),
    },
    {
      platform: 'darwin',
      killImpl: (pid, signal) => calls.push(['process.kill', pid, signal]),
      delayImpl: async () => {
        calls.push(['delay'])
      },
    }
  )

  assert.deepEqual(calls, [
    ['process.kill', -987, 'SIGTERM'],
    ['delay'],
    ['child.kill', 'SIGTERM'],
  ])
})
