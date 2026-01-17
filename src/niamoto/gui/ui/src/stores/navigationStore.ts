import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface NavigationSection {
  id: string
  label: string
  icon?: string
  badge?: { type: 'status' | 'count'; value: string | number }
  items: NavigationItem[]
  defaultOpen?: boolean
  dynamic?: boolean // Items are loaded dynamically
}

export interface NavigationItem {
  id: string
  label: string
  path?: string
  panel?: string // Panel to show in flow page
  icon?: string
  badge?: string | number
  action?: string // Special action like 'add'
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

  // Active panel (for flow page internal navigation)
  activePanel: string | null
  setActivePanel: (panel: string | null) => void
}

// Static navigation structure
// Note: 'sources' section has dynamic items for datasets and references
// Note: 'groups' section items are loaded dynamically from useReferences()
export const navigationSections: NavigationSection[] = [
  {
    id: 'sources',
    label: 'Sources',
    defaultOpen: true,
    dynamic: true, // Datasets and references loaded dynamically
    items: [
      { id: 'dashboard', label: 'Dashboard', path: '/sources' },
      { id: 'import', label: 'Import', path: '/sources/import' },
      // Dynamic items (datasets, references) will be added here
      // Pattern: { id: 'dataset-{name}', label: '{name}', path: '/sources/dataset/{name}' }
      // Pattern: { id: 'reference-{name}', label: '{name}', path: '/sources/reference/{name}' }
    ]
  },
  {
    id: 'groups',
    label: 'Groupes',
    defaultOpen: true,
    dynamic: true, // Items loaded from useReferences()
    items: [
      { id: 'groups-index', label: 'Vue d\'ensemble', path: '/groups' },
      // Dynamic items will be added here
      // Pattern: { id: 'group-{name}', label: '{name}', path: '/groups/{name}' }
    ]
  },
  {
    id: 'site',
    label: 'Site',
    defaultOpen: true,
    dynamic: true, // Badge will show page count
    items: [
      { id: 'site-pages', label: 'Pages', path: '/site/pages' },
      { id: 'site-navigation', label: 'Navigation', path: '/site/navigation' },
      { id: 'site-apparence', label: 'Apparence', path: '/site/apparence' },
      { id: 'site-theme', label: 'Thème', path: '/site/theme' },
    ]
  },
  {
    id: 'publish',
    label: 'Publish',
    defaultOpen: true,
    dynamic: true, // Badge will show last build/deploy status
    items: [
      { id: 'publish-overview', label: 'Vue d\'ensemble', path: '/publish' },
      { id: 'publish-build', label: 'Build', path: '/publish/build' },
      { id: 'publish-deploy', label: 'Deploy', path: '/publish/deploy' },
      { id: 'publish-history', label: 'Historique', path: '/publish/history' },
    ]
  },
  {
    id: 'tools',
    label: 'Outils',
    defaultOpen: false,
    items: [
      { id: 'data-explorer', label: 'Data Explorer', path: '/tools/explorer' },
      { id: 'live-preview', label: 'Live Preview', path: '/tools/preview' },
      { id: 'showcase', label: 'Showcase', path: '/showcase' },
      { id: 'config-editor', label: 'Config Editor', path: '/tools/config-editor' },
      { id: 'plugins', label: 'Plugins', path: '/tools/plugins' },
      { id: 'docs', label: 'Documentation', path: '/tools/docs' }
    ]
  },
  {
    id: 'labs',
    label: 'Labs',
    defaultOpen: true,
    items: [
      { id: 'labs-index', label: 'Vue d\'ensemble', path: '/labs' },
      { id: 'mockup-hybrid', label: 'Option A: Hybride', path: '/labs/mockup-widgets-hybrid' },
      { id: 'mockup-canvas', label: 'Option B: Canvas', path: '/labs/mockup-canvas-builder' },
      { id: 'mockup-inline', label: 'Option C: Inline', path: '/labs/mockup-widgets-inline' }
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
      activePanel: null,

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
      setBreadcrumbs: (breadcrumbs) => set({ breadcrumbs }),

      // Active panel
      setActivePanel: (panel) => set({ activePanel: panel })
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
