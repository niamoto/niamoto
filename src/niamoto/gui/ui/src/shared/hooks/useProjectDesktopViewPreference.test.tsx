// @vitest-environment jsdom

import { act, useLayoutEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { buildProjectDesktopContextStorageKey } from '@/shared/desktop/projectDesktopContext'
import { useProjectDesktopViewPreference } from './useProjectDesktopViewPreference'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const useCurrentProjectScope = vi.hoisted(() => vi.fn())

vi.mock('./useCurrentProjectScope', () => ({
  useCurrentProjectScope,
}))

function createStorage(initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial))

  return {
    getItem: vi.fn((key: string) => values.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      values.set(key, value)
    }),
    removeItem: vi.fn((key: string) => {
      values.delete(key)
    }),
  }
}

async function renderPreferenceProbe({
  storage,
  overrideValue = null,
  enabled = true,
}: {
  storage: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
  overrideValue?: 'content' | 'api' | null
  enabled?: boolean
}) {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  const latest: {
    value: 'content' | 'api' | null
    setValue: ((value: 'content' | 'api') => void) | null
  } = {
    value: null,
    setValue: null,
  }

  function Probe() {
    const [value, setValue] = useProjectDesktopViewPreference({
      key: 'collections.activeTab',
      defaultValue: 'content',
      allowedValues: ['content', 'api'] as const,
      overrideValue,
      enabled,
      storage,
    })

    useLayoutEffect(() => {
      latest.value = value
      latest.setValue = setValue
    }, [setValue, value])

    return null
  }

  await act(async () => {
    root.render(<Probe />)
    await Promise.resolve()
  })

  return {
    get value() {
      return latest.value
    },
    setValue(value: 'content' | 'api') {
      latest.setValue?.(value)
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

describe('useProjectDesktopViewPreference', () => {
  beforeEach(() => {
    useCurrentProjectScope.mockReturnValue({
      projectScope: 'desktop:/tmp/project-a',
      desktopProjectScope: 'desktop:/tmp/project-a',
      fallbackProjectScope: null,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('hydrates a stored project preference', async () => {
    const storage = createStorage({
      [buildProjectDesktopContextStorageKey('desktop:/tmp/project-a')]:
        JSON.stringify({
          viewPreferences: { 'collections.activeTab': 'api' },
          updatedAt: 100,
        }),
    })

    const harness = await renderPreferenceProbe({ storage })

    expect(harness.value).toBe('api')
    await harness.unmount()
  })

  it('lets explicit overrides win over stored preferences', async () => {
    const storage = createStorage({
      [buildProjectDesktopContextStorageKey('desktop:/tmp/project-a')]:
        JSON.stringify({
          viewPreferences: { 'collections.activeTab': 'api' },
          updatedAt: 100,
        }),
    })

    const harness = await renderPreferenceProbe({
      storage,
      overrideValue: 'content',
    })

    expect(harness.value).toBe('content')
    expect(storage.setItem).toHaveBeenCalledWith(
      buildProjectDesktopContextStorageKey('desktop:/tmp/project-a'),
      expect.stringContaining('"collections.activeTab":"content"'),
    )
    await harness.unmount()
  })

  it('stores preference updates when enabled', async () => {
    const storage = createStorage()
    const harness = await renderPreferenceProbe({ storage })

    await act(async () => {
      harness.setValue('api')
    })

    expect(harness.value).toBe('api')
    expect(storage.setItem).toHaveBeenCalledWith(
      buildProjectDesktopContextStorageKey('desktop:/tmp/project-a'),
      expect.stringContaining('"collections.activeTab":"api"'),
    )
    await harness.unmount()
  })

  it('does not store preference updates when disabled', async () => {
    const storage = createStorage()
    const harness = await renderPreferenceProbe({
      storage,
      enabled: false,
    })

    await act(async () => {
      harness.setValue('api')
    })

    expect(harness.value).toBe('api')
    expect(storage.setItem).not.toHaveBeenCalled()
    await harness.unmount()
  })

  it('does not read or write fallback project preferences by default', async () => {
    useCurrentProjectScope.mockReturnValue({
      projectScope: 'project:Demo:unknown',
      desktopProjectScope: null,
      fallbackProjectScope: 'project:Demo:unknown',
    })
    const storage = createStorage({
      [buildProjectDesktopContextStorageKey('project:Demo:unknown')]:
        JSON.stringify({
          viewPreferences: { 'collections.activeTab': 'api' },
          updatedAt: 100,
        }),
    })

    const harness = await renderPreferenceProbe({ storage })

    expect(harness.value).toBe('content')
    expect(storage.getItem).not.toHaveBeenCalled()

    await act(async () => {
      harness.setValue('api')
    })

    expect(harness.value).toBe('api')
    expect(storage.setItem).not.toHaveBeenCalled()
    await harness.unmount()
  })
})
