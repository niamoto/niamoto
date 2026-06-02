import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import {
  Settings,
  MessageSquarePlus,
  Loader2,
} from 'lucide-react'
import { useNavigationStore, navItems } from '@/stores/navigationStore'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { usePlatform } from '@/shared/hooks/usePlatform'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { useFeedback, useBrowserOnline } from '@/features/feedback'
import { ProjectSwitcher } from '@/components/common'
import { useReferences } from '@/hooks/useReferences'
import { usePipelineStatus } from '@/hooks/usePipelineStatus'
import { useCollectionsCatalog } from '@/features/collections/hooks/useCollectionsCatalog'
import {
  applyCompletedTransformGroups,
  getCurrentTransformBatchGroup,
  getTransformActivityByGroup,
  type TransformGroupActivity,
} from '@/features/collections/hooks/useCollectionTransforms'
import {
  buildCollectionDisplayItems,
  defaultCollectionTab,
} from '@/features/collections/utils/collectionDisplay'
import { buildCollectionsPath } from '@/features/collections/routing'
import { useNotificationStore } from '@/stores/notificationStore'
import { useTheme } from '@/stores/themeStore'
import { getNiamotoLogoSrc } from '@/shared/branding/niamotoLogo'

interface NavigationSidebarProps {
  className?: string
  showHeader?: boolean
}

