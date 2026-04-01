/**
 * useUnifiedSiteTree - Merge/decompose hook for the unified site tree
 *
 * Phase B: read-only projection from navigation[] + static_pages[] + groups[]
 * Phase C: becomes the source of truth, with decompose for API save
 *
 * Architecture (D1):
 *   buildUnifiedTree(navigation, staticPages, groups) → UnifiedTreeItem[]
 *   decomposeUnifiedTree(tree, allPages) → { navigation, staticPages }
 */

import type { LocalizedString } from '@/components/ui/localized-input'
import type {
  NavigationItem,
  StaticPage,
  GroupInfo,
} from '@/shared/hooks/useSiteConfig'

// =============================================================================
// TYPES
// =============================================================================

export interface UnifiedTreeItem {
  id: string
  type: 'page' | 'collection' | 'external-link'
  label: LocalizedString
  visible: boolean
  pageRef?: string          // StaticPage.name (type 'page')
  collectionRef?: string    // GroupInfo.name (type 'collection')
  url?: string              // URL for external links or page output
  template?: string         // page template
  hasIndex?: boolean        // collection with index_output_pattern
  children: UnifiedTreeItem[]
}

// =============================================================================
// ID GENERATION
// =============================================================================

let nextId = 1

function generateId(prefix: string): string {
  return `${prefix}-${nextId++}`
}

/** Reset ID counter (for testing) */
export function resetIdCounter(): void {
  nextId = 1
}

// =============================================================================
// BUILD: navigation[] + static_pages[] + groups[] → UnifiedTreeItem[]
// =============================================================================

/**
 * Match a navigation URL to a static page.
 * Pages are matched by their output_file (with leading slash normalization).
 */
