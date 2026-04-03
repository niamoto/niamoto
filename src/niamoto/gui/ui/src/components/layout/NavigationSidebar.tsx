import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import {
  Settings,
  PanelLeft,
  Command,
} from 'lucide-react'
import { useNavigationStore, navItems } from '@/stores/navigationStore'
import { Button } from '@/components/ui/button'
import niamotoLogo from '@/assets/niamoto_logo.png'

interface NavigationSidebarProps {
  className?: string
}

export function NavigationSidebar({ className }: NavigationSidebarProps) {
  const { t } = useTranslation('common')
  const location = useLocation()
  const {
    sidebarMode,
    toggleSidebar,
    setCommandPaletteOpen,
  } = useNavigationStore()

  if (sidebarMode === 'hidden') {
    return null
  }

  const isCompact = sidebarMode === 'compact'

  const isActive = (matchPrefix: string) => {
    // Home ("/") must be exact match to avoid highlighting on every route
    if (matchPrefix === '/') return location.pathname === '/'
    return location.pathname === matchPrefix || location.pathname.startsWith(matchPrefix + '/')
  }

  return (
    <div
      className={cn(
        'flex h-full flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-200',
        isCompact ? 'w-16' : 'w-52',
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
          <PanelLeft className="h-4 w-4" />
        </Button>
      </div>

      {/* Navigation — Flat rail */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.matchPrefix)

          return (
            <NavLink
              key={item.id}
              to={item.path}
              className={cn(
                'flex items-center gap-3 rounded-theme-md px-3 py-2.5 text-sm font-medium transition-theme-fast',
                'hover:bg-accent hover:text-accent-foreground',
                active && 'bg-accent text-accent-foreground',
                !active && 'text-muted-foreground',
                isCompact && 'justify-center px-0'
              )}
              title={isCompact ? t(item.labelKey, item.fallbackLabel) : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!isCompact && (
                <span>{t(item.labelKey, item.fallbackLabel)}</span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Cmd+K hint */}
      {!isCompact && (
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="mx-3 mb-2 flex items-center gap-2 rounded-theme-sm px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-theme-fast"
        >
          <Command className="h-3 w-3" />
          <span>K</span>
          <span className="ml-1 opacity-60">{t('sidebar.cmdkHint', 'Outils & recherche')}</span>
        </button>
      )}

      {/* Footer */}
      <div className="border-t p-3 space-y-2">
        {!isCompact ? (
          <>
            <NavLink
              to="/tools/settings"
              className={({ isActive: active }) =>
                cn(
                  'flex w-full items-center gap-2 rounded-theme-sm px-3 py-2 text-sm transition-theme-fast',
                  'hover:bg-accent hover:text-accent-foreground',
                  active && 'bg-accent text-accent-foreground font-medium'
                )
              }
            >
              <Settings className="h-4 w-4" />
              {t('sidebar.footer.settings')}
            </NavLink>
          </>
        ) : (
          <>
            <NavLink
              to="/tools/settings"
              className={({ isActive: active }) =>
                cn(
                  'flex h-8 w-8 items-center justify-center rounded-theme-sm transition-theme-fast mx-auto',
                  'hover:bg-accent hover:text-accent-foreground',
                  active && 'bg-accent text-accent-foreground'
                )
              }
              title={t('sidebar.footer.settings')}
            >
              <Settings className="h-4 w-4" />
            </NavLink>
            <Button
              variant="ghost"
              size="icon"
              className="mx-auto flex"
              title="⌘K"
              onClick={() => setCommandPaletteOpen(true)}
            >
              <Command className="h-3.5 w-3.5" />
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
