import { useDeferredValue, useMemo, useState } from 'react'
import { ArrowRight, BookOpenText, FileCode2, Search } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { HelpManifest, HelpSection } from '../api'

interface DocumentationHomeProps {
  manifest: HelpManifest
  onNavigate: (slug: string) => void
}

function filterSections(sections: HelpSection[], query: string) {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) {
    return sections
  }

  const tokens = normalizedQuery.split(/\s+/).filter(Boolean)

  return sections
    .map((section) => {
      const pages = section.pages.filter((page) => {
        const haystacks = [
          page.title,
          page.description,
          ...page.headings.map((heading) => heading.title),
        ].map((value) => value.toLowerCase())

        return tokens.every((token) =>
          haystacks.some((value) => value.includes(token)),
        )
      })

      const sectionMatches = tokens.every((token) =>
        [section.title, section.description]
          .map((value) => value.toLowerCase())
          .some((value) => value.includes(token)),
      )

      if (!sectionMatches && pages.length === 0) {
        return null
      }

      return {
        ...section,
        pages: pages.length > 0 ? pages : section.pages.slice(0, 4),
      }
    })
    .filter((section): section is HelpSection => section !== null)
}

export function DocumentationHome({
  manifest,
  onNavigate,
}: DocumentationHomeProps) {
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)

  const visibleSections = useMemo(
    () => filterSections(manifest.sections, deferredSearch),
    [deferredSearch, manifest.sections],
  )

  const totalArticles = manifest.sections.reduce(
    (count, section) => count + section.article_count,
    0,
  )

  return (
    <div className="space-y-6">
      <Card className="border-primary/20 bg-linear-to-br from-primary/6 via-background to-background">
        <CardHeader className="gap-3">
          <div className="flex items-center gap-2 text-sm text-primary">
            <BookOpenText className="h-4 w-4" />
            Public documentation
          </div>
          <CardTitle className="text-2xl">Documentation</CardTitle>
          <CardDescription className="max-w-3xl text-sm leading-relaxed">
            Browse the same public guides shipped with Niamoto: getting started,
            user workflows, automation, plugins, reference, architecture,
            roadmaps, and troubleshooting.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{manifest.sections.length} sections</Badge>
            <Badge variant="secondary">{totalArticles} pages</Badge>
            <Badge variant="secondary">API docs stay separate</Badge>
          </div>

          <div className="relative max-w-xl">
            <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="pl-9"
              placeholder="Search sections, pages, or headings..."
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        {visibleSections.map((section) => (
          <Card key={section.slug} className="h-full">
            <CardHeader className="gap-3">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="text-lg">{section.title}</CardTitle>
                  <CardDescription className="line-clamp-3">
                    {section.description}
                  </CardDescription>
                </div>
                <Badge variant="outline">{section.article_count} pages</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {section.pages.slice(0, 4).map((page) => (
                  <button
                    key={page.slug}
                    type="button"
                    onClick={() => onNavigate(page.slug)}
                    className="flex w-full items-start justify-between gap-3 rounded-theme-md border px-3 py-2 text-left transition-colors hover:bg-muted/60"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {page.title}
                      </div>
                      <div className="truncate text-xs text-muted-foreground">
                        {page.description}
                      </div>
                    </div>
                    <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="default"
                  onClick={() => onNavigate(section.slug)}
                >
                  Open section
                </Button>
                {section.slug === '06-reference' ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => onNavigate('06-reference/cli-commands')}
                  >
                    <FileCode2 className="mr-2 h-4 w-4" />
                    CLI reference
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
