/**
 * StalenessBanner — Contextual banner showing pipeline freshness warnings.
 *
 * Displays at the top of each section page when actions are needed.
 * Disappears when everything is up to date.
 */

import { useTranslation } from 'react-i18next'
import { usePipelineStatus, type FreshnessStatus } from '@/hooks/usePipelineStatus'
import { AlertTriangle, CheckCircle2, RefreshCw, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type PipelineStage = 'data' | 'groups' | 'site' | 'publication'

interface StalenessBannerProps {
  /** Which pipeline stage this banner monitors */
  stage: PipelineStage
  /** Callback when the user clicks the action button */
  onAction?: () => void
  /** Override the action label */
  actionLabel?: string
  className?: string
}

const stageConfig: Record<PipelineStage, {
  staleKey: string
  staleFallback: string
  freshKey: string
  freshFallback: string
  actionKey: string
  actionFallback: string
}> = {
  data: {
    staleKey: 'pipeline.data_stale',
    staleFallback: 'Données importées — groupes à recalculer',
    freshKey: 'pipeline.data_fresh',
    freshFallback: 'Données à jour',
    actionKey: 'pipeline.action_transform',
    actionFallback: 'Recalculer les groupes',
  },
  groups: {
    staleKey: 'pipeline.groups_stale',
    staleFallback: 'Calculs périmés — données modifiées depuis le dernier calcul',
    freshKey: 'pipeline.groups_fresh',
    freshFallback: 'Tous les groupes sont à jour',
    actionKey: 'pipeline.action_recalculate',
    actionFallback: 'Recalculer',
  },
  site: {
    staleKey: 'pipeline.site_stale',
    staleFallback: 'Site non configuré',
    freshKey: 'pipeline.site_fresh',
    freshFallback: 'Site configuré',
    actionKey: 'pipeline.action_configure',
    actionFallback: 'Configurer',
  },
  publication: {
    staleKey: 'pipeline.publication_stale',
    staleFallback: 'Groupes recalculés — site à reconstruire',
    freshKey: 'pipeline.publication_fresh',
    freshFallback: 'Site généré et à jour',
    actionKey: 'pipeline.action_rebuild',
    actionFallback: 'Reconstruire le site',
  },
}

function StatusIcon({ status }: { status: FreshnessStatus }) {
  switch (status) {
    case 'running':
      return <Loader2 className="h-4 w-4 animate-spin" />
    case 'stale':
      return <AlertTriangle className="h-4 w-4" />
    case 'fresh':
      return <CheckCircle2 className="h-4 w-4" />
    default:
      return null
  }
}

export function StalenessBanner({ stage, onAction, actionLabel, className }: StalenessBannerProps) {
  const { t } = useTranslation('common')
  const { data: pipeline } = usePipelineStatus()

  if (!pipeline) return null

  const stageData = pipeline[stage]
  if (!stageData) return null

  const config = stageConfig[stage]
  const { status } = stageData

  // Don't show banner for never_run — that's handled by the page's empty state
  if (status === 'never_run') return null

  // Stale items count for groups
  const staleCount = stageData.items?.filter(i => i.status === 'stale' || i.status === 'never_run').length ?? 0

  const isFresh = status === 'fresh'
  const isRunning = status === 'running'

  // Build message
  let message: string
  if (isRunning) {
    message = t('pipeline.running', 'Traitement en cours...')
  } else if (isFresh) {
    message = t(config.freshKey, config.freshFallback)
  } else {
    message = t(config.staleKey, config.staleFallback)
    if (stage === 'groups' && staleCount > 0) {
      message = t('pipeline.groups_stale_count', '{{count}} groupe(s) à recalculer', { count: staleCount })
    }
  }

  return (
    <div
      className={cn(
        'flex items-center gap-3 border-b px-6 py-2 text-sm transition-colors',
        isFresh && 'border-green-200 bg-green-50 text-green-700 dark:border-green-900 dark:bg-green-950/30 dark:text-green-400',
        !isFresh && !isRunning && 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-400',
        isRunning && 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-400',
        className,
      )}
    >
      <StatusIcon status={status} />
      <span className="flex-1">{message}</span>

      {!isFresh && !isRunning && onAction && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1.5 text-xs"
          onClick={onAction}
        >
          <RefreshCw className="h-3 w-3" />
          {actionLabel || t(config.actionKey, config.actionFallback)}
        </Button>
      )}
    </div>
  )
}
