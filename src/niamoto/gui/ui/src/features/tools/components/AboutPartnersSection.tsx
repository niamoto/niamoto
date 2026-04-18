import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { openExternalUrl } from '@/shared/desktop/openExternalUrl'
import type { AboutOrganization } from '@/features/tools/content/aboutContent'

interface AboutPartnersSectionProps {
  title: string
  intro: string
  organizations: AboutOrganization[]
}

export function AboutPartnersSection({
  title,
  intro,
  organizations,
}: AboutPartnersSectionProps) {
  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-base font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{intro}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {organizations.map((organization) => {
          const organizationUrl = organization.url
          const content = (
            <>
              <div className="flex h-16 items-center justify-center rounded-theme-sm bg-background/80 p-3">
                <img
                  src={organization.logoSrc}
                  alt={organization.logoAlt}
                  className="max-h-10 w-full object-contain"
                />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium">{organization.name}</p>
                {organizationUrl ? (
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <ExternalLink className="h-3 w-3" />
                    {new URL(organizationUrl).hostname.replace(/^www\./, '')}
                  </span>
                ) : null}
              </div>
            </>
          )

          const cardClassName = cn(
            'rounded-theme-md border bg-muted/30 p-4 text-center transition-theme-fast',
            organizationUrl
              ? 'hover:border-primary/30 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
              : null
          )

          if (organizationUrl) {
            return (
              <button
                key={organization.id}
                type="button"
                className={cardClassName}
                onClick={() => void openExternalUrl(organizationUrl)}
              >
                {content}
              </button>
            )
          }

          return (
            <div key={organization.id} className={cardClassName}>
              {content}
            </div>
          )
        })}
      </div>
    </section>
  )
}
