/**
 * Site Panel - Unified Site Builder Interface
 */

import { SiteBuilder } from '@/components/site/SiteBuilder'

interface SitePanelProps {
  subSection?: 'pages' | 'navigation' | 'general' | 'appearance'
}

export function SitePanel({ subSection }: SitePanelProps) {
  const initialSection =
    subSection === 'pages' ? 'pages'
    : subSection === 'navigation' ? 'navigation'
    : subSection === 'general' ? 'general'
    : subSection === 'appearance' ? 'appearance'
    : 'pages'

  return <SiteBuilder initialSection={initialSection} />
}
