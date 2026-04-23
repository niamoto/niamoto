import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { FolderOpen, Loader2 } from 'lucide-react'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import {
  usePipelineStatus,
  type FreshnessStatus,
} from '@/hooks/usePipelineStatus'
import { cn } from '@/lib/utils'
import { useNavigationStore } from '@/stores/navigationStore'

const routeToStage: Record<string, 'data' | 'groups' | 'site' | 'publication'> =
  {
    '/sources': 'data',
    '/groups': 'groups',
    '/site': 'site',
    '/publish': 'publication',
  }

const stageLabels: Record<
  'data' | 'groups' | 'site' | 'publication',
  {
    freshKey: string
    freshFallback: string
    staleKey: string
    staleFallback: string
    errorFallback: string
  }
> = {
  data: {
    freshKey: 'pipeline.data_fresh',
    freshFallback: 'Data ready',
    staleKey: 'pipeline.data_stale',
    staleFallback: 'Data stale',
    errorFallback: 'Data error',
  },
  groups: {
    freshKey: 'pipeline.collections_fresh',
    freshFallback: 'Collections ready',
    staleKey: 'pipeline.collections_stale',
    staleFallback: 'Collections stale',
    errorFallback: 'Collections error',
  },
  site: {
    freshKey: 'pipeline.site_fresh',
    freshFallback: 'Site ready',
    staleKey: 'pipeline.site_stale',
    staleFallback: 'Site stale',
    errorFallback: 'Site error',
  },
  publication: {
    freshKey: 'pipeline.publication_fresh',
    freshFallback: 'Publish ready',
    staleKey: 'pipeline.publication_stale',
    staleFallback: 'Publish stale',
    errorFallback: 'Publish error',
  },
}

function getDisplayStatus(
  stage: 'data' | 'groups' | 'site' | 'publication' | null,
  status: FreshnessStatus,
  itemStatuses: FreshnessStatus[] = []
): FreshnessStatus {
  if (stage !== 'groups' || itemStatuses.length === 0) {
    return status
  }

  const hasStale = itemStatuses.includes('stale')
  const hasNeverRun = itemStatuses.includes('never_run')

  if (!hasStale && hasNeverRun) {
    return 'never_run'
  }

  return status
}

function getStatusTone(status: FreshnessStatus) {
  return cn(
    'border',
    status === 'fresh' &&
      'border-emerald-500/25 bg-emerald-500/8 text-emerald-700 dark:text-emerald-300',
    status === 'stale' &&
      'border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300',
    status === 'running' &&
      'border-blue-500/25 bg-blue-500/10 text-blue-700 dark:text-blue-300',
    status === 'error' &&
      'border-red-500/25 bg-red-500/10 text-red-700 dark:text-red-300'
  )
}

export function DesktopStatusBar() {
  const { t } = useTranslation('common')
  const location = useLocation()
  const { data: projectInfo } = useProjectInfo()
  const { data: pipeline } = usePipelineStatus()
  const breadcrumbs = useNavigationStore((state) => state.breadcrumbs)

  const currentLabel =
    breadcrumbs[breadcrumbs.length - 1]?.label ?? t('sidebar.nav.home', 'Home')
  const projectLabel = projectInfo?.name ?? t('project.none_selected', 'No project')

  const matchedPrefix =
    Object.keys(routeToStage).find(
      (prefix) =>
        location.pathname === prefix || location.pathname.startsWith(prefix + '/')
    ) ?? null

  const stage = matchedPrefix ? routeToStage[matchedPrefix] : null
  const stageData = stage && pipeline ? pipeline[stage] : null
  const displayStatus = getDisplayStatus(
    stage,
    stageData?.status ?? 'never_run',
    stageData?.items?.map((item) => item.status) ?? []
  )

  let statusCopy:
    | {
        label: string
        status: 'fresh' | 'stale' | 'running' | 'error'
      }
    | null = null

  if (pipeline?.running_job) {
    statusCopy = {
      label: pipeline.running_job.message || t('pipeline.running', 'Processing...'),
      status: 'running',
    }
  } else if (
    stage &&
    stageData &&
    displayStatus !== 'never_run' &&
    displayStatus !== 'unconfigured' &&
    displayStatus !== 'running'
  ) {
    if (displayStatus === 'fresh') {
      statusCopy = {
        label: t(
          stageLabels[stage].freshKey,
          stageLabels[stage].freshFallback
        ),
        status: displayStatus,
      }
    } else if (displayStatus === 'stale') {
      statusCopy = {
        label: t(
          stageLabels[stage].staleKey,
          stageLabels[stage].staleFallback
        ),
        status: displayStatus,
      }
    } else if (displayStatus === 'error') {
      statusCopy = {
        label: stageLabels[stage].errorFallback,
        status: displayStatus,
      }
    }
  }

  return (
    <footer className="flex h-9 items-center gap-2.5 border-t border-border/70 bg-sidebar/45 px-3 text-[11px] text-muted-foreground supports-[backdrop-filter]:bg-sidebar/70 supports-[backdrop-filter]:backdrop-blur-md">
      <div className="flex min-w-0 items-center gap-2.5">
        <div className="inline-flex min-w-0 items-center gap-1.5 rounded-theme-sm bg-background/80 px-2 py-1 text-foreground/90 shadow-none">
          <FolderOpen className="h-3.5 w-3.5 shrink-0 text-foreground/55" />
          <span className="max-w-36 truncate font-medium lg:max-w-52">
            {projectLabel}
          </span>
        </div>

        <span className="hidden h-3.5 w-px bg-border/80 md:block" />

        <span className="hidden truncate md:inline">{currentLabel}</span>

        {statusCopy && (
          <div
            className={cn(
              'inline-flex max-w-56 items-center gap-1.5 rounded-full px-2 py-0.5 font-medium lg:max-w-72',
              getStatusTone(statusCopy.status)
            )}
          >
            {statusCopy.status === 'running' ? (
              <Loader2 className="h-3 w-3 shrink-0 animate-spin" />
            ) : (
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-current opacity-80" />
            )}
            <span className="truncate">{statusCopy.label}</span>
          </div>
        )}
      </div>
    </footer>
  )
}
