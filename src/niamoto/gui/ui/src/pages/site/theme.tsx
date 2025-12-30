/**
 * Site Theme - Configure site theme
 * Route: /site/theme
 */

import { SitePanel } from '@/components/panels/SitePanel'

export default function SiteThemePage() {
  return (
    <div className="h-full overflow-auto">
      <SitePanel subSection="theme" />
    </div>
  )
}
