import { useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, ExternalLink } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import type { HelpPage, HelpSection } from '../api'
import { buildHelpPath } from '../routing'

interface DocumentationArticleProps {
  page: HelpPage
  section: HelpSection
}

function isExternalLink(href: string) {
  return /^https?:\/\//.test(href)
}

export function DocumentationArticle({
  page,
  section,
}: DocumentationArticleProps) {
  const navigate = useNavigate()
  const articleRef = useRef<HTMLDivElement | null>(null)

  const visibleHeadings = useMemo(
    () => page.headings.filter((heading) => heading.level <= 3),
    [page.headings],
  )

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, '')
    if (!hash) {
      articleRef.current?.scrollIntoView({ block: 'start' })
      return
    }

    const target = document.getElementById(hash)
    target?.scrollIntoView({ block: 'start' })
  }, [page.slug])

  useEffect(() => {
    const container = articleRef.current
    if (!container) {
      return
    }

    const anchors = Array.from(container.querySelectorAll('a[href]'))
    for (const anchor of anchors) {
      const href = anchor.getAttribute('href')
      if (href && isExternalLink(href)) {
        anchor.setAttribute('target', '_blank')
        anchor.setAttribute('rel', 'noreferrer noopener')
      }
    }
  }, [page.html])

  const handleContentClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const target = event.target instanceof Element
      ? event.target.closest('a[href]')
      : null

    if (!(target instanceof HTMLAnchorElement)) {
      return
    }

    const href = target.getAttribute('href')
    if (!href) {
      return
    }

    if (href.startsWith('/help/')) {
      event.preventDefault()
      navigate(href)
      return
    }

    if (href.startsWith('#')) {
      event.preventDefault()
      window.history.replaceState(null, '', `${window.location.pathname}${href}`)
      const element = document.getElementById(href.slice(1))
      element?.scrollIntoView({ block: 'start' })
    }
  }

  return (
    <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_220px]">
      <div className="min-w-0 space-y-6">
        <Card>
          <CardHeader className="gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{section.title}</Badge>
              {page.is_section_index ? (
                <Badge variant="outline">Section overview</Badge>
              ) : null}
            </div>
            <div className="space-y-2">
              <CardTitle className="text-2xl">{page.title}</CardTitle>
              <CardDescription className="max-w-3xl text-sm leading-relaxed">
                {page.description}
              </CardDescription>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardContent className="px-6 py-6">
            <div
              ref={articleRef}
              onClick={handleContentClick}
              className="documentation-prose max-w-none"
              dangerouslySetInnerHTML={{ __html: page.html }}
            />
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4 2xl:sticky 2xl:top-6 2xl:self-start">
        <Card>
          <CardHeader className="gap-2">
            <CardTitle className="text-base">On this page</CardTitle>
            <CardDescription>
              Jump to the main sections of this article.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            {visibleHeadings.length > 0 ? (
              visibleHeadings.map((heading) => (
                <Button
                  key={heading.id}
                  type="button"
                  variant="ghost"
                  className="h-auto w-full justify-start px-2 py-2 text-left"
                  onClick={() => {
                    const path = `${buildHelpPath(page.slug)}#${heading.id}`
                    navigate(path)
                    requestAnimationFrame(() => {
                      document.getElementById(heading.id)?.scrollIntoView({
                        block: 'start',
                      })
                    })
                  }}
                >
                  <span className="truncate text-sm">{heading.title}</span>
                </Button>
              ))
            ) : (
              <div className="flex items-start gap-2 rounded-theme-md border px-3 py-2 text-sm text-muted-foreground">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>No indexed headings for this page.</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="gap-2">
            <CardTitle className="text-base">Section</CardTitle>
            <CardDescription>{section.title}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              type="button"
              variant="outline"
              className="w-full justify-start"
              onClick={() => navigate(buildHelpPath(section.slug))}
            >
              Open section overview
            </Button>
            <Separator />
            <div className="space-y-1">
              {section.pages
                .filter((candidate) => candidate.slug !== page.slug)
                .slice(0, 6)
                .map((candidate) => (
                  <Button
                    key={candidate.slug}
                    type="button"
                    variant="ghost"
                    className="h-auto w-full justify-start px-2 py-2 text-left"
                    onClick={() => navigate(buildHelpPath(candidate.slug))}
                  >
                    <span className="truncate text-sm">{candidate.title}</span>
                  </Button>
                ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="gap-2">
            <CardTitle className="text-base">Need the API?</CardTitle>
            <CardDescription>
              The generated API reference stays on its own screen for now.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              type="button"
              variant="outline"
              className="w-full justify-between"
              onClick={() => navigate('/tools/docs')}
            >
              API documentation
              <ExternalLink className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
