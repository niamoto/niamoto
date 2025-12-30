/**
 * Sources Dashboard - Overview of all imported data
 * Route: /sources
 */

import { DataDashboard } from '@/components/panels/DataDashboard'

export default function SourcesPage() {
  return (
    <div className="h-full overflow-auto">
      <DataDashboard />
    </div>
  )
}
