import { Outlet, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { NavigationSidebar } from './NavigationSidebar'
import { TopBar } from './TopBar'
import { BreadcrumbNav } from './BreadcrumbNav'
import { CommandPalette } from './CommandPalette'
import { useNavigationStore, navigationSections } from '@/stores/navigationStore'
import { cn } from '@/lib/utils'

export function MainLayout() {
  const location = useLocation()
  const { t } = useTranslation()
  const { setBreadcrumbs } = useNavigationStore()

  // Update breadcrumbs based on current route
  useEffect(() => {
    const pathParts = location.pathname.split('/').filter(Boolean)
    const breadcrumbs: { label: string; path?: string }[] = []

    let currentPath = ''
    pathParts.forEach((part, index) => {
      currentPath += `/${part}`

      // Find the label from navigation sections
      let label = part
      for (const section of navigationSections) {
        const item = section.items.find(i => i.path === currentPath)
        if (item) {
          label = t(`navigation.${item.id}`, item.label)
          break
        }
      }

      breadcrumbs.push({
        label: label.charAt(0).toUpperCase() + label.slice(1),
        path: index < pathParts.length - 1 ? currentPath : undefined
      })
    })

    setBreadcrumbs(breadcrumbs)
  }, [location.pathname, setBreadcrumbs, t])

  // Handle responsive sidebar
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      if (width < 768) {
        useNavigationStore.getState().setSidebarMode('hidden')
      } else if (width < 1024) {
        useNavigationStore.getState().setSidebarMode('compact')
      } else {
        // Don't force full mode on desktop, respect user preference
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
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <NavigationSidebar />

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <TopBar />

        {/* Breadcrumb navigation */}
        <BreadcrumbNav />

        {/* Page content */}
        <main
          className={cn(
            'flex-1 overflow-auto bg-background',
            'transition-all duration-200'
          )}
        >
          <Outlet />
        </main>
      </div>

      {/* Command Palette (hidden by default) */}
      <CommandPalette />
    </div>
  )
}
