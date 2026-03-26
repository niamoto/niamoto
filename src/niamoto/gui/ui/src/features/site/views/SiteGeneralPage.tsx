import { SiteBuilder } from '@/features/site/components/SiteBuilder'

export default function SiteGeneralPage() {
  return (
    <div className="h-full overflow-hidden">
      <SiteBuilder initialSection="general" />
    </div>
  )
}
