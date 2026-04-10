/**
 * EnrichmentTab - Multi-source enrichment management for reference entities.
 *
 * Features:
 * - Configure several external APIs per reference
 * - Start one source or all enabled sources
 * - Track global and per-source progress
 * - Preview enrichment results grouped by source
 * - View persisted enrichment results grouped by source
 */

import { useTranslation } from 'react-i18next'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  Database,
  Eye,
  ExternalLink,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  StopCircle,
  Trash2,
  WifiOff,
} from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import { ApiEnrichmentConfig } from './ApiEnrichmentConfig'
import {
  useEnrichmentState,
  getResultEntityName,
} from '../../hooks/useEnrichmentState'

interface EnrichmentTabProps {
  referenceName: string
  hasEnrichment: boolean
  onConfigSaved?: () => void
  mode?: 'workspace' | 'quick'
  initialSourceId?: string | null
  onOpenWorkspace?: (sourceId?: string) => void
}

import {
  isStructuredSourceSummary,
  renderMappedPreview,
  renderRawPreview,
  renderStructuredSummary,
  renderValue,
} from './enrichmentRenderers'

export function EnrichmentTab({
  referenceName,
  hasEnrichment,
  onConfigSaved,
  mode = 'workspace',
  initialSourceId = null,
  onOpenWorkspace,
}: EnrichmentTabProps) {
  const { t } = useTranslation(['sources', 'common'])

  const {
    // Config
    referenceConfig,
    configLoading,
    configSaving,
    configError,
    configSaved,

    // Stats
    stats,
    statsLoading,

    // Job
    job,
    jobLoadingScope,
    isTerminalJob,

    // Results
    resultsLoading,
    recentResults,

    // Entities
    entities,
    entitiesLoading,
    entitySearch,
    setEntitySearch,

    // Preview
    previewQuery,
    setPreviewQuery,
    previewData,
    previewLoading,
    previewError,
    previewResultMode,
    setPreviewResultMode,

    // Sources
    sources,
    enabledSources,
    activeSource,
    setActiveSourceId,
    activeSourceStats,
    activeSourceResults,
    activeSourceProgress,
    activeSourceIndex,
    activePreviewResult,
    isRunningSingleSource,
    canStartActiveSource,
    quickSelectedSource,

    // UI
    workspacePane,
    setWorkspacePane,
    selectedResult,
    setSelectedResult,
    isRefreshing,
    isSpatialReference,
    apiCategory,

    // Network
    isOffline,

    // Actions
    addSource,
    updateSourceLabel,
    updateSourceConfig,
    applyPresetLabel,
    toggleSourceEnabled,
    duplicateSource,
    moveSource,
    removeSource,
    saveEnrichmentConfig,
    startGlobalJob,
    startSourceJob,
    pauseJob,
    resumeJob,
    cancelJob,
    handleRefresh,
    previewEnrichment,
    resetPreviewState,
    loadEntities,
    getSourceProgress,

    // Refs
    workspaceSectionRef,
  } = useEnrichmentState({
    referenceName,
    hasEnrichment,
    mode,
    initialSourceId,
    onConfigSaved,
  })

  if (mode === 'quick') {
    const quickPreviewResult =
      quickSelectedSource && previewData?.results?.length
        ? previewData.results.find((result) => result.source_id === quickSelectedSource.id) ?? null
        : null

    return (
      <div className="space-y-4">
        {configError ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{configError}</AlertDescription>
          </Alert>
        ) : null}

        <Card className="sticky top-0 z-20 overflow-hidden border-border/70 bg-background shadow-sm">
          <CardContent className="space-y-4 p-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {t('enrichmentTab.summary.enabledSources', {
                    defaultValue: '{{count}} source(s) enabled',
                    count: enabledSources.length,
                  })}
                </Badge>
                <Badge variant="outline">
                  {t('enrichmentTab.summary.totalSources', {
                    defaultValue: '{{count}} source(s) configured',
                    count: sources.length,
                  })}
                </Badge>
                {stats ? (
                  <>
                    <Badge variant="outline">
                      {t('enrichmentTab.stats.enriched')}: {stats.enriched.toLocaleString()}
                    </Badge>
                    <Badge variant="outline">
                      {t('enrichmentTab.stats.pending')}: {stats.pending.toLocaleString()}
                    </Badge>
                  </>
                ) : null}
              </div>

              {job ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge variant={job.status === 'running' ? 'default' : 'outline'}>
                      {t(`enrichmentTab.status.${job.status}`, {
                        defaultValue: job.status,
                      })}
                    </Badge>
                    {job.current_source_label ? (
                      <span className="text-muted-foreground">{job.current_source_label}</span>
                    ) : null}
                    {job.current_entity ? (
                      <span className="truncate text-muted-foreground">
                        {t('enrichmentTab.currentEntity', { name: job.current_entity })}
                      </span>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{t('enrichmentTab.cards.progress')}</span>
                      <span>
                        {job.processed.toLocaleString()} / {job.total.toLocaleString()}
                      </span>
                    </div>
                    <Progress value={job.total > 0 ? (job.processed / job.total) * 100 : 0} className="h-1.5" />
                  </div>
                </div>
              ) : stats?.total ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{t('enrichmentTab.cards.progress')}</span>
                    <span>
                      {stats.enriched.toLocaleString()} / {stats.total.toLocaleString()}
                    </span>
                  </div>
                  <Progress value={stats.total > 0 ? (stats.enriched / stats.total) * 100 : 0} className="h-1.5" />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t('enrichmentTab.actions.description')}
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-4">
              {isTerminalJob ? (
                <Button
                  onClick={startGlobalJob}
                  disabled={jobLoadingScope !== null || !stats || stats.pending === 0 || isOffline}
                  title={isOffline ? t('enrichmentTab.offline.internetRequired') : undefined}
                >
                  {jobLoadingScope === 'all' ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  {t('enrichmentTab.runtime.startAll', {
                    defaultValue: 'Lancer toutes les APIs',
                  })}
                </Button>
              ) : job?.status === 'running' ? (
                <>
                  <Button variant="secondary" onClick={() => pauseJob()} disabled={jobLoadingScope !== null}>
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Pause className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.pause')}
                  </Button>
                  <Button variant="destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                    <StopCircle className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                </>
              ) : job?.status === 'paused' || job?.status === 'paused_offline' ? (
                <>
                  <Button
                    onClick={() => resumeJob()}
                    disabled={jobLoadingScope !== null || isOffline}
                    title={isOffline ? t('enrichmentTab.offline.internetRequiredResume') : undefined}
                  >
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.resume')}
                  </Button>
                  <Button variant="destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                    <StopCircle className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                </>
              ) : null}

              <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                {t('common:actions.refresh')}
              </Button>

              {onOpenWorkspace ? (
                <Button variant="outline" onClick={() => onOpenWorkspace(quickSelectedSource?.id)}>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  {t('dashboard.actions.openWorkspace', {
                    defaultValue: 'Ouvrir le workspace',
                  })}
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>

        {isOffline ? (
          <Alert>
            <WifiOff className="h-4 w-4" />
            <AlertTitle>{t('enrichmentTab.offline.title')}</AlertTitle>
            <AlertDescription>{t('enrichmentTab.offline.description')}</AlertDescription>
          </Alert>
        ) : null}

        {configLoading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : sources.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-start gap-3 p-6">
              <div>
                <h3 className="font-medium">
                  {t('enrichmentTab.config.empty', {
                    defaultValue: 'Aucune source API configurée pour cette référence.',
                  })}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {t('dashboard.enrichment.quickEmpty', {
                    defaultValue: 'Le panel rapide sert à lancer et tester. Ouvre le workspace pour configurer les sources.',
                  })}
                </p>
              </div>
              {onOpenWorkspace ? (
                <Button onClick={() => onOpenWorkspace(quickSelectedSource?.id)}>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  {t('dashboard.actions.openWorkspace', {
                    defaultValue: 'Ouvrir le workspace',
                  })}
                </Button>
              ) : null}
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(400px,1.1fr)]">
            <Card className="border-border/70">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">
                  {t('enrichmentTab.config.sourcesTitle', {
                    defaultValue: 'API sources',
                  })}
                </CardTitle>
                <CardDescription>
                  {t('dashboard.enrichment.quickPanelDescription', {
                    defaultValue: 'Sélectionne une source pour la tester ou lancer un enrichissement rapide.',
                  })}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {sources.map((source) => {
                  const sourceStats = stats?.sources.find((item) => item.source_id === source.id)
                  const sourceProgress = getSourceProgress(source.id, sourceStats)
                  const isSelected = quickSelectedSource?.id === source.id
                  const canStartSource =
                    source.enabled &&
                    (!job || ['completed', 'failed', 'cancelled'].includes(job.status)) &&
                    (sourceStats?.pending ?? 0) > 0

                  return (
                    <div
                      key={source.id}
                      className={`rounded-xl border px-4 py-3 transition-colors ${
                        isSelected ? 'border-primary/40 bg-primary/5' : 'border-border/70 bg-background'
                      }`}
                    >
                      <div className="space-y-3">
                        <div className="min-w-0 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              type="button"
                              className="truncate text-left font-medium hover:text-primary"
                              onClick={() => resetPreviewState(source.id)}
                            >
                              {source.label}
                            </button>
                            <Badge variant={source.enabled ? 'secondary' : 'outline'}>
                              {source.enabled
                                ? t('sources:configEditor.enabled')
                                : t('sources:configEditor.disabled')}
                            </Badge>
                            {sourceStats ? (
                              <Badge variant="outline">
                                {t(`enrichmentTab.status.${sourceStats.status}`, {
                                  defaultValue: sourceStats.status,
                                })}
                              </Badge>
                            ) : null}
                          </div>
                          <div className="truncate text-xs text-muted-foreground">
                            {source.config.api_url || source.plugin}
                          </div>
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                              <span>{t('enrichmentTab.cards.progress')}</span>
                              <span>
                                {sourceProgress.processed.toLocaleString()} / {sourceProgress.total.toLocaleString()}
                              </span>
                            </div>
                            <Progress value={sourceProgress.percentage} className="h-1.5" />
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-3">
                          <Button
                            type="button"
                            size="sm"
                            variant={isSelected ? 'default' : 'outline'}
                            onClick={() => resetPreviewState(source.id)}
                          >
                            <Eye className="mr-2 h-4 w-4" />
                            {t('dashboard.actions.testApi', {
                              defaultValue: "Tester l'API",
                            })}
                          </Button>

                          {canStartSource ? (
                            <Button
                              type="button"
                              size="sm"
                              onClick={() => startSourceJob(source.id)}
                              disabled={jobLoadingScope !== null || isOffline}
                            >
                              {jobLoadingScope === source.id ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="mr-2 h-4 w-4" />
                              )}
                              {t('enrichmentTab.runtime.startSource', {
                                defaultValue: 'Lancer cette API',
                              })}
                            </Button>
                          ) : null}

                          {onOpenWorkspace ? (
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => onOpenWorkspace(source.id)}
                            >
                              {t('common:actions.edit')}
                            </Button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </CardContent>
            </Card>

            <div className="space-y-4">
              <Card className="border-border/70">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">
                    {t('dashboard.actions.testApi', {
                      defaultValue: "Tester l'API",
                    })}
                  </CardTitle>
                  <div className="space-y-1">
                    <CardDescription>
                      {quickSelectedSource
                        ? quickSelectedSource.label
                        : t('dashboard.enrichment.quickSelectSource', {
                            defaultValue: 'Sélectionne une source pour tester sa réponse.',
                          })}
                    </CardDescription>
                    {quickSelectedSource?.config.api_url ? (
                      <div className="truncate text-xs text-muted-foreground">
                        {quickSelectedSource.config.api_url}
                      </div>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {quickSelectedSource?.enabled ? (
                    <>
                      <div className="space-y-2">
                        <Label>
                          {isSpatialReference
                            ? t('dashboard.enrichment.manualGeometryLabel', {
                                defaultValue: 'Coordinates or geometry',
                              })
                            : t('common:labels.name')}
                        </Label>
                        <div className="flex gap-2">
                          <Input
                            placeholder={
                              isSpatialReference
                                ? t('dashboard.enrichment.manualGeometryPlaceholder', {
                                    defaultValue: 'Latitude, longitude or WKT geometry',
                                  })
                                : t('enrichmentTab.preview.manualInput')
                            }
                            value={previewQuery}
                            onChange={(event) => setPreviewQuery(event.target.value)}
                            onKeyDown={(event) => {
                              if (event.key === 'Enter') {
                                void previewEnrichment(undefined, quickSelectedSource.id)
                              }
                            }}
                          />
                          <Button
                            type="button"
                            onClick={() => previewEnrichment(undefined, quickSelectedSource.id)}
                            disabled={previewLoading || !String(previewQuery ?? '').trim()}
                          >
                            {previewLoading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>

                      {entities.length > 0 ? (
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">
                            {t('dashboard.enrichment.quickExamples', {
                              defaultValue: 'Essayer avec une entité existante',
                            })}
                          </Label>
                          <div className="flex flex-wrap gap-2">
                            {entities.slice(0, 6).map((entity) => (
                              <Button
                                key={entity.id}
                                type="button"
                                size="sm"
                                variant="outline"
                                className="max-w-full"
                                onClick={() => {
                                  const entityName = String(entity.name ?? '')
                                  setPreviewQuery(entityName)
                                  void previewEnrichment(entityName, quickSelectedSource.id, entity.id)
                                }}
                              >
                                <span className="truncate">{entity.name}</span>
                              </Button>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      <div className="rounded-lg border bg-muted/20 p-3">
                        {previewLoading ? (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                          </div>
                        ) : previewError ? (
                          <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{previewError}</AlertDescription>
                          </Alert>
                        ) : quickPreviewResult?.success ? (
                          <div className="space-y-3">
                            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/70 bg-background p-1">
                              <Button
                                type="button"
                                size="sm"
                                variant={previewResultMode === 'mapped' ? 'default' : 'ghost'}
                                onClick={() => setPreviewResultMode('mapped')}
                              >
                                {t('dashboard.enrichment.mappedFields', {
                                  defaultValue: 'Champs mappés',
                                })}
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant={previewResultMode === 'raw' ? 'default' : 'ghost'}
                                onClick={() => setPreviewResultMode('raw')}
                              >
                                {t('dashboard.enrichment.rawApiResponse', {
                                  defaultValue: 'Réponse brute API',
                                })}
                              </Button>
                            </div>

                            {previewResultMode === 'mapped' ? (
                              quickPreviewResult.data && Object.keys(quickPreviewResult.data).length > 0 ? (
                                isStructuredSourceSummary(quickPreviewResult.data)
                                  ? renderStructuredSummary(quickPreviewResult.data, t)
                                  : renderMappedPreview(quickPreviewResult.data)
                              ) : (
                                <div className="py-8 text-center text-sm text-muted-foreground">
                                  {t('dashboard.enrichment.noMappedFields', {
                                    defaultValue: 'Aucun champ mappé pour cette source.',
                                  })}
                                </div>
                              )
                            ) : quickPreviewResult.raw_data !== undefined ? (
                              renderRawPreview(quickPreviewResult.raw_data)
                            ) : (
                              <div className="py-8 text-center text-sm text-muted-foreground">
                                {t('dashboard.enrichment.noRawApiResponse', {
                                  defaultValue: 'Aucune réponse brute disponible pour ce test.',
                                })}
                              </div>
                            )}
                          </div>
                        ) : quickPreviewResult?.error ? (
                          <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{quickPreviewResult.error}</AlertDescription>
                          </Alert>
                        ) : (
                          <div className="py-8 text-center text-sm text-muted-foreground">
                            {t('dashboard.enrichment.quickTesterEmpty', {
                              defaultValue: "Lance un test pour voir immédiatement la réponse de l'API.",
                            })}
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                      {t('dashboard.enrichment.quickTesterDisabled', {
                        defaultValue: 'Active cette source dans le workspace complet pour pouvoir la tester.',
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/70">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">
                    {t('enrichmentTab.tabs.results')}
                  </CardTitle>
                  <CardDescription>
                    {t('dashboard.enrichment.quickResultsDescription', {
                      defaultValue: 'Aperçu rapide des derniers traitements. Le détail complet est dans le workspace.',
                    })}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {resultsLoading ? (
                    <div className="flex items-center justify-center py-6">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : recentResults.length > 0 ? (
                    <div className="space-y-2">
                      {recentResults.map((result) => (
                        <div
                          key={`${result.source_id}-${getResultEntityName(result)}-${result.processed_at}`}
                          className="rounded-lg border px-3 py-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium">{getResultEntityName(result)}</div>
                              <div className="truncate text-xs text-muted-foreground">{result.source_label}</div>
                            </div>
                            <Badge variant={result.success ? 'secondary' : 'destructive'}>
                              {result.success
                                ? t('enrichmentTab.result.success')
                                : t('enrichmentTab.result.failed')}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {t('enrichmentTab.results.emptyDescription')}
                    </p>
                  )}

                  {onOpenWorkspace ? (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => onOpenWorkspace(quickSelectedSource?.id)}
                    >
                      <ExternalLink className="mr-2 h-4 w-4" />
                      {t('dashboard.actions.openWorkspace', {
                        defaultValue: 'Ouvrir le workspace',
                      })}
                    </Button>
                  ) : null}
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {configError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{configError}</AlertDescription>
        </Alert>
      ) : null}

      {configSaved ? (
        <Alert className="border-success/30 bg-success/10">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <AlertDescription className="text-success">
            {t('sources:configEditor.savedSuccess')}
          </AlertDescription>
        </Alert>
      ) : null}

      <Card className="sticky top-0 z-20 overflow-hidden border-border/70 bg-background shadow-sm">
        <CardContent className="space-y-4 p-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {t('enrichmentTab.summary.enabledSources', {
                    defaultValue: '{{count}} source(s) enabled',
                    count: enabledSources.length,
                  })}
                </Badge>
                <Badge variant="outline">
                  {t('enrichmentTab.summary.totalSources', {
                    defaultValue: '{{count}} source(s) configured',
                    count: sources.length,
                  })}
                </Badge>
                {stats ? (
                  <>
                    <Badge variant="outline">
                      {t('enrichmentTab.stats.enriched')}: {stats.enriched.toLocaleString()}
                    </Badge>
                    <Badge variant="outline">
                      {t('enrichmentTab.stats.pending')}: {stats.pending.toLocaleString()}
                    </Badge>
                  </>
                ) : null}
              </div>

              {job ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge variant={job.status === 'running' ? 'default' : 'outline'}>
                      {t(`enrichmentTab.status.${job.status}`, {
                        defaultValue: job.status,
                      })}
                    </Badge>
                    {job.current_source_label ? (
                      <span className="text-muted-foreground">{job.current_source_label}</span>
                    ) : null}
                    {job.current_entity ? (
                      <span className="truncate text-muted-foreground">
                        {t('enrichmentTab.currentEntity', { name: job.current_entity })}
                      </span>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{t('enrichmentTab.cards.progress')}</span>
                      <span>
                        {job.processed.toLocaleString()} / {job.total.toLocaleString()}
                      </span>
                    </div>
                    <Progress value={job.total > 0 ? (job.processed / job.total) * 100 : 0} className="h-1.5" />
                  </div>
                </div>
              ) : statsLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('tree.loading', 'Loading...')}
                </div>
              ) : stats?.total ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{t('enrichmentTab.cards.progress')}</span>
                    <span>
                      {stats.enriched.toLocaleString()} / {stats.total.toLocaleString()}
                    </span>
                  </div>
                  <Progress value={stats.total > 0 ? (stats.enriched / stats.total) * 100 : 0} className="h-1.5" />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t('enrichmentTab.actions.description')}
                </p>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={saveEnrichmentConfig} disabled={configSaving || configLoading || !referenceConfig}>
                {configSaving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('sources:configEditor.saving')}
                  </>
                ) : (
                  t('sources:configEditor.save')
                )}
              </Button>

              {isTerminalJob ? (
                <Button
                  onClick={startGlobalJob}
                  disabled={jobLoadingScope !== null || !stats || stats.pending === 0 || isOffline}
                  title={isOffline ? t('enrichmentTab.offline.internetRequired') : undefined}
                >
                  {jobLoadingScope === 'all' ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  {t('enrichmentTab.runtime.startAll', {
                    defaultValue: 'Lancer toutes les APIs',
                  })}
                </Button>
              ) : job?.status === 'running' ? (
                <>
                  <Button variant="secondary" onClick={() => pauseJob()} disabled={jobLoadingScope !== null}>
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Pause className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.pause')}
                  </Button>
                  <Button variant="destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                    <StopCircle className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                </>
              ) : job?.status === 'paused' || job?.status === 'paused_offline' ? (
                <>
                  <Button
                    onClick={() => resumeJob()}
                    disabled={jobLoadingScope !== null || isOffline}
                    title={isOffline ? t('enrichmentTab.offline.internetRequiredResume') : undefined}
                  >
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.resume')}
                  </Button>
                  <Button variant="destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                    <StopCircle className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                </>
              ) : null}

              <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                {t('common:actions.refresh')}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {isOffline ? (
        <Alert>
          <WifiOff className="h-4 w-4" />
          <AlertTitle>{t('enrichmentTab.offline.title')}</AlertTitle>
          <AlertDescription>{t('enrichmentTab.offline.description')}</AlertDescription>
        </Alert>
      ) : null}

      {job?.error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{t('common:status.error')}</AlertTitle>
          <AlertDescription>{job.error}</AlertDescription>
        </Alert>
      ) : null}

      {configLoading || !referenceConfig ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : sources.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-start gap-3 p-6">
            <div>
              <h3 className="font-medium">
                {t('enrichmentTab.config.empty', {
                  defaultValue: 'Aucune source API configurée pour cette référence.',
                })}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {t('dashboard.enrichment.workspaceEmpty', {
                  defaultValue: 'Ajoute une première source pour configurer, tester et lancer ton enrichissement.',
                })}
              </p>
            </div>
            <Button onClick={addSource}>
              <Plus className="mr-2 h-4 w-4" />
              {t('enrichmentTab.config.addSource', {
                defaultValue: 'Ajouter une API',
              })}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
          <Card className="border-border/70">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-sm font-medium">
                    {t('enrichmentTab.config.sourcesTitle', {
                      defaultValue: 'API sources',
                    })}
                  </CardTitle>
                  <CardDescription>
                    {t('dashboard.enrichment.workspaceListDescription', {
                      defaultValue: 'Sélectionne une source pour la configurer ou la tester.',
                    })}
                  </CardDescription>
                </div>
                <Button type="button" size="sm" onClick={addSource}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                {sources.map((source) => {
                  const sourceStats = stats?.sources.find((item) => item.source_id === source.id)
                  const sourceProgress = getSourceProgress(source.id, sourceStats)
                  const isSelected = activeSource?.id === source.id

                  return (
                    <button
                      key={source.id}
                      type="button"
                      onClick={() => {
                        setActiveSourceId(source.id)
                        setWorkspacePane('config')
                        resetPreviewState(source.id)
                      }}
                      className={`w-full rounded-xl border px-3 py-3 text-left transition-colors ${
                        isSelected ? 'border-primary/40 bg-primary/5' : 'border-border/70 bg-background hover:bg-muted/30'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium">{source.label}</div>
                          <div className="mt-1 truncate text-xs text-muted-foreground">
                            {source.config.api_url || source.plugin}
                          </div>
                        </div>
                        <Badge variant={source.enabled ? 'secondary' : 'outline'}>
                          {source.enabled
                            ? t('sources:configEditor.enabled')
                            : t('sources:configEditor.disabled')}
                        </Badge>
                      </div>

                      <div className="mt-3 space-y-1.5">
                        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                          <span>{sourceStats?.status || t('enrichmentTab.status.ready')}</span>
                          <span>
                            {sourceProgress.processed.toLocaleString()} / {sourceProgress.total.toLocaleString()}
                          </span>
                        </div>
                        <Progress value={sourceProgress.percentage} className="h-1.5" />
                      </div>
                      {sourceStats ? (
                        <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                          <span>
                            {t('enrichmentTab.stats.enriched')}: {sourceStats.enriched.toLocaleString()}
                          </span>
                          <span>
                            {t('enrichmentTab.stats.pending')}: {sourceStats.pending.toLocaleString()}
                          </span>
                        </div>
                      ) : null}
                    </button>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {activeSource ? (
            <>
              <div ref={workspaceSectionRef} className="space-y-4">
                <Card className="border-border/70">
                  <CardHeader className="space-y-5 pb-4">
                    <div className="space-y-3">
                      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline">{activeSource.id}</Badge>
                          <Badge
                            variant={
                              activeSourceStats?.status === 'running' || isRunningSingleSource
                                ? 'default'
                                : 'outline'
                            }
                          >
                            {t(`enrichmentTab.status.${activeSourceStats?.status || 'ready'}`, {
                              defaultValue: activeSourceStats?.status || 'ready',
                            })}
                          </Badge>
                        </div>

                        <div className="flex items-center justify-between gap-3 rounded-full border border-border/70 bg-muted/20 px-3 py-2 xl:min-w-[230px] xl:justify-start">
                          <div className="min-w-0">
                            <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                              {t('dashboard.enrichment.sourceAvailability', {
                                defaultValue: 'Disponibilité',
                              })}
                            </div>
                            <div className="text-sm font-medium">
                              {activeSource.enabled
                                ? t('sources:configEditor.enabled')
                                : t('sources:configEditor.disabled')}
                            </div>
                          </div>
                          <Switch
                            id={`source-enabled-${activeSource.id}`}
                            checked={activeSource.enabled}
                            onCheckedChange={(checked) => toggleSourceEnabled(activeSource.id, checked)}
                          />
                        </div>
                      </div>

                      <div className="min-w-0 space-y-2">
                        <Label htmlFor={`source-label-${activeSource.id}`} className="text-xs font-medium text-muted-foreground">
                          {t('enrichmentTab.config.sourceLabel', {
                            defaultValue: 'Nom de la source',
                          })}
                        </Label>
                        <Input
                          id={`source-label-${activeSource.id}`}
                          value={activeSource.label}
                          onChange={(event) => updateSourceLabel(activeSource.id, event.target.value)}
                          placeholder={t('enrichmentTab.config.sourceLabel', {
                            defaultValue: 'Nom de la source',
                          })}
                          className="max-w-md xl:max-w-lg"
                        />
                        <div className="truncate text-xs text-muted-foreground">
                          {activeSource.config.api_url || activeSource.plugin}
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{t('enrichmentTab.cards.progress')}</span>
                          <span>
                            {activeSourceProgress?.processed.toLocaleString() ?? 0} / {activeSourceProgress?.total.toLocaleString() ?? 0}
                          </span>
                        </div>
                        <Progress value={activeSourceProgress?.percentage ?? 0} className="h-1.5" />
                      </div>

                      {activeSourceStats ? (
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={activeSource.enabled ? 'secondary' : 'outline'}>
                            {activeSource.enabled
                              ? t('sources:configEditor.enabled')
                              : t('sources:configEditor.disabled')}
                          </Badge>
                          <Badge variant="outline">
                            {t('enrichmentTab.stats.enriched')}: {activeSourceStats.enriched.toLocaleString()}
                          </Badge>
                          <Badge variant="outline">
                            {t('enrichmentTab.stats.pending')}: {activeSourceStats.pending.toLocaleString()}
                          </Badge>
                        </div>
                      ) : (
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={activeSource.enabled ? 'secondary' : 'outline'}>
                            {activeSource.enabled
                              ? t('sources:configEditor.enabled')
                              : t('sources:configEditor.disabled')}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-3 border-t border-border/70 pt-4">
                      <div className="flex flex-col gap-3 2xl:flex-row 2xl:items-center 2xl:justify-between">
                        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/70 bg-muted/20 p-1">
                          <Button
                            type="button"
                            size="sm"
                            variant={workspacePane === 'config' ? 'default' : 'ghost'}
                            onClick={() => setWorkspacePane('config')}
                          >
                            <Settings className="mr-2 h-4 w-4" />
                            {t('reference.configuration', {
                              defaultValue: 'Configuration',
                            })}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant={workspacePane === 'preview' ? 'default' : 'ghost'}
                            onClick={() => setWorkspacePane('preview')}
                          >
                            <Eye className="mr-2 h-4 w-4" />
                            {t('dashboard.actions.testApi', {
                              defaultValue: "Tester l'API",
                            })}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant={workspacePane === 'results' ? 'default' : 'ghost'}
                            onClick={() => setWorkspacePane('results')}
                          >
                            <Database className="mr-2 h-4 w-4" />
                            {t('enrichmentTab.tabs.results')}
                          </Button>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                          {canStartActiveSource ? (
                            <Button
                              type="button"
                              size="sm"
                              onClick={() => startSourceJob(activeSource.id)}
                              disabled={jobLoadingScope !== null || isOffline}
                            >
                              {jobLoadingScope === activeSource.id ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="mr-2 h-4 w-4" />
                              )}
                              {t('enrichmentTab.runtime.startSource', {
                                defaultValue: 'Lancer cette API',
                              })}
                            </Button>
                          ) : null}

                          {isRunningSingleSource && job?.status === 'running' ? (
                            <>
                              <Button size="sm" variant="secondary" onClick={() => pauseJob(activeSource.id)} disabled={jobLoadingScope !== null}>
                                {jobLoadingScope === activeSource.id ? (
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                  <Pause className="mr-2 h-4 w-4" />
                                )}
                                {t('enrichmentTab.actions.pause')}
                              </Button>
                              <Button size="sm" variant="destructive" onClick={() => cancelJob(activeSource.id)} disabled={jobLoadingScope !== null}>
                                <StopCircle className="mr-2 h-4 w-4" />
                                {t('common:actions.cancel')}
                              </Button>
                            </>
                          ) : null}

                          {isRunningSingleSource && (job?.status === 'paused' || job?.status === 'paused_offline') ? (
                            <>
                              <Button size="sm" onClick={() => resumeJob(activeSource.id)} disabled={jobLoadingScope !== null || isOffline}>
                                {jobLoadingScope === activeSource.id ? (
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                  <Play className="mr-2 h-4 w-4" />
                                )}
                                {t('enrichmentTab.actions.resume')}
                              </Button>
                              <Button size="sm" variant="destructive" onClick={() => cancelJob(activeSource.id)} disabled={jobLoadingScope !== null}>
                                <StopCircle className="mr-2 h-4 w-4" />
                                {t('common:actions.cancel')}
                              </Button>
                            </>
                          ) : null}

                          <div className="flex items-center gap-1 rounded-xl border border-border/70 bg-background p-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              disabled={activeSourceIndex === 0}
                              onClick={() => moveSource(activeSource.id, 'up')}
                            >
                              <ChevronUp className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              disabled={activeSourceIndex === sources.length - 1}
                              onClick={() => moveSource(activeSource.id, 'down')}
                            >
                              <ChevronDown className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => duplicateSource(activeSource.id)}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button type="button" variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:bg-destructive/10 hover:text-destructive">
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>
                                    {t('dashboard.enrichment.deleteSourceTitle', {
                                      defaultValue: 'Supprimer cette source ?',
                                    })}
                                  </AlertDialogTitle>
                                  <AlertDialogDescription>
                                    {t('dashboard.enrichment.deleteSourceDescription', {
                                      defaultValue: 'La source sera retirée de la configuration locale jusqu’à la prochaine sauvegarde.',
                                    })}
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>{t('common:actions.cancel')}</AlertDialogCancel>
                                  <AlertDialogAction onClick={() => removeSource(activeSource.id)}>
                                    {t('common:actions.delete')}
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {workspacePane === 'config' ? (
                  <Card className="border-border/70">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium">
                        {t('dashboard.enrichment.configTitle', {
                          defaultValue: 'Configuration détaillée',
                        })}
                      </CardTitle>
                      <CardDescription>
                        {t('dashboard.enrichment.configDescription', {
                          defaultValue: 'Règle la connexion, l’authentification et le mapping pour la source active.',
                        })}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ApiEnrichmentConfig
                        key={activeSource.id}
                        config={activeSource.config}
                        onChange={(apiConfig) => updateSourceConfig(activeSource.id, apiConfig)}
                        onPresetSelect={(presetName) => applyPresetLabel(activeSource.id, presetName)}
                        category={apiCategory}
                      />
                    </CardContent>
                  </Card>
                ) : null}

                {workspacePane === 'preview' ? (
                  <Card className="border-border/70">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium">
                        {t('dashboard.actions.testApi', {
                          defaultValue: "Tester l'API",
                        })}
                      </CardTitle>
                      <CardDescription>
                        {t('dashboard.enrichment.inspectorDescription', {
                          defaultValue: 'Teste la source active et consulte ses derniers résultats sans quitter la configuration.',
                        })}
                      </CardDescription>
                      {activeSource.config.api_url ? (
                        <div className="truncate text-xs text-muted-foreground">
                          {activeSource.config.api_url}
                        </div>
                      ) : null}
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {activeSource.enabled ? (
                        <>
                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">
                              {t('enrichmentTab.preview.manualInput')}
                            </Label>
                            <div className="flex gap-2">
                              <Input
                                placeholder={
                                  isSpatialReference
                                    ? t('dashboard.enrichment.manualGeometryPlaceholder', {
                                        defaultValue: 'Latitude, longitude or WKT geometry',
                                      })
                                    : t('common:labels.name')
                                }
                                value={previewQuery}
                                onChange={(event) => setPreviewQuery(event.target.value)}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter') {
                                    void previewEnrichment(undefined, activeSource.id)
                                  }
                                }}
                              />
                              <Button
                                type="button"
                                onClick={() => previewEnrichment(undefined, activeSource.id)}
                                disabled={previewLoading || !String(previewQuery ?? '').trim()}
                              >
                                {previewLoading ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Eye className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                          </div>

                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">
                              {t('dashboard.enrichment.quickExamples', {
                                defaultValue: 'Essayer avec une entité existante',
                              })}
                            </Label>
                            <div className="flex gap-2">
                              <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                  placeholder={t('common:actions.search')}
                                  value={entitySearch}
                                  onChange={(event) => setEntitySearch(event.target.value)}
                                  className="pl-9"
                                  onKeyDown={(event) => {
                                    if (event.key === 'Enter') {
                                      void loadEntities(entitySearch)
                                    }
                                  }}
                                />
                              </div>
                              <Button type="button" variant="outline" onClick={() => loadEntities(entitySearch)}>
                                <Search className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>

                          <ScrollArea className="h-[220px] rounded-md border">
                            {entitiesLoading ? (
                              <div className="flex items-center justify-center py-8">
                                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                              </div>
                            ) : entities.length === 0 ? (
                              <div className="py-8 text-center text-muted-foreground">
                                <Database className="mx-auto mb-2 h-8 w-8 opacity-50" />
                                <p className="text-sm">{t('enrichmentTab.preview.loadEntities')}</p>
                              </div>
                            ) : (
                              <div className="p-1">
                                {entities.map((entity) => (
                                  <button
                                    key={entity.id}
                                    type="button"
                                    onClick={() => {
                                      const entityName = String(entity.name ?? '')
                                      setPreviewQuery(entityName)
                                      void previewEnrichment(entityName, activeSource.id, entity.id)
                                    }}
                                    className={`group flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-accent ${
                                      previewQuery === String(entity.name ?? '') ? 'bg-accent' : ''
                                    }`}
                                  >
                                    <span className="truncate flex-1">{entity.name}</span>
                                    <Eye className="h-4 w-4 opacity-0 group-hover:opacity-50" />
                                  </button>
                                ))}
                              </div>
                            )}
                          </ScrollArea>

                          <div className="rounded-lg border bg-muted/20 p-3">
                            {previewLoading ? (
                              <div className="flex min-h-[220px] items-center justify-center">
                                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                              </div>
                            ) : previewError ? (
                              <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{previewError}</AlertDescription>
                              </Alert>
                            ) : activePreviewResult?.success ? (
                              <div className="space-y-3">
                                <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/70 bg-background p-1">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant={previewResultMode === 'mapped' ? 'default' : 'ghost'}
                                    onClick={() => setPreviewResultMode('mapped')}
                                  >
                                    {t('dashboard.enrichment.mappedFields', {
                                      defaultValue: 'Champs mappés',
                                    })}
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant={previewResultMode === 'raw' ? 'default' : 'ghost'}
                                    onClick={() => setPreviewResultMode('raw')}
                                  >
                                    {t('dashboard.enrichment.rawApiResponse', {
                                      defaultValue: 'Réponse brute API',
                                    })}
                                  </Button>
                                </div>

                                {previewResultMode === 'mapped' ? (
                                  activePreviewResult.data && Object.keys(activePreviewResult.data).length > 0 ? (
                                    isStructuredSourceSummary(activePreviewResult.data)
                                      ? renderStructuredSummary(activePreviewResult.data, t)
                                      : renderMappedPreview(activePreviewResult.data)
                                  ) : (
                                    <div className="py-8 text-center text-sm text-muted-foreground">
                                      {t('dashboard.enrichment.noMappedFields', {
                                        defaultValue: 'Aucun champ mappé pour cette source.',
                                      })}
                                    </div>
                                  )
                                ) : activePreviewResult.raw_data !== undefined ? (
                                  renderRawPreview(activePreviewResult.raw_data)
                                ) : (
                                  <div className="py-8 text-center text-sm text-muted-foreground">
                                    {t('dashboard.enrichment.noRawApiResponse', {
                                      defaultValue: 'Aucune réponse brute disponible pour ce test.',
                                    })}
                                  </div>
                                )}
                              </div>
                            ) : activePreviewResult?.error ? (
                              <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{activePreviewResult.error}</AlertDescription>
                              </Alert>
                            ) : (
                              <div className="flex min-h-[220px] flex-col items-center justify-center text-center text-muted-foreground">
                                <Eye className="mb-3 h-10 w-10 opacity-30" />
                                <div className="text-sm font-medium">{t('enrichmentTab.preview.emptyTitle')}</div>
                                <div className="text-sm">{t('enrichmentTab.preview.emptyDescription')}</div>
                              </div>
                            )}
                          </div>
                        </>
                      ) : (
                        <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                          {t('dashboard.enrichment.quickTesterDisabled', {
                            defaultValue: 'Active cette source pour pouvoir la tester.',
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ) : null}

                {workspacePane === 'results' ? (
                  <Card className="border-border/70">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium">
                        {t('enrichmentTab.tabs.results')}
                      </CardTitle>
                      <CardDescription>
                        {t('dashboard.enrichment.resultsDescription', {
                          defaultValue: 'Consulte les enrichissements déjà produits pour la source active.',
                        })}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {resultsLoading ? (
                        <div className="flex items-center justify-center py-10">
                          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                      ) : activeSourceResults.length === 0 ? (
                        <Alert>
                          <AlertCircle className="h-4 w-4" />
                          <AlertTitle>{t('enrichmentTab.results.emptyTitle')}</AlertTitle>
                          <AlertDescription>{t('enrichmentTab.results.emptyDescription')}</AlertDescription>
                        </Alert>
                      ) : (
                        <>
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline">
                              {activeSourceResults.length.toLocaleString()} result(s)
                            </Badge>
                            <Badge variant="outline">
                              {t('enrichmentTab.stats.enriched')}: {(activeSourceStats?.enriched ?? 0).toLocaleString()}
                            </Badge>
                            <Badge variant="outline">
                              {t('enrichmentTab.stats.pending')}: {(activeSourceStats?.pending ?? 0).toLocaleString()}
                            </Badge>
                          </div>

                          <ScrollArea className="max-h-[620px]">
                            <div className="space-y-2">
                              {activeSourceResults.map((result) => (
                                <button
                                  key={`${activeSource.id}-${getResultEntityName(result)}-${result.processed_at}`}
                                  type="button"
                                  className="w-full rounded-lg border px-3 py-3 text-left transition-colors hover:bg-muted/30"
                                  onClick={() => setSelectedResult(result)}
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                      <div className="truncate text-sm font-medium">
                                        {getResultEntityName(result)}
                                      </div>
                                      <div className="mt-1 text-xs text-muted-foreground">
                                        {new Date(result.processed_at).toLocaleString()}
                                      </div>
                                    </div>
                                    <Badge variant={result.success ? 'secondary' : 'destructive'}>
                                      {result.success
                                        ? t('enrichmentTab.result.success')
                                        : t('enrichmentTab.result.failed')}
                                    </Badge>
                                  </div>
                                </button>
                              ))}
                            </div>
                          </ScrollArea>
                        </>
                      )}
                    </CardContent>
                  </Card>
                ) : null}
              </div>
            </>
          ) : null}
        </div>
      )}

      <Dialog open={selectedResult !== null} onOpenChange={(open) => !open && setSelectedResult(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>{selectedResult ? getResultEntityName(selectedResult) : ''}</DialogTitle>
            <DialogDescription>
              {selectedResult?.source_label
                ? `${selectedResult.source_label} · ${new Date(selectedResult.processed_at).toLocaleString()}`
                : ''}
            </DialogDescription>
          </DialogHeader>
          {selectedResult ? (
            selectedResult.success && selectedResult.data ? (
              <ScrollArea className="max-h-[60vh]">
                {isStructuredSourceSummary(selectedResult.data) ? (
                  renderStructuredSummary(selectedResult.data, t)
                ) : (
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t('enrichmentTab.table.field')}</TableHead>
                          <TableHead>{t('enrichmentTab.table.value')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(selectedResult.data).map(([field, value]) => (
                          <TableRow key={field} className="align-top">
                            <TableCell className="align-top font-medium">{field}</TableCell>
                            <TableCell className="align-top break-words">{renderValue(value)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </ScrollArea>
            ) : (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{selectedResult.error || t('enrichmentTab.result.failed')}</AlertDescription>
              </Alert>
            )
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
