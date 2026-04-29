export type ResolvedCollectionsPreviewMode = 'off' | 'focused' | 'thumbnail'
export type CollectionsPreviewPreference = ResolvedCollectionsPreviewMode

const PREVIEW_PREFERENCE_STORAGE_KEY = 'niamoto.collectionsPreviewPreference'
const DEFAULT_PREVIEW_PREFERENCE: CollectionsPreviewPreference = 'focused'

export function normalizeCollectionsPreviewPreference(
  value?: string | null,
): CollectionsPreviewPreference {
  switch (value) {
    case 'off':
    case 'focused':
    case 'thumbnail':
      return value
    default:
      return DEFAULT_PREVIEW_PREFERENCE
  }
}

export function resolveCollectionsPreviewMode({
  preference,
  isDragging,
}: {
  preference: CollectionsPreviewPreference
  isDragging?: boolean
}): ResolvedCollectionsPreviewMode {
  if (isDragging) {
    return 'off'
  }

  return preference
}

export function shouldAutoRefreshCollectionsDetailPreview(
  preference: CollectionsPreviewPreference,
): boolean {
  return preference === 'thumbnail'
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
  storage: Pick<Storage, 'setItem'> | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
): void {
  if (!storage) {
    return
  }

  storage.setItem(PREVIEW_PREFERENCE_STORAGE_KEY, preference)
}
