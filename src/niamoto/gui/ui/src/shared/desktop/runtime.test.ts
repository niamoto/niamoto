import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  getBootstrappedRuntimeMode,
  getDesktopShell,
  isRuntimeModeState,
} from './runtime'

interface DocumentElementStub {
  getAttribute: (name: string) => string | null
  setAttribute: (name: string, value: string) => void
  removeAttribute: (name: string) => void
}

function createDocumentElementStub(): DocumentElementStub {
  const attributes = new Map<string, string>()

  return {
    getAttribute(name: string) {
      return attributes.get(name) ?? null
    },
    setAttribute(name: string, value: string) {
      attributes.set(name, value)
    },
    removeAttribute(name: string) {
      attributes.delete(name)
    },
  }
}

describe('desktop runtime helpers', () => {
  const documentElement = createDocumentElementStub()
  const windowStub: Record<string, unknown> = {}

  beforeEach(() => {
    vi.stubGlobal('document', {
      documentElement,
    })
    vi.stubGlobal('window', windowStub)
  })

  afterEach(() => {
    documentElement.removeAttribute('data-shell')
    documentElement.removeAttribute('data-runtime-mode')
    delete windowStub.__NIAMOTO_ELECTRON__
    delete windowStub.__TAURI__
    delete windowStub.__TAURI_INTERNALS__
    vi.unstubAllGlobals()
  })

  it('prefers the bootstrapped shell attribute when present', () => {
    documentElement.setAttribute('data-shell', 'electron')

    expect(getDesktopShell()).toBe('electron')
    expect(getBootstrappedRuntimeMode()).toEqual({
      mode: 'desktop',
      shell: 'electron',
      project: null,
      features: {
        project_switching: true,
      },
    })
  })

  it('detects tauri from injected globals when no bootstrap attribute exists', () => {
    windowStub.__TAURI_INTERNALS__ = {}

    expect(getDesktopShell()).toBe('tauri')
    expect(getBootstrappedRuntimeMode().mode).toBe('desktop')
  })

  it('falls back to web mode when no desktop shell is available', () => {
    expect(getDesktopShell()).toBeNull()
    expect(getBootstrappedRuntimeMode()).toEqual({
      mode: 'web',
      shell: null,
      project: null,
      features: {
        project_switching: false,
      },
    })
  })

  it('validates the expanded runtime payload contract', () => {
    expect(
      isRuntimeModeState({
        mode: 'desktop',
        shell: 'tauri',
        project: '/tmp/demo',
        features: {
          project_switching: true,
        },
      })
    ).toBe(true)

    expect(
      isRuntimeModeState({
        mode: 'desktop',
        shell: 'desktop',
        project: '/tmp/demo',
        features: {
          project_switching: true,
        },
      })
    ).toBe(false)
  })
})
