import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertCircle, AlertTriangle, CheckCircle2, Clock, Loader2, Pause, Play, Sparkles, StopCircle, WifiOff } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { EnrichmentWorkspaceSheet } from './EnrichmentWorkspaceSheet'
import { useImportSummaryDetailed } from '@/hooks/useImportSummaryDetailed'
import { useReferences, type ReferenceInfo } from '@/hooks/useReferences'
import { apiClient } from '@/shared/lib/api/client'
import { toast } from 'sonner'
import { useNotificationStore } from '@/stores/notificationStore'

interface EnrichmentJobSummary {
  id: string
  status: 'pending' | 'running' | 'paused' | 'paused_offline' | 'completed' | 'failed' | 'cancelled'
  total: number
  processed: number
  current_entity?: string
}

interface EnrichmentStatsSummary {
  total: number
  enriched: number
  pending: number
}

export function EnrichmentView() {
  const { t } = useTranslation('sources')
  const queryClient = useQueryClient()
  const { data: referencesData, isLoading, error } = useReferences()
  const { data: summary } = useImportSummaryDetailed()
  const [activeReference, setActiveReference] = useState<ReferenceInfo | null>(null)
  const [startingReferenceName, setStartingReferenceName] = useState<string | null>(null)
  const [jobsByReference, setJobsByReference] = useState<Record<string, EnrichmentJobSummary | null>>({})
  const [statsByReference, setStatsByReference] = useState<Record<string, EnrichmentStatsSummary>>({})
  const [progressLoadingByReference, setProgressLoadingByReference] = useState<Record<string, boolean>>({})

  const references = referencesData?.references ?? []
  const enrichableReferences = references.filter((reference) => reference.can_enrich)
  const unavailableReferences = references.filter((reference) => !reference.can_enrich)
  const configuredReferences = enrichableReferences.filter((reference) => reference.enrichment_enabled)
  const configuredReferenceKey = configuredReferences.map((reference) => reference.name).join('|')

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
      const updates = await Promise.all(
        configuredReferences.map(async (reference) => {
          const [statsResult, jobResult] = await Promise.allSettled([
            apiClient.get<EnrichmentStatsSummary>(`/enrichment/stats/${reference.name}`),
            apiClient.get<EnrichmentJobSummary>(`/enrichment/job/${reference.name}`),
          ])

          const stats =
            statsResult.status === 'fulfilled'
              ? statsResult.value.data
              : { total: 0, enriched: 0, pending: 0 }

          const job =
            jobResult.status === 'fulfilled'
              ? jobResult.value.data
              : null

          return {
            referenceName: reference.name,
            stats,
            job,
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
  }, [configuredReferenceKey])

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
    } catch (err: any) {
      toast.error(t('enrichmentTab.toasts.startErrorTitle'), {
        description: err.response?.data?.detail || t('enrichmentTab.errors.startJob'),
      })
    } finally {
      setStartingReferenceName(null)
    }
  }

  if (error) {
    return (
      <div className="p-6">
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
    <div className="flex h-full flex-col overflow-auto p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
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
              const currentProgress = job
                ? (job.total > 0 ? (job.processed / job.total) * 100 : 0)
                : stats && stats.total > 0
                  ? (stats.enriched / stats.total) * 100
                  : 0
              const progressLabel = job
                ? `${job.processed.toLocaleString()} / ${job.total.toLocaleString()} (${Math.round(currentProgress)}%)`
                : stats
                  ? `${stats.enriched.toLocaleString()} / ${stats.total.toLocaleString()}`
                  : '-'
              return (
                <Card key={reference.name} className="border-border/70">
                  <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="min-w-0 flex-1 space-y-3">
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
                            ) : null}
                          </div>
                        )
                      ) : null}
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      {reference.enrichment_enabled ? (
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
                      ) : null}
                      <Button
                        type="button"
                        variant={reference.enrichment_enabled ? 'outline' : 'default'}
                        onClick={() => setActiveReference(reference)}
                      >
                        {reference.enrichment_enabled
                          ? t('dashboard.actions.manageEnrichment', 'Manage enrichment')
                          : t('dashboard.actions.configureEnrichment', 'Configure enrichment')}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}

        {unavailableReferences.length > 0 ? (
          <p className="text-sm text-muted-foreground">
            {t('dashboard.enrichmentView.unavailable', 'No enrichment available for: {{names}}', {
              names: unavailableReferences.map((reference) => reference.name).join(', '),
            })}
          </p>
        ) : null}
      </div>

      <EnrichmentWorkspaceSheet
        open={activeReference !== null}
        reference={activeReference}
        onOpenChange={(open) => !open && setActiveReference(null)}
        onConfigSaved={async () => {
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['references'] }),
            queryClient.invalidateQueries({ queryKey: ['import-summary'] }),
          ])
        }}
      />
    </div>
  )
}
