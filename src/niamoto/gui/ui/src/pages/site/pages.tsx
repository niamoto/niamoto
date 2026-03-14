/**
 * Site Pages - Manage static pages
 * Route: /site/pages
 */

import { SitePanel } from '@/components/panels/SitePanel'
import { StalenessBanner } from '@/components/pipeline/StalenessBanner'

export default function SitePagesPage() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <StalenessBanner stage="site" />
      <div className="min-h-0 flex-1 overflow-hidden">
        <SitePanel subSection="pages" />
      </div>
    </div>
  )
}
