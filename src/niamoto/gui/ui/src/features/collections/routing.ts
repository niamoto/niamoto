import type { CollectionsSelection } from './components/CollectionsTree'

export const COLLECTION_TABS = ['sources', 'content', 'index', 'api'] as const

export type CollectionTab = (typeof COLLECTION_TABS)[number]

export function selectionFromPath(pathname: string): CollectionsSelection {
  if (pathname === '/groups/api-settings') {
    return { type: 'api-settings' }
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
  tab?: string
): string {
  const normalizedTab = normalizeCollectionTab(tab)

  if (selection.type === 'overview') {
    return '/groups'
  }

  if (selection.type === 'api-settings') {
    return '/groups/api-settings'
  }

  const basePath = `/groups/${encodeURIComponent(selection.name)}`
  if (!normalizedTab || normalizedTab === 'content') {
    return basePath
  }

  return `${basePath}?tab=${normalizedTab}`
}

export function buildCollectionTabPath(
  selection: CollectionsSelection,
  tab: string,
  currentSearch = ''
): string {
  if (selection.type !== 'collection') {
    return buildCollectionsPath(selection, tab)
  }

  const normalizedTab = normalizeCollectionTab(tab)
  const searchParams = new URLSearchParams(currentSearch)

  if (!normalizedTab || normalizedTab === 'content') {
    searchParams.delete('tab')
  } else {
    searchParams.set('tab', normalizedTab)
  }

  const search = searchParams.toString()
  return `${buildCollectionsPath(selection)}${search ? `?${search}` : ''}`
}
