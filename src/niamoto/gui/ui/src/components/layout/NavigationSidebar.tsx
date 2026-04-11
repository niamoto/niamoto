import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import {
  Settings,
  Command,
  MessageSquarePlus,
  Loader2,
} from 'lucide-react'
import { useNavigationStore, navItems } from '@/stores/navigationStore'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { usePlatform } from '@/shared/hooks/usePlatform'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { useFeedback, useBrowserOnline } from '@/features/feedback'
import { ProjectSwitcher } from '@/components/common'
import { useReferences } from '@/hooks/useReferences'
import niamotoLogo from '@/assets/niamoto_logo.png'

interface NavigationSidebarProps {
  className?: string
  showHeader?: boolean
}

export function NavigationSidebar({ className, showHeader = true }: NavigationSidebarProps) {
  const { t } = useTranslation('common')
  const location = useLocation()
  const {
    sidebarMode,
    setCommandPaletteOpen,
  } = useNavigationStore()
  const { isMac } = usePlatform()
  const { isDesktop, features } = useRuntimeMode()
  const feedback = useFeedback()
  const browserOnline = useBrowserOnline()
  const feedbackDisabled = !browserOnline || feedback.cooldownRemaining > 0 || feedback.isPreparingScreenshot

  const collectionsRouteActive =
    location.pathname === '/groups' || location.pathname.startsWith('/groups/')
  const { data: referencesData } = useReferences()
  const references = referencesData?.references ?? []
  const activeCollectionName = collectionsRouteActive
    ? decodeURIComponent(location.pathname.replace(/^\/groups\/?/, '').split('/')[0] ?? '')
    : ''

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
          isCompact ? (isMac && isDesktop ? 'w-20' : 'w-16') : 'w-52',
          className
        )}
      >
      {/* Header — on macOS the space is reserved for window traffic lights.
          On other platforms, shows the Niamoto brand. */}
      {showHeader && (
        <div
          data-tauri-drag-region={isMac && isDesktop ? true : undefined}
          className={cn(
            'flex h-14 shrink-0 items-center border-b',
            isCompact ? 'justify-center px-0' : 'gap-2 px-4'
          )}
        >
          {!(isMac && isDesktop) && (
            <>
              <img
                src={niamotoLogo}
                alt="Niamoto"
                className="h-7 w-7 shrink-0 object-contain"
              />
              {!isCompact && (
                <span className="text-base font-semibold tracking-tight text-foreground">
                  Niamoto
                </span>
              )}
            </>
          )}
        </div>
      )}

      <div className="flex flex-1 flex-col">
        {/* Workspace: project switcher */}
        {features.project_switching && (
          <div
            className={cn(
              'border-b px-3 py-3',
              isCompact && 'flex justify-center px-2'
            )}
          >
            <ProjectSwitcher compact={isCompact} />
          </div>
        )}

        {/* Navigation — Flat rail */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.matchPrefix)
            const showCollectionsChildren =
              item.id === 'groups' && collectionsRouteActive && !isCompact && references.length > 0

            return (
              <div key={item.id}>
                <NavLink
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

                {showCollectionsChildren && (
                  <ul className="mt-1 ml-4 border-l border-border/60 pl-2 space-y-0.5">
                    {references.map((ref) => {
                      const isCurrent = ref.name === activeCollectionName
                      return (
                        <li key={ref.name}>
                          <NavLink
                            to={`/groups/${encodeURIComponent(ref.name)}`}
                            className={cn(
                              'flex items-center gap-2 rounded-theme-sm px-2 py-1.5 text-xs transition-theme-fast',
                              'hover:bg-accent hover:text-accent-foreground',
                              isCurrent
                                ? 'bg-accent text-accent-foreground font-medium'
                                : 'text-muted-foreground'
                            )}
                            title={ref.name}
                          >
                            <span
                              className={cn(
                                'h-1.5 w-1.5 rounded-full shrink-0',
                                isCurrent ? 'bg-primary' : 'bg-muted-foreground/40'
                              )}
                            />
                            <span className="truncate">{ref.name}</span>
                          </NavLink>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
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
              <div className="flex items-center gap-1">
                <NavLink
                  to="/tools/settings"
                  className={({ isActive: active }) =>
                    cn(
                      'flex flex-1 items-center gap-2 rounded-theme-sm px-3 py-2 text-sm transition-theme-fast',
                      'hover:bg-accent hover:text-accent-foreground',
                      active && 'bg-accent text-accent-foreground font-medium'
                    )
                  }
                >
                  <Settings className="h-4 w-4" />
                  {t('sidebar.footer.settings')}
                </NavLink>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => feedback.openWithType('bug')}
                      disabled={feedbackDisabled}
                      aria-label={t('feedback:button_label')}
                      className={cn(
                        'flex h-8 w-8 shrink-0 items-center justify-center rounded-theme-sm transition-theme-fast',
                        'hover:bg-accent hover:text-accent-foreground text-muted-foreground',
                        feedbackDisabled && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      {feedback.isPreparingScreenshot ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <MessageSquarePlus className="h-4 w-4" />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    {!browserOnline
                      ? t('feedback:offline_tooltip')
                      : feedback.cooldownRemaining > 0
                        ? t('feedback:cooldown', { seconds: feedback.cooldownRemaining })
                        : t('feedback:button_label')}
                  </TooltipContent>
                </Tooltip>
              </div>
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
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => feedback.openWithType('bug')}
                    disabled={feedbackDisabled}
                    aria-label={t('feedback:button_label')}
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-theme-sm transition-theme-fast mx-auto',
                      'hover:bg-accent hover:text-accent-foreground text-muted-foreground',
                      feedbackDisabled && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    {feedback.isPreparingScreenshot ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <MessageSquarePlus className="h-4 w-4" />
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  {!browserOnline
                    ? t('feedback:offline_tooltip')
                    : feedback.cooldownRemaining > 0
                      ? t('feedback:cooldown', { seconds: feedback.cooldownRemaining })
                      : t('feedback:button_label')}
                </TooltipContent>
              </Tooltip>
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
    </div>
  )
}
