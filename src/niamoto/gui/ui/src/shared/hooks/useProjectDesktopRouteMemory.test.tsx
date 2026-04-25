// @vitest-environment jsdom

import { act, useLayoutEffect } from 'react'
import { createRoot } from 'react-dom/client'
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { buildProjectDesktopContextStorageKey } from '@/shared/desktop/projectDesktopContext'
import {
  resetProjectDesktopRouteMemoryForTests,
  useProjectDesktopRouteMemory,
} from './useProjectDesktopRouteMemory'

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

async function renderRouteMemoryProbe({
  initialEntry,
  storage,
  enabled = true,
}: {
  initialEntry: string
  storage: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
  enabled?: boolean
}) {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  const latestLocation: { current: string | null } = { current: null }

  function Probe() {
    useProjectDesktopRouteMemory({ enabled, storage })
    const location = useLocation()

    useLayoutEffect(() => {
      latestLocation.current = `${location.pathname}${location.search}${location.hash}`
    }, [location.hash, location.pathname, location.search])

    return null
  }

  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="*" element={<Probe />} />
        </Routes>
      </MemoryRouter>,
    )
    await Promise.resolve()
    await Promise.resolve()
  })

  return {
    get location() {
      return latestLocation.current
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

describe('useProjectDesktopRouteMemory', () => {
  beforeEach(() => {
    resetProjectDesktopRouteMemoryForTests()
    useCurrentProjectScope.mockReturnValue({
      projectScope: 'desktop:/tmp/project-a',
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('restores the stored project route from the startup route', async () => {
    const storage = createStorage({
      [buildProjectDesktopContextStorageKey('desktop:/tmp/project-a')]:
        JSON.stringify({
          lastRoute: {
            pathname: '/publish',
            search: '?panel=history',
            hash: '',
          },
          updatedAt: 100,
        }),
    })

    const harness = await renderRouteMemoryProbe({
      initialEntry: '/',
      storage,
    })

    expect(harness.location).toBe('/publish?panel=history')
    await harness.unmount()
  })

  it('does not override an explicit initial route', async () => {
    const storage = createStorage({
      [buildProjectDesktopContextStorageKey('desktop:/tmp/project-a')]:
        JSON.stringify({
          lastRoute: { pathname: '/publish', search: '', hash: '' },
          updatedAt: 100,
        }),
    })

    const harness = await renderRouteMemoryProbe({
      initialEntry: '/sources',
      storage,
    })

    expect(harness.location).toBe('/sources')
    expect(storage.setItem).toHaveBeenCalledWith(
      buildProjectDesktopContextStorageKey('desktop:/tmp/project-a'),
      expect.stringContaining('"pathname":"/sources"'),
    )
    await harness.unmount()
  })

  it('keeps route memory disabled outside desktop context', async () => {
    const storage = createStorage()

    const harness = await renderRouteMemoryProbe({
      initialEntry: '/groups',
      storage,
      enabled: false,
    })

    expect(harness.location).toBe('/groups')
    expect(storage.setItem).not.toHaveBeenCalled()
    await harness.unmount()
  })
})
