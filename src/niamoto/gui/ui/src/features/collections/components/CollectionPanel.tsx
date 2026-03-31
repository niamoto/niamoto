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
import { Package, Loader2, ListOrdered, LayoutGrid, Play, CheckCircle, XCircle, FileCode } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'
import { ApiExportsTab } from '@/features/collections/components/api/ApiExportsTab'
import { SourcesDialog } from '@/features/collections/components/sources/SourcesDialog'
import { IndexConfigEditor } from '@/components/index-config'
import { ContentTab } from '@/components/content'
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
  initialTab?: string
}

export function CollectionPanel({ reference, initialTab }: CollectionPanelProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [activeTab, setActiveTab] = useState(initialTab ?? 'content')
  const { configuredIds, loading: widgetsLoading } = useConfiguredWidgets(reference.name)

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

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b bg-background px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Package className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold">{reference.name}</h1>
              <p className="text-sm text-muted-foreground">
                {reference.entity_count ?? '?'} {t('reference.entities')}
                <span className="mx-2">·</span>
                <Badge variant="outline" className="text-xs">
                  {kindLabels[reference.kind] || reference.kind}
                </Badge>
                {reference.description && (
                  <>
                    <span className="mx-2">·</span>
                    {reference.description}
                  </>
                )}
              </p>
            </div>
          </div>

          {/* Transform button */}
          <div className="flex items-center gap-3">
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
            <Button
              size="sm"
              onClick={runTransform}
              disabled={runButtonDisabled}
              title={runButtonTitle}
            >
              {isTransforming ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('collectionPanel.transform.running', { progress: transformProgress })}
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  {t('collectionPanel.transform.trigger')}
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Progress bar during transform */}
        {isTransforming && (
          <div className="mt-3 space-y-1">
            <Progress value={transformProgress} className="h-2" />
            <p className="text-xs text-muted-foreground">{transformMessage}</p>
          </div>
        )}
      </div>

      {/* Tabs - 3 tabs: Blocs / Liste / Export */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <div className="flex items-center justify-between border-b px-6">
          <TabsList className="h-10 w-fit gap-1 bg-muted/50 p-1 rounded-lg">
            <TabsTrigger
              value="content"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <LayoutGrid className="mr-2 h-4 w-4" />
              {t('collectionPanel.tabs.blocks')}
            </TabsTrigger>
            <TabsTrigger
              value="index"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <ListOrdered className="mr-2 h-4 w-4" />
              {t('collectionPanel.tabs.list')}
            </TabsTrigger>
            <TabsTrigger
              value="api"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <FileCode className="mr-2 h-4 w-4" />
              {t('collectionPanel.tabs.export')}
            </TabsTrigger>
          </TabsList>
          <SourcesDialog reference={reference} />
        </div>

        {/* Tab Content */}
        <TabsContent value="content" className="flex-1 m-0 overflow-hidden">
          <ContentTab reference={reference} />
        </TabsContent>

        <TabsContent value="index" className="flex-1 m-0 p-6 overflow-auto">
          <IndexTab reference={reference} />
        </TabsContent>

        <TabsContent value="api" className="flex-1 m-0 p-6 overflow-auto">
          <ApiExportsTab groupBy={reference.name} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function IndexTab({ reference }: { reference: ReferenceInfo }) {
  return (
    <div className="h-[calc(100vh-280px)]">
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
