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
// Note: 'groups' section items are loaded dynamically from useReferences()
export const navigationSections: NavigationSection[] = [
  {
    id: 'data',
    label: 'Données',
    defaultOpen: true,
    badge: { type: 'status', value: 'Importé' },
    items: [
      { id: 'data-overview', label: 'Vue d\'ensemble', path: '/flow', panel: 'data' },
    ]
  },
  {
    id: 'groups',
    label: 'Groupes',
    defaultOpen: true,
    dynamic: true, // Items loaded from useReferences()
    items: [] // Will be populated dynamically
  },
  {
    id: 'site',
    label: 'Site',
    defaultOpen: true,
    badge: { type: 'count', value: '0 pages' },
    items: [
      { id: 'site-structure', label: 'Structure', path: '/flow', panel: 'site-structure' },
      { id: 'site-pages', label: 'Pages', path: '/flow', panel: 'site-pages' },
      { id: 'site-theme', label: 'Thème', path: '/flow', panel: 'site-theme' },
    ]
  },
  {
    id: 'tools',
    label: 'Outils',
    defaultOpen: false,
    items: [
      { id: 'data-explorer', label: 'Data Explorer', path: '/data/explorer' },
      { id: 'live-preview', label: 'Live Preview', path: '/data/preview' },
      { id: 'showcase', label: 'Showcase', path: '/showcase' },
      { id: 'settings', label: 'Paramètres', path: '/tools/settings' },
      { id: 'config-editor', label: 'Config Editor', path: '/tools/config-editor' },
      { id: 'plugins', label: 'Plugins', path: '/tools/plugins' },
      { id: 'docs', label: 'Documentation', path: '/tools/docs' }
    ]
  },
  {
    id: 'legacy',
    label: 'Legacy',
    defaultOpen: false,
    items: [
      { id: 'demo-entity', label: 'Demo Entity', path: '/legacy/demos/entity-centric' },
      { id: 'demo-pipeline', label: 'Demo Pipeline', path: '/legacy/demos/pipeline-visual' },
      { id: 'demo-wizard', label: 'Demo Wizard', path: '/legacy/demos/wizard-form' },
      { id: 'demo-goal', label: 'Demo Goal', path: '/legacy/demos/goal-driven' },
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
