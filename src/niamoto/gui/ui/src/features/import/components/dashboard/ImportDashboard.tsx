/**
 * ImportDashboard - Durable post-import workspace for the Data module.
 *
 * The page is intentionally organized around the three real jobs users have
 * after import:
 * - verify imported data
 * - enrich references
 * - prepare static pages
 */

import { useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  AlertTriangle,
  ArrowRight,
  Download,
  FileBarChart2,
  GitBranch,
  Globe2,
  Layers3,
  Map as MapIcon,
  Network,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { useDatasets, type DatasetInfo } from '@/hooks/useDatasets'
import { useReferences, type ReferenceInfo } from '@/hooks/useReferences'
import type {
  DatasetConfig,
  ReferenceConfig,
} from '@/features/import/components/editors/EntityConfigEditor'
import { apiClient } from '@/shared/lib/api/client'
import { AnalysisToolSheet } from './AnalysisToolSheet'
import { DashboardConfigEditorSheet } from './DashboardConfigEditorSheet'
import { DataCompletenessView } from './DataCompletenessView'
import { EnrichmentWorkspaceSheet } from './EnrichmentWorkspaceSheet'
import { GeoCoverageView } from './GeoCoverageView'
import { SupportingSourceCard } from './SupportingSourceCard'
import { TaxonomicConsistencyView } from './TaxonomicConsistencyView'
import { ValueValidationView } from './ValueValidationView'

interface ImportSummary {
  total_entities: number
  total_rows: number
  entities: Array<{
    name: string
    entity_type: string
    row_count: number
    column_count: number
    columns: string[]
  }>
  alerts: Array<{
    level: string
    entity: string
    message: string
  }>
}

interface ImportDashboardProps {
  onExploreEntity?: (name: string) => void
  onExploreReference?: (name: string) => void
  onOpenGroups?: () => void
  onOpenGroup?: (name: string) => void
  onReimport?: () => void
}

type ToolKey = 'completeness' | 'validation' | 'taxonomy' | 'coverage'

type EditingState =
  | {
      entityType: 'dataset'
      name: string
      config: DatasetConfig | null
      detectedColumns: string[]
    }
  | {
      entityType: 'reference'
      name: string
      config: ReferenceConfig | null
      detectedColumns: string[]
    }
  | null

type GroupStatusKey =
  | 'needsReview'
  | 'enrichmentAvailable'
  | 'enrichmentConfigured'
  | 'readyForPages'

interface DashboardGroup extends ReferenceInfo {
  metrics?: {
    row_count: number
    column_count: number
  }
  columnNames: string[]
  issueCount: number
}

function getGroupIcon(kind?: ReferenceInfo['kind']) {
  switch (kind) {
    case 'hierarchical':
      return GitBranch
    case 'spatial':
      return Globe2
    default:
      return Network
  }
}

function getAggregationKindLabel(
  t: (key: string, defaultValue?: string) => string,
  kind: ReferenceInfo['kind']
) {
  switch (kind) {
    case 'hierarchical':
      return t('dashboard.kinds.taxonomic', 'Taxonomic')
    case 'spatial':
      return t('dashboard.kinds.spatial', 'Spatial')
    default:
      return t('dashboard.kinds.reference', 'Reference')
  }
}

function getGroupStatus(group: DashboardGroup): GroupStatusKey {
  if (group.issueCount > 0) return 'needsReview'
  if (group.can_enrich && !group.enrichment_enabled) return 'enrichmentAvailable'
  if (group.enrichment_enabled) return 'enrichmentConfigured'
  return 'readyForPages'
}

function statusBadgeVariant(status: GroupStatusKey) {
  switch (status) {
    case 'needsReview':
      return 'secondary' as const
    case 'enrichmentConfigured':
      return 'default' as const
    default:
      return 'outline' as const
  }
}

interface CompactGroupOverviewItemProps {
  group: DashboardGroup
  t: (key: string, defaultValue?: string, options?: Record<string, unknown>) => string
  onExploreReference?: (name: string) => void
  onOpenGroup?: (name: string) => void
  onOpenEnrichment?: (reference: ReferenceInfo) => void
}

function CompactGroupOverviewItem({
  group,
  t,
  onExploreReference,
  onOpenGroup,
  onOpenEnrichment,
}: CompactGroupOverviewItemProps) {
  const Icon = getGroupIcon(group.kind)
  const status = getGroupStatus(group)
  const statusLabel = t(
    `dashboard.groupStatus.${status}`,
    {
      needsReview: 'Needs review',
      enrichmentAvailable: 'Enrichment available',
      enrichmentConfigured: 'Enrichment configured',
      readyForPages: 'Ready for pages',
    }[status]
  )

  const primaryAction =
    status === 'needsReview'
      ? {
          label: t('dashboard.actions.review', 'Review'),
          onClick: () => onExploreReference?.(group.name),
          disabled: !onExploreReference,
        }
      : status === 'enrichmentAvailable' || status === 'enrichmentConfigured'
        ? {
            label:
              status === 'enrichmentConfigured'
                ? t('dashboard.actions.manageEnrichment', 'Manage enrichment')
                : t('dashboard.actions.configureEnrichment', 'Configure enrichment'),
            onClick: () => onOpenEnrichment?.(group),
            disabled: !onOpenEnrichment,
          }
        : {
            label: t('dashboard.actions.openGroup', 'Open group'),
            onClick: () => onOpenGroup?.(group.name),
            disabled: !onOpenGroup,
          }

  return (
    <Card className="border-border/70">
      <CardContent className="flex flex-col gap-4 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <Icon className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-semibold">{group.name}</h3>
                <Badge variant="outline">
                  {getAggregationKindLabel(t, group.kind)}
                </Badge>
                <Badge variant={statusBadgeVariant(status)}>{statusLabel}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">{group.table_name}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            <span>
              {t('dashboard.rows', '{{count}} rows', {
                count: group.metrics?.row_count ?? group.entity_count ?? 0,
              })}
            </span>
            <span className="text-muted-foreground/60">•</span>
            <span>
              {t('dashboard.fields', '{{count}} fields', {
                count: group.metrics?.column_count ?? group.schema_fields?.length ?? 0,
              })}
            </span>
            {group.issueCount > 0 && (
              <>
                <span className="text-muted-foreground/60">•</span>
                <span>
                  {t('dashboard.groupStatus.reviewCount', '{{count}} items to review', {
                    count: group.issueCount,
                  })}
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 lg:justify-end">
          <Button onClick={primaryAction.onClick} disabled={primaryAction.disabled}>
            {primaryAction.label}
          </Button>
          {status !== 'needsReview' && onExploreReference && (
            <Button variant="ghost" onClick={() => onExploreReference(group.name)}>
              <Search className="mr-2 h-4 w-4" />
              {t('dashboard.actions.details', 'Details')}
            </Button>
          )}
          {status !== 'readyForPages' && onOpenGroup && (
            <Button variant="ghost" onClick={() => onOpenGroup(group.name)}>
              {t('dashboard.actions.openGroup', 'Open group')}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function ImportDashboard({
  onExploreEntity,
  onExploreReference,
  onOpenGroups,
  onOpenGroup,
  onReimport,
}: ImportDashboardProps) {
  const { t } = useTranslation('sources')
  const tt = (key: string, defaultValue: string, options?: Record<string, unknown>) =>
    t(key, { defaultValue, ...(options ?? {}) })
  const queryClient = useQueryClient()
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<ImportSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTool, setActiveTool] = useState<ToolKey | null>(null)
  const [editingState, setEditingState] = useState<EditingState>(null)
  const [editorError, setEditorError] = useState<string | null>(null)
  const [savingConfig, setSavingConfig] = useState(false)
  const [activeEnrichmentReference, setActiveEnrichmentReference] =
    useState<ReferenceInfo | null>(null)
  const { data: referencesData } = useReferences()
  const { data: datasetsData } = useDatasets()

  const references = referencesData?.references ?? []
  const datasets = datasetsData?.datasets ?? []

  const fetchSummary = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get<ImportSummary>('/stats/summary')
      setSummary(response.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('dashboard.errors.loadSummary'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchSummary()
  }, [])

  const summaryEntities = summary?.entities ?? []

  const referenceMetrics = useMemo(
    () =>
      new Map(
        summaryEntities
          .filter((entity) => entity.entity_type === 'reference')
          .map((entity) => [entity.name, entity])
      ),
    [summaryEntities]
  )

  const datasetMetrics = useMemo(
    () =>
      new Map(
        summaryEntities
          .filter((entity) => entity.entity_type === 'dataset')
          .map((entity) => [entity.name, entity])
      ),
    [summaryEntities]
  )

  const layerEntities = useMemo(
    () => summaryEntities.filter((entity) => entity.entity_type === 'layer'),
    [summaryEntities]
  )

  const referenceColumnsMap = useMemo(
    () =>
      new Map(
        references.map((reference) => [
          reference.name,
          reference.schema_fields?.map((field) => field.name) ?? [],
        ])
      ),
    [references]
  )

  const datasetColumnsMap = useMemo(
    () =>
      new Map(
        datasets.map((dataset) => [
          dataset.name,
          dataset.schema_fields?.map((field) => field.name) ?? [],
        ])
      ),
    [datasets]
  )

  const aggregationGroups = useMemo<DashboardGroup[]>(
    () =>
      references.map((reference) => {
        const metrics =
          referenceMetrics.get(reference.table_name) || referenceMetrics.get(reference.name)
        const issueCount = (summary?.alerts ?? []).filter(
          (alert) => alert.entity === reference.name || alert.entity === reference.table_name
        ).length

        return {
          ...reference,
          metrics,
          issueCount,
          columnNames: reference.schema_fields?.map((field) => field.name) ?? [],
        }
      }),
    [referenceMetrics, references, summary?.alerts]
  )

  const supportingSources = [
    ...datasets.map((dataset) => ({
      type: 'dataset' as const,
      name: dataset.name,
      tableName: dataset.table_name,
      description: dataset.description,
      rowCount: datasetMetrics.get(dataset.table_name)?.row_count ?? dataset.entity_count ?? 0,
      columnCount:
        datasetMetrics.get(dataset.table_name)?.column_count ?? dataset.schema_fields?.length ?? 0,
      columns:
        datasetMetrics.get(dataset.table_name)?.columns ??
        dataset.schema_fields?.map((field) => field.name) ??
        [],
    })),
    ...layerEntities.map((layer) => ({
      type: 'layer' as const,
      name: layer.name,
      tableName: layer.name,
      description: undefined,
      rowCount: layer.row_count,
      columnCount: layer.column_count,
      columns: layer.columns,
    })),
  ]

  const toolCards = [
    {
      key: 'completeness' as const,
      icon: FileBarChart2,
      title: t('dashboard.tools.fieldAvailability.title'),
    },
    {
      key: 'validation' as const,
      icon: ShieldAlert,
      title: t('dashboard.tools.validation.title'),
    },
    {
      key: 'taxonomy' as const,
      icon: GitBranch,
      title: t('dashboard.tools.taxonomy.title'),
    },
    {
      key: 'coverage' as const,
      icon: MapIcon,
      title: t('dashboard.tools.coverage.title'),
    },
  ]

  const toolMeta = useMemo(() => {
    if (!activeTool || !summary) {
      return null
    }

    switch (activeTool) {
      case 'completeness':
        return {
          title: t('dashboard.tools.fieldAvailability.title'),
          description: t('dashboard.tools.fieldAvailability.description'),
          content: <DataCompletenessView entities={summary.entities} />,
        }
      case 'validation':
        return {
          title: t('dashboard.tools.validation.title'),
          description: t('dashboard.tools.validation.description'),
          content: <ValueValidationView entities={summary.entities} />,
        }
      case 'taxonomy':
        return {
          title: t('dashboard.tools.taxonomy.title'),
          description: t('dashboard.tools.taxonomy.description'),
          content: <TaxonomicConsistencyView />,
        }
      case 'coverage':
        return {
          title: t('dashboard.tools.coverage.title'),
          description: t('dashboard.tools.coverage.description'),
          content: <GeoCoverageView />,
        }
    }
  }, [activeTool, summary, t])

  const availableReferences = references.map((reference) => ({
    name: reference.name,
    columns: referenceColumnsMap.get(reference.name) ?? [],
  }))

  const availableDatasets = datasets.map((dataset) => dataset.name)

  const openDatasetEditor = async (dataset: DatasetInfo) => {
    setEditorError(null)
    setEditingState({
      entityType: 'dataset',
      name: dataset.name,
      config: null,
      detectedColumns: datasetColumnsMap.get(dataset.name) ?? [],
    })

    try {
      const response = await apiClient.get<DatasetConfig>(
        `/config/datasets/${encodeURIComponent(dataset.name)}/config`
      )
      const config = response.data
      setEditingState({
        entityType: 'dataset',
        name: dataset.name,
        config,
        detectedColumns: datasetColumnsMap.get(dataset.name) ?? [],
      })
    } catch (err) {
      setEditorError(err instanceof Error ? err.message : t('dashboard.errors.loadConfig'))
    }
  }

  const closeEditor = () => {
    setEditingState(null)
    setEditorError(null)
  }

  const persistDatasetConfig = async (name: string, config: DatasetConfig) => {
    setSavingConfig(true)
    setEditorError(null)
    try {
      await apiClient.put(`/config/datasets/${encodeURIComponent(name)}/config`, config)
      await queryClient.invalidateQueries({ queryKey: ['datasets'] })
      await fetchSummary()
      closeEditor()
    } catch (err) {
      setEditorError(err instanceof Error ? err.message : t('dashboard.errors.saveConfig'))
    } finally {
      setSavingConfig(false)
    }
  }

  const refreshReferencesAndSummary = async () => {
    await queryClient.invalidateQueries({ queryKey: ['references'] })
    await fetchSummary()
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>{t('dashboard.errors.loadTitle')}</AlertTitle>
        <AlertDescription>
          {error}
          <Button variant="link" onClick={fetchSummary} className="ml-2 h-auto p-0">
            {t('dashboard.actions.retry')}
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  if (!summary) {
    return null
  }

  const issueCount = summary.alerts.length
  const enrichableGroups = aggregationGroups.filter((group) => group.can_enrich)
  const configuredEnrichmentCount = enrichableGroups.filter(
    (group) => group.enrichment_enabled
  ).length
  const reviewGroups = aggregationGroups.filter(
    (group) => getGroupStatus(group) === 'needsReview'
  )
  const enrichmentGroups = aggregationGroups.filter(
    (group) => getGroupStatus(group) === 'enrichmentAvailable'
  )
  const readyForPagesGroups = aggregationGroups.filter(
    (group) => getGroupStatus(group) === 'readyForPages' || getGroupStatus(group) === 'enrichmentConfigured'
  )
  const defaultVerifyTool: ToolKey = issueCount > 0 ? 'validation' : 'completeness'

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t(
              'dashboard.missionControl.title',
              'Turn imported data into a working project'
            )}
          </h1>
          <p className="text-sm leading-6 text-muted-foreground">
            {t(
              'dashboard.missionControl.description',
              'Verify imported data, enrich references, and prepare the static pages you will configure next.'
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={fetchSummary}>
            <RefreshCw className="mr-1 h-3.5 w-3.5" />
            {t('dashboard.actions.refresh')}
          </Button>
          {onReimport && (
            <Button variant="outline" size="sm" onClick={onReimport}>
              <Download className="mr-1 h-3.5 w-3.5" />
              {t('dashboard.actions.reimport')}
            </Button>
          )}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <Card className="border-border/70">
          <CardHeader className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                  <ShieldAlert className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg">
                    {t('dashboard.missionControl.verify.title', 'Verify data')}
                  </CardTitle>
                  <CardDescription>
                    {t(
                      'dashboard.missionControl.verify.description',
                      'Check imported values, taxonomy consistency, and spatial coverage before building pages.'
                    )}
                  </CardDescription>
                </div>
              </div>
              <Badge variant={issueCount > 0 ? 'secondary' : 'outline'}>
                {issueCount > 0
                  ? tt(
                      'dashboard.missionControl.verify.issues',
                      '{{count}} items to review',
                      { count: issueCount }
                    )
                  : tt('dashboard.missionControl.verify.noIssues', 'No issue detected')}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {toolCards.map((tool) => {
                const Icon = tool.icon
                return (
                  <Button
                    key={tool.key}
                    variant="outline"
                    size="sm"
                    onClick={() => setActiveTool(tool.key)}
                  >
                    <Icon className="mr-2 h-4 w-4" />
                    {tool.title}
                  </Button>
                )
              })}
            </div>

            <Button onClick={() => setActiveTool(defaultVerifyTool)}>
              {t('dashboard.missionControl.verify.openChecks', 'Open checks')}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg">
                    {t('dashboard.missionControl.enrich.title', 'Enrich references')}
                  </CardTitle>
                  <CardDescription>
                    {t(
                      'dashboard.missionControl.enrich.description',
                      'Configure and run external enrichment directly from the data workspace.'
                    )}
                  </CardDescription>
                </div>
              </div>
              <Badge variant="outline">
                {tt(
                  'dashboard.missionControl.enrich.summary',
                  '{{configured}} configured · {{total}} available',
                  {
                    configured: configuredEnrichmentCount,
                    total: enrichableGroups.length,
                  }
                )}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {enrichableGroups.length > 0 ? (
              <div className="space-y-3">
                {enrichableGroups.slice(0, 3).map((group) => {
                  const status = group.enrichment_enabled
                    ? t('dashboard.groupStatus.enrichmentConfigured', 'Enrichment configured')
                    : t('dashboard.groupStatus.enrichmentAvailable', 'Enrichment available')

                  return (
                    <div
                      key={group.name}
                      className="flex flex-col gap-3 rounded-lg border bg-muted/20 p-3 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="space-y-1">
                        <div className="font-medium">{group.name}</div>
                        <div className="text-sm text-muted-foreground">{status}</div>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => setActiveEnrichmentReference(group)}
                      >
                        {group.enrichment_enabled
                          ? t('dashboard.actions.manageEnrichment', 'Manage enrichment')
                          : t('dashboard.actions.configureEnrichment', 'Configure enrichment')}
                      </Button>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {t(
                  'dashboard.missionControl.enrich.empty',
                  'No enrichment-capable references are available in this workspace.'
                )}
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                  <Layers3 className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg">
                    {t(
                      'dashboard.missionControl.prepare.title',
                      'Prepare static pages'
                    )}
                  </CardTitle>
                  <CardDescription>
                    {t(
                      'dashboard.missionControl.prepare.description',
                      'Move into Groups to choose widgets, sources, and index pages for each group.'
                    )}
                  </CardDescription>
                </div>
              </div>
              <Badge variant="outline">
                {tt(
                  'dashboard.missionControl.prepare.summary',
                  '{{count}} groups available',
                  {
                    count: aggregationGroups.length,
                  }
                )}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {aggregationGroups.slice(0, 3).map((group) => {
                const status = getGroupStatus(group)
                return (
                  <button
                    key={group.name}
                    type="button"
                    onClick={() => onOpenGroup?.(group.name)}
                    className="flex w-full items-center justify-between gap-3 rounded-lg border bg-muted/20 p-3 text-left transition-colors hover:border-primary/40 hover:bg-primary/5 disabled:cursor-default disabled:hover:border-border disabled:hover:bg-muted/20"
                    disabled={!onOpenGroup}
                  >
                    <div className="space-y-1">
                      <div className="font-medium">{group.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {t(
                          `dashboard.groupStatus.${status}`,
                          {
                            needsReview: 'Needs review',
                            enrichmentAvailable: 'Enrichment available',
                            enrichmentConfigured: 'Enrichment configured',
                            readyForPages: 'Ready for pages',
                          }[status]
                        )}
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </button>
                )
              })}
            </div>

            {onOpenGroups && (
              <Button onClick={onOpenGroups}>
                {t('dashboard.actions.openGroups', 'Open Groups')}
              </Button>
            )}
          </CardContent>
        </Card>
      </section>

      {summary.alerts.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-semibold">{t('dashboard.needsAttention')}</h2>
          </div>
          <div className="grid gap-3">
            {summary.alerts.slice(0, 3).map((alert, idx) => (
              <Alert
                key={`${alert.entity}-${idx}`}
                variant={alert.level === 'error' ? 'destructive' : 'default'}
                className={alert.level === 'warning' ? 'border-amber-200 bg-amber-50/70' : undefined}
              >
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
                  <span>{alert.message}</span>
                  {onExploreEntity && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => onExploreEntity(alert.entity)}
                    >
                      {t('dashboard.actions.open')}
                    </Button>
                  )}
                </AlertDescription>
              </Alert>
            ))}
          </div>
        </section>
      )}

      <section className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">
            {t('dashboard.groupOverview.title', 'Groups overview')}
          </h2>
          <p className="text-sm text-muted-foreground">
            {t(
              'dashboard.groupOverview.description',
              'Keep the imported groups visible, but focus each one on its current status and the next useful action.'
            )}
          </p>
        </div>

        {(reviewGroups.length > 0 || enrichmentGroups.length > 0 || readyForPagesGroups.length > 0) && (
          <div className="flex flex-wrap gap-2">
            {reviewGroups.length > 0 && (
              <Badge variant="secondary">
                {tt('dashboard.groupOverview.reviewSummary', '{{count}} need review', {
                  count: reviewGroups.length,
                })}
              </Badge>
            )}
            {enrichmentGroups.length > 0 && (
              <Badge variant="outline">
                {tt(
                  'dashboard.groupOverview.enrichmentSummary',
                  '{{count}} have enrichment available',
                  {
                    count: enrichmentGroups.length,
                  }
                )}
              </Badge>
            )}
            {readyForPagesGroups.length > 0 && (
              <Badge variant="outline">
                {tt(
                  'dashboard.groupOverview.readySummary',
                  '{{count}} ready for pages',
                  {
                    count: readyForPagesGroups.length,
                  }
                )}
              </Badge>
            )}
          </div>
        )}

        <div className="space-y-3">
          {aggregationGroups.map((group) => (
            <CompactGroupOverviewItem
              key={group.name}
              group={group}
              t={(key, defaultValue, options) =>
                t(key, { defaultValue, ...(options ?? {}) })
              }
              onExploreReference={onExploreReference}
              onOpenGroup={onOpenGroup}
              onOpenEnrichment={(reference) => setActiveEnrichmentReference(reference)}
            />
          ))}
        </div>
      </section>

      {supportingSources.length > 0 && (
        <section className="space-y-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold">
              {t('dashboard.supportingSourcesTitle')}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t(
                'dashboard.missionControl.supportingSourcesDescription',
                'Raw datasets and imported layers remain available for direct inspection, updates, and configuration changes.'
              )}
            </p>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {supportingSources.map((entity) => (
              <SupportingSourceCard
                key={`${entity.type}:${entity.name}`}
                entity={entity}
                datasetLabel={t('dashboard.kinds.dataset')}
                layerLabel={t('dashboard.kinds.layer')}
                rowsLabel={t('dashboard.rows', { count: entity.rowCount })}
                fieldsLabel={t('dashboard.fields', { count: entity.columnCount })}
                fallbackDescription={
                  entity.type === 'dataset'
                    ? t('dashboard.datasetFallbackDescription')
                    : t('dashboard.layerFallbackDescription')
                }
                editConfigAction={
                  entity.type === 'dataset' ? t('dashboard.actions.editConfig') : undefined
                }
                exploreAction={
                  entity.type === 'dataset' ? t('dashboard.actions.explore') : undefined
                }
                updateAction={
                  entity.type === 'dataset'
                    ? t('dashboard.actions.updateFile')
                    : t('dashboard.actions.updateLayer')
                }
                onEdit={
                  entity.type === 'dataset'
                    ? () => {
                        const dataset = datasets.find((item) => item.name === entity.name)
                        if (dataset) {
                          void openDatasetEditor(dataset)
                        }
                      }
                    : undefined
                }
                onExplore={
                  entity.type === 'dataset' && onExploreEntity
                    ? () => onExploreEntity(entity.name)
                    : undefined
                }
                onUpdate={onReimport}
              />
            ))}
          </div>
        </section>
      )}

      <AnalysisToolSheet
        open={activeTool !== null}
        title={toolMeta?.title}
        description={toolMeta?.description}
        content={toolMeta?.content}
        tools={toolCards.map((tool) => ({
          key: tool.key,
          title: tool.title,
        }))}
        activeTool={activeTool}
        onSelectTool={(toolKey) => setActiveTool(toolKey as ToolKey)}
        onOpenChange={(open) => !open && setActiveTool(null)}
      />

      <EnrichmentWorkspaceSheet
        open={activeEnrichmentReference !== null}
        reference={activeEnrichmentReference}
        onOpenChange={(open) => !open && setActiveEnrichmentReference(null)}
        onConfigSaved={() => {
          void refreshReferencesAndSummary()
        }}
      />

      <DashboardConfigEditorSheet
        editingState={editingState}
        editorError={editorError}
        savingConfig={savingConfig}
        title={
          editingState?.entityType === 'dataset'
            ? t('autoConfig.sheetTitles.dataset', { name: editingState.name })
            : editingState?.entityType === 'reference'
              ? t('autoConfig.sheetTitles.reference', { name: editingState.name })
              : ''
        }
        description={
          editingState?.entityType === 'dataset'
            ? t('autoConfig.sheetDescriptions.dataset')
            : editingState?.entityType === 'reference'
              ? t('autoConfig.sheetDescriptions.reference')
              : ''
        }
        availableReferences={availableReferences}
        availableDatasets={availableDatasets}
        loadingLabel={t('dashboard.editor.loadingConfig')}
        savingLabel={t('dashboard.editor.savingConfig')}
        onClose={closeEditor}
        onDatasetSave={(name, updated) => persistDatasetConfig(name, updated)}
        onReferenceSave={async (_name, _updated) => undefined}
      />
    </div>
  )
}
