import { SiteBuilder } from '@/features/site/components/SiteBuilder'

export default function SiteNavigationPage() {
  return (
    <div className="h-full overflow-hidden">
      <SiteBuilder initialSection="navigation" />
    </div>
  )
}
