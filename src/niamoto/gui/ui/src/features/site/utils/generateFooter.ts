/**
 * generateFooter - One-shot footer generation from the unified tree
 *
 * Computes a FooterSection[] from the page/collection structure.
 * Not a live mode — the result is written to editedFooterNavigation
 * and can be manually edited afterwards.
 *
 * Section titles use LocalizedString (fr/en) to avoid hardcoding
 * English into persisted config.
 */

import type { FooterSection } from '@/shared/hooks/useSiteConfig'
import type { SiteSettings } from '@/shared/hooks/useSiteConfig'
import type { UnifiedTreeItem } from '../hooks/useUnifiedSiteTree'

function getLabel(item: UnifiedTreeItem): string {
  if (typeof item.label === 'string') return item.label
  if (typeof item.label === 'object' && item.label !== null) {
    return (Object.values(item.label)[0] as string) || item.pageRef || item.collectionRef || ''
  }
  return item.pageRef || item.collectionRef || ''
}

/**
 * Generate footer sections from the unified site tree.
 * Uses localized titles so the footer renders correctly in both languages.
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
      text: getLabel(item),
      url: item.url || '',
      external: false,
    }))

  // Collections column: visible collections (root + nested under pages)
  const collectionLinks = visibleRoots
    .filter(item => item.type === 'collection')
    .map(item => ({
      text: getLabel(item),
      url: item.url || '',
      external: false,
    }))

  for (const root of visibleRoots) {
    for (const child of root.children) {
      if (child.type === 'collection' && child.visible) {
        collectionLinks.push({
          text: getLabel(child),
          url: child.url || '',
          external: false,
        })
      }
    }
  }

  const sections: FooterSection[] = []

  if (pageLinks.length > 0) {
    sections.push({
      title: { fr: 'Navigation', en: 'Navigation' },
      links: pageLinks,
    })
  }

  if (collectionLinks.length > 0) {
    sections.push({
      title: { fr: 'Collections', en: 'Collections' },
      links: collectionLinks,
    })
  }

  // Project info column
  const year = new Date().getFullYear()
  const projectTitle = siteSettings.title || ''
  sections.push({
    title: projectTitle || { fr: 'Projet', en: 'Project' },
    links: [
      {
        text: `© ${year} ${projectTitle}`.trim(),
        url: '/index.html',
        external: false,
      },
    ],
  })

  return sections
}
