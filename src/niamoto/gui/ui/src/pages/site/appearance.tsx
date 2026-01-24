/**
 * Site Appearance - Configure site appearance/theme
 * Route: /site/appearance
 */

import { SitePanel } from '@/components/panels/SitePanel'

export default function SiteAppearancePage() {
  return (
    <div className="h-full overflow-auto">
      <SitePanel subSection="appearance" />
    </div>
  )
}
