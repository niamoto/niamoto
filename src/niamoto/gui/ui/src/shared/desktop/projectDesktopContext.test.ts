import { describe, expect, it, vi } from 'vitest'

import {
  buildProjectDesktopContextStorageKey,
  DEFAULT_PROJECT_DESKTOP_CONTEXT,
  isRestorableProjectRoute,
  normalizeProjectDesktopRoute,
  readStoredProjectDesktopContext,
  readStoredProjectDesktopViewPreference,
  serializeProjectDesktopRoute,
  writeStoredProjectDesktopContext,
  writeStoredProjectDesktopRoute,
  writeStoredProjectDesktopViewPreference,
} from './projectDesktopContext'

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

describe('projectDesktopContext', () => {
  it('accepts only known app routes as restorable routes', () => {
    expect(isRestorableProjectRoute('/')).toBe(true)
    expect(isRestorableProjectRoute('/sources')).toBe(true)
    expect(isRestorableProjectRoute('/groups/plots_hierarchy')).toBe(true)
    expect(isRestorableProjectRoute('/site/pages')).toBe(true)
    expect(isRestorableProjectRoute('/publish')).toBe(true)
    expect(isRestorableProjectRoute('/tools/settings')).toBe(true)

    expect(isRestorableProjectRoute('https://example.com')).toBe(false)
    expect(isRestorableProjectRoute('//example.com')).toBe(false)
    expect(isRestorableProjectRoute('/unknown')).toBe(false)
    expect(isRestorableProjectRoute('/site')).toBe(false)
    expect(isRestorableProjectRoute('/publish/history')).toBe(false)
    expect(isRestorableProjectRoute('/tools/settings/debug')).toBe(false)
  })

  it('normalizes and serializes a safe route', () => {
    const route = normalizeProjectDesktopRoute({
      pathname: '/publish',
      search: '?panel=history',
      hash: '#latest',
    })

    expect(route).toEqual({
      pathname: '/publish',
      search: '?panel=history',
      hash: '#latest',
    })
    expect(route ? serializeProjectDesktopRoute(route) : null).toBe(
      '/publish?panel=history#latest',
    )
  })

  it('rejects malformed route segments', () => {
    expect(
      normalizeProjectDesktopRoute({
        pathname: '/publish?panel=history',
        search: '',
        hash: '',
      }),
    ).toBeNull()
    expect(
      normalizeProjectDesktopRoute({
        pathname: '/publish',
        search: 'panel=history',
        hash: '',
      }),
    ).toBeNull()
    expect(
      normalizeProjectDesktopRoute({
        pathname: '/publish',
        search: '',
        hash: 'latest',
      }),
    ).toBeNull()
  })

  it('reads separate context entries for separate project scopes', () => {
    const projectA = 'desktop:/tmp/project-a'
    const projectB = 'desktop:/tmp/project-b'
    const storage = createStorage({
      [buildProjectDesktopContextStorageKey(projectA)]: JSON.stringify({
        lastRoute: { pathname: '/sources', search: '', hash: '' },
        updatedAt: 100,
      }),
      [buildProjectDesktopContextStorageKey(projectB)]: JSON.stringify({
        lastRoute: { pathname: '/site/pages', search: '', hash: '' },
        updatedAt: 200,
      }),
    })

    expect(readStoredProjectDesktopContext(projectA, storage)).toEqual({
      lastRoute: { pathname: '/sources', search: '', hash: '' },
      viewPreferences: {},
      updatedAt: 100,
    })
    expect(readStoredProjectDesktopContext(projectB, storage)).toEqual({
      lastRoute: { pathname: '/site/pages', search: '', hash: '' },
      viewPreferences: {},
      updatedAt: 200,
    })
  })

  it('clears malformed stored payloads and falls back to defaults', () => {
    const projectScope = 'desktop:/tmp/project-a'
    const storage = createStorage({
      [buildProjectDesktopContextStorageKey(projectScope)]: '{bad json',
    })

    expect(readStoredProjectDesktopContext(projectScope, storage)).toEqual(
      DEFAULT_PROJECT_DESKTOP_CONTEXT,
    )
    expect(storage.removeItem).toHaveBeenCalledWith(
      buildProjectDesktopContextStorageKey(projectScope),
    )
  })

  it('removes the storage entry when no valid context data remains', () => {
    const projectScope = 'desktop:/tmp/project-a'
    const storage = createStorage()

    writeStoredProjectDesktopContext(
      projectScope,
      {
        lastRoute: { pathname: '/unknown', search: '', hash: '' },
        viewPreferences: {},
        updatedAt: 100,
      },
      storage,
    )

    expect(storage.removeItem).toHaveBeenCalledWith(
      buildProjectDesktopContextStorageKey(projectScope),
    )
    expect(storage.setItem).not.toHaveBeenCalled()
  })

  it('writes the last route with a timestamp', () => {
    const projectScope = 'desktop:/tmp/project-a'
    const storage = createStorage()

    writeStoredProjectDesktopRoute(
      projectScope,
      { pathname: '/groups', search: '', hash: '' },
      storage,
      123,
    )

    expect(storage.setItem).toHaveBeenCalledWith(
      buildProjectDesktopContextStorageKey(projectScope),
      JSON.stringify({
        lastRoute: { pathname: '/groups', search: '', hash: '' },
        updatedAt: 123,
      }),
    )
  })

  it('reads and writes view preferences without mixing project scopes', () => {
    const projectA = 'desktop:/tmp/project-a'
    const projectB = 'desktop:/tmp/project-b'
    const storage = createStorage()

    writeStoredProjectDesktopViewPreference(
      projectA,
      'collections.activeTab',
      'api',
      ['sources', 'content', 'index', 'api'],
      storage,
      123,
    )
    writeStoredProjectDesktopViewPreference(
      projectB,
      'collections.activeTab',
      'index',
      ['sources', 'content', 'index', 'api'],
      storage,
      456,
    )

    expect(
      readStoredProjectDesktopViewPreference(
        projectA,
        'collections.activeTab',
        ['sources', 'content', 'index', 'api'],
        storage,
      ),
    ).toBe('api')
    expect(
      readStoredProjectDesktopViewPreference(
        projectB,
        'collections.activeTab',
        ['sources', 'content', 'index', 'api'],
        storage,
      ),
    ).toBe('index')
  })

  it('preserves view preferences when writing the last route', () => {
    const projectScope = 'desktop:/tmp/project-a'
    const storage = createStorage()

    writeStoredProjectDesktopViewPreference(
      projectScope,
      'publish.compactPanel',
      'preview',
      ['actions', 'preview'],
      storage,
      100,
    )
    writeStoredProjectDesktopRoute(
      projectScope,
      { pathname: '/publish', search: '', hash: '' },
      storage,
      200,
    )

    expect(readStoredProjectDesktopContext(projectScope, storage)).toEqual({
      lastRoute: { pathname: '/publish', search: '', hash: '' },
      viewPreferences: { 'publish.compactPanel': 'preview' },
      updatedAt: 200,
    })
  })
})
