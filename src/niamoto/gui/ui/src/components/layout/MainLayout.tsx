import { Outlet, useLocation } from 'react-router-dom'
import { PageTransition } from '@/components/motion/PageTransition'
import { useEffect } from 'react'
import { NavigationSidebar } from './NavigationSidebar'
import { TopBar } from './TopBar'
import { BreadcrumbNav } from './BreadcrumbNav'
import { CommandPalette } from './CommandPalette'
import { FeedbackProvider, FeedbackModal } from '@/features/feedback'
import { DesktopTitlebar } from './DesktopTitlebar'
import { useNavigationStore, routeLabels } from '@/stores/navigationStore'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { usePlatform } from '@/shared/hooks/usePlatform'
import { useJobPolling } from '@/hooks/useJobPolling'
import { useAppUpdater } from '@/shared/desktop/updater/useAppUpdater'
import { cn } from '@/lib/utils'

export function MainLayout() {
  const location = useLocation()
  const { setBreadcrumbs } = useNavigationStore()
  const { isDesktop } = useRuntimeMode()
  const { isMac } = usePlatform()

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
          {isDesktop && !isMac && <DesktopTitlebar />}
          <TopBar />
          <BreadcrumbNav />

          <main
            className={cn(
              'flex-1 overflow-hidden bg-background',
              'transition-all duration-200'
            )}
          >
            <PageTransition>
              <Outlet />
            </PageTransition>
          </main>
        </div>

        <CommandPalette />
        <FeedbackModal />
      </div>
    </FeedbackProvider>
  )
}
