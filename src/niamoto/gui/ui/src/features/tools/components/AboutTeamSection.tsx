import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { openExternalUrl } from '@/shared/desktop/openExternalUrl'
import type { AboutTeamMember } from '@/features/tools/content/aboutContent'

interface AboutTeamSectionProps {
  title: string
  intro: string
  members: AboutTeamMember[]
}

export function AboutTeamSection({ title, intro, members }: AboutTeamSectionProps) {
  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-base font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{intro}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {members.map((member) => {
          const cardClassName =
            'rounded-theme-md border bg-muted/30 p-4 text-left transition-theme-fast'
          const memberUrl = member.url

          if (memberUrl) {
            return (
              <button
                key={member.id}
                type="button"
                className={cn(
                  cardClassName,
                  'hover:border-primary/30 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
                )}
                onClick={() => void openExternalUrl(memberUrl)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-medium">{member.name}</p>
                    <p className="text-sm text-muted-foreground">{member.role}</p>
                  </div>
                  <ExternalLink className="mt-0.5 h-4 w-4 text-muted-foreground" />
                </div>
              </button>
            )
          }

          return (
            <div key={member.id} className={cardClassName}>
              <p className="font-medium">{member.name}</p>
              <p className="mt-1 text-sm text-muted-foreground">{member.role}</p>
            </div>
          )
        })}
      </div>
    </section>
  )
}
