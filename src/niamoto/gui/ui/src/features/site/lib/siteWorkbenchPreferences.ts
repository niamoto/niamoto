import type { DeviceSize } from '@/components/ui/preview-frame'

const SITE_WORKBENCH_STORAGE_KEY_PREFIX = 'niamoto.siteWorkbench'

export type SiteWorkbenchPreviewState = 'unset' | 'open' | 'closed'
export type SiteWorkbenchLayout = Record<string, number>

export interface SiteWorkbenchPreferences {
  previewState: SiteWorkbenchPreviewState
  previewDevice: DeviceSize
  previewLayout: SiteWorkbenchLayout | null
}

interface StoredSiteWorkbenchPreferences {
  previewState?: Exclude<SiteWorkbenchPreviewState, 'unset'>
  previewDevice?: DeviceSize
  previewLayout?: SiteWorkbenchLayout
}

export const DEFAULT_SITE_WORKBENCH_PREFERENCES: SiteWorkbenchPreferences = {
  previewState: 'unset',
  previewDevice: 'desktop',
  previewLayout: null,
}

export function buildSiteWorkbenchPreferencesStorageKey(
  projectScope: string,
): string {
  return `${SITE_WORKBENCH_STORAGE_KEY_PREFIX}:${encodeURIComponent(projectScope)}`
}

export function normalizeSiteWorkbenchPreviewState(
  value?: string | null,
): SiteWorkbenchPreviewState {
  switch (value) {
    case 'open':
    case 'closed':
      return value
    default:
      return 'unset'
  }
}

export function normalizeSiteWorkbenchPreviewDevice(
  value?: string | null,
): DeviceSize {
  switch (value) {
    case 'mobile':
    case 'tablet':
    case 'desktop':
      return value
    default:
      return 'desktop'
  }
}

export function normalizeSiteWorkbenchLayout(
  value: unknown,
): SiteWorkbenchLayout | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return null
  }

  const entries = Object.entries(value).filter(
    ([key, size]) =>
      key.length > 0 &&
      typeof size === 'number' &&
      Number.isFinite(size) &&
      size > 0 &&
      size <= 100,
  )

  if (entries.length === 0) {
    return null
  }

  return Object.fromEntries(entries)
}

function sanitizeStoredSiteWorkbenchPreferences(
  preferences: SiteWorkbenchPreferences,
): StoredSiteWorkbenchPreferences {
  const stored: StoredSiteWorkbenchPreferences = {}

  if (preferences.previewState !== 'unset') {
    stored.previewState = preferences.previewState
  }

  if (preferences.previewDevice !== 'desktop') {
    stored.previewDevice = preferences.previewDevice
  }

  if (preferences.previewLayout) {
    stored.previewLayout = preferences.previewLayout
  }

  return stored
}

export function readStoredSiteWorkbenchPreferences(
  projectScope: string | null,
  storage:
    | Pick<Storage, 'getItem' | 'removeItem'>
    | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
): SiteWorkbenchPreferences {
  if (!projectScope || !storage) {
    return DEFAULT_SITE_WORKBENCH_PREFERENCES
  }

  const storageKey = buildSiteWorkbenchPreferencesStorageKey(projectScope)

  try {
    const raw = storage.getItem(storageKey)
    if (!raw) {
      return DEFAULT_SITE_WORKBENCH_PREFERENCES
    }

    const parsed = JSON.parse(raw) as StoredSiteWorkbenchPreferences
    return {
      previewState: normalizeSiteWorkbenchPreviewState(parsed.previewState),
      previewDevice: normalizeSiteWorkbenchPreviewDevice(parsed.previewDevice),
      previewLayout: normalizeSiteWorkbenchLayout(parsed.previewLayout),
    }
  } catch {
    storage.removeItem(storageKey)
    return DEFAULT_SITE_WORKBENCH_PREFERENCES
  }
}

export function writeStoredSiteWorkbenchPreferences(
  projectScope: string | null,
  preferences: SiteWorkbenchPreferences,
  storage:
    | Pick<Storage, 'setItem' | 'removeItem'>
    | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
): void {
  if (!projectScope || !storage) {
    return
  }

  const storageKey = buildSiteWorkbenchPreferencesStorageKey(projectScope)
  const stored = sanitizeStoredSiteWorkbenchPreferences(preferences)

  if (Object.keys(stored).length === 0) {
    storage.removeItem(storageKey)
    return
  }

  storage.setItem(storageKey, JSON.stringify(stored))
}
