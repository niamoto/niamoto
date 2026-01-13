/**
 * Site Panel - Unified Site Builder Interface
 *
 * Uses the new SiteBuilder component with:
 * - Split Preview layout (Tree | Editor | Preview)
 * - Contextual editing based on selection
 * - Live markdown preview
 */

import { SiteBuilder } from '@/components/site/SiteBuilder'

interface SitePanelProps {
  subSection?: 'pages' | 'navigation' | 'apparence' | 'theme'
}

export function SitePanel({ subSection }: SitePanelProps) {
  // Map sub-sections to initial selections in the tree
  const initialSection =
    subSection === 'pages' ? 'pages'
    : subSection === 'navigation' ? 'navigation'
    : subSection === 'apparence' ? 'identity'
    : subSection === 'theme' ? 'theme'
    : 'pages' // Default to pages (most used)

  return <SiteBuilder initialSection={initialSection} />
}
