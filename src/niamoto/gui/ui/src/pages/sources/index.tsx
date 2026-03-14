/**
 * Sources Dashboard - Overview of all imported data
 * Route: /sources
 */

import { DataDashboard } from '@/components/panels/DataDashboard'
import { StalenessBanner } from '@/components/pipeline/StalenessBanner'

export default function SourcesPage() {
  return (
    <div className="flex h-full flex-col overflow-auto">
      <StalenessBanner stage="data" />
      <div className="flex-1">
        <DataDashboard />
      </div>
    </div>
  )
}
