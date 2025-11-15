import { UseCasesSection } from './UseCasesSection'
import { TeamSection } from './TeamSection'
import { CallToAction } from './CallToAction'

export function CommunitySection() {
  return (
    <div className="space-y-16">
      <UseCasesSection />
      <div className="border-t border-border/50" />
      <TeamSection />
      <div className="border-t border-border/50" />
      <CallToAction />
    </div>
  )
}
