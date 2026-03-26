import { SiteBuilder } from '@/features/site/components/SiteBuilder'

export default function SiteAppearancePage() {
  return (
    <div className="h-full overflow-hidden">
      <SiteBuilder initialSection="appearance" />
    </div>
  )
}