export function NavigationSidebar({ className, showHeader = true }: NavigationSidebarProps) {
  const { t } = useTranslation('common')
  const location = useLocation()
  const { sidebarMode } = useNavigationStore()
  const { resolvedMode } = useTheme()
  const { isMac } = usePlatform()
  const { isDesktop, features } = useRuntimeMode()
  const feedback = useFeedback()
  const browserOnline = useBrowserOnline()
  const feedbackDisabled = !browserOnline || feedback.cooldownRemaining > 0 || feedback.isPreparingScreenshot

  const collectionsRouteActive =
    location.pathname === '/groups' || location.pathname.startsWith('/groups/')
  const {
    data: referencesData,
    isLoading: referencesLoading,
  } = useReferences()
  const references = useMemo(
    () => referencesData?.references ?? [],
    [referencesData],
  )
  const {
    data: catalogData,
    isLoading: catalogLoading,
  } = useCollectionsCatalog({
    enabled: collectionsRouteActive,
  })
  const { data: pipelineStatus } = usePipelineStatus(collectionsRouteActive)
  const trackedJobs = useNotificationStore((state) => state.trackedJobs)
  const [transformProgressMemory, setTransformProgressMemory] = useState<{
    jobId: string | null
    currentGroup: string | null
    completedGroups: string[]
  }>({ jobId: null, currentGroup: null, completedGroups: [] })
  const catalogCollections = useMemo(
    () => catalogData?.collections ?? [],
    [catalogData],
  )
  const collections = useMemo(
    () => buildCollectionDisplayItems(
      references,
      catalogCollections,
    ),
    [catalogCollections, references],
  )
  const collectionsNavLoading =
    collectionsRouteActive
    && (
      (referencesLoading && !referencesData)
      || (catalogLoading && !catalogData)
    )
  const runningTransformJob = pipelineStatus?.running_job?.type === 'transform'
    ? pipelineStatus.running_job
    : null
  const trackedTransformJob = trackedJobs.find((job) => job.jobType === 'transform') ?? null
  const activeTransformJobId = runningTransformJob?.id ?? trackedTransformJob?.jobId ?? null
  const currentRunningTransformGroup = getCurrentTransformBatchGroup(runningTransformJob?.message)
  const hasObservedCurrentGroup =
    activeTransformJobId !== null
    && transformProgressMemory.jobId === activeTransformJobId
    && (
      transformProgressMemory.currentGroup !== null
      || transformProgressMemory.completedGroups.length > 0
    )

  /* eslint-disable react-hooks/set-state-in-effect --
     The sidebar keeps short-lived progress memory from the external transform job stream. */
  useEffect(() => {
    setTransformProgressMemory((previous) => {
      if (!activeTransformJobId) {
        if (
          previous.jobId === null
          && previous.currentGroup === null
          && previous.completedGroups.length === 0
        ) {
          return previous
        }
        return { jobId: null, currentGroup: null, completedGroups: [] }
      }

      if (previous.jobId !== activeTransformJobId) {
        return {
          jobId: activeTransformJobId,
          currentGroup: currentRunningTransformGroup,
          completedGroups: [],
        }
      }

      if (currentRunningTransformGroup) {
        const completedGroups =
          previous.currentGroup
          && previous.currentGroup !== currentRunningTransformGroup
          && !previous.completedGroups.includes(previous.currentGroup)
            ? [...previous.completedGroups, previous.currentGroup]
            : previous.completedGroups

        if (
          previous.currentGroup === currentRunningTransformGroup
          && completedGroups === previous.completedGroups
        ) {
          return previous
        }

        return {
          jobId: activeTransformJobId,
          currentGroup: currentRunningTransformGroup,
          completedGroups,
        }
      }

      if (!runningTransformJob && previous.currentGroup) {
        const completedGroups = previous.completedGroups.includes(previous.currentGroup)
          ? previous.completedGroups
          : [...previous.completedGroups, previous.currentGroup]
        return {
          jobId: activeTransformJobId,
          currentGroup: null,
          completedGroups,
        }
      }

      return previous
    })
  }, [activeTransformJobId, currentRunningTransformGroup, runningTransformJob])
  /* eslint-enable react-hooks/set-state-in-effect */

  const baseTransformActivityByGroup = useMemo(
    () => getTransformActivityByGroup({
      runningJob: runningTransformJob,
      trackedJobs: runningTransformJob || !hasObservedCurrentGroup ? trackedJobs : [],
    }),
    [hasObservedCurrentGroup, runningTransformJob, trackedJobs]
  )
  const transformActivityByGroup = useMemo(
    () => applyCompletedTransformGroups(
      baseTransformActivityByGroup,
      transformProgressMemory.jobId === activeTransformJobId
        ? transformProgressMemory.completedGroups
        : []
    ),
    [
      activeTransformJobId,
      baseTransformActivityByGroup,
      transformProgressMemory.completedGroups,
      transformProgressMemory.jobId,
    ]
  )
  const collectionStatusByName = useMemo(() => {
    const statuses = new Map<string, string>()
    for (const item of pipelineStatus?.groups?.items ?? []) {
      statuses.set(item.name, item.status)
    }
    return statuses
  }, [pipelineStatus?.groups?.items])
  const activeCollectionName = collectionsRouteActive
    ? decodeURIComponent(location.pathname.replace(/^\/groups\/?/, '').split('/')[0] ?? '')
    : ''

  if (sidebarMode === 'hidden') {
    return null
  }

  const isCompact = sidebarMode === 'compact'
  const showDesktopTrafficLightStrip = showHeader && isDesktop && isMac
  const showWebBrandHeader = showHeader && !isDesktop
  const logoSrc = getNiamotoLogoSrc(resolvedMode)

  const isActive = (matchPrefix: string) => {
    // Home ("/") must be exact match to avoid highlighting on every route
    if (matchPrefix === '/') return location.pathname === '/'
    return location.pathname === matchPrefix || location.pathname.startsWith(matchPrefix + '/')
  }

  return (
    <div
      className={cn(
        'flex h-full flex-col border-r border-border/70 bg-sidebar/92 text-sidebar-foreground transition-all duration-200 supports-[backdrop-filter]:bg-sidebar/80 supports-[backdrop-filter]:backdrop-blur-md',
        isCompact ? (isMac && isDesktop ? 'w-20' : 'w-16') : 'w-48',
        className
      )}
    >
      {/* Header behavior:
          - macOS desktop keeps a drag strip for the native traffic lights
          - web shows the Niamoto brand
          - Windows/Linux desktop render no extra header to avoid duplicate branding */}
      {(showDesktopTrafficLightStrip || showWebBrandHeader) && (
        <div
          data-tauri-drag-region={showDesktopTrafficLightStrip ? true : undefined}
          className={cn(
            'flex shrink-0 items-center border-b border-border/70 bg-background/88 supports-[backdrop-filter]:bg-background/75 supports-[backdrop-filter]:backdrop-blur-md',
            showDesktopTrafficLightStrip ? 'h-[39px]' : 'h-10',
            isCompact ? 'justify-center px-0' : 'gap-2 px-4'
          )}
        >
          {showWebBrandHeader && (
            <>
              <img
                src={logoSrc}
                alt="Niamoto"
                className={cn(
                  'h-7 w-7 shrink-0 object-contain',
                  resolvedMode === 'dark' && 'niamoto-brand-logo--dark'
                )}
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
              'border-b border-border/55 px-2.5 py-2.5',
              isCompact && 'flex justify-center px-2'
            )}
          >
            <ProjectSwitcher
              compact={isCompact}
              className={cn(
                'border-border/70 bg-background/70 shadow-none hover:bg-background/85',
                isCompact && 'h-8 w-8'
              )}
            />
          </div>
        )}

        {/* Navigation — Flat rail */}
        <nav className="flex-1 space-y-0.5 px-2 py-2.5">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.matchPrefix)
            const showCollectionsChildren =
              item.id === 'groups'
              && collectionsRouteActive
              && !isCompact
              && (collectionsNavLoading || collections.length > 0)

            return (
              <div key={item.id}>
                <NavLink
                  to={item.path}
                  prefetch="intent"
                  className={cn(
                    'flex items-center gap-2.5 rounded-theme-sm px-2.5 py-1.5 text-[13px] font-medium transition-theme-fast',
                    'hover:bg-background/80 hover:text-foreground',
                    active && 'bg-background/90 text-foreground',
                    !active && 'text-muted-foreground',
                    isCompact && 'justify-center px-0'
                  )}
                  title={isCompact ? t(item.labelKey, item.fallbackLabel) : undefined}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!isCompact && (
                    <span>{t(item.labelKey, item.fallbackLabel)}</span>
                  )}
                </NavLink>

                {showCollectionsChildren && (
                  <ul className="mt-1 ml-4 border-l border-border/60 pl-2 space-y-0.5">
                    {collectionsNavLoading
                      ? Array.from({ length: 3 }).map((_, index) => (
                        <li key={`collection-loading-${index}`}>
                          <div className="flex min-w-0 items-center gap-2 rounded-theme-sm px-2 py-1.5">
                            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/30" />
                            <span className="h-3 flex-1 rounded bg-muted/70" />
                          </div>
                        </li>
                      ))
                      : collections.map((ref) => {
                        const isCurrent = ref.name === activeCollectionName
                        const activity = transformActivityByGroup.get(ref.name)
                        const status = collectionStatusByName.get(ref.name)
                        return (
                          <li key={ref.name}>
                            <NavLink
                              to={buildCollectionsPath(
                                { type: 'collection', name: ref.name },
                                defaultCollectionTab(ref),
                              )}
                              title={ref.name}
                              className={cn(
                                'relative flex min-w-0 items-center gap-2 overflow-hidden rounded-theme-sm px-2 py-1.5 text-[11px] transition-theme-fast',
                                'hover:bg-background/80 hover:text-foreground',
                                activity?.state === 'running' && 'bg-primary/5',
                                isCurrent
                                  ? 'bg-background/90 text-foreground font-medium'
                                  : activity
                                    ? 'text-foreground'
                                    : 'text-muted-foreground'
                              )}
                            >
                              <span
                                className={cn(
                                  'h-1.5 w-1.5 rounded-full shrink-0',
                                  activity?.state === 'running'
                                    ? 'animate-pulse bg-primary ring-2 ring-primary/15'
                                    : activity?.state === 'completed'
                                      ? 'bg-green-500'
                                      : status === 'fresh'
                                        ? 'bg-green-500'
                                        : status === 'stale' || status === 'pending'
                                          ? 'bg-amber-500'
                                          : isCurrent
                                            ? 'bg-primary'
                                            : 'bg-muted-foreground/40'
                                )}
                              />
                              <span className="truncate">{ref.displayName}</span>
                              {activity && (
                                <span
                                  aria-hidden="true"
                                  className="pointer-events-none absolute inset-x-1 bottom-0.5 h-px overflow-hidden rounded-full bg-primary/10"
                                >
                                  <span
                                    className={cn(
                                      'block h-full rounded-full transition-[width] duration-500 ease-out',
                                      activity.state === 'completed' ? 'bg-green-500' : 'bg-primary'
                                    )}
                                    style={{ width: `${getSidebarActivityProgress(activity)}%` }}
                                  />
                                </span>
                              )}
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

        {/* Footer */}
        <div
          className={cn(
            'flex h-9 items-center border-t border-border/60 px-2',
            isCompact ? 'justify-center gap-1' : 'gap-1.5'
          )}
        >
          {!isCompact ? (
            <>
              <NavLink
                to="/tools/settings"
                prefetch="intent"
                className={({ isActive: active }) =>
                  cn(
                    'flex h-7 flex-1 items-center gap-2 rounded-theme-sm px-2.5 text-[13px] transition-theme-fast',
                    'hover:bg-background/80 hover:text-foreground',
                    active && 'bg-background/90 text-foreground font-medium'
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
                      'flex h-7 w-7 shrink-0 items-center justify-center rounded-theme-sm transition-theme-fast',
                      'text-muted-foreground hover:bg-background/80 hover:text-foreground',
                      feedbackDisabled && 'cursor-not-allowed opacity-50'
                    )}
                  >
                    {feedback.isPreparingScreenshot ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <MessageSquarePlus className="h-3.5 w-3.5" />
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
            </>
          ) : (
            <>
              <NavLink
                to="/tools/settings"
                prefetch="intent"
                className={({ isActive: active }) =>
                  cn(
                    'flex h-7 w-7 items-center justify-center rounded-theme-sm transition-theme-fast',
                    'hover:bg-background/80 hover:text-foreground',
                    active && 'bg-background/90 text-foreground'
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
                      'flex h-7 w-7 items-center justify-center rounded-theme-sm transition-theme-fast',
                      'text-muted-foreground hover:bg-background/80 hover:text-foreground',
                      feedbackDisabled && 'cursor-not-allowed opacity-50'
                    )}
                  >
                    {feedback.isPreparingScreenshot ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <MessageSquarePlus className="h-3.5 w-3.5" />
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
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function getSidebarActivityProgress(activity: TransformGroupActivity): number {
  if (activity.state === 'completed') return 100
  return Math.min(100, Math.max(8, activity.progress || 0))
}