function findPageByUrl(url: string | undefined, pages: StaticPage[]): StaticPage | null {
  if (!url) return null
  const normalized = url.replace(/^\//, '')
  return pages.find(p => p.output_file === normalized || p.output_file === url) ?? null
}

/**
 * Match a navigation URL to a group index page.
 * Groups are matched by their index_output_pattern.
 */
function findGroupByUrl(url: string | undefined, groups: GroupInfo[]): GroupInfo | null {
  if (!url) return null
  const normalized = url.replace(/^\//, '')
  return groups.find(g => {
    if (!g.index_output_pattern) return false
    const pattern = g.index_output_pattern.replace(/^\//, '')
    return pattern === normalized
  }) ?? null
}

/**
 * Convert a NavigationItem into a UnifiedTreeItem, recursively processing children.
 * Tracks which pages and groups have been matched to avoid duplicates.
 */
function navItemToTreeItem(
  item: NavigationItem,
  pages: StaticPage[],
  groups: GroupInfo[],
  matchedPages: Set<string>,
  matchedGroups: Set<string>,
): UnifiedTreeItem {
  // Try to match with a static page
  const page = findPageByUrl(item.url, pages)
  if (page) {
    matchedPages.add(page.name)
    return {
      id: generateId('page'),
      type: 'page',
      label: item.text,
      visible: true,
      pageRef: page.name,
      url: item.url,
      template: page.template,
      children: (item.children ?? []).map(child =>
        navItemToTreeItem(child, pages, groups, matchedPages, matchedGroups)
      ),
    }
  }

  // Try to match with a group index
  const group = findGroupByUrl(item.url, groups)
  if (group) {
    matchedGroups.add(group.name)
    return {
      id: generateId('collection'),
      type: 'collection',
      label: item.text,
      visible: true,
      collectionRef: group.name,
      url: item.url,
      hasIndex: !!group.index_output_pattern,
      children: (item.children ?? []).map(child =>
        navItemToTreeItem(child, pages, groups, matchedPages, matchedGroups)
      ),
    }
  }

  // No match → external link (or a nav item pointing to an unknown URL)
  return {
    id: generateId('link'),
    type: 'external-link',
    label: item.text,
    visible: true,
    url: item.url,
    children: (item.children ?? []).map(child =>
      navItemToTreeItem(child, pages, groups, matchedPages, matchedGroups)
    ),
  }
}

/**
 * Build the unified tree from API data.
 *
 * Algorithm:
 * 1. Process navigation[] items in order → create tree items, matching pages/groups by URL
 * 2. Append orphan pages (in static_pages but not in navigation) as visible: false
 * 3. Append unreferenced groups as visible: false
 */
export function buildUnifiedTree(
  navigation: NavigationItem[],
  staticPages: StaticPage[],
  groups: GroupInfo[],
): UnifiedTreeItem[] {
  const matchedPages = new Set<string>()
  const matchedGroups = new Set<string>()

  // 1. Navigation items → tree items (preserving order and nesting)
  const menuItems = navigation.map(item =>
    navItemToTreeItem(item, staticPages, groups, matchedPages, matchedGroups)
  )

  // 2. Orphan pages (exist but not in navigation)
  const orphanPages: UnifiedTreeItem[] = staticPages
    .filter(page => !matchedPages.has(page.name))
    .map(page => ({
      id: generateId('page'),
      type: 'page' as const,
      label: page.name as LocalizedString,
      visible: false,
      pageRef: page.name,
      url: `/${page.output_file}`,
      template: page.template,
      children: [],
    }))

  // 3. Unreferenced groups
  const orphanGroups: UnifiedTreeItem[] = groups
    .filter(group => !matchedGroups.has(group.name))
    .map(group => ({
      id: generateId('collection'),
      type: 'collection' as const,
      label: group.name as LocalizedString,
      visible: false,
      collectionRef: group.name,
      url: group.index_output_pattern ? `/${group.index_output_pattern}` : undefined,
      hasIndex: !!group.index_output_pattern,
      children: [],
    }))

  return [...menuItems, ...orphanPages, ...orphanGroups]
}

// =============================================================================
// DECOMPOSE: UnifiedTreeItem[] → { navigation[], staticPages[] }
// =============================================================================

/**
 * Convert a UnifiedTreeItem back to a NavigationItem.
 * Only visible items (and their children) become navigation items.
 */
function treeItemToNavItem(item: UnifiedTreeItem): NavigationItem {
  const navItem: NavigationItem = {
    text: item.label,
    url: item.url,
  }
  const visibleChildren = item.children.filter(c => c.visible)
  if (visibleChildren.length > 0) {
    navItem.children = visibleChildren.map(treeItemToNavItem)
  }
  return navItem
}

/**
 * Collect all page refs from the tree (in tree order), for reconstructing static_pages[].
 */
function collectPageRefs(items: UnifiedTreeItem[]): string[] {
  const refs: string[] = []
  for (const item of items) {
    if (item.type === 'page' && item.pageRef) {
      refs.push(item.pageRef)
    }
    refs.push(...collectPageRefs(item.children))
  }
  return refs
}

/**
 * Decompose the unified tree back into API-compatible structures.
 *
 * @param tree - The unified tree items
 * @param allPages - The full list of StaticPage objects (needed to preserve page data)
 * @returns navigation[] (from visible root items) and staticPages[] (in tree order)
 */
export function decomposeUnifiedTree(
  tree: UnifiedTreeItem[],
  allPages: StaticPage[],
): { navigation: NavigationItem[]; staticPages: StaticPage[] } {
  // Navigation: only visible root items
  const navigation = tree
    .filter(item => item.visible)
    .map(treeItemToNavItem)

  // Static pages: all pages in tree order (visible or not)
  const pageRefOrder = collectPageRefs(tree)
  const pageMap = new Map(allPages.map(p => [p.name, p]))

  // Pages in tree order first, then any remaining pages not in tree
  const orderedPages: StaticPage[] = []
  const seen = new Set<string>()

  for (const ref of pageRefOrder) {
    const page = pageMap.get(ref)
    if (page && !seen.has(ref)) {
      orderedPages.push(page)
      seen.add(ref)
    }
  }

  // Append any pages not referenced in the tree (shouldn't happen, but safety)
  for (const page of allPages) {
    if (!seen.has(page.name)) {
      orderedPages.push(page)
    }
  }

  return { navigation, staticPages: orderedPages }
}
