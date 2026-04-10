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

import { useEffect, useState } from 'react'
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
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
    selectedResult,
    setSelectedResult,
    isRefreshing,
    isSpatialReference,
    apiCategory,
    workspacePane,
    setWorkspacePane,

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
  } = useEnrichmentState({
    referenceName,
    hasEnrichment,
    mode,
    initialSourceId,
    onConfigSaved,
  })

  const [isCompactWorkspace, setIsCompactWorkspace] = useState(() => {
    if (typeof window === 'undefined') {
      return false
    }
    return window.matchMedia('(max-width: 1099px)').matches
  })

  useEffect(() => {
    if (mode !== 'workspace' || typeof window === 'undefined') {
      return
    }

    const mediaQuery = window.matchMedia('(max-width: 1099px)')
    const updateLayout = (matches: boolean) => setIsCompactWorkspace(matches)
    updateLayout(mediaQuery.matches)

    const listener = (event: MediaQueryListEvent) => updateLayout(event.matches)
    mediaQuery.addEventListener('change', listener)
    return () => mediaQuery.removeEventListener('change', listener)
  }, [mode])

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

  const sourceListRegionLabel = t('dashboard.enrichment.sourcesRegion', {
    defaultValue: 'Source list',
  })
  const configRegionLabel = t('dashboard.enrichment.configRegion', {
    defaultValue: 'Configuration',
  })
  const inspectorRegionLabel = t('dashboard.enrichment.inspectorRegion', {
    defaultValue: 'Inspector',
  })

  /* ── Sidebar: compact source list ── */
  const sourceSidebarContent = (
    <div className="p-2" role="region" aria-label={sourceListRegionLabel}>
      <div className="mb-2 flex items-center justify-between gap-2 px-1">
        <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {t('enrichmentTab.config.sourcesTitle', {
            defaultValue: 'Sources',
          })}
        </h3>
        <Button type="button" variant="ghost" size="icon" className="h-6 w-6" onClick={addSource}>
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>
      <div className="space-y-px">
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
                resetPreviewState(source.id)
              }}
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors ${
                isSelected
                  ? 'border-l-2 border-l-primary bg-muted/40'
                  : 'border-l-2 border-l-transparent hover:bg-muted/20'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                  source.enabled ? 'bg-emerald-500' : 'bg-muted-foreground/30'
                }`}
              />
              <span className="min-w-0 flex-1 truncate text-xs">{source.label}</span>
              <span className="flex-shrink-0 text-[10px] tabular-nums text-muted-foreground">
                {sourceProgress.total > 0 ? `${Math.round(sourceProgress.percentage)}%` : ''}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )

  /* ── Workspace header: compact toolbar ── */
  const workspaceHeaderCard = activeSource ? (
    <div className="space-y-2">
      {/* Toolbar line */}
      <div className="flex items-center gap-2">
        <Input
          value={activeSource.label}
          onChange={(event) => updateSourceLabel(activeSource.id, event.target.value)}
          placeholder={t('enrichmentTab.config.sourceLabel', {
            defaultValue: 'Source name',
          })}
          className="h-7 max-w-[200px] border-transparent bg-transparent px-1 text-sm font-medium hover:border-border focus:border-border"
        />

        <Switch
          id={`source-enabled-${activeSource.id}`}
          checked={activeSource.enabled}
          onCheckedChange={(checked) => toggleSourceEnabled(activeSource.id, checked)}
          className="scale-75"
        />
        <span className="text-[11px] text-muted-foreground">
          {activeSource.enabled
            ? t('sources:configEditor.enabled')
            : t('sources:configEditor.disabled')}
        </span>

        <div className="flex-1" />

        {/* Job action buttons */}
        {canStartActiveSource ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => startSourceJob(activeSource.id)}
            disabled={jobLoadingScope !== null || isOffline}
            title={t('enrichmentTab.runtime.startSource', { defaultValue: 'Launch this API' })}
          >
            {jobLoadingScope === activeSource.id ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
          </Button>
        ) : null}

        {isRunningSingleSource && job?.status === 'running' ? (
          <>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => pauseJob(activeSource.id)} disabled={jobLoadingScope !== null}>
              {jobLoadingScope === activeSource.id ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Pause className="h-3.5 w-3.5" />
              )}
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => cancelJob(activeSource.id)} disabled={jobLoadingScope !== null}>
              <StopCircle className="h-3.5 w-3.5" />
            </Button>
          </>
        ) : null}

        {isRunningSingleSource && (job?.status === 'paused' || job?.status === 'paused_offline') ? (
          <>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => resumeJob(activeSource.id)} disabled={jobLoadingScope !== null || isOffline}>
              {jobLoadingScope === activeSource.id ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => cancelJob(activeSource.id)} disabled={jobLoadingScope !== null}>
              <StopCircle className="h-3.5 w-3.5" />
            </Button>
          </>
        ) : null}

        {/* Separator before structural actions */}
        <div className="h-4 w-px bg-border" />

        <Button type="button" variant="ghost" size="icon" className="h-7 w-7" disabled={activeSourceIndex === 0} onClick={() => moveSource(activeSource.id, 'up')}>
          <ChevronUp className="h-3.5 w-3.5" />
        </Button>
        <Button type="button" variant="ghost" size="icon" className="h-7 w-7" disabled={activeSourceIndex === sources.length - 1} onClick={() => moveSource(activeSource.id, 'down')}>
          <ChevronDown className="h-3.5 w-3.5" />
        </Button>
        <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => duplicateSource(activeSource.id)}>
          <Copy className="h-3.5 w-3.5" />
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:bg-destructive/10 hover:text-destructive">
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {t('dashboard.enrichment.deleteSourceTitle', {
                  defaultValue: 'Delete this source?',
                })}
              </AlertDialogTitle>
              <AlertDialogDescription>
                {t('dashboard.enrichment.deleteSourceDescription', {
                  defaultValue: 'The source will be removed from the local configuration until the next save.',
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

      {/* Progress bar — only when there are stats */}
      {(activeSourceProgress?.total ?? 0) > 0 ? (
        <div className="flex items-center gap-3">
          <Progress value={activeSourceProgress?.percentage ?? 0} className="h-1" />
          <span className="flex-shrink-0 text-[10px] tabular-nums text-muted-foreground">
            {activeSourceProgress?.processed.toLocaleString() ?? 0}/{activeSourceProgress?.total.toLocaleString() ?? 0}
          </span>
        </div>
      ) : null}
    </div>
  ) : (
    <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
      {t('enrichmentTab.config.selectSource', { defaultValue: 'Select a source on the left' })}
    </div>
  )

  /* ── Config details: render ApiEnrichmentConfig directly ── */
  const configDetailsCard = activeSource ? (
    <ApiEnrichmentConfig
      key={activeSource.id}
      config={activeSource.config}
      onChange={(apiConfig) => updateSourceConfig(activeSource.id, apiConfig)}
      onPresetSelect={(presetName) => applyPresetLabel(activeSource.id, presetName)}
      category={apiCategory}
    />
  ) : null

  /* ── Preview inspector: compact header ── */
  const previewInspectorCard = activeSource ? (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {t('dashboard.actions.testApi', { defaultValue: 'Test API' })}
        </h4>
        {activeSource.config.api_url ? (
          <span className="truncate text-[10px] text-muted-foreground">
            {activeSource.config.api_url}
          </span>
        ) : null}
      </div>

      {activeSource.enabled ? (
        <>
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
                  void previewEnrichment(undefined, activeSource.id)
                }
              }}
              className="h-8 text-sm"
            />
            <Button
              type="button"
              size="sm"
              className="h-8"
              onClick={() => previewEnrichment(undefined, activeSource.id)}
              disabled={previewLoading || !String(previewQuery ?? '').trim()}
            >
              {previewLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>

          <div className="space-y-1.5">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder={t('common:actions.search')}
                  value={entitySearch}
                  onChange={(event) => setEntitySearch(event.target.value)}
                  className="h-8 pl-8 text-sm"
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      void loadEntities(entitySearch)
                    }
                  }}
                />
              </div>
              <Button type="button" variant="outline" size="sm" className="h-8" onClick={() => loadEntities(entitySearch)}>
                <Search className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="max-h-[180px] overflow-auto rounded-md border">
            {entitiesLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : entities.length === 0 ? (
              <div className="py-4 text-center text-muted-foreground">
                <Database className="mx-auto mb-1 h-5 w-5 opacity-40" />
                <p className="text-xs">{t('enrichmentTab.preview.loadEntities')}</p>
              </div>
            ) : (
              <div className="p-0.5">
                {entities.slice(0, 15).map((entity) => (
                  <button
                    key={entity.id}
                    type="button"
                    onClick={() => {
                      const entityName = String(entity.name ?? '')
                      setPreviewQuery(entityName)
                      void previewEnrichment(entityName, activeSource.id, entity.id)
                    }}
                    className={`group flex w-full items-center justify-between rounded px-2 py-1 text-left text-xs hover:bg-accent ${
                      previewQuery === String(entity.name ?? '') ? 'bg-accent' : ''
                    }`}
                  >
                    <span className="truncate flex-1">{entity.name}</span>
                    <Eye className="h-3 w-3 opacity-0 group-hover:opacity-40" />
                  </button>
                ))}
                {entities.length > 15 ? (
                  <p className="px-2 py-1 text-[10px] text-muted-foreground">
                    {t('enrichmentTab.preview.moreEntities', {
                      defaultValue: '{{count}} more — use search to filter',
                      count: entities.length - 15,
                    })}
                  </p>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-md border bg-muted/10 p-2">
            {previewLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : previewError ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{previewError}</AlertDescription>
              </Alert>
            ) : activePreviewResult?.success ? (
              <div className="space-y-2">
                <div className="flex items-center gap-1 rounded border border-border/50 bg-background p-0.5">
                  <Button
                    type="button"
                    size="sm"
                    variant={previewResultMode === 'mapped' ? 'default' : 'ghost'}
                    className="h-6 text-xs"
                    onClick={() => setPreviewResultMode('mapped')}
                  >
                    {t('dashboard.enrichment.mappedFields', {
                      defaultValue: 'Mapped fields',
                    })}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={previewResultMode === 'raw' ? 'default' : 'ghost'}
                    className="h-6 text-xs"
                    onClick={() => setPreviewResultMode('raw')}
                  >
                    {t('dashboard.enrichment.rawApiResponse', {
                      defaultValue: 'Raw API response',
                    })}
                  </Button>
                </div>

                {previewResultMode === 'mapped' ? (
                  activePreviewResult.data && Object.keys(activePreviewResult.data).length > 0 ? (
                    isStructuredSourceSummary(activePreviewResult.data)
                      ? renderStructuredSummary(activePreviewResult.data, t)
                      : renderMappedPreview(activePreviewResult.data)
                  ) : (
                    <div className="py-6 text-center text-xs text-muted-foreground">
                      {t('dashboard.enrichment.noMappedFields', {
                        defaultValue: 'No mapped fields for this source.',
                      })}
                    </div>
                  )
                ) : activePreviewResult.raw_data !== undefined ? (
                  renderRawPreview(activePreviewResult.raw_data)
                ) : (
                  <div className="py-6 text-center text-xs text-muted-foreground">
                    {t('dashboard.enrichment.noRawApiResponse', {
                      defaultValue: 'No raw response available for this test.',
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
              <div className="py-8 text-center text-muted-foreground">
                <Eye className="mx-auto mb-2 h-8 w-8 opacity-20" />
                <div className="text-xs">{t('enrichmentTab.preview.emptyTitle')}</div>
                <div className="text-[11px] text-muted-foreground/70">{t('enrichmentTab.preview.emptyDescription')}</div>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
          {t('dashboard.enrichment.quickTesterDisabled', {
            defaultValue: 'Enable this source to test it.',
          })}
        </div>
      )}
    </div>
  ) : null

  /* ── Results inspector: compact ── */
  const resultsInspectorCard = activeSource ? (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {t('enrichmentTab.tabs.results')}
        </h4>
        {activeSourceStats ? (
          <span className="text-[10px] tabular-nums text-muted-foreground">
            {activeSourceStats.enriched.toLocaleString()}/{(activeSourceStats.enriched + activeSourceStats.pending).toLocaleString()}
          </span>
        ) : null}
      </div>

      {resultsLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : activeSourceResults.length === 0 ? (
        <div className="py-6 text-center">
          <p className="text-xs text-muted-foreground">{t('enrichmentTab.results.emptyDescription')}</p>
        </div>
      ) : (
        <div className="space-y-px">
          {activeSourceResults.map((result) => (
            <button
              key={`${activeSource.id}-${getResultEntityName(result)}-${result.processed_at}`}
              type="button"
              className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left transition-colors hover:bg-muted/20"
              onClick={() => setSelectedResult(result)}
            >
              <div className="min-w-0">
                <div className="truncate text-xs font-medium">
                  {getResultEntityName(result)}
                </div>
                <div className="text-[10px] text-muted-foreground">
                  {new Date(result.processed_at).toLocaleString()}
                </div>
              </div>
              <span
                className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                  result.success ? 'bg-emerald-500' : 'bg-destructive'
                }`}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  ) : null

  return (
    <div className="flex h-full flex-col gap-2 overflow-hidden">
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

      {/* ── Summary bar: compact single-line ── */}
      <div className="sticky top-0 z-20 flex items-center gap-3 border-b border-border/50 bg-background/95 px-3 py-1.5 backdrop-blur-sm">
        <span className="text-xs text-muted-foreground">
          {enabledSources.length}/{sources.length} {t('enrichmentTab.summary.enabledSources', { defaultValue: 'enabled', count: enabledSources.length })}
          {statsLoading ? (
            <> &middot; <Loader2 className="inline h-3 w-3 animate-spin" /></>
          ) : stats ? (
            <> &middot; {stats.enriched.toLocaleString()}/{stats.total.toLocaleString()} {t('enrichmentTab.stats.enriched')}</>
          ) : null}
        </span>

        {job ? (
          <span className="flex items-center gap-1.5 text-xs">
            <span className={`h-1.5 w-1.5 rounded-full ${job.status === 'running' ? 'animate-pulse bg-primary' : 'bg-muted-foreground/40'}`} />
            <span className="text-muted-foreground">
              {t(`enrichmentTab.status.${job.status}`, { defaultValue: job.status })}
              {job.total > 0 ? ` ${job.processed}/${job.total}` : ''}
            </span>
          </span>
        ) : null}

        <div className="flex-1" />

        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={saveEnrichmentConfig} disabled={configSaving || configLoading || !referenceConfig}>
            {configSaving ? (
              <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
            ) : null}
            {t('sources:configEditor.save')}
          </Button>

          {isTerminalJob ? (
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-2 text-xs"
              onClick={startGlobalJob}
              disabled={jobLoadingScope !== null || !stats || stats.pending === 0 || isOffline}
              title={isOffline ? t('enrichmentTab.offline.internetRequired') : undefined}
            >
              {jobLoadingScope === 'all' ? (
                <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
              ) : (
                <Play className="mr-1 h-3 w-3" />
              )}
              {t('enrichmentTab.runtime.startAll', { defaultValue: 'Start all' })}
            </Button>
          ) : job?.status === 'running' ? (
            <>
              <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={() => pauseJob()} disabled={jobLoadingScope !== null}>
                <Pause className="mr-1 h-3 w-3" />
                {t('enrichmentTab.actions.pause')}
              </Button>
              <Button size="sm" variant="ghost" className="h-6 px-2 text-xs text-destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                <StopCircle className="mr-1 h-3 w-3" />
                {t('common:actions.cancel')}
              </Button>
            </>
          ) : job?.status === 'paused' || job?.status === 'paused_offline' ? (
            <>
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-xs"
                onClick={() => resumeJob()}
                disabled={jobLoadingScope !== null || isOffline}
                title={isOffline ? t('enrichmentTab.offline.internetRequiredResume') : undefined}
              >
                <Play className="mr-1 h-3 w-3" />
                {t('enrichmentTab.actions.resume')}
              </Button>
              <Button size="sm" variant="ghost" className="h-6 px-2 text-xs text-destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                <StopCircle className="mr-1 h-3 w-3" />
                {t('common:actions.cancel')}
              </Button>
            </>
          ) : null}

          <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`h-3 w-3 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

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
      ) : isCompactWorkspace ? (
        <ResizablePanelGroup direction="horizontal" className="min-h-0 flex-1">
          <ResizablePanel id="enrichment-sources-compact" defaultSize="24%" minSize="18%" maxSize="34%">
            <ScrollArea className="h-full">
              {sourceSidebarContent}
            </ScrollArea>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel id="enrichment-main-compact" defaultSize="76%" minSize="66%">
            <ScrollArea className="h-full">
              <div className="space-y-3 p-3" role="region" aria-label={configRegionLabel}>
                {workspaceHeaderCard}
                {activeSource ? (
                  <Tabs
                    value={workspacePane}
                    onValueChange={(value) => setWorkspacePane(value as 'config' | 'preview' | 'results')}
                    className="space-y-3"
                  >
                    <TabsList className="h-auto flex-wrap justify-start gap-2 bg-transparent p-0">
                      <TabsTrigger value="config" className="gap-2">
                        {t('state.configurationTab', {
                          defaultValue: 'Configuration',
                        })}
                      </TabsTrigger>
                      <TabsTrigger value="preview" className="gap-2">
                        {t('dashboard.actions.testApi', {
                          defaultValue: 'Test API',
                        })}
                      </TabsTrigger>
                      <TabsTrigger value="results" className="gap-2">
                        {t('enrichmentTab.tabs.results')}
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="config" className="m-0 space-y-3">
                      {configDetailsCard}
                    </TabsContent>
                    <TabsContent value="preview" className="m-0 space-y-3">
                      {previewInspectorCard}
                    </TabsContent>
                    <TabsContent value="results" className="m-0 space-y-3">
                      {resultsInspectorCard}
                    </TabsContent>
                  </Tabs>
                ) : null}
              </div>
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>
      ) : (
        <ResizablePanelGroup direction="horizontal" className="min-h-0 flex-1">
          <ResizablePanel id="enrichment-sources" defaultSize="18%" minSize="14%" maxSize="25%">
            <ScrollArea className="h-full">
              {sourceSidebarContent}
            </ScrollArea>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel id="enrichment-config" defaultSize="45%" minSize="30%">
            <ScrollArea className="h-full">
              <div className="space-y-3 p-3" role="region" aria-label={configRegionLabel}>
                {workspaceHeaderCard}
                <div className="border-t border-border/30 pt-3">
                  {configDetailsCard}
                </div>
              </div>
            </ScrollArea>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel id="enrichment-results" defaultSize="37%" minSize="22%">
            <ScrollArea className="h-full">
              <div className="space-y-4 p-3" role="region" aria-label={inspectorRegionLabel}>
                {previewInspectorCard}
                <div className="border-t border-border/30 pt-4">
                  {resultsInspectorCard}
                </div>
              </div>
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>
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
