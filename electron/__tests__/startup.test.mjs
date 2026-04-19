import assert from 'node:assert/strict'
import os from 'node:os'
import path from 'node:path'
import fs from 'node:fs/promises'
import test from 'node:test'

import {
  healthProbeIsAuthenticated,
  probeHealth,
  resolveStartupUrl,
  startSidecarSession,
  waitForSidecarReady,
} from '../shell/startup.mjs'

test('healthProbeIsAuthenticated requires both success status and matching token', () => {
  assert.equal(healthProbeIsAuthenticated(200, 'secret', 'secret'), true)
  assert.equal(healthProbeIsAuthenticated(200, 'wrong', 'secret'), false)
  assert.equal(healthProbeIsAuthenticated(500, 'secret', 'secret'), false)
})

test('probeHealth only succeeds when the desktop probe token matches', async () => {
  const ok = await probeHealth({
    port: 8080,
    expectedToken: 'desktop-secret',
    fetchImpl: async () => ({
      status: 200,
      headers: {
        get(name) {
          return name === 'x-niamoto-desktop-token' ? 'desktop-secret' : null
        },
      },
    }),
  })

  const rejected = await probeHealth({
    port: 8080,
    expectedToken: 'desktop-secret',
    fetchImpl: async () => ({
      status: 200,
      headers: {
        get() {
          return 'wrong-secret'
        },
      },
    }),
  })

  assert.equal(ok, true)
  assert.equal(rejected, false)
})

test('waitForSidecarReady retries until the authenticated health probe succeeds', async () => {
  const attempts = []
  const result = await waitForSidecarReady({
    port: 8080,
    expectedToken: 'desktop-secret',
    timeoutMs: 1_000,
    pollIntervalMs: 100,
    fetchImpl: async () => {
      attempts.push('fetch')
      return {
        status: attempts.length >= 3 ? 200 : 503,
        headers: {
          get() {
            return attempts.length >= 3 ? 'desktop-secret' : null
          },
        },
      }
    },
    sleep: async () => {},
  })

  assert.equal(result.status, 'ready')
  assert.equal(result.attempts, 3)
})

test('waitForSidecarReady surfaces early child-process exit', async () => {
  const childProcess = { exitCode: 42, signalCode: null }
  const result = await waitForSidecarReady({
    port: 8080,
    expectedToken: 'desktop-secret',
    childProcess,
    timeoutMs: 1_000,
    pollIntervalMs: 100,
    fetchImpl: async () => {
      throw new Error('backend not ready yet')
    },
    sleep: async () => {},
  })

  assert.equal(result.status, 'exited')
  assert.equal(result.exitCode, 42)
})

test('resolveStartupUrl mirrors Tauri semantics for dev and packaged modes', () => {
  assert.equal(
    resolveStartupUrl({
      hotReloadEnabled: true,
      rendererUrl: 'http://127.0.0.1:5173',
      readyPort: 8080,
    }),
    'http://127.0.0.1:5173'
  )
  assert.equal(
    resolveStartupUrl({
      hotReloadEnabled: false,
      rendererUrl: 'http://127.0.0.1:5173',
      readyPort: 4123,
    }),
    'http://127.0.0.1:4123'
  )
})

test('startSidecarSession launches the sidecar with project-aware environment and returns the ready URL', async () => {
  const logDir = await fs.mkdtemp(path.join(os.tmpdir(), 'niamoto-electron-startup-'))
  const spawnCalls = []
  const childProcess = {
    pid: 5150,
    stdout: null,
    stderr: null,
    exitCode: null,
    signalCode: null,
  }

  const session = await startSidecarSession({
    hotReloadEnabled: true,
    rendererUrl: 'http://127.0.0.1:5173',
    logDir,
    projectPath: '/tmp/demo-project',
    isPackaged: false,
    platform: 'darwin',
    arch: 'arm64',
    projectRoot: '/tmp/project-root',
    env: { EXISTING_ENV: '1' },
    findFreePortImpl: async () => {
      throw new Error('hot reload mode should not request a dynamic port')
    },
    randomBytesImpl: () => Uint8Array.from({ length: 32 }, () => 7),
    spawnImpl: (command, args, options) => {
      spawnCalls.push({ command, args, options })
      return childProcess
    },
    fetchImpl: async () => ({
      status: 200,
      headers: {
        get(name) {
          return name === 'x-niamoto-desktop-token'
            ? '0707070707070707070707070707070707070707070707070707070707070707'
            : null
        },
      },
    }),
    sleep: async () => {},
  })

  assert.equal(session.port, 8080)
  assert.equal(session.readyUrl, 'http://127.0.0.1:5173')
  assert.match(session.startupSession, /^desktop-startup-/)
  assert.equal(spawnCalls.length, 1)
  assert.equal(spawnCalls[0].args[0], 'gui')
  assert.equal(spawnCalls[0].options.env.NIAMOTO_HOME, '/tmp/demo-project')
  assert.equal(spawnCalls[0].options.env.NIAMOTO_DESKTOP_SHELL, 'electron')
  assert.equal(spawnCalls[0].options.env.EXISTING_ENV, '1')
  assert.match(session.startupLogPath, /desktop-startup-.*\.log$/)
})

test('startSidecarSession fails with a recoverable timeout error when the sidecar never becomes ready', async () => {
  const logDir = await fs.mkdtemp(path.join(os.tmpdir(), 'niamoto-electron-timeout-'))
  const childProcess = {
    pid: 2121,
    stdout: null,
    stderr: null,
    exitCode: null,
    signalCode: null,
    kill() {},
  }
  const cleanupCalls = []

  await assert.rejects(
    startSidecarSession({
      hotReloadEnabled: false,
      logDir,
      isPackaged: true,
      platform: 'darwin',
      arch: 'arm64',
      resourcesPath: '/tmp/resources',
      execPath: '/tmp/Niamoto Electron.app/Contents/MacOS/Niamoto Electron',
      env: {},
      findFreePortImpl: async () => 4321,
      spawnImpl: () => childProcess,
      fetchImpl: async () => {
        throw new Error('still booting')
      },
      sleep: async () => {},
      timeoutMs: 1_000,
      startupTimeoutMs: 1_000,
      pollIntervalMs: 250,
      execFileImpl: async (...args) => {
        cleanupCalls.push(args)
      },
      killImpl: (...args) => {
        cleanupCalls.push(args)
      },
    }),
    /failed to become ready/i
  )

  assert.ok(cleanupCalls.length > 0)
})
