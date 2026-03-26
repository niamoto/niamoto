import { StalenessBanner } from '@/components/pipeline/StalenessBanner'
import { SiteBuilder } from '@/features/site/components/SiteBuilder'

export default function SitePagesPage() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <StalenessBanner stage="site" />
      <div className="min-h-0 flex-1 overflow-hidden">
        <SiteBuilder initialSection="pages" />
      </div>
    </div>
  )
}
