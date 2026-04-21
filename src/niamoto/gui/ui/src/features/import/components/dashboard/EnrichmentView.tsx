import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, AlertTriangle, CheckCircle2, Clock, Loader2, Pause, Play, Sparkles, StopCircle, WifiOff } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { EnrichmentWorkspaceSheet } from './EnrichmentWorkspaceSheet'
import { useImportSummaryDetailed } from '@/features/import/hooks/useImportSummaryDetailed'
import { useReferences, type ReferenceInfo } from '@/features/import/hooks/useReferences'
import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'
import { toast } from 'sonner'
import { useNotificationStore } from '@/stores/notificationStore'
import { importQueryKeys } from '@/features/import/queryKeys'

interface EnrichmentJobSummary {
  id: string
  mode: 'all' | 'single'
  status: 'pending' | 'running' | 'paused' | 'paused_offline' | 'completed' | 'failed' | 'cancelled'
  total: number
  processed: number
  already_completed?: number
  pending_total?: number
  pending_processed?: number
  current_entity?: string
  current_source_label?: string
}

interface EnrichmentSourceStatsSummary {
  source_id: string
  label: string
  total: number
  enriched: number
  pending: number
  status: 'ready' | 'running' | 'paused' | 'paused_offline' | 'completed' | 'failed' | 'cancelled'
}

interface EnrichmentStatsSummary {
  total: number
  enriched: number
  pending: number
  sources: EnrichmentSourceStatsSummary[]
}

const EMPTY_REFERENCES: ReferenceInfo[] = []

function getJobRunProgress(job: EnrichmentJobSummary | null | undefined) {
  if (!job) {
    return null
  }

  const total = Math.max(job.pending_total ?? Math.max(job.total - (job.already_completed ?? 0), 0), 0)
  const processed = Math.min(
    Math.max(job.pending_processed ?? Math.max(job.processed - (job.already_completed ?? 0), 0), 0),
    total
  )
  const percentage = total > 0 ? (processed / total) * 100 : 0

  return { total, processed, percentage }
}

