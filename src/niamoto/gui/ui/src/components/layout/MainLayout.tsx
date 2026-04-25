import { Outlet, useLocation } from 'react-router-dom'
import { PageTransition } from '@/components/motion/PageTransition'
import { useEffect, useLayoutEffect } from 'react'
import { NavigationSidebar } from './NavigationSidebar'
import { TopBar } from './TopBar'
import { DesktopStatusBar } from './DesktopStatusBar'
import { CommandPalette } from './CommandPalette'
import { FeedbackProvider, FeedbackModal } from '@/features/feedback'
import { FeedbackErrorBoundary } from '@/features/feedback/components/FeedbackErrorBoundary'
import { recordNavigation } from '@/features/feedback/lib/navigation-tracker'
import { useNavigationStore, routeLabels } from '@/stores/navigationStore'
import { useJobPolling } from '@/hooks/useJobPolling'
import { AppUpdaterProvider } from '@/shared/desktop/updater/useAppUpdater'
import { useShellBindings } from '@/shared/shell/useShellBindings'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { useProjectDesktopRouteMemory } from '@/shared/hooks/useProjectDesktopRouteMemory'
import { cn } from '@/lib/utils'

function syncSidebarModeToViewport() {
  const { sidebarMode, setSidebarMode } = useNavigationStore.getState()
  const width = window.innerWidth

  if (width < 768) {
    if (sidebarMode !== 'hidden') {
      setSidebarMode('hidden')
    }
    return
  }

  if (width < 1024) {
    if (sidebarMode !== 'compact') {
      setSidebarMode('compact')
    }
    return
  }

  if (sidebarMode === 'hidden') {
    setSidebarMode('full')
  }
}

export function MainLayout() {
  const location = useLocation()
  const { setBreadcrumbs } = useNavigationStore()
  const { isDesktop, isTauri } = useRuntimeMode()
  const routeSurfaceKey = location.pathname.startsWith('/help/')
    || location.pathname === '/help'
    ? '/help'
    : location.pathname

  useJobPolling()
  useShellBindings({ isDesktop, isTauri })
  useProjectDesktopRouteMemory({ enabled: isDesktop })

  // Build breadcrumbs from route path using routeLabels map
  useEffect(() => {
    const pathParts = location.pathname.split('/').filter(Boolean)
    const breadcrumbs: { label: string; path?: string }[] = []

    let currentPath = ''
    pathParts.forEach((part, index) => {
      currentPath += `/${part}`

      // Try exact match in routeLabels, then fall back to capitalized path segment
      const label = routeLabels[currentPath]
        || part.charAt(0).toUpperCase() + part.slice(1)

      breadcrumbs.push({
        label,
        path: index < pathParts.length - 1 ? currentPath : undefined
      })
    })

    setBreadcrumbs(breadcrumbs)
    recordNavigation(location.pathname)
  }, [location.pathname, setBreadcrumbs])

  // Handle responsive sidebar
  useLayoutEffect(() => {
    syncSidebarModeToViewport()
    window.addEventListener('resize', syncSidebarModeToViewport)
    return () => window.removeEventListener('resize', syncSidebarModeToViewport)
  }, [])

  return (
    <AppUpdaterProvider>
      <FeedbackProvider>
        <div className="flex h-screen overflow-hidden bg-sidebar/35">
          <NavigationSidebar />

          <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-background">
            <div className="border-b border-border/70 bg-background/88 supports-[backdrop-filter]:bg-background/75 supports-[backdrop-filter]:backdrop-blur-md">
              <TopBar />
            </div>

            <main
              className={cn(
                'min-h-0 flex-1 overflow-hidden bg-background',
                'transition-all duration-200'
              )}
            >
              <FeedbackErrorBoundary key={routeSurfaceKey}>
                <PageTransition transitionKey={routeSurfaceKey}>
                  <Outlet />
                </PageTransition>
              </FeedbackErrorBoundary>
            </main>

            {isDesktop && <DesktopStatusBar />}
          </div>

          <CommandPalette />
          <FeedbackModal />
        </div>
      </FeedbackProvider>
    </AppUpdaterProvider>
  )
}
