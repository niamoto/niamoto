/**
 * Site Appearance - Configure site appearance/theme
 * Route: /site/appearance
 */

import { SitePanel } from '@/components/panels/SitePanel'

export default function SiteAppearancePage() {
  return (
    <div className="h-full overflow-hidden">
      <SitePanel subSection="appearance" />
    </div>
  )
}
