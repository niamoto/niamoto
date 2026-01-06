import { NavLink, useLocation } from 'react-router-dom'
import { useMemo } from 'react'
import * as Collapsible from '@radix-ui/react-collapsible'
import { cn } from '@/lib/utils'
import {
  Database,
  FileSpreadsheet,
  Leaf,
  MapPin,
  Map,
  FolderTree,
  FileText,
  Palette,
  Search,
  Eye,
  Settings,
  Puzzle,
  BookOpen,
  Layers,
  Archive,
  ChevronRight,
  ChevronDown,
  Menu,
  ExternalLink,
  Upload,
  LayoutDashboard,
  Table2,
  FlaskConical,
  ListCollapse,
  Combine,
  PaintBucket,
  type LucideIcon
} from 'lucide-react'
import { useNavigationStore, navigationSections, type NavigationSection, type NavigationItem } from '@/stores/navigationStore'
import { useReferences } from '@/hooks/useReferences'
import { useDatasets } from '@/hooks/useDatasets'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import niamotoLogo from '@/assets/niamoto_logo.png'

// Icon mapping for sections
const sectionIconMap: Record<string, LucideIcon> = {
  sources: Database,
  groups: Layers,
  site: FolderTree,
  tools: Settings,
  legacy: Archive,
  labs: FlaskConical
}

// Icon mapping for items
const itemIconMap: Record<string, LucideIcon> = {
  // Sources - static items
  import: Upload,
  dashboard: LayoutDashboard,
  'data-overview': FileSpreadsheet,
  // Sources - dynamic items (datasets)
  occurrences: Table2,
  // Groups
  'groups-index': Layers,
  taxons: Leaf,
  plots: MapPin,
  shapes: Map,
  // Site
  'site-structure': FolderTree,
  'site-pages': FileText,
  'site-theme': Palette,
  // Tools
  'data-explorer': Search,
  'live-preview': Eye,
  showcase: Layers,
  'config-editor': FileText,
  plugins: Puzzle,
  docs: BookOpen,
  // Legacy
  'demo-entity': Archive,
  'demo-pipeline': Archive,
  'demo-wizard': Archive,
  'demo-goal': Archive,
  // Labs
  'labs-index': FlaskConical,
  'mockup-hybrid': Combine,
  'mockup-canvas': PaintBucket,
  'mockup-inline': ListCollapse
}

// Get icon for a reference kind
function getReferenceIcon(kind: string): LucideIcon {
  switch (kind) {
    case 'hierarchical':
      return Leaf
    case 'spatial':
      return Map
    default:
      return MapPin
  }
}

interface NavigationSidebarProps {
  className?: string
}