export function EnrichmentView() {
  const { t } = useTranslation('sources')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: referencesData, isLoading, error } = useReferences()
  const { data: summary } = useImportSummaryDetailed()
  const [activeReference, setActiveReference] = useState<ReferenceInfo | null>(null)
  const [startingReferenceName, setStartingReferenceName] = useState<string | null>(null)
  const [jobsByReference, setJobsByReference] = useState<Record<string, EnrichmentJobSummary | null>>({})
  const [statsByReference, setStatsByReference] = useState<Record<string, EnrichmentStatsSummary>>({})
  const [progressLoadingByReference, setProgressLoadingByReference] = useState<Record<string, boolean>>({})
  const trackedJobs = useNotificationStore((state) => state.trackedJobs)
  const jobsByReferenceRef = useRef<Record<string, EnrichmentJobSummary | null>>({})
  const statsByReferenceRef = useRef<Record<string, EnrichmentStatsSummary>>({})
  const trackedJobsRef = useRef(trackedJobs)

  const references = useMemo(() => referencesData?.references ?? EMPTY_REFERENCES, [referencesData?.references])
  const enrichableReferences = useMemo(
    () => references.filter((reference) => reference.can_enrich),
    [references]
  )
  const configuredReferences = useMemo(
    () => enrichableReferences.filter((reference) => reference.enrichment_enabled),
    [enrichableReferences]
  )

  useEffect(() => {
    jobsByReferenceRef.current = jobsByReference
  }, [jobsByReference])

  useEffect(() => {
    statsByReferenceRef.current = statsByReference
  }, [statsByReference])

  useEffect(() => {
    trackedJobsRef.current = trackedJobs
  }, [trackedJobs])

  const entityRows = new Map(summary?.entities.map((entity) => [entity.name, entity]) ?? [])

  useEffect(() => {
    const configuredReferenceNames = new Set(configuredReferences.map((reference) => reference.name))

    setJobsByReference((previous) =>
      Object.fromEntries(
        Object.entries(previous).filter(([referenceName]) => configuredReferenceNames.has(referenceName))
      )
    )
    setStatsByReference((previous) =>
      Object.fromEntries(
        Object.entries(previous).filter(([referenceName]) => configuredReferenceNames.has(referenceName))
      ) as Record<string, EnrichmentStatsSummary>
    )
    setProgressLoadingByReference((previous) =>
      Object.fromEntries(
        Object.entries(previous).filter(([referenceName]) => configuredReferenceNames.has(referenceName))
      )
    )

    if (configuredReferences.length === 0) {
      return
    }

    let isCancelled = false

    const loadProgress = async () => {
      const activeTrackedJobsByReference = new Map(
        trackedJobsRef.current
          .filter((job) => job.jobType === 'enrichment' && job.meta?.referenceName)
          .map((job) => [job.meta?.referenceName as string, job])
      )

      const updates = await Promise.all(
        configuredReferences.map(async (reference) => {
          try {
            const statsResult = await apiClient.get<EnrichmentStatsSummary>(`/enrichment/stats/${reference.name}`)

            const knownJob = jobsByReferenceRef.current[reference.name]
            const shouldPollJob =
              Boolean(activeTrackedJobsByReference.get(reference.name)) ||
              (knownJob !== null &&
                knownJob !== undefined &&
                !['completed', 'failed', 'cancelled'].includes(knownJob.status))

            const jobResult = shouldPollJob
              ? await apiClient.get<EnrichmentJobSummary>(`/enrichment/job/${reference.name}`).catch((error: unknown) => {
                  const isNotFound =
                    typeof error === 'object' &&
                    error !== null &&
                    'response' in error &&
                    typeof error.response === 'object' &&
                    error.response !== null &&
                    'status' in error.response &&
                    error.response.status === 404

                  if (isNotFound) {
                    return null
                  }

                  throw error
                })
              : null

            return {
              referenceName: reference.name,
              stats: statsResult.data ?? { total: 0, enriched: 0, pending: 0, sources: [] },
              job: jobResult?.data ?? null,
            }
          } catch {
            return {
              referenceName: reference.name,
              stats: statsByReferenceRef.current[reference.name] ?? { total: 0, enriched: 0, pending: 0, sources: [] },
              job: jobsByReferenceRef.current[reference.name] ?? null,
            }
          }
        })
      )

      if (isCancelled) return

      setStatsByReference((previous) => {
        const next = { ...previous }
        for (const update of updates) {
          next[update.referenceName] = update.stats
        }
        return next
      })

      setJobsByReference((previous) => {
        const next = { ...previous }
        for (const update of updates) {
          next[update.referenceName] = update.job
        }
        return next
      })

      setProgressLoadingByReference((previous) => {
        const next = { ...previous }
        for (const update of updates) {
          next[update.referenceName] = false
        }
        return next
      })
    }

    setProgressLoadingByReference((previous) => {
      const next = { ...previous }
      for (const reference of configuredReferences) {
        if (!(reference.name in next)) {
          next[reference.name] = true
        }
      }
      return next
    })

    loadProgress()
    const intervalId = window.setInterval(loadProgress, 3000)

    return () => {
      isCancelled = true
      window.clearInterval(intervalId)
    }
  }, [configuredReferences])

  const getStatusBadge = (status?: EnrichmentJobSummary['status']) => {
    switch (status) {
      case 'running':
        return <Badge className="bg-blue-500"><Loader2 className="mr-1 h-3 w-3 animate-spin" />{t('enrichmentTab.status.running')}</Badge>
      case 'paused':
        return <Badge variant="secondary"><Pause className="mr-1 h-3 w-3" />{t('enrichmentTab.status.paused')}</Badge>
      case 'paused_offline':
        return <Badge variant="secondary"><WifiOff className="mr-1 h-3 w-3" />{t('enrichmentTab.status.pausedOffline')}</Badge>
      case 'completed':
        return <Badge className="bg-green-500"><CheckCircle2 className="mr-1 h-3 w-3" />{t('enrichmentTab.status.completed')}</Badge>
      case 'failed':
        return <Badge variant="destructive"><AlertCircle className="mr-1 h-3 w-3" />{t('enrichmentTab.status.failed')}</Badge>
      case 'cancelled':
        return <Badge variant="outline"><StopCircle className="mr-1 h-3 w-3" />{t('enrichmentTab.status.cancelled')}</Badge>
      default:
        return <Badge variant="outline">{t('enrichmentTab.status.ready')}</Badge>
    }
  }

  const handleStartEnrichment = async (reference: ReferenceInfo) => {
    setStartingReferenceName(reference.name)

    try {
      const statsResponse = await apiClient.get(`/enrichment/stats/${reference.name}`)
      const pendingCount = statsResponse.data?.pending ?? 0
      setStatsByReference((previous) => ({
        ...previous,
        [reference.name]: statsResponse.data,
      }))

      const response = await apiClient.post(`/enrichment/start/${reference.name}`)
      setJobsByReference((previous) => ({
        ...previous,
        [reference.name]: response.data,
      }))

      useNotificationStore.getState().trackJob({
        jobId: response.data.id,
        jobType: 'enrichment',
        status: 'running',
        progress: 0,
        message: t('enrichmentTab.toasts.startedDescription', {
          count: pendingCount,
        }),
        startedAt: new Date().toISOString(),
        meta: { referenceName: reference.name },
      })

      toast.success(t('enrichmentTab.toasts.startedTitle'), {
        description: t('enrichmentTab.toasts.startedDescription', {
          count: pendingCount,
        }),
      })
    } catch (err: unknown) {
      toast.error(t('enrichmentTab.toasts.startErrorTitle'), {
        description: getApiErrorMessage(err, t('enrichmentTab.errors.startJob')),
      })
    } finally {
      setStartingReferenceName(null)
    }
  }

  if (error) {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>{t('dashboard.errors.loadTitle')}</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : t('dashboard.errors.loadSummary')}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-auto p-4">
      <div className="space-y-4">
        <div className="space-y-2">
          <h1 className="text-xl font-semibold tracking-tight">
            {t('dashboard.enrichmentView.title', 'API enrichment')}
          </h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            {t(
              'dashboard.enrichmentView.description',
              'Configure external enrichment for compatible references.'
            )}
          </p>
        </div>

        {!isLoading && enrichableReferences.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">
              {t('dashboard.enrichmentView.configuredCount', '{{count}} configured', {
                count: enrichableReferences.filter((reference) => reference.enrichment_enabled)
                  .length,
              })}
            </Badge>
            <Badge variant="outline">
              {t('dashboard.enrichmentView.availableCount', '{{count}} available', {
                count: enrichableReferences.filter((reference) => !reference.enrichment_enabled)
                  .length,
              })}
            </Badge>
          </div>
        ) : null}

        {isLoading ? (
          <div className="text-sm text-muted-foreground">
            {t('tree.loading', 'Loading...')}
          </div>
        ) : enrichableReferences.length === 0 ? (
          <Alert>
            <Sparkles className="h-4 w-4" />
            <AlertDescription>
              {t(
                'dashboard.enrichmentView.empty',
                'No enrichable references are currently available.'
              )}
            </AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-3">
            {enrichableReferences.map((reference) => {
              const metrics =
                entityRows.get(reference.table_name) ?? entityRows.get(reference.name)
              const job = jobsByReference[reference.name]
              const stats = statsByReference[reference.name]
              const progressLoading = progressLoadingByReference[reference.name] ?? false
              const jobRunProgress = getJobRunProgress(job)
              const currentProgress = jobRunProgress
                ? jobRunProgress.percentage
                : stats && stats.total > 0
                  ? (stats.enriched / stats.total) * 100
                  : 0
              const progressLabel = jobRunProgress
                ? `${t('enrichmentTab.runtime.runProgress')}: ${jobRunProgress.processed.toLocaleString()} / ${jobRunProgress.total.toLocaleString()} (${Math.round(currentProgress)}%)`
                : stats
                  ? `${stats.enriched.toLocaleString()} / ${stats.total.toLocaleString()}`
                  : '-'
              return (
                <Card key={reference.name} className="border-border/70">
                  <CardContent className="space-y-4 p-4">
                    <div className="min-w-0 space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-medium">{reference.name}</div>
                        <Badge variant="outline">
                          {t(`dashboard.referenceKinds.${reference.kind}`, {
                            defaultValue: reference.kind,
                          })}
                        </Badge>
                        <Badge variant={reference.enrichment_enabled ? 'secondary' : 'default'}>
                          {reference.enrichment_enabled
                            ? t('dashboard.status.enrichment_configured', 'Enrichment configured')
                            : t('dashboard.status.enrichment_available', 'Enrichment available')}
                        </Badge>
                      </div>
                    <div className="text-sm text-muted-foreground">
                        {t('dashboard.rows', '{{count}} rows', {
                          count: metrics?.row_count ?? reference.entity_count ?? 0,
                        })}
                      </div>
                      {reference.enrichment_enabled ? (
                        progressLoading ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            {t('tree.loading', 'Loading...')}
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              {getStatusBadge(job?.status)}
                              {job?.current_source_label ? (
                                <span className="text-xs text-muted-foreground">
                                  {job.current_source_label}
                                </span>
                              ) : null}
                              {job?.current_entity ? (
                                <span className="text-xs text-muted-foreground truncate">
                                  {t('enrichmentTab.currentEntity', { name: job.current_entity })}
                                </span>
                              ) : null}
                            </div>
                            <div className="space-y-1">
                              <div className="flex items-center justify-between text-xs text-muted-foreground">
                                <span>{t('enrichmentTab.cards.progress')}</span>
                                <span>{progressLabel}</span>
                              </div>
                              <Progress value={currentProgress} className="h-1.5" />
                            </div>
                            {stats ? (
                              <div className="space-y-2">
                                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                                  <span className="flex items-center gap-1">
                                    <CheckCircle2 className="h-3 w-3 text-green-600" />
                                    {t('enrichmentTab.stats.enriched')}: {stats.enriched.toLocaleString()}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3 text-orange-500" />
                                    {t('enrichmentTab.stats.pending')}: {stats.pending.toLocaleString()}
                                  </span>
                                </div>

                                {stats.sources.length > 0 ? (
                                  <div className="grid gap-2 md:grid-cols-2">
                                    {stats.sources.map((source) => {
                                      const sourceProgress = source.total > 0
                                        ? (source.enriched / source.total) * 100
                                        : 0

                                      return (
                                        <div
                                          key={source.source_id}
                                          className="rounded-md border bg-muted/20 px-3 py-2"
                                        >
                                          <div className="flex items-center justify-between gap-2">
                                            <span className="truncate text-xs font-medium text-foreground">
                                              {source.label}
                                            </span>
                                            <span className="text-[11px] text-muted-foreground">
                                              {source.enriched.toLocaleString()} / {source.total.toLocaleString()}
                                            </span>
                                          </div>
                                          <div className="mt-2 flex items-center gap-2">
                                            <Progress value={sourceProgress} className="h-1.5 flex-1" />
                                            <span className="text-[11px] text-muted-foreground">
                                              {Math.round(sourceProgress)}%
                                            </span>
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        )
                      ) : null}
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-4">
                      {reference.enrichment_enabled ? (
                        <>
                          <Button
                            type="button"
                            onClick={() => handleStartEnrichment(reference)}
                            disabled={startingReferenceName === reference.name}
                          >
                            {startingReferenceName === reference.name ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="mr-2 h-4 w-4" />
                            )}
                            {startingReferenceName === reference.name
                              ? t('enrichmentTab.state.starting', 'Starting...')
                              : t('dashboard.actions.enrichNow', 'Enrich now')}
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setActiveReference(reference)}
                          >
                            {t('dashboard.actions.quickPanel', 'Quick panel')}
                          </Button>
                        </>
                      ) : null}
                      <Button
                        type="button"
                        variant={reference.enrichment_enabled ? 'ghost' : 'default'}
                        onClick={() =>
                          navigate(`/sources/reference/${encodeURIComponent(reference.name)}?tab=enrichment`)
                        }
                      >
                        {reference.enrichment_enabled
                          ? t('dashboard.actions.openWorkspace', 'Open workspace')
                          : t('dashboard.actions.configureEnrichment', 'Configure enrichment')}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      <EnrichmentWorkspaceSheet
        open={activeReference !== null}
        reference={activeReference}
        onOpenChange={(open) => !open && setActiveReference(null)}
        onConfigSaved={async () => {
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: importQueryKeys.entities.references() }),
            queryClient.invalidateQueries({ queryKey: importQueryKeys.summary() }),
          ])
        }}
      />
    </div>
  )
}
