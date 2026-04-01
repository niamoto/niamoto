import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LucideIcon } from 'lucide-react'
import { Home, Database, Layers, Globe, Send } from 'lucide-react'

// --- Flat navigation items (new) ---

export interface NavItem {
  id: string
  labelKey: string       // i18n key in common:sidebar.nav.*
  fallbackLabel: string  // Fallback if i18n not loaded
  icon: LucideIcon
  path: string           // Default navigation target
  matchPrefix: string    // Route prefix for active state (e.g., '/sources')
}

export const navItems: NavItem[] = [
  {
    id: 'home',
    labelKey: 'sidebar.nav.home',
    fallbackLabel: 'Home',
    icon: Home,
    path: '/',
    matchPrefix: '/',  // Exact match (handled specially in sidebar)
  },
  {
    id: 'data',
    labelKey: 'sidebar.nav.data',
    fallbackLabel: 'Data',
    icon: Database,
    path: '/sources',
    matchPrefix: '/sources',
  },
  {
    id: 'groups',
    labelKey: 'sidebar.nav.collections',
    fallbackLabel: 'Collections',
    icon: Layers,
    path: '/groups',
    matchPrefix: '/groups',
  },
  {
    id: 'site',
    labelKey: 'sidebar.nav.site',
    fallbackLabel: 'Site',
    icon: Globe,
    path: '/site',
    matchPrefix: '/site',
  },
  {
    id: 'publish',
    labelKey: 'sidebar.nav.publish',
    fallbackLabel: 'Publish',
    icon: Send,
    path: '/publish',
    matchPrefix: '/publish',
  },
]

// --- Route labels for breadcrumbs ---

export const routeLabels: Record<string, string> = {
  '/': 'Home',
  '/sources': 'Data',
  '/sources/import': 'Import',
  '/sources/verification': 'Verification',
  '/sources/enrichment': 'Enrichment',
  '/sources/dataset': 'Dataset',
  '/sources/reference': 'Reference',
  '/groups': 'Collections',
  '/site': 'Site',
  '/site/pages': 'Pages',
  // '/site/navigation' removed — redirects to /site/pages
  '/site/general': 'Settings',
  '/site/appearance': 'Appearance',
  '/publish': 'Publish',
  '/publish/build': 'Build',
  '/publish/deploy': 'Deploy',
  '/publish/history': 'History',
  '/tools/explorer': 'Data Explorer',
  '/tools/preview': 'Preview',
  '/tools/settings': 'Settings',
  '/tools/plugins': 'Plugins',
  '/tools/docs': 'Documentation',
  '/tools/config-editor': 'Config Editor',
}

// --- Legacy export (kept for backward compat during migration) ---

export interface NavigationSection {
  id: string
  label: string
  icon?: string
  badge?: { type: 'status' | 'count'; value: string | number }
  items: NavigationItem[]
  defaultOpen?: boolean
  dynamic?: boolean
}

export interface NavigationItem {
  id: string
  label: string
  path?: string
  panel?: string
  icon?: string
  badge?: string | number
  action?: string
}

/** @deprecated Use navItems instead. Kept for breadcrumb transition. */
export const navigationSections: NavigationSection[] = []

// --- Store ---

interface NavigationState {
  sidebarExpanded: boolean
  sidebarMode: 'full' | 'compact' | 'hidden'

  toggleSidebar: () => void
  setSidebarMode: (mode: 'full' | 'compact' | 'hidden') => void

  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void

  breadcrumbs: { label: string; path?: string }[]
  setBreadcrumbs: (breadcrumbs: { label: string; path?: string }[]) => void

  activePanel: string | null
  setActivePanel: (panel: string | null) => void
}

export const useNavigationStore = create<NavigationState>()(
  persist(
    (set) => ({
      sidebarExpanded: true,
      sidebarMode: 'full',
      commandPaletteOpen: false,
      breadcrumbs: [],
      activePanel: null,

      toggleSidebar: () => set((state) => ({
        sidebarExpanded: !state.sidebarExpanded,
        sidebarMode: !state.sidebarExpanded ? 'full' : 'compact'
      })),

      setSidebarMode: (mode) => set({
        sidebarMode: mode,
        sidebarExpanded: mode === 'full'
      }),

      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      setBreadcrumbs: (breadcrumbs) => set({ breadcrumbs }),
      setActivePanel: (panel) => set({ activePanel: panel })
    }),
    {
      name: 'navigation-storage',
      version: 2,
      migrate: (persisted: unknown) => {
        // Clean up old section-based state from v1
        const old = persisted as Record<string, unknown>
        return { sidebarMode: old.sidebarMode ?? 'full' } as unknown as NavigationState
      },
      partialize: (state) => ({
        sidebarMode: state.sidebarMode,
      } as unknown as NavigationState)
    }
  )
)

export const useResponsiveSidebar = () => {
  const { setSidebarMode } = useNavigationStore()

  const updateSidebarMode = () => {
    const width = window.innerWidth
    if (width < 768) {
      setSidebarMode('hidden')
    } else if (width < 1024) {
      setSidebarMode('compact')
    } else {
      setSidebarMode('full')
    }
  }

  return { updateSidebarMode }
}
