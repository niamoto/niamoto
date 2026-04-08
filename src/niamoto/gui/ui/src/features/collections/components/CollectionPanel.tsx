/**
 * Collection Panel - Configuration for a Reference
 *
 * Three tabs:
 * - Blocs: Widget management with contextual panel (list + layout/details)
 * - Liste: Index/listing page configuration
 * - Export: API export configuration
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { ReferenceInfo } from '@/hooks/useReferences'
import { Loader2, ListOrdered, LayoutGrid, Play, CheckCircle, XCircle, FileCode, Database } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { ApiExportsTab } from '@/features/collections/components/api/ApiExportsTab'
import { SourcesPanel } from '@/features/collections/components/sources/SourcesPanel'
import { IndexConfigEditor } from '@/components/index-config'
import { ContentTab } from '@/components/content'
import { PanelTransition } from '@/components/motion/PanelTransition'
import { useConfiguredWidgets } from '@/components/widgets'
import {
  executeTransformAndWait,
  getActiveTransformJob,
  getLastTransformRun,
  getTransformStatus,
  type TransformStatus,
} from '@/lib/api/transform'
import { getActiveExportJob } from '@/lib/api/export'

interface CollectionPanelProps {
  reference: ReferenceInfo
  references: ReferenceInfo[]
  initialTab?: string
  onSelectCollection: (name: string, tab?: string) => void
}

export function CollectionPanel({
  reference,
  references,
  initialTab,
  onSelectCollection,
}: CollectionPanelProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [activeTab, setActiveTab] = useState(initialTab ?? 'content')
  const { configuredIds, loading: widgetsLoading } = useConfiguredWidgets(reference.name)

  // Sync active tab when initialTab changes (e.g. from overview shortcuts)
  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab)
    }
  }, [initialTab])

  // Transform job state
  const [isTransforming, setIsTransforming] = useState(false)
  const [transformProgress, setTransformProgress] = useState(0)
  const [transformMessage, setTransformMessage] = useState('')
  const [lastRun, setLastRun] = useState<TransformStatus | null>(null)
  const [exportRunning, setExportRunning] = useState(false)
  const cancelledRef = useRef(false)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // Track whether runTransform owns the current job (to avoid double toast)
  const ownedByRunTransformRef = useRef(false)

  // Kind display mapping using i18n
  const kindLabels: Record<string, string> = {
    hierarchical: t('collectionPanel.kinds.hierarchical'),
    generic: t('collectionPanel.kinds.flat'),
    spatial: t('collectionPanel.kinds.spatial'),
  }

  // Stop any active polling
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  // Poll an already-running job until it completes (guarded by cancelledRef).
  // Only used for jobs discovered on mount (not launched by runTransform).
  const pollRunningJob = useCallback((jobId: string) => {
    // If runTransform owns this job, don't double-poll
    if (ownedByRunTransformRef.current) return

    setIsTransforming(true)
    let polling = false // guard against async overlap
    const interval = setInterval(async () => {
      if (cancelledRef.current || polling) return
      polling = true
      try {
        const status = await getTransformStatus(jobId)
        if (cancelledRef.current) return
        setTransformProgress(status.progress)
        setTransformMessage(status.message)
        if (status.status === 'completed' || status.status === 'failed') {
          stopPolling()
          setIsTransforming(false)
          setTransformProgress(0)
          setTransformMessage('')
          if (status.status === 'completed') {
            setLastRun(status)
            toast.success(t('collectionPanel.transform.successToast', { name: reference.name }))
          } else {
            toast.error(status.error || t('collectionPanel.transform.failedToast'))
          }
        }
      } catch {
        if (!cancelledRef.current) {
          stopPolling()
          setIsTransforming(false)
        }
      } finally {
        polling = false
      }
    }, 1000)
    pollIntervalRef.current = interval
  }, [reference.name, t, stopPolling])

  // Load last run info on mount + resume polling if job is running
  useEffect(() => {
    cancelledRef.current = false

    getLastTransformRun(reference.name)
      .then((run) => {
        if (!cancelledRef.current) setLastRun(run)
      })
      .catch(() => {})

    // Check if a transform is already running for THIS collection
    getActiveTransformJob()
      .then((job) => {
        if (cancelledRef.current) return
        if (job && job.status === 'running' && job.group_by === reference.name) {
          setTransformProgress(job.progress)
          setTransformMessage(job.message)
          pollRunningJob(job.job_id)
        }
      })
      .catch(() => {})

    // Check if an export or transform on another collection is running (disable button)
    getActiveExportJob()
      .then((job) => {
        if (cancelledRef.current) return
        setExportRunning(job != null && job.status === 'running')
      })
      .catch(() => {})

    // Also disable if a transform is running on a different collection
    getActiveTransformJob()
      .then((job) => {
        if (cancelledRef.current) return
        if (job && job.status === 'running' && job.group_by !== reference.name) {
          setExportRunning(true) // reuse flag to disable the button
        }
      })
      .catch(() => {})

    return () => {
      cancelledRef.current = true
      stopPolling()
    }
  }, [reference.name, pollRunningJob, stopPolling])

  const runTransform = useCallback(async () => {
    if (configuredIds.length === 0) {
      toast.error(t('collectionPanel.transform.noWidgetsConfigured'))
      return
    }

    ownedByRunTransformRef.current = true
    setIsTransforming(true)
    setTransformProgress(0)
    setTransformMessage(t('collectionPanel.transform.starting'))

    try {
      const result = await executeTransformAndWait(
        { group_by: reference.name },
        (progress, message) => {
          setTransformProgress(progress)
          setTransformMessage(message)
        }
      )
      setLastRun(result)
      toast.success(t('collectionPanel.transform.successToast', { name: reference.name }))
    } catch (error) {
      toast.error(t('collectionPanel.transform.errorToast', { message: error instanceof Error ? error.message : String(error) }))
    } finally {
      ownedByRunTransformRef.current = false
      setIsTransforming(false)
      setTransformProgress(0)
      setTransformMessage('')
    }
  }, [configuredIds.length, reference.name, t])

  // Format relative time for last run
  const lastRunLabel = lastRun?.completed_at
    ? formatRelativeTime(lastRun.completed_at, t)
    : null
  const cannotRunWithoutWidgets = !widgetsLoading && configuredIds.length === 0
  const runButtonDisabled = isTransforming || exportRunning || widgetsLoading || cannotRunWithoutWidgets
  const runButtonTitle = exportRunning
    ? t('collectionPanel.transform.exportRunning')
    : cannotRunWithoutWidgets
      ? t('collectionPanel.transform.noWidgetsTooltip')
      : undefined
  const tabsTriggerClassName =
    "h-7 rounded border border-transparent px-2.5 text-xs text-muted-foreground data-[state=active]:border-primary/20 data-[state=active]:bg-primary/10 data-[state=active]:text-foreground data-[state=active]:shadow-sm"
  const activeContent = getTabContent(activeTab, reference)

  return (
    <div className="relative h-full">
    <div className="absolute inset-0 flex flex-col">
      {/* Compact toolbar: tabs + actions in one row */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 min-h-0 flex flex-col">
        <div className="flex items-center gap-3 border-b bg-background px-4 py-1.5">
          <Select
            value={reference.name}
            onValueChange={(value) => onSelectCollection(value, activeTab)}
          >
            <SelectTrigger className="h-7 w-[180px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {references.map((item) => (
                <SelectItem key={item.name} value={item.name}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Tabs */}
          <TabsList className="h-8 w-fit gap-0.5 bg-muted/50 p-0.5 rounded-md">
            <TabsTrigger
              value="sources"
              className={tabsTriggerClassName}
            >
              <Database className="mr-1.5 h-3.5 w-3.5" />
              {t('collectionPanel.tabs.sources')}
            </TabsTrigger>
            <TabsTrigger
              value="content"
              className={tabsTriggerClassName}
            >
              <LayoutGrid className="mr-1.5 h-3.5 w-3.5" />
              {t('collectionPanel.tabs.blocks')}
            </TabsTrigger>
            <TabsTrigger
              value="index"
              className={tabsTriggerClassName}
            >
              <ListOrdered className="mr-1.5 h-3.5 w-3.5" />
              {t('collectionPanel.tabs.list')}
            </TabsTrigger>
            <TabsTrigger
              value="api"
              className={tabsTriggerClassName}
            >
              <FileCode className="mr-1.5 h-3.5 w-3.5" />
              {t('collectionPanel.tabs.export')}
            </TabsTrigger>
          </TabsList>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Info: entity count + kind */}
          <span className="hidden md:flex items-center gap-1.5 text-xs text-muted-foreground">
            {reference.entity_count ?? '?'} {t('reference.entities')}
            <span>·</span>
            <Badge variant="outline" className="text-[10px] py-0">
              {kindLabels[reference.kind] || reference.kind}
            </Badge>
          </span>

          {/* Last run status */}
          {lastRunLabel && !isTransforming && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              {lastRun?.status === 'completed' ? (
                <CheckCircle className="h-3 w-3 text-green-500" />
              ) : lastRun?.status === 'failed' ? (
                <XCircle className="h-3 w-3 text-destructive" />
              ) : null}
              {lastRunLabel}
            </span>
          )}

          {/* Transform button */}
          <Button
            size="sm"
            className="h-7 text-xs"
            onClick={runTransform}
            disabled={runButtonDisabled}
            title={runButtonTitle}
          >
            {isTransforming ? (
              <>
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                {transformProgress}%
              </>
            ) : (
              <>
                <Play className="mr-1.5 h-3.5 w-3.5" />
                {t('collectionPanel.transform.trigger')}
              </>
            )}
          </Button>
        </div>

        {/* Progress bar during transform */}
        {isTransforming && (
          <div className="px-4 py-1 border-b">
            <Progress value={transformProgress} className="h-1.5" />
            <p className="text-[10px] text-muted-foreground mt-0.5">{transformMessage}</p>
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-hidden">
          <PanelTransition transitionKey={activeTab}>
            {activeContent}
          </PanelTransition>
        </div>
      </Tabs>
    </div>
    </div>
  )
}

function getTabContent(activeTab: string, reference: ReferenceInfo) {
  switch (activeTab) {
    case 'sources':
      return (
        <div className="h-full overflow-hidden">
          <SourcesPanel reference={reference} />
        </div>
      )
    case 'index':
      return (
        <div className="h-full overflow-auto">
          <IndexTab reference={reference} />
        </div>
      )
    case 'api':
      return (
        <div className="h-full overflow-hidden">
          <ApiExportsTab groupBy={reference.name} />
        </div>
      )
    case 'content':
    default:
      return (
        <div className="h-full overflow-hidden">
          <ContentTab reference={reference} />
        </div>
      )
  }
}

function IndexTab({ reference }: { reference: ReferenceInfo }) {
  return (
    <div className="h-full">
      <IndexConfigEditor groupBy={reference.name} />
    </div>
  )
}

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
