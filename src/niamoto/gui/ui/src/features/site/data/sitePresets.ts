/**
 * sitePresets - Site template presets for first-launch experience
 *
 * Three presets that generate a complete site structure from scratch.
 * Collections are auto-detected and added to the structure.
 * Page presentation names = collection names (generic, no domain mapping).
 */

import type { StaticPage, GroupInfo, SiteSettings } from '@/shared/hooks/useSiteConfig'
import { DEFAULT_STATIC_PAGE } from '@/shared/hooks/useSiteConfig'
import type { UnifiedTreeItem } from '../hooks/useUnifiedSiteTree'
import { generateFooterFromTree } from '../utils/generateFooter'
import type { FooterSection } from '@/shared/hooks/useSiteConfig'

// =============================================================================
// PRESET DEFINITIONS
// =============================================================================

interface PresetPageDef {
  name: string
  template: string
  output_file: string
}

export interface SitePreset {
  id: string
  nameKey: string       // i18n key for preset name
  descriptionKey: string // i18n key for description
  pages: PresetPageDef[]
}

export const SITE_PRESETS: SitePreset[] = [
  {
    id: 'minimal',
    nameKey: 'presets.minimal',
    descriptionKey: 'presets.minimalDesc',
    pages: [
      { name: 'home', template: 'index.html', output_file: 'index.html' },
    ],
  },
  {
    id: 'scientific',
    nameKey: 'presets.scientific',
    descriptionKey: 'presets.scientificDesc',
    pages: [
      { name: 'home', template: 'index.html', output_file: 'index.html' },
      { name: 'methodology', template: 'page.html', output_file: 'methodology.html' },
      { name: 'team', template: 'team.html', output_file: 'team.html' },
      { name: 'bibliography', template: 'bibliography.html', output_file: 'bibliography.html' },
      { name: 'contact', template: 'contact.html', output_file: 'contact.html' },
    ],
  },
  {
    id: 'complete',
    nameKey: 'presets.complete',
    descriptionKey: 'presets.completeDesc',
    pages: [
      { name: 'home', template: 'index.html', output_file: 'index.html' },
      { name: 'methodology', template: 'page.html', output_file: 'methodology.html' },
      { name: 'team', template: 'team.html', output_file: 'team.html' },
      { name: 'resources', template: 'resources.html', output_file: 'resources.html' },
      { name: 'bibliography', template: 'bibliography.html', output_file: 'bibliography.html' },
      { name: 'glossary', template: 'glossary.html', output_file: 'glossary.html' },
      { name: 'contact', template: 'contact.html', output_file: 'contact.html' },
    ],
  },
]

// =============================================================================
// APPLY PRESET
// =============================================================================

/**
 * Apply a site preset, generating:
 * - StaticPage[] from the preset definition
 * - UnifiedTreeItem[] including detected collections
 * - FooterSection[] via generateFooterFromTree
 */
export function applySitePreset(
  preset: SitePreset,
  groups: GroupInfo[],
): {
  staticPages: StaticPage[]
  tree: UnifiedTreeItem[]
  footerSections: FooterSection[]
  site: Partial<SiteSettings>
} {
  // Create static pages
  const staticPages: StaticPage[] = preset.pages.map(def => ({
    ...DEFAULT_STATIC_PAGE,
    name: def.name,
    template: def.template,
    output_file: def.output_file,
  }))

  // Build tree items for pages
  let idCounter = 1
  const pageItems: UnifiedTreeItem[] = staticPages.map(page => ({
    id: `preset-page-${idCounter++}`,
    type: 'page' as const,
    label: page.name,
    visible: true,
    pageRef: page.name,
    url: `/${page.output_file}`,
    template: page.template,
    children: [],
  }))

  // Add collections: visible if they have an index, hidden otherwise
  const collectionItems: UnifiedTreeItem[] = groups.map(group => ({
    id: `preset-collection-${idCounter++}`,
    type: 'collection' as const,
    label: group.name,
    visible: !!group.index_output_pattern,
    collectionRef: group.name,
    url: group.index_output_pattern ? `/${group.index_output_pattern}` : undefined,
    hasIndex: !!group.index_output_pattern,
    children: [],
  }))

  const visibleCollections = collectionItems.filter(c => c.visible)
  const hiddenCollections = collectionItems.filter(c => !c.visible)

  const tree = [...pageItems, ...visibleCollections, ...hiddenCollections]

  // Generate footer from tree
  const site: Partial<SiteSettings> = {}
  const footerSections = generateFooterFromTree(tree, { title: '', lang: 'fr' } as SiteSettings)

  return { staticPages, tree, footerSections, site }
}
