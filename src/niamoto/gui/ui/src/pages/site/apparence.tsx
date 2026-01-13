/**
 * Site Apparence - Configure site identity
 * Route: /site/apparence
 */

import { SitePanel } from '@/components/panels/SitePanel'

export default function SiteApparencePage() {
  return (
    <div className="h-full overflow-auto">
      <SitePanel subSection="apparence" />
    </div>
  )
}
