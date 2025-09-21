import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import * as Collapsible from '@radix-ui/react-collapsible'
import { cn } from '@/lib/utils'
import {
  Upload,
  Settings,
  Download,
  Database,
  Search,
  Eye,
  Wrench,
  FileText,
  ChevronRight,
  ChevronDown,
  Menu,
  Layers,
  Package,
  FlaskConical
} from 'lucide-react'
import { useNavigationStore, navigationSections } from '@/stores/navigationStore'
import { Button } from '@/components/ui/button'
import niamotoLogo from '@/assets/niamoto_logo.png'

// Icon mapping
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  import: Upload,
  transform: Settings,
  export: Download,
  explorer: Search,
  preview: Eye,
  settings: Wrench,
  plugins: Package,
  docs: FileText,
  'pipeline-editor': Layers
}

const sectionIconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  pipeline: Layers,
  data: Database,
  tools: Wrench,
  demos: FlaskConical
}

interface NavigationSidebarProps {
  className?: string
}

export function NavigationSidebar({ className }: NavigationSidebarProps) {
  const location = useLocation()
  const { t } = useTranslation()
  const {
    sidebarMode,
    expandedSections,
    toggleSection,
    toggleSidebar
  } = useNavigationStore()

  if (sidebarMode === 'hidden') {
    return null
  }

  const isCompact = sidebarMode === 'compact'

  return (
    <div
      className={cn(
        'flex h-full flex-col border-r bg-background transition-all duration-200',
        isCompact ? 'w-16' : 'w-64',
        className
      )}
    >
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        {!isCompact && (
          <div className="flex items-center gap-2">
            <img
              src={niamotoLogo}
              alt={t('app.logo')}
              className="h-10 w-10 object-contain"
            />
            <h1 className="text-lg font-bold text-primary">
              {t('app.title', 'Niamoto')}
            </h1>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className={cn(isCompact && 'mx-auto')}
        >
          <Menu className="h-4 w-4" />
        </Button>
      </div>

      {/* Navigation Content */}
      <div className="flex-1 overflow-y-auto py-4">
        <nav className="space-y-2 px-2">
          {navigationSections.map((section) => {
            const SectionIcon = sectionIconMap[section.id] || Layers
            const isExpanded = expandedSections.includes(section.id)

            return (
              <Collapsible.Root
                key={section.id}
                open={!isCompact && isExpanded}
                onOpenChange={() => !isCompact && toggleSection(section.id)}
              >
                {/* Section Header */}
                <Collapsible.Trigger asChild>
                  <button
                    className={cn(
                      'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                      isCompact && 'justify-center'
                    )}
                    title={isCompact ? section.label : undefined}
                  >
                    <SectionIcon className="h-4 w-4 shrink-0" />
                    {!isCompact && (
                      <>
                        <span className="flex-1 text-left">
                          {t(`navigation.sections.${section.id}`, section.label)}
                        </span>
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </>
                    )}
                  </button>
                </Collapsible.Trigger>

                {/* Section Items */}
                {!isCompact && (
                  <Collapsible.Content className="mt-1 space-y-1">
                    {section.items.map((item) => {
                      const ItemIcon = iconMap[item.id] || FileText
                      const isActive = location.pathname === item.path

                      return (
                        <NavLink
                          key={item.id}
                          to={item.path}
                          className={cn(
                            'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors',
                            'hover:bg-accent hover:text-accent-foreground',
                            isActive && 'bg-accent text-accent-foreground font-medium',
                            'ml-4' // Indent for hierarchy
                          )}
                        >
                          <ItemIcon className="h-4 w-4 shrink-0" />
                          <span className="flex-1">
                            {t(`navigation.${item.id}`, item.label)}
                          </span>
                          {item.badge && (
                            <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                              {item.badge}
                            </span>
                          )}
                        </NavLink>
                      )
                    })}
                  </Collapsible.Content>
                )}

                {/* Compact mode - show items as icons */}
                {isCompact && (
                  <div className="mt-1 space-y-1">
                    {section.items.map((item) => {
                      const ItemIcon = iconMap[item.id] || FileText
                      const isActive = location.pathname === item.path

                      return (
                        <NavLink
                          key={item.id}
                          to={item.path}
                          className={cn(
                            'flex h-10 w-10 items-center justify-center rounded-lg transition-colors',
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
          })}
        </nav>
      </div>

      {/* Footer */}
      <div className="border-t p-4">
        {!isCompact ? (
          <div className="text-xs text-muted-foreground">
            {t('app.description', 'Ecological Data Platform')}
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="text-xs text-muted-foreground">v1.0</span>
          </div>
        )}
      </div>
    </div>
  )
}
