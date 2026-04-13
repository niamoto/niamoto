export type CollectionsPreviewPreference = 'auto' | 'off' | 'focused' | 'thumbnail'
export type ResolvedCollectionsPreviewMode = 'off' | 'focused' | 'thumbnail'
export type CollectionsPerformanceTier = 'low' | 'standard'

const PREVIEW_PREFERENCE_STORAGE_KEY = 'niamoto.collectionsPreviewPreference'

export interface CollectionsPreviewContext {
  widgetCount: number
  hardwareConcurrency?: number | null
}

export function normalizeCollectionsPreviewPreference(
  value?: string | null,
): CollectionsPreviewPreference {
  switch (value) {
    case 'off':
    case 'focused':
    case 'thumbnail':
    case 'auto':
      return value
    default:
      return 'auto'
  }
}

export function getCollectionsHardwareConcurrency(
  nav: Pick<Navigator, 'hardwareConcurrency'> | undefined = typeof navigator !== 'undefined'
    ? navigator
    : undefined,
): number | null {
  const value = nav?.hardwareConcurrency
  if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) {
    return null
  }

  return Math.round(value)
}

export function classifyCollectionsPerformanceTier({
  widgetCount,
  hardwareConcurrency,
}: CollectionsPreviewContext): CollectionsPerformanceTier {
  const cpu = hardwareConcurrency ?? null

  if (cpu !== null && cpu <= 4) {
    return 'low'
  }

  if (cpu !== null && cpu <= 6 && widgetCount >= 8) {
    return 'low'
  }

  if (widgetCount >= 18) {
    return 'low'
  }

  return 'standard'
}

export function resolveDefaultCollectionsPreviewMode(
  context: CollectionsPreviewContext,
): ResolvedCollectionsPreviewMode {
  const tier = classifyCollectionsPerformanceTier(context)

  if (tier === 'low') {
    return 'focused'
  }

  if (context.widgetCount >= 12) {
    return 'focused'
  }

  return 'thumbnail'
}

export function resolveCollectionsPreviewMode({
  preference,
  widgetCount,
  hardwareConcurrency,
  isDragging,
}: CollectionsPreviewContext & {
  preference: CollectionsPreviewPreference
  isDragging?: boolean
}): ResolvedCollectionsPreviewMode {
  if (isDragging) {
    return 'off'
  }

  if (preference === 'auto') {
    return resolveDefaultCollectionsPreviewMode({
      widgetCount,
      hardwareConcurrency,
    })
  }

  return preference
}

export function shouldAutoRefreshCollectionsDetailPreview(
  context: CollectionsPreviewContext & {
    preference: CollectionsPreviewPreference
  },
): boolean {
  const resolvedMode = resolveCollectionsPreviewMode({
    ...context,
    isDragging: false,
  })

  if (resolvedMode === 'off' || resolvedMode === 'focused') {
    return false
  }

  return classifyCollectionsPerformanceTier(context) === 'standard'
}

export function readStoredCollectionsPreviewPreference(
  storage: Pick<Storage, 'getItem'> | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
): CollectionsPreviewPreference {
  return normalizeCollectionsPreviewPreference(
    storage?.getItem(PREVIEW_PREFERENCE_STORAGE_KEY),
  )
}

export function writeStoredCollectionsPreviewPreference(
  preference: CollectionsPreviewPreference,
  storage: Pick<Storage, 'setItem' | 'removeItem'> | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
): void {
  if (!storage) {
    return
  }

  if (preference === 'auto') {
    storage.removeItem(PREVIEW_PREFERENCE_STORAGE_KEY)
    return
  }

  storage.setItem(PREVIEW_PREFERENCE_STORAGE_KEY, preference)
}
