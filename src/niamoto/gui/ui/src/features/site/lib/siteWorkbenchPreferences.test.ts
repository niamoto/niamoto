import { describe, expect, it, vi } from 'vitest'

import {
  buildSiteWorkbenchPreferencesStorageKey,
  DEFAULT_SITE_WORKBENCH_PREFERENCES,
  normalizeSiteWorkbenchLayout,
  normalizeSiteWorkbenchPreviewDevice,
  normalizeSiteWorkbenchPreviewState,
  readStoredSiteWorkbenchPreferences,
  writeStoredSiteWorkbenchPreferences,
} from './siteWorkbenchPreferences'

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

describe('siteWorkbenchPreferences', () => {
  it('normalizes preview state and device safely', () => {
    expect(normalizeSiteWorkbenchPreviewState('open')).toBe('open')
    expect(normalizeSiteWorkbenchPreviewState('closed')).toBe('closed')
    expect(normalizeSiteWorkbenchPreviewState('weird')).toBe('unset')
    expect(normalizeSiteWorkbenchPreviewState(null)).toBe('unset')

    expect(normalizeSiteWorkbenchPreviewDevice('mobile')).toBe('mobile')
    expect(normalizeSiteWorkbenchPreviewDevice('tablet')).toBe('tablet')
    expect(normalizeSiteWorkbenchPreviewDevice('desktop')).toBe('desktop')
    expect(normalizeSiteWorkbenchPreviewDevice('watch')).toBe('desktop')
  })

  it('normalizes stored layouts conservatively', () => {
    expect(
      normalizeSiteWorkbenchLayout({
        tree: 15,
        editor: 50,
        preview: 35,
      }),
    ).toEqual({
      tree: 15,
      editor: 50,
      preview: 35,
    })

    expect(normalizeSiteWorkbenchLayout({ preview: 0 })).toBeNull()
    expect(normalizeSiteWorkbenchLayout({ preview: '35' })).toBeNull()
    expect(normalizeSiteWorkbenchLayout(null)).toBeNull()
  })

  it('reads stored preferences for a specific project scope', () => {
    const projectScope = 'desktop:/tmp/project-a'
    const storage = createStorage({
      [buildSiteWorkbenchPreferencesStorageKey(projectScope)]: JSON.stringify({
        previewState: 'closed',
        previewDevice: 'tablet',
        previewLayout: {
          tree: 12,
          editor: 53,
          preview: 35,
        },
      }),
    })

    expect(readStoredSiteWorkbenchPreferences(projectScope, storage)).toEqual({
      previewState: 'closed',
      previewDevice: 'tablet',
      previewLayout: {
        tree: 12,
        editor: 53,
        preview: 35,
      },
    })
  })

  it('clears malformed stored payloads and falls back to defaults', () => {
    const projectScope = 'desktop:/tmp/project-a'
    const storage = createStorage({
      [buildSiteWorkbenchPreferencesStorageKey(projectScope)]: '{bad json',
    })

    expect(readStoredSiteWorkbenchPreferences(projectScope, storage)).toEqual(
      DEFAULT_SITE_WORKBENCH_PREFERENCES,
    )
    expect(storage.removeItem).toHaveBeenCalledWith(
      buildSiteWorkbenchPreferencesStorageKey(projectScope),
    )
  })

  it('writes separate entries for separate project scopes', () => {
    const projectA = 'desktop:/tmp/project-a'
    const projectB = 'desktop:/tmp/project-b'
    const storage = createStorage()

    writeStoredSiteWorkbenchPreferences(
      projectA,
      {
        previewState: 'closed',
        previewDevice: 'desktop',
        previewLayout: null,
      },
      storage,
    )
    writeStoredSiteWorkbenchPreferences(
      projectB,
      {
        previewState: 'open',
        previewDevice: 'mobile',
        previewLayout: { tree: 20, editor: 45, preview: 35 },
      },
      storage,
    )

    expect(storage.setItem).toHaveBeenCalledTimes(2)
    expect(storage.setItem).toHaveBeenNthCalledWith(
      1,
      buildSiteWorkbenchPreferencesStorageKey(projectA),
      JSON.stringify({ previewState: 'closed' }),
    )
    expect(storage.setItem).toHaveBeenNthCalledWith(
      2,
      buildSiteWorkbenchPreferencesStorageKey(projectB),
      JSON.stringify({
        previewState: 'open',
        previewDevice: 'mobile',
        previewLayout: { tree: 20, editor: 45, preview: 35 },
      }),
    )
  })

  it('removes the storage entry when preferences are back to defaults', () => {
    const projectScope = 'desktop:/tmp/project-a'
    const storage = createStorage()

    writeStoredSiteWorkbenchPreferences(
      projectScope,
      DEFAULT_SITE_WORKBENCH_PREFERENCES,
      storage,
    )

    expect(storage.removeItem).toHaveBeenCalledWith(
      buildSiteWorkbenchPreferencesStorageKey(projectScope),
    )
    expect(storage.setItem).not.toHaveBeenCalled()
  })
})
