import { StalenessBanner } from '@/components/pipeline/StalenessBanner'
import { SitePanel } from '@/features/site/components/SitePanel'

export default function SitePagesPage() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <StalenessBanner stage="site" />
      <div className="min-h-0 flex-1 overflow-hidden">
        <SitePanel subSection="pages" />
      </div>
    </div>
  )
}
