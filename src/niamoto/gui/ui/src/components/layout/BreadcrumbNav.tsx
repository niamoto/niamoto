import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight, Home, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useNavigationStore } from '@/stores/navigationStore'
import { usePipelineStatus, type FreshnessStatus } from '@/hooks/usePipelineStatus'

// Map route prefixes to pipeline stages
const routeToStage: Record<string, 'data' | 'groups' | 'site' | 'publication'> = {
  '/sources': 'data',
  '/groups': 'groups',
  '/site': 'site',
  '/publish': 'publication',
}

const stageLabels: Record<string, { freshKey: string; staleKey: string }> = {
  data: { freshKey: 'pipeline.data_fresh', staleKey: 'pipeline.data_stale' },
  groups: { freshKey: 'pipeline.collections_fresh', staleKey: 'pipeline.collections_stale' },
  site: { freshKey: 'pipeline.site_fresh', staleKey: 'pipeline.site_stale' },
  publication: { freshKey: 'pipeline.publication_fresh', staleKey: 'pipeline.publication_stale' },
}

function StatusDot({ status }: { status: FreshnessStatus }) {
  return (
    <span
      className={cn(
        'inline-block h-1.5 w-1.5 rounded-full',
        status === 'fresh' && 'bg-green-500',
        status === 'stale' && 'bg-amber-500',
        status === 'running' && 'bg-blue-500',
        status === 'error' && 'bg-red-500',
        status === 'never_run' && 'bg-muted-foreground/30'
      )}
    />
  )
}

interface BreadcrumbNavProps {
  className?: string
}

export function BreadcrumbNav({ className }: BreadcrumbNavProps) {
  const { breadcrumbs } = useNavigationStore()
  const { t } = useTranslation('common')
  const location = useLocation()
  const { data: pipeline } = usePipelineStatus()

  if (!breadcrumbs || breadcrumbs.length === 0) {
    return null
  }

  // Detect pipeline stage from current route
  const matchedPrefix = Object.keys(routeToStage).find(
    (prefix) => location.pathname === prefix || location.pathname.startsWith(prefix + '/')
  )
  const stage = matchedPrefix ? routeToStage[matchedPrefix] : null
  const stageData = stage && pipeline ? pipeline[stage] : null

  return (
    <nav
      className={cn(
        'flex h-9 items-center border-b bg-muted/40 px-4',
        className
      )}
      aria-label="Breadcrumb"
    >
      <ol className="flex flex-1 items-center gap-1 text-sm text-muted-foreground">
        {/* Home link */}
        <li>
          <Link
            to="/"
            className="flex items-center gap-1 hover:text-foreground transition-colors"
          >
            <Home className="h-3 w-3" />
          </Link>
        </li>

        {/* Breadcrumb items */}
        {breadcrumbs.map((crumb, index) => {
          const isLast = index === breadcrumbs.length - 1

          return (
            <li key={index} className="flex items-center gap-1">
              <ChevronRight className="h-3 w-3" />
              {crumb.path && !isLast ? (
                <Link
                  to={crumb.path}
                  className="hover:text-foreground transition-colors"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span className={cn(isLast && 'text-foreground font-medium')}>
                  {crumb.label}
                </span>
              )}
            </li>
          )
        })}
      </ol>

      {/* Pipeline status indicator */}
      {stageData && stageData.status !== 'never_run' && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {stageData.status === 'running' ? (
            <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
          ) : (
            <StatusDot status={stageData.status} />
          )}
          <span
            className={cn(
              stageData.status === 'fresh' && 'text-green-600 dark:text-green-400',
              stageData.status === 'stale' && 'text-amber-600 dark:text-amber-400',
              stageData.status === 'running' && 'text-blue-600 dark:text-blue-400'
            )}
          >
            {stageData.status === 'running'
              ? t('pipeline.running', 'Processing...')
              : stageData.status === 'fresh'
                ? t(stageLabels[stage!].freshKey, 'Up to date')
                : t(stageLabels[stage!].staleKey, 'Needs attention')
            }
          </span>
        </div>
      )}
    </nav>
  )
}
