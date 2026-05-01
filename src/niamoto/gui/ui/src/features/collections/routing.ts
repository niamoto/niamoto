import type { CollectionsSelection } from './components/CollectionsTree'

export const COLLECTION_TABS = [
  'sources',
  'content',
  'index',
  'api',
  'standards',
] as const

export type CollectionTab = (typeof COLLECTION_TABS)[number]

interface BuildCollectionPathOptions {
  defaultTab?: CollectionTab | null
}

export function selectionFromPath(pathname: string): CollectionsSelection {
  if (pathname === '/groups/api-settings') {
    return { type: 'api-settings' }
  }

  if (pathname === '/groups/review') {
    return { type: 'review' }
  }

  const match = pathname.match(/^\/groups\/(.+)$/)
  if (match) {
    return { type: 'collection', name: decodeURIComponent(match[1]) }
  }

  return { type: 'overview' }
}

export function normalizeCollectionTab(
  value: string | null | undefined
): CollectionTab | undefined {
  if (!value) {
    return undefined
  }

  return COLLECTION_TABS.includes(value as CollectionTab)
    ? (value as CollectionTab)
    : undefined
}

export function buildCollectionsPath(
  selection: CollectionsSelection,
  tab?: string,
  options: BuildCollectionPathOptions = {},
): string {
  const normalizedTab = normalizeCollectionTab(tab)

  if (selection.type === 'overview') {
    return '/groups'
  }

  if (selection.type === 'api-settings') {
    return '/groups/api-settings'
  }

  if (selection.type === 'review') {
    return '/groups/review'
  }

  const basePath = `/groups/${encodeURIComponent(selection.name)}`
  if (!normalizedTab || shouldOmitCollectionTab(normalizedTab, options.defaultTab)) {
    return basePath
  }

  return `${basePath}?tab=${normalizedTab}`
}

export function buildCollectionTabPath(
  selection: CollectionsSelection,
  tab: string,
  currentSearch = '',
  options: BuildCollectionPathOptions = {},
): string {
  if (selection.type !== 'collection') {
    return buildCollectionsPath(selection, tab, options)
  }

  const normalizedTab = normalizeCollectionTab(tab)
  const searchParams = new URLSearchParams(currentSearch)

  if (!normalizedTab || shouldOmitCollectionTab(normalizedTab, options.defaultTab)) {
    searchParams.delete('tab')
  } else {
    searchParams.set('tab', normalizedTab)
  }

  const search = searchParams.toString()
  return `${buildCollectionsPath(selection)}${search ? `?${search}` : ''}`
}

function shouldOmitCollectionTab(
  tab: CollectionTab,
  defaultTab?: CollectionTab | null,
) {
  const effectiveDefaultTab = defaultTab ?? 'content'
  return tab === 'content' && effectiveDefaultTab === 'content'
}
