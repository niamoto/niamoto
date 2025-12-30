/**
 * Site Pages - Manage static pages
 * Route: /site/pages
 */

import { SitePanel } from '@/components/panels/SitePanel'

export default function SitePagesPage() {
  return (
    <div className="h-full overflow-auto">
      <SitePanel subSection="pages" />
    </div>
  )
}
