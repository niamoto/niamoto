/**
 * Collection Panel - Configuration for a Reference
 *
 * Three tabs:
 * - Blocs: Widget management with contextual panel (list + layout/details)
 * - Liste: Index/listing page configuration
 * - Export: API export configuration
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useReferences, type ReferenceInfo } from '@/hooks/useReferences'
import { ListOrdered, LayoutGrid, Play, CheckCircle, XCircle, FileCode, Database, ChevronDown, Check, AlertTriangle } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { ApiExportsTab } from '@/features/collections/components/api/ApiExportsTab'
import { SourcesPanel } from '@/features/collections/components/sources/SourcesPanel'
import { IndexConfigEditor } from '@/components/index-config'
import { ContentTab } from '@/components/content'
import { PanelTransition } from '@/components/motion/PanelTransition'
import { useConfiguredWidgets } from '@/components/widgets'
import { SquareCascadeLoader } from '@/components/ui/square-cascade-loader'
import {
  useCollectionTransformState,
  useStartTransformJob,
} from '@/features/collections/hooks/useCollectionTransforms'
import { useNotificationStore } from '@/stores/notificationStore'
import { buildCollectionsPath, type CollectionTab } from '@/features/collections/routing'

interface CollectionPanelProps {
  reference: ReferenceInfo
  initialTab?: string
}

export function CollectionPanel({
  reference,
  initialTab,
}: CollectionPanelProps) {
  const { t } = useTranslation(['sources', 'common'])
  const navigate = useNavigate()
  const { data: referencesData } = useReferences()
  const references = referencesData?.references ?? []
  const [activeTab, setActiveTab] = useState(initialTab ?? 'content')
  const [isStartingTransform, setIsStartingTransform] = useState(false)
  const [ownedTransformJobId, setOwnedTransformJobId] = useState<string | null>(null)
  const { configuredIds, loading: widgetsLoading } = useConfiguredWidgets(reference.name)
  const notifications = useNotificationStore((state) => state.notifications)
  const startTransformJob = useStartTransformJob()
  const {
    groupStatus,
    isTransforming,
    transformProgress,
    transformMessage,
    isBlockedByOtherPipelineJob,
  } = useCollectionTransformState(reference.name)

  // Sync active tab when initialTab changes (e.g. from overview shortcuts)
  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab)
    }
  }, [initialTab])

  // Kind display mapping using i18n
  const kindLabels: Record<string, string> = {
    hierarchical: t('collectionPanel.kinds.hierarchical'),
    generic: t('collectionPanel.kinds.flat'),
    spatial: t('collectionPanel.kinds.spatial'),
  }

  useEffect(() => {
    if (!ownedTransformJobId) {
      return
    }
    const terminalNotification = notifications.find(
      (notification) =>
        notification.jobId === ownedTransformJobId
        && notification.jobType === 'transform'
    )
    if (!terminalNotification) {
      return
    }
    if (terminalNotification.status === 'completed') {
      toast.success(t('collectionPanel.transform.successToast', { name: reference.name }), {
        id: `collection-transform-${ownedTransformJobId}`,
      })
    } else {
      toast.error(terminalNotification.message || t('collectionPanel.transform.failedToast'), {
        id: `collection-transform-${ownedTransformJobId}`,
      })
    }
    setOwnedTransformJobId(null)
  }, [notifications, ownedTransformJobId, reference.name, t])

  const runTransform = async () => {
    if (configuredIds.length === 0) {
      toast.error(t('collectionPanel.transform.noWidgetsConfigured'))
      return
    }

    setIsStartingTransform(true)
    try {
      const response = await startTransformJob({
        groups: [reference.name],
        trackingMessage: t('collectionPanel.transform.starting'),
      })
      setOwnedTransformJobId(response.job_id)
    } catch (error) {
      toast.error(t('collectionPanel.transform.errorToast', { message: error instanceof Error ? error.message : String(error) }), {
        id: `collection-transform-${reference.name}-error`,
      })
    } finally {
      setIsStartingTransform(false)
    }
  }

  // Format relative time for last run
  const lastRunLabel = groupStatus?.last_run_at
    ? formatRelativeTime(groupStatus.last_run_at, t)
    : null
  const cannotRunWithoutWidgets = !widgetsLoading && configuredIds.length === 0
  const isBusy = isStartingTransform || isTransforming
  const runButtonDisabled = isBusy || isBlockedByOtherPipelineJob || widgetsLoading || cannotRunWithoutWidgets
  const runButtonTitle = isBlockedByOtherPipelineJob
    ? t('collectionPanel.transform.pipelineRunning')
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
          {/* Collection selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="group flex items-center gap-1.5 -ml-1 rounded-theme-sm px-2 py-1 text-base font-semibold tracking-tight text-foreground transition-theme-fast hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                title={reference.name}
              >
                <span className="max-w-[240px] truncate">{reference.name}</span>
                <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[220px]">
              {references.map((item) => {
                const isCurrent = item.name === reference.name
                return (
                  <DropdownMenuItem
                    key={item.name}
                    onClick={() => {
                      if (!isCurrent) {
                        navigate(
                          buildCollectionsPath(
                            { type: 'collection', name: item.name },
                            activeTab as CollectionTab
                          )
                        )
                      }
                    }}
                    className={cn(
                      'flex items-center justify-between gap-2 cursor-pointer',
                      isCurrent && 'bg-accent/60'
                    )}
                  >
                    <span className="truncate text-sm">{item.name}</span>
                    {isCurrent && <Check className="h-4 w-4 text-primary shrink-0" />}
                  </DropdownMenuItem>
                )
              })}
            </DropdownMenuContent>
          </DropdownMenu>

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
          {lastRunLabel && !isBusy && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              {groupStatus?.status === 'fresh' ? (
                <CheckCircle className="h-3 w-3 text-green-500" />
              ) : groupStatus?.status === 'stale' ? (
                <AlertTriangle className="h-3 w-3 text-amber-500" />
              ) : groupStatus?.status === 'error' ? (
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
            {isBusy ? (
              <>
                <SquareCascadeLoader className="mr-1.5 h-[14px] w-[14px] gap-[2px]" squareClassName="h-[6px] w-[6px]" />
                {typeof transformProgress === 'number' && transformProgress > 0 ? `${transformProgress}%` : t('collectionPanel.transform.starting')}
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
        {isBusy && (
          <div className="px-4 py-1 border-b">
            <Progress value={transformProgress > 0 ? transformProgress : 5} className="h-1.5" />
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {transformMessage || t('collectionPanel.transform.starting')}
            </p>
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
