/**
 * Site General - Configure site identity
 * Route: /site/general
 */

import { SitePanel } from '@/components/panels/SitePanel'

export default function SiteGeneralPage() {
  return (
    <div className="h-full overflow-auto">
      <SitePanel subSection="general" />
    </div>
  )
}
