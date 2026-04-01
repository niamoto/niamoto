/**
 * generateFooter - One-shot footer generation from the unified tree
 *
 * Computes a FooterSection[] from the page/collection structure.
 * Not a live mode — the result is written to editedFooterNavigation
 * and can be manually edited afterwards.
 */

import type { FooterSection } from '@/shared/hooks/useSiteConfig'
import type { SiteSettings } from '@/shared/hooks/useSiteConfig'
import type { UnifiedTreeItem } from '../hooks/useUnifiedSiteTree'

/**
 * Generate footer sections from the unified site tree.
 *
 * Creates columns:
 * - "Navigation" → visible root pages (except homepage)
 * - "Collections" → visible collections (only if any exist)
 * - Copyright line derived from site title
 */
export function generateFooterFromTree(
  tree: UnifiedTreeItem[],
  siteSettings: SiteSettings,
): FooterSection[] {
  const visibleRoots = tree.filter(item => item.visible)

  // Navigation column: visible pages (skip homepage)
  const pageLinks = visibleRoots
    .filter(item => item.type === 'page' && item.url !== '/index.html')
    .map(item => ({
      text: typeof item.label === 'string' ? item.label : Object.values(item.label)[0] as string || item.pageRef || '',
      url: item.url || '',
      external: false,
    }))

  // Collections column: visible collections
  const collectionLinks = visibleRoots
    .filter(item => item.type === 'collection')
    .map(item => ({
      text: typeof item.label === 'string' ? item.label : Object.values(item.label)[0] as string || item.collectionRef || '',
      url: item.url || '',
      external: false,
    }))

  // Also check children for collections nested under pages
  for (const root of visibleRoots) {
    for (const child of root.children) {
      if (child.type === 'collection' && child.visible) {
        collectionLinks.push({
          text: typeof child.label === 'string' ? child.label : Object.values(child.label)[0] as string || child.collectionRef || '',
          url: child.url || '',
          external: false,
        })
      }
    }
  }

  const sections: FooterSection[] = []

  if (pageLinks.length > 0) {
    sections.push({
      title: 'Navigation',
      links: pageLinks,
    })
  }

  if (collectionLinks.length > 0) {
    sections.push({
      title: 'Collections',
      links: collectionLinks,
    })
  }

  // Project info column
  const year = new Date().getFullYear()
  sections.push({
    title: siteSettings.title || 'Project',
    links: [
      {
        text: `© ${year} ${siteSettings.title || ''}`.trim(),
        url: '/index.html',
        external: false,
      },
    ],
  })

  return sections
}
