/**
 * CollectionsOverview - Enriched card grid for the Collections module
 *
 * Each card shows: counters, freshness status, configured block badges,
 * last transform date, and direct shortcut buttons to Blocs/Liste/Export.
 */

import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'
import {
  usePipelineStatus,
  type EntityStatus,
} from '@/hooks/usePipelineStatus'
import { useQueryClient } from '@tanstack/react-query'
import { useConfiguredWidgets } from '@/components/widgets'
import { useApiExportTargets } from '@/features/collections/hooks/useApiExportConfigs'
import type { ReferenceInfo } from '@/hooks/useReferences'
import type { CollectionsSelection } from './CollectionsTree'
import { executeTransform } from '@/lib/api/transform'
import { useNotificationStore } from '@/stores/notificationStore'
import {
  Card,
  CardContent,
  CardHeader,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { SquareCascadeLoader } from '@/components/ui/square-cascade-loader'
import { Layers, LayoutGrid, ListOrdered, FileCode, CheckCircle, AlertTriangle, Clock, Minus, Play } from 'lucide-react'
import { toast } from 'sonner'

// =============================================================================
// COLLECTION CARD
// =============================================================================

interface CollectionCardProps {
  reference: ReferenceInfo
  entityStatus?: EntityStatus
  isRunning?: boolean
  isSubmitting?: boolean
  isDisabled?: boolean
  onSelect: (selection: CollectionsSelection, tab?: string) => void
  onRun: (reference: ReferenceInfo) => void
}

function CollectionCard({
  reference,
  entityStatus,
  isRunning = false,
  isSubmitting = false,
  isDisabled = false,
  onSelect,
  onRun,
}: CollectionCardProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { configuredIds } = useConfiguredWidgets(reference.name)
  const { data: targets } = useApiExportTargets()

  // Count exports for this collection
  const exportCount = (targets ?? []).filter((target) =>
    target.groups.some((g) => g.group_by === reference.name && g.enabled)
  ).length

  // Freshness
  const status = entityStatus?.status ?? 'unconfigured'
  const isFresh = status === 'fresh'
  const isStale = status === 'stale'
  const isUnconfigured = status === 'unconfigured'
  const isError = status === 'error'
  const lastRunAt = entityStatus?.last_run_at
  const canRun = configuredIds.length > 0
  const isBusy = isRunning || isSubmitting

  // Kind labels
  const kindLabels: Record<string, string> = {
    hierarchical: t('collectionPanel.kinds.hierarchical'),
    generic: t('collectionPanel.kinds.flat'),
    spatial: t('collectionPanel.kinds.spatial'),
  }

  // Format last run
  const lastRunLabel = lastRunAt ? formatRelativeTime(lastRunAt, t) : null

  return (
    <Card
      className="flex h-full min-w-0 cursor-pointer flex-col overflow-hidden transition-all hover:border-primary hover:shadow-sm"
      onClick={() => onSelect({ type: 'collection', name: reference.name })}
    >
      <CardHeader className="pb-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <Layers className="h-4 w-4 text-muted-foreground" />
            <span className="truncate text-lg font-semibold">{reference.name}</span>
          </div>
          {isBusy ? (
            <Badge variant="outline" className="shrink-0 gap-1 border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400">
              <SquareCascadeLoader className="h-[14px] w-[14px] gap-[2px]" squareClassName="h-[6px] w-[6px]" />
              {t('collections.overviewRunning', 'Calcul en cours')}
            </Badge>
          ) : isFresh ? (
            <Badge variant="outline" className="shrink-0 gap-1 border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400">
              <CheckCircle className="h-3 w-3" />
              {t('collections.overviewFresh', 'Up to date')}
            </Badge>
          ) : isStale ? (
            <Badge variant="outline" className="shrink-0 gap-1 border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400">
              <AlertTriangle className="h-3 w-3" />
              {t('collections.overviewStale', 'Needs recomputing')}
            </Badge>
          ) : isError ? (
            <Badge variant="outline" className="shrink-0 gap-1 border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              <AlertTriangle className="h-3 w-3" />
              {t('collections.overviewError', 'Erreur')}
            </Badge>
          ) : isUnconfigured ? (
            <Badge variant="outline" className="shrink-0 gap-1 text-muted-foreground">
              <Minus className="h-3 w-3" />
              {t('collections.noCollectionsConfigured', 'No collection configured')}
            </Badge>
          ) : (
            <Badge variant="outline" className="shrink-0 gap-1 text-muted-foreground">
              <Minus className="h-3 w-3" />
              {t('collections.overviewNeverRun', 'Never computed')}
            </Badge>
          )}
        </div>
        {!isBusy && (
          <div className="mt-3 flex items-center justify-end" onClick={(e) => e.stopPropagation()}>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              disabled={isDisabled || !canRun}
              title={!canRun ? t('collectionPanel.transform.noWidgetsTooltip') : undefined}
              onClick={() => onRun(reference)}
            >
              <Play className="h-3.5 w-3.5" />
              {isFresh
                ? t('collections.overviewRunOneFallback', 'Recalculer')
                : t('collections.overviewRunOne', 'Calculer')}
            </Button>
          </div>
        )}
        <div className="flex min-w-0 flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Badge variant="secondary" className="text-[10px]">
            {kindLabels[reference.kind] || reference.kind}
          </Badge>
          <span>{reference.entity_count ?? '?'} {t('reference.entities', 'entities')}</span>
        </div>
      </CardHeader>

      <CardContent className="flex min-w-0 flex-1 flex-col space-y-4">
        {/* Counters */}
        <div className="grid grid-cols-3 gap-2">
          <CounterBox
            value={configuredIds.length}
            label={t('collections.overviewBlocks', 'Blocks')}
          />
          <CounterBox
            value={reference.entity_count ?? 0}
            label={t('collections.overviewSheets', 'Sheets')}
          />
          <CounterBox
            value={exportCount}
            label={t('collections.overviewExports', 'Exports')}
          />
        </div>

        {/* Block type badges */}
        {configuredIds.length > 0 && (
          <div className="flex min-w-0 flex-wrap gap-1">
            {configuredIds.slice(0, 5).map((id) => (
              <Badge key={id} variant="outline" className="text-[10px]">
                {id}
              </Badge>
            ))}
            {configuredIds.length > 5 && (
              <Badge variant="outline" className="text-[10px]">
                +{configuredIds.length - 5}
              </Badge>
            )}
          </div>
        )}

        {/* Last run */}
        {lastRunLabel && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {t('collections.overviewLastRun', 'Last computation')}: {lastRunLabel}
          </div>
        )}

        {/* Shortcut buttons */}
        <div className="mt-auto grid min-w-0 grid-cols-3 gap-2" onClick={(e) => e.stopPropagation()}>
          <Button
            variant="default"
            size="sm"
            className="min-w-0 px-2 text-xs"
            onClick={() => onSelect({ type: 'collection', name: reference.name }, 'content')}
          >
            <LayoutGrid className="h-3 w-3 shrink-0" />
            <span className="truncate">{t('collectionPanel.tabs.blocks')}</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="min-w-0 px-2 text-xs"
            onClick={() => onSelect({ type: 'collection', name: reference.name }, 'index')}
          >
            <ListOrdered className="h-3 w-3 shrink-0" />
            <span className="truncate">{t('collectionPanel.tabs.list')}</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="min-w-0 px-2 text-xs"
            onClick={() => onSelect({ type: 'collection', name: reference.name }, 'api')}
          >
            <FileCode className="h-3 w-3 shrink-0" />
            <span className="truncate">{t('collectionPanel.tabs.export')}</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// COUNTER BOX
// =============================================================================

function CounterBox({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-md bg-muted/50 p-2 text-center">
      <div className="text-lg font-bold">{value}</div>
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
    </div>
  )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

interface CollectionsOverviewProps {
  references: ReferenceInfo[]
  onSelect: (selection: CollectionsSelection, tab?: string) => void
}

export function CollectionsOverview({ references, onSelect }: CollectionsOverviewProps) {
  const { t } = useTranslation(['sources', 'common'])
  const queryClient = useQueryClient()
  const { data: pipelineStatus } = usePipelineStatus()
  const trackedJobs = useNotificationStore((state) => state.trackedJobs)
  const trackJob = useNotificationStore((state) => state.trackJob)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submittingGroupName, setSubmittingGroupName] = useState<string | null>(null)
  const fallbackStatus = pipelineStatus?.groups?.status === 'unconfigured' ? 'unconfigured' : undefined

  // Build a map of entity statuses by name
  const statusByName = new Map<string, EntityStatus>()
  if (pipelineStatus?.groups?.items) {
    for (const item of pipelineStatus.groups.items) {
      statusByName.set(item.name, item)
    }
  }

  const eligibleStatuses = new Set(['stale', 'never_run', 'error'])
  const runnableReferences = references.filter((ref) => {
    const status = statusByName.get(ref.name)?.status ?? fallbackStatus
    return status !== 'unconfigured' && status !== 'running'
  })

  const eligibleReferences = runnableReferences.filter((ref) => {
    const status = statusByName.get(ref.name)?.status ?? fallbackStatus
    return status != null && eligibleStatuses.has(status)
  })
  const targetReferences = eligibleReferences.length > 0 ? eligibleReferences : runnableReferences

  const runningJob = pipelineStatus?.running_job
  const isTransformRunning = runningJob?.type === 'transform'
  const hasActivePipelineJob =
    trackedJobs.some((job) => job.jobType === 'transform' || job.jobType === 'export')
    || runningJob?.type === 'transform'
    || runningJob?.type === 'export'
  const runningGroups = new Set(
    isTransformRunning
      ? runningJob.group_bys?.length
        ? runningJob.group_bys
        : runningJob.group_by
          ? [runningJob.group_by]
          : []
      : []
  )
  if (submittingGroupName && !runningGroups.has(submittingGroupName) && !isSubmitting) {
    runningGroups.add(submittingGroupName)
  }

  useEffect(() => {
    if (submittingGroupName && isTransformRunning) {
      setSubmittingGroupName(null)
    }
  }, [isTransformRunning, submittingGroupName])

  const startTransform = async (groups: string[], successCount: number, singleGroupName?: string) => {
    if (groups.length === 0) {
      toast.error(t('collections.overviewRunVisibleEmpty'))
      return
    }

    setIsSubmitting(true)
    setSubmittingGroupName(singleGroupName ?? null)
    try {
      const response = await executeTransform({
        group_bys: groups,
      })
      trackJob({
        jobId: response.job_id,
        jobType: 'transform',
        status: 'running',
        progress: 0,
        message: t('collections.overviewRunVisibleTrackingMessage', {
          count: successCount,
        }),
        startedAt: response.started_at,
      })
      void queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
      toast.success(
        t('collections.overviewRunVisibleStarted', {
          count: successCount,
        }),
        { id: `collections-overview-${response.job_id}` }
      )
    } catch (error) {
      setSubmittingGroupName(null)
      toast.error(
        error instanceof Error
          ? error.message
          : t('collections.overviewRunVisibleError')
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleRunVisibleCollections = async () => {
    await startTransform(
      targetReferences.map((ref) => ref.name),
      targetReferences.length
    )
  }

  const handleRunSingleCollection = async (reference: ReferenceInfo) => {
    await startTransform([reference.name], 1, reference.name)
  }

  return (
    <div className="min-w-0 space-y-6 p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('collections.title', 'Collections')}</h1>
          {isTransformRunning ? (
            <p className="mt-1 flex items-center gap-2 text-muted-foreground">
              <SquareCascadeLoader className="h-[16px] w-[16px] gap-[2px]" squareClassName="h-[7px] w-[7px]" />
              <span>
                {runningJob.message || t('collections.overviewRunVisibleSubmitting')}
                {typeof runningJob.progress === 'number' ? ` (${runningJob.progress}%)` : ''}
              </span>
            </p>
          ) : (
            <p className="mt-1 text-muted-foreground">
              {t('collections.description', 'Configure blocks and data sources for each collection.')}
            </p>
          )}
        </div>
        <Button
          onClick={handleRunVisibleCollections}
          disabled={isSubmitting || hasActivePipelineJob || targetReferences.length === 0}
          className="shrink-0"
        >
          {isSubmitting || isTransformRunning ? (
            <SquareCascadeLoader className="mr-2 h-[16px] w-[16px] gap-[2px]" squareClassName="h-[7px] w-[7px]" />
          ) : (
            <Play className="mr-2 h-4 w-4" />
          )}
          {isSubmitting || isTransformRunning
            ? t('collections.overviewRunVisibleSubmitting')
            : eligibleReferences.length > 0
              ? t('collections.overviewRunVisible', { count: eligibleReferences.length })
              : t('collections.overviewRunVisibleFallback', { count: targetReferences.length })}
        </Button>
      </div>
      <div className="grid min-w-0 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {references.map((ref) => (
          <CollectionCard
            key={ref.name}
            reference={ref}
            isRunning={runningGroups.has(ref.name)}
            isSubmitting={submittingGroupName === ref.name}
            isDisabled={Boolean(hasActivePipelineJob && !runningGroups.has(ref.name) && submittingGroupName !== ref.name)}
            entityStatus={
              statusByName.get(ref.name) ??
              (fallbackStatus ? ({ name: ref.name, status: fallbackStatus, last_run_at: null, reason: null } as EntityStatus) : undefined)
            }
            onSelect={onSelect}
            onRun={handleRunSingleCollection}
          />
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// HELPERS
// =============================================================================

function formatRelativeTime(isoDate: string, t: (key: string, options?: Record<string, unknown>) => string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return t('collectionPanel.relativeTime.justNow')
  if (minutes < 60) return t('collectionPanel.relativeTime.minutesAgo', { count: minutes })
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return t('collectionPanel.relativeTime.hoursAgo', { count: hours })
  const days = Math.floor(hours / 24)
  return t('collectionPanel.relativeTime.daysAgo', { count: days })
}
