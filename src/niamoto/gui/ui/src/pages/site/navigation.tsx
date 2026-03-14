/**
 * Site Navigation - Configure menus
 * Route: /site/navigation
 */

import { SitePanel } from '@/components/panels/SitePanel'

export default function SiteNavigationPage() {
  return (
    <div className="h-full overflow-hidden">
      <SitePanel subSection="navigation" />
    </div>
  )
}
