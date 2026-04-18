import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { HelpSection } from '../api'

interface DocumentationNavProps {
  sections: HelpSection[]
  currentSectionSlug?: string
  currentPageSlug?: string
  onNavigate: (slug: string) => void
  className?: string
}

export function DocumentationNav({
  sections,
  currentSectionSlug,
  currentPageSlug,
  onNavigate,
  className,
}: DocumentationNavProps) {
  return (
    <div className={cn('space-y-4', className)}>
      {sections.map((section) => {
        const isActiveSection = section.slug === currentSectionSlug

        return (
          <div
            key={section.slug}
            className={cn(
              'rounded-theme-lg border bg-card p-3 shadow-theme-sm',
              isActiveSection && 'border-border bg-muted/40',
            )}
          >
            <button
              type="button"
              onClick={() => onNavigate(section.slug)}
              className="flex w-full min-w-0 items-start justify-between gap-3 text-left"
            >
              <div className="min-w-0 space-y-1">
                <div className="line-clamp-2 font-display text-sm font-semibold leading-tight">
                  {section.title}
                </div>
                <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                  {section.description}
                </p>
              </div>
              <Badge variant="secondary" className="shrink-0">
                {section.article_count}
              </Badge>
            </button>

            <div className="mt-3 space-y-1">
              {section.pages.map((page) => {
                const isActivePage = page.slug === currentPageSlug

                return (
                  <Button
                    key={page.slug}
                    type="button"
                    variant="ghost"
                    onClick={() => onNavigate(page.slug)}
                    className={cn(
                      'h-auto w-full items-start justify-start px-2 py-2 text-left whitespace-normal hover:bg-secondary hover:text-secondary-foreground',
                      isActivePage && 'bg-secondary text-secondary-foreground',
                    )}
                  >
                    <div className="min-w-0 space-y-0.5">
                      <div className="line-clamp-2 text-sm font-medium leading-snug break-words">
                        {page.title}
                      </div>
                      {!page.is_section_index ? (
                        <div className="line-clamp-2 text-xs leading-snug text-muted-foreground break-words">
                          {page.headings[0]?.title ?? page.description}
                        </div>
                      ) : null}
                    </div>
                  </Button>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
