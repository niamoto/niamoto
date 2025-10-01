import { HeroSection } from './HeroSection'
import { ArchitectureSection } from './ArchitectureSection'
import { StackTechSection } from './StackTechSection'

export function OverviewSection() {
  return (
    <div className="space-y-16">
      <HeroSection />
      <div className="border-t border-border/50" />
      <ArchitectureSection />
      <div className="border-t border-border/50" />
      <StackTechSection />
    </div>
  )
}
