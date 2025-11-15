import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface NavigationSection {
  id: string
  label: string
  icon?: string
  items: NavigationItem[]
  defaultOpen?: boolean
}

interface NavigationItem {
  id: string
  label: string
  path: string
  icon?: string
  badge?: string | number
}

interface NavigationState {
  // Sidebar state
  sidebarExpanded: boolean
  sidebarMode: 'full' | 'compact' | 'hidden'
  expandedSections: string[]

  // Actions
  toggleSidebar: () => void
  setSidebarMode: (mode: 'full' | 'compact' | 'hidden') => void
  toggleSection: (sectionId: string) => void
  expandSection: (sectionId: string) => void
  collapseSection: (sectionId: string) => void

  // Command palette
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void

  // Breadcrumb
  breadcrumbs: { label: string; path?: string }[]
  setBreadcrumbs: (breadcrumbs: { label: string; path?: string }[]) => void
}

// Navigation structure definition
export const navigationSections: NavigationSection[] = [
  {
    id: 'home',
    label: 'Home',
    defaultOpen: true,
    items: [
      { id: 'showcase', label: 'Niamoto Flow', path: '/showcase' }
    ]
  },
  {
    id: 'setup',
    label: 'Setup',
    defaultOpen: false,
    items: [
      { id: 'import', label: 'Import Data', path: '/setup/import' },
      { id: 'transform', label: 'Transform', path: '/setup/transform' },
      { id: 'export', label: 'Export Site', path: '/setup/export' }
    ]
  },
  {
    id: 'data',
    label: 'Data',
    defaultOpen: false,
    items: [
      { id: 'explorer', label: 'Data Explorer', path: '/data/explorer' },
      { id: 'preview', label: 'Live Preview', path: '/data/preview' }
    ]
  },
  {
    id: 'tools',
    label: 'Tools',
    defaultOpen: false,
    items: [
      { id: 'settings', label: 'Settings', path: '/tools/settings' },
      { id: 'config-editor', label: 'Config Editor', path: '/tools/config-editor' },
      { id: 'plugins', label: 'Plugins', path: '/tools/plugins' },
      { id: 'docs', label: 'API Documentation', path: '/tools/docs' }
    ]
  },
  {
    id: 'labs',
    label: 'Labs',
    defaultOpen: false,
    items: [
      { id: 'pipeline-editor', label: 'Flow Editor', path: '/setup/pipeline' },
      { id: 'bootstrap', label: 'Bootstrap', path: '/setup/bootstrap' },
      { id: 'demo-entity', label: 'Entity-Centric', path: '/demos/entity-centric' },
      { id: 'demo-pipeline', label: 'Pipeline Visual', path: '/demos/pipeline-visual' },
      { id: 'demo-wizard', label: 'Wizard & Forms', path: '/demos/wizard-form'},
      { id: 'demo-goal-driven', label: 'Goal-Driven Builder', path: '/demos/goal-driven'}
    ]
  }
]

export const useNavigationStore = create<NavigationState>()(
  persist(
    (set) => ({
      // Initial state
      sidebarExpanded: true,
      sidebarMode: 'full',
      expandedSections: navigationSections
        .filter(s => s.defaultOpen)
        .map(s => s.id),
      commandPaletteOpen: false,
      breadcrumbs: [],

      // Sidebar actions
      toggleSidebar: () => set((state) => ({
        sidebarExpanded: !state.sidebarExpanded,
        sidebarMode: !state.sidebarExpanded ? 'full' : 'compact'
      })),

      setSidebarMode: (mode) => set({
        sidebarMode: mode,
        sidebarExpanded: mode === 'full'
      }),

      // Section actions
      toggleSection: (sectionId) => set((state) => ({
        expandedSections: state.expandedSections.includes(sectionId)
          ? state.expandedSections.filter(id => id !== sectionId)
          : [...state.expandedSections, sectionId]
      })),

      expandSection: (sectionId) => set((state) => ({
        expandedSections: state.expandedSections.includes(sectionId)
          ? state.expandedSections
          : [...state.expandedSections, sectionId]
      })),

      collapseSection: (sectionId) => set((state) => ({
        expandedSections: state.expandedSections.filter(id => id !== sectionId)
      })),

      // Command palette
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

      // Breadcrumbs
      setBreadcrumbs: (breadcrumbs) => set({ breadcrumbs })
    }),
    {
      name: 'navigation-storage',
      partialize: (state) => ({
        sidebarMode: state.sidebarMode,
        expandedSections: state.expandedSections
      })
    }
  )
)

// Helper hook for responsive sidebar
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
