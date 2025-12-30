/**
 * Site Structure - Configure site navigation
 * Route: /site/structure
 */

import { SitePanel } from '@/components/panels/SitePanel'

export default function SiteStructurePage() {
  return (
    <div className="h-full overflow-auto">
      <SitePanel subSection="structure" />
    </div>
  )
}
