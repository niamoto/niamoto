import { Outlet, useLocation } from 'react-router-dom'
import { PageTransition } from '@/components/motion/PageTransition'
import { useEffect } from 'react'
import { NavigationSidebar } from './NavigationSidebar'
import { TopBar } from './TopBar'
import { BreadcrumbNav } from './BreadcrumbNav'
import { CommandPalette } from './CommandPalette'
import { FeedbackProvider, FeedbackModal } from '@/features/feedback'
import { FeedbackErrorBoundary } from '@/features/feedback/components/FeedbackErrorBoundary'
import { recordNavigation } from '@/features/feedback/lib/navigation-tracker'
import { useNavigationStore, routeLabels } from '@/stores/navigationStore'
import { useJobPolling } from '@/hooks/useJobPolling'
import { useAppUpdater } from '@/shared/desktop/updater/useAppUpdater'
import { cn } from '@/lib/utils'

export function MainLayout() {
  const location = useLocation()
  const { setBreadcrumbs } = useNavigationStore()

  useJobPolling()
  useAppUpdater()

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
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      if (width < 768) {
        useNavigationStore.getState().setSidebarMode('hidden')
      } else if (width < 1024) {
        useNavigationStore.getState().setSidebarMode('compact')
      } else {
        const currentMode = useNavigationStore.getState().sidebarMode
        if (currentMode === 'hidden') {
          useNavigationStore.getState().setSidebarMode('full')
        }
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <FeedbackProvider>
      <div className="flex h-screen overflow-hidden">
        <NavigationSidebar />

        <div className="flex flex-1 flex-col overflow-hidden">
          <TopBar />
          <BreadcrumbNav />

          <main
            className={cn(
              'flex-1 overflow-hidden bg-background',
              'transition-all duration-200'
            )}
          >
            <FeedbackErrorBoundary key={location.pathname}>
              <PageTransition>
                <Outlet />
              </PageTransition>
            </FeedbackErrorBoundary>
          </main>
        </div>

        <CommandPalette />
        <FeedbackModal />
      </div>
    </FeedbackProvider>
  )
}