export function NavigationSidebar({ className }: NavigationSidebarProps) {
  const location = useLocation()
  const {
    sidebarMode,
    expandedSections,
    toggleSection,
    toggleSidebar,
  } = useNavigationStore()

  // Fetch datasets and references dynamically
  const { data: datasetsData } = useDatasets()
  const { data: referencesData } = useReferences()
  const datasets = datasetsData?.datasets ?? []
  const references = referencesData?.references ?? []

  // Build navigation sections with dynamic items
  const sections = useMemo(() => {
    return navigationSections.map(section => {
      // Sources section: add datasets and references dynamically
      if (section.id === 'sources' && section.dynamic) {
        const sourceItems: NavigationItem[] = [
          // Static items first
          { id: 'dashboard', label: 'Dashboard', path: '/sources' },
          { id: 'import', label: 'Import', path: '/sources/import' },
        ]

        // Add datasets
        if (datasets.length > 0) {
          datasets.forEach(ds => {
            sourceItems.push({
              id: `dataset-${ds.name}`,
              label: ds.name,
              path: `/sources/dataset/${ds.name}`,
              badge: ds.entity_count,
            })
          })
        }

        // Add references
        if (references.length > 0) {
          references.forEach(ref => {
            sourceItems.push({
              id: `ref-${ref.name}`,
              label: ref.name,
              path: `/sources/reference/${ref.name}`,
              badge: ref.entity_count,
              icon: ref.kind,
            })
          })
        }

        const totalEntities = datasets.length + references.length
        return {
          ...section,
          badge: totalEntities > 0
            ? { type: 'count' as const, value: totalEntities }
            : { type: 'status' as const, value: 'Vide' },
          items: sourceItems
        }
      }

      // Groups section: references for widget configuration
      if (section.id === 'groups' && section.dynamic) {
        const groupItems: NavigationItem[] = [
          { id: 'groups-index', label: 'Vue d\'ensemble', path: '/groups' },
        ]

        references.forEach(ref => {
          groupItems.push({
            id: `group-${ref.name}`,
            label: ref.name,
            path: `/groups/${ref.name}`,
            badge: ref.entity_count,
            icon: ref.kind
          })
        })

        return {
          ...section,
          badge: { type: 'count' as const, value: references.length },
          items: groupItems
        }
      }

      return section
    })
  }, [datasets, references])

  if (sidebarMode === 'hidden') {
    return null
  }

  const isCompact = sidebarMode === 'compact'

  const handleItemClick = (item: NavigationItem, e: React.MouseEvent) => {
    if (item.action === 'add') {
      e.preventDefault()
      // TODO: Open add group dialog
      console.log('Add group clicked')
      return
    }
    // Navigation is handled by NavLink, no need for manual navigation
  }

  const isItemActive = (item: NavigationItem) => {
    if (!item.path) return false
    // Exact match only - no parent highlighting
    return location.pathname === item.path
  }

  return (
    <div
      className={cn(
        'flex h-full flex-col border-r bg-background transition-all duration-200',
        isCompact ? 'w-16' : 'w-64',
        className
      )}
    >
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-3">
        {!isCompact && (
          <div className="flex items-center gap-2">
            <img
              src={niamotoLogo}
              alt="Niamoto"
              className="h-8 w-8 object-contain"
            />
            <span className="text-lg font-bold text-primary">Niamoto</span>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className={cn('h-8 w-8', isCompact && 'mx-auto')}
        >
          <Menu className="h-4 w-4" />
        </Button>
      </div>

      {/* Navigation Content */}
      <div className="flex-1 overflow-y-auto py-2">
        <nav className="space-y-1 px-2">
          {sections.map((section) => (
            <SectionComponent
              key={section.id}
              section={section}
              isCompact={isCompact}
              isExpanded={expandedSections.includes(section.id)}
              onToggle={() => toggleSection(section.id)}
              onItemClick={handleItemClick}
              isItemActive={isItemActive}
            />
          ))}
        </nav>
      </div>

      {/* Footer with Settings and Preview */}
      <div className="border-t p-3 space-y-2">
        {!isCompact ? (
          <>
            <NavLink
              to="/tools/settings"
              className={({ isActive }) =>
                cn(
                  'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-accent text-accent-foreground font-medium'
                )
              }
            >
              <Settings className="h-4 w-4" />
              Paramètres
            </NavLink>
            <Button
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={() => window.open('/preview', '_blank')}
            >
              <Eye className="h-4 w-4" />
              Prévisualiser le site
              <ExternalLink className="ml-auto h-3 w-3 opacity-50" />
            </Button>
          </>
        ) : (
          <>
            <NavLink
              to="/tools/settings"
              className={({ isActive }) =>
                cn(
                  'flex h-8 w-8 items-center justify-center rounded-md transition-colors mx-auto',
                  'hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-accent text-accent-foreground'
                )
              }
              title="Paramètres"
            >
              <Settings className="h-4 w-4" />
            </NavLink>
            <Button
              variant="ghost"
              size="icon"
              className="mx-auto flex"
              title="Prévisualiser le site"
              onClick={() => window.open('/preview', '_blank')}
            >
              <Eye className="h-4 w-4" />
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

// Section component for cleaner code
function SectionComponent({
  section,
  isCompact,
  isExpanded,
  onToggle,
  onItemClick,
  isItemActive
}: {
  section: NavigationSection
  isCompact: boolean
  isExpanded: boolean
  onToggle: () => void
  onItemClick: (item: NavigationItem, e: React.MouseEvent) => void
  isItemActive: (item: NavigationItem) => boolean
}) {
  const SectionIcon = sectionIconMap[section.id] || Layers

  return (
    <Collapsible.Root
      open={!isCompact && isExpanded}
      onOpenChange={() => !isCompact && onToggle()}
    >
      {/* Section Header */}
      <Collapsible.Trigger asChild>
        <button
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors',
            'hover:bg-accent/50 hover:text-foreground',
            isCompact && 'justify-center'
          )}
          title={isCompact ? section.label : undefined}
        >
          <SectionIcon className="h-3.5 w-3.5 shrink-0" />
          {!isCompact && (
            <>
              <span className="flex-1 text-left">{section.label}</span>
              {section.badge && (
                <Badge
                  variant={section.badge.type === 'status' ? 'secondary' : 'outline'}
                  className="h-5 px-1.5 text-[10px] font-normal"
                >
                  {section.badge.value}
                </Badge>
              )}
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 opacity-50" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 opacity-50" />
              )}
            </>
          )}
        </button>
      </Collapsible.Trigger>

      {/* Section Items */}
      {!isCompact && (
        <Collapsible.Content className="mt-0.5 space-y-0.5">
          {section.items.map((item) => (
            <ItemComponent
              key={item.id}
              item={item}
              isActive={isItemActive(item)}
              onClick={onItemClick}
            />
          ))}
        </Collapsible.Content>
      )}

      {/* Compact mode - show items as icons */}
      {isCompact && isExpanded && (
        <div className="mt-1 space-y-1">
          {section.items.slice(0, 3).map((item) => {
            const ItemIcon = item.icon
              ? getReferenceIcon(item.icon)
              : itemIconMap[item.id] || FileText
            const isActive = isItemActive(item)

            return (
              <NavLink
                key={item.id}
                to={item.path || '#'}
                onClick={(e) => onItemClick(item, e)}
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-md transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-accent text-accent-foreground',
                  'mx-auto'
                )}
                title={item.label}
              >
                <ItemIcon className="h-4 w-4" />
              </NavLink>
            )
          })}
        </div>
      )}
    </Collapsible.Root>
  )
}

// Item component
function ItemComponent({
  item,
  isActive,
  onClick
}: {
  item: NavigationItem
  isActive: boolean
  onClick: (item: NavigationItem, e: React.MouseEvent) => void
}) {
  const ItemIcon = item.icon
    ? getReferenceIcon(item.icon)
    : itemIconMap[item.id] || FileText

  if (item.action) {
    return (
      <button
        onClick={(e) => onClick(item, e)}
        className={cn(
          'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
          'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
          'ml-2'
        )}
      >
        <ItemIcon className="h-4 w-4 shrink-0 opacity-70" />
        <span className="flex-1 text-left">{item.label}</span>
      </button>
    )
  }

  return (
    <NavLink
      to={item.path || '#'}
      onClick={(e) => onClick(item, e)}
      className={cn(
        'flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
        'hover:bg-accent hover:text-accent-foreground',
        isActive && 'bg-accent text-accent-foreground font-medium',
        'ml-2'
      )}
    >
      <ItemIcon className="h-4 w-4 shrink-0" />
      <span className="flex-1">{item.label}</span>
      {item.badge !== undefined && (
        <span className="text-xs text-muted-foreground tabular-nums">
          {item.badge}
        </span>
      )}
    </NavLink>
  )
}
