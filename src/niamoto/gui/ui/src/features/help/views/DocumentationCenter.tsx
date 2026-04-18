import { useLayoutEffect, useMemo, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AlertCircle, BookOpenText } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { DocumentationNav } from '../components/DocumentationNav'
import { useHelpManifest, useHelpPage } from '../hooks/useDocumentationContent'
import {
  buildHelpPath,
  findHelpSelection,
  helpSlugFromPathname,
  normalizeHelpPathname,
} from '../routing'
import { DocumentationArticle } from './DocumentationArticle'
import { DocumentationHome } from './DocumentationHome'

function DocumentationSkeleton() {
  return (
    <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
      <Card className="hidden xl:block">
        <CardContent className="space-y-3 p-4">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-[520px] w-full" />
      </div>
    </div>
  )
}

let documentationSidebarScrollTop = 0

export function DocumentationCenter() {
  const location = useLocation()
  const navigate = useNavigate()
  const manifestQuery = useHelpManifest()
  const sidebarScrollRef = useRef<HTMLDivElement | null>(null)

  const normalizedPath = normalizeHelpPathname(location.pathname)
  const requestedSlug = helpSlugFromPathname(normalizedPath)

  const selection = useMemo(
    () => findHelpSelection(manifestQuery.data, normalizedPath),
    [manifestQuery.data, normalizedPath],
  )

  const pageQuery = useHelpPage(selection.page?.slug)
  const manifestReady = !manifestQuery.isLoading && !manifestQuery.isError && Boolean(manifestQuery.data)

  const handleNavigate = (slug: string) => {
    navigate(buildHelpPath(slug))
  }

  useLayoutEffect(() => {
    if (!manifestReady) {
      return
    }

    const container = sidebarScrollRef.current
    if (!container) {
      return
    }

    const restoreScroll = () => {
      container.scrollTop = documentationSidebarScrollTop
    }

    restoreScroll()
    const frame = window.requestAnimationFrame(restoreScroll)

    return () => {
      window.cancelAnimationFrame(frame)
      documentationSidebarScrollTop = container.scrollTop
    }
  }, [manifestReady, normalizedPath])

  if (manifestQuery.isLoading) {
    return (
      <div className="h-full overflow-auto p-6">
        <DocumentationSkeleton />
      </div>
    )
  }

  if (manifestQuery.isError || !manifestQuery.data) {
    return (
      <div className="mx-auto flex h-full max-w-3xl items-center px-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Documentation unavailable</AlertTitle>
          <AlertDescription>
            The in-app documentation pack could not be loaded. Rebuild the
            generated help content and try again.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  const showHome = normalizedPath === '/help'
  const isUnknownArticle = Boolean(requestedSlug) && !selection.page

  return (
    <div className="flex h-full overflow-hidden">
      <aside className="hidden w-[320px] shrink-0 border-r bg-muted/20 xl:block">
        <div
          ref={sidebarScrollRef}
          className="h-full overflow-y-auto"
          onScroll={(event) => {
            documentationSidebarScrollTop = event.currentTarget.scrollTop
          }}
        >
          <div className="space-y-4 p-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <BookOpenText className="h-4 w-4" />
                Documentation
              </div>
              <p className="text-sm text-muted-foreground">
                Public docs embedded in the desktop app.
              </p>
            </div>
            <DocumentationNav
              sections={manifestQuery.data.sections}
              currentSectionSlug={selection.section?.slug}
              currentPageSlug={selection.page?.slug}
              onNavigate={handleNavigate}
            />
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 lg:px-6">
            <div className="xl:hidden">
              <DocumentationNav
                sections={manifestQuery.data.sections}
                currentSectionSlug={selection.section?.slug}
                currentPageSlug={selection.page?.slug}
                onNavigate={handleNavigate}
              />
            </div>

            {showHome ? (
              <DocumentationHome
                manifest={manifestQuery.data}
                onNavigate={handleNavigate}
              />
            ) : isUnknownArticle ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Page not found</AlertTitle>
                <AlertDescription className="gap-3">
                  <p>
                    This documentation page is not part of the embedded public
                    pack.
                  </p>
                  <div>
                    <Button type="button" variant="outline" onClick={() => navigate('/help')}>
                      Back to documentation
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            ) : pageQuery.isError ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Article unavailable</AlertTitle>
                <AlertDescription className="gap-3">
                  <p>
                    The article metadata exists in the manifest, but the page
                    payload could not be loaded from the embedded help pack.
                  </p>
                  <div>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => selection.section && navigate(buildHelpPath(selection.section.slug))}
                    >
                      Back to section overview
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            ) : pageQuery.isLoading || !pageQuery.data || !selection.section ? (
              <DocumentationSkeleton />
            ) : (
              <DocumentationArticle
                page={pageQuery.data}
                section={selection.section}
              />
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
