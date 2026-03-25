/**
 * ImportDashboard - Post-import workspace focused on aggregation groups.
 *
 * The page intentionally mirrors the pre-import review:
 * - aggregation groups first
 * - supporting sources second
 * - analysis tools visible but secondary
 * - config editing kept in side sheets
 */

import { useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Download,
  FileBarChart2,
  GitBranch,
  Globe2,
  Layers,
  Loader2,
  Map as MapIcon,
  Network,
  Pencil,
  PlusCircle,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { useDatasets, type DatasetInfo } from '@/hooks/useDatasets'
import { useReferences, type ReferenceInfo } from '@/hooks/useReferences'
import { EntityConfigEditor } from '@/components/sources/EntityConfigEditor'
import type { DatasetConfig, ReferenceConfig } from '@/components/sources/EntityConfigEditor'
import { DataCompletenessView } from './DataCompletenessView'
import { GeoCoverageView } from './GeoCoverageView'
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
  onOpenGroup?: (name: string) => void
  onEnrich?: (refName: string, targetTab?: 'config' | 'enrichment') => void
  onReimport?: () => void
}

type ToolKey = 'completeness' | 'validation' | 'taxonomy' | 'coverage'
type TranslateFn = (key: string, options?: Record<string, unknown>) => string

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

function getAggregationKindLabel(
  t: TranslateFn,
  kind: ReferenceInfo['kind']
) {
  switch (kind) {
    case 'hierarchical':
      return t('dashboard.kinds.taxonomic')
    case 'spatial':
      return t('dashboard.kinds.spatial')
    default:
      return t('dashboard.kinds.reference')
  }
}

function getAggregationDescription(
  t: TranslateFn,
  kind: ReferenceInfo['kind']
) {
  switch (kind) {
    case 'hierarchical':
      return t('dashboard.aggregationDescriptions.hierarchical')
    case 'spatial':
      return t('dashboard.aggregationDescriptions.spatial')
    default:
      return t('dashboard.aggregationDescriptions.generic')
  }
}

export function ImportDashboard({
  onExploreEntity,
  onExploreReference,
  onOpenGroup,
  onEnrich,
  onReimport,
}: ImportDashboardProps) {
  const { t } = useTranslation('sources')
  const queryClient = useQueryClient()
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<ImportSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTool, setActiveTool] = useState<ToolKey | null>(null)
  const [editingState, setEditingState] = useState<EditingState>(null)
  const [editorError, setEditorError] = useState<string | null>(null)
  const [savingConfig, setSavingConfig] = useState(false)
  const { data: referencesData } = useReferences()
  const { data: datasetsData } = useDatasets()

  const references = referencesData?.references ?? []
  const datasets = datasetsData?.datasets ?? []

  const fetchSummary = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/stats/summary')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      setSummary(data)
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

  const aggregationGroups = references.map((reference) => {
    const metrics =
      referenceMetrics.get(reference.table_name) || referenceMetrics.get(reference.name)

    return {
      ...reference,
      metrics,
      columnNames: reference.schema_fields?.map((field) => field.name) ?? [],
      canAddSource: reference.kind === 'spatial',
    }
  })

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
      description: t('dashboard.tools.fieldAvailability.description'),
    },
    {
      key: 'validation' as const,
      icon: ShieldAlert,
      title: t('dashboard.tools.validation.title'),
      description: t('dashboard.tools.validation.description'),
    },
    {
      key: 'taxonomy' as const,
      icon: GitBranch,
      title: t('dashboard.tools.taxonomy.title'),
      description: t('dashboard.tools.taxonomy.description'),
    },
    {
      key: 'coverage' as const,
      icon: MapIcon,
      title: t('dashboard.tools.coverage.title'),
      description: t('dashboard.tools.coverage.description'),
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
      const response = await fetch(
        `/api/config/datasets/${encodeURIComponent(dataset.name)}/config`
      )
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const config = (await response.json()) as DatasetConfig
      setEditingState({
        entityType: 'dataset',
        name: dataset.name,
        config,
        detectedColumns: datasetColumnsMap.get(dataset.name) ?? [],
      })
    } catch (err) {
      setEditorError(
        err instanceof Error ? err.message : t('dashboard.errors.loadConfig')
      )
    }
  }

  const openReferenceEditor = async (reference: ReferenceInfo) => {
    setEditorError(null)
    setEditingState({
      entityType: 'reference',
      name: reference.name,
      config: null,
      detectedColumns: referenceColumnsMap.get(reference.name) ?? [],
    })

    try {
      const response = await fetch(
        `/api/config/references/${encodeURIComponent(reference.name)}/config`
      )
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const config = (await response.json()) as ReferenceConfig
      const detectedColumns =
        config.connector?.type === 'derived' && config.connector?.source
          ? datasetColumnsMap.get(config.connector.source) ?? []
          : referenceColumnsMap.get(reference.name) ?? []

      setEditingState({
        entityType: 'reference',
        name: reference.name,
        config,
        detectedColumns,
      })
    } catch (err) {
      setEditorError(
        err instanceof Error ? err.message : t('dashboard.errors.loadConfig')
      )
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
      const response = await fetch(
        `/api/config/datasets/${encodeURIComponent(name)}/config`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config),
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      await queryClient.invalidateQueries({ queryKey: ['datasets'] })
      await fetchSummary()
      closeEditor()
    } catch (err) {
      setEditorError(
        err instanceof Error ? err.message : t('dashboard.errors.saveConfig')
      )
    } finally {
      setSavingConfig(false)
    }
  }

  const persistReferenceConfig = async (name: string, config: ReferenceConfig) => {
    setSavingConfig(true)
    setEditorError(null)
    try {
      const response = await fetch(
        `/api/config/references/${encodeURIComponent(name)}/config`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config),
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      await queryClient.invalidateQueries({ queryKey: ['references'] })
      await fetchSummary()
      closeEditor()
    } catch (err) {
      setEditorError(
        err instanceof Error ? err.message : t('dashboard.errors.saveConfig')
      )
    } finally {
      setSavingConfig(false)
    }
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

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <Badge variant="outline" className="rounded-full">
            {t('dashboard.importedWorkspace')}
          </Badge>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t('dashboard.workspaceTitle')}
          </h1>
          <p className="text-sm leading-6 text-muted-foreground">
            {t('dashboard.workspaceDescription')}
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

      <section className="rounded-xl border bg-muted/20 p-4">
        <div className="mb-4 flex flex-col gap-1">
          <h2 className="text-sm font-semibold">{t('dashboard.toolsBandTitle')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('dashboard.toolsBandDescription')}
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {toolCards.map((tool) => {
            const Icon = tool.icon
            return (
              <button
                key={tool.key}
                type="button"
                onClick={() => setActiveTool(tool.key)}
                className="rounded-xl border bg-background px-4 py-3 text-left transition-colors hover:border-primary/40 hover:bg-primary/5"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="space-y-0.5">
                    <div className="text-sm font-medium">{tool.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {tool.description}
                    </div>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
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
          <h2 className="text-lg font-semibold">{t('dashboard.aggregationGroupsTitle')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('dashboard.aggregationGroupsDescription')}
          </p>
        </div>

        <div className="space-y-4">
          {aggregationGroups.map((group) => {
            const Icon =
              group.kind === 'spatial'
                ? Globe2
                : group.kind === 'hierarchical'
                  ? GitBranch
                  : Network
            const rowCount = group.metrics?.row_count ?? group.entity_count ?? 0
            const fieldCount = group.metrics?.column_count ?? group.schema_fields?.length ?? 0
            const canEnrich = Boolean(group.can_enrich)

            return (
              <Card key={group.name} className="overflow-hidden border-border/70">
                <CardContent className="p-0">
                  <div className="space-y-5 p-6">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-3">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                            <Icon className="h-4 w-4 text-primary" />
                          </div>
                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="text-lg font-semibold">{group.name}</h3>
                              <Badge variant="outline">{t('dashboard.importedState')}</Badge>
                              <Badge variant="secondary">
                                {getAggregationKindLabel(t, group.kind)}
                              </Badge>
                              {group.enrichment_enabled && (
                                <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">
                                  {t('dashboard.badges.enrichmentEnabled')}
                                </Badge>
                              )}
                              {!group.enrichment_enabled && canEnrich && (
                                <Badge variant="outline">
                                  {t('dashboard.badges.enrichmentAvailable')}
                                </Badge>
                              )}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {group.table_name}
                            </div>
                          </div>
                        </div>

                        <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                          {group.description || getAggregationDescription(t, group.kind)}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2 lg:justify-end">
                        {onExploreReference && (
                          <Button onClick={() => onExploreReference(group.name)}>
                            <Search className="mr-2 h-4 w-4" />
                            {t('dashboard.actions.explore')}
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          onClick={() => void openReferenceEditor(group)}
                        >
                          <Pencil className="mr-2 h-4 w-4" />
                          {t('dashboard.actions.editConfig')}
                        </Button>
                        {group.canAddSource && onReimport && (
                          <Button variant="outline" onClick={onReimport}>
                            <PlusCircle className="mr-2 h-4 w-4" />
                            {t('dashboard.actions.addSource')}
                          </Button>
                        )}
                        {onOpenGroup && (
                          <Button variant="ghost" onClick={() => onOpenGroup(group.name)}>
                            {t('dashboard.actions.openGroup')}
                          </Button>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                      <span>{t('dashboard.rows', { count: rowCount })}</span>
                      <span className="text-muted-foreground/60">•</span>
                      <span>{t('dashboard.fields', { count: fieldCount })}</span>
                      <span className="text-muted-foreground/60">•</span>
                      <span>
                        {group.kind === 'spatial'
                          ? t('dashboard.card.spatialReference')
                          : group.kind === 'hierarchical'
                            ? t('dashboard.card.taxonomicReference')
                            : t('dashboard.card.genericReference')}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">
                        {t('dashboard.card.fieldPreview')}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {group.columnNames.slice(0, 6).map((column) => (
                          <Badge key={column} variant="outline" className="font-normal">
                            {column}
                          </Badge>
                        ))}
                        {group.columnNames.length > 6 && (
                          <Badge variant="outline" className="font-normal text-muted-foreground">
                            +{group.columnNames.length - 6}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="border-t bg-muted/25 p-6">
                    {canEnrich ? (
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm font-medium text-primary">
                            <Sparkles className="h-4 w-4" />
                            {t('dashboard.nextStep.label')}
                          </div>
                          <div className="text-base font-semibold">
                            {group.enrichment_enabled
                              ? t('dashboard.nextStep.enrichmentConfiguredTitle')
                              : t('dashboard.nextStep.enrichmentTitle')}
                          </div>
                          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                            {group.enrichment_enabled
                              ? t('dashboard.nextStep.enrichmentConfiguredDescription')
                              : t('dashboard.nextStep.enrichmentDescription')}
                          </p>
                        </div>
                        {onEnrich && (
                          <Button
                            size="lg"
                            onClick={() =>
                              onEnrich(
                                group.name,
                                group.enrichment_enabled ? 'enrichment' : 'config'
                              )
                            }
                          >
                            <Sparkles className="mr-2 h-4 w-4" />
                            {group.enrichment_enabled
                              ? t('dashboard.actions.manageEnrichment')
                              : t('dashboard.actions.enrichNow')}
                          </Button>
                        )}
                      </div>
                    ) : (
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                            {t('dashboard.nextStep.readyLabel')}
                          </div>
                          <div className="text-base font-semibold">
                            {t('dashboard.nextStep.exploreTitle')}
                          </div>
                          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                            {t('dashboard.nextStep.exploreDescription')}
                          </p>
                        </div>
                        {onExploreReference && (
                          <Button size="lg" onClick={() => onExploreReference(group.name)}>
                            <Search className="mr-2 h-4 w-4" />
                            {t('dashboard.actions.explore')}
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      <section className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">{t('dashboard.supportingSourcesTitle')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('dashboard.supportingSourcesDescription')}
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          {supportingSources.map((entity) => (
            <Card key={`${entity.type}:${entity.name}`} className="border-border/70">
              <CardContent className="space-y-4 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {entity.type === 'dataset' ? (
                        <Database className="h-4 w-4 text-blue-500" />
                      ) : (
                        <Layers className="h-4 w-4 text-orange-500" />
                      )}
                      <div className="font-medium">{entity.name}</div>
                      <Badge variant="outline">
                        {entity.type === 'dataset'
                          ? t('dashboard.kinds.dataset')
                          : t('dashboard.kinds.layer')}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">{entity.tableName}</div>
                  </div>
                  {entity.type === 'dataset' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const dataset = datasets.find((item) => item.name === entity.name)
                        if (dataset) {
                          void openDatasetEditor(dataset)
                        }
                      }}
                    >
                      <Pencil className="mr-2 h-4 w-4" />
                      {t('dashboard.actions.editConfig')}
                    </Button>
                  )}
                </div>

                <p className="text-sm text-muted-foreground">
                  {entity.description ||
                    (entity.type === 'dataset'
                      ? t('dashboard.datasetFallbackDescription')
                      : t('dashboard.layerFallbackDescription'))}
                </p>

                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary">{t('dashboard.rows', { count: entity.rowCount })}</Badge>
                  <Badge variant="secondary">
                    {t('dashboard.fields', { count: entity.columnCount })}
                  </Badge>
                  {entity.columns.slice(0, 4).map((column) => (
                    <Badge key={column} variant="outline" className="font-normal">
                      {column}
                    </Badge>
                  ))}
                  {entity.columns.length > 4 && (
                    <Badge variant="outline" className="font-normal text-muted-foreground">
                      +{entity.columns.length - 4}
                    </Badge>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {entity.type === 'dataset' && onExploreEntity && (
                    <Button variant="outline" onClick={() => onExploreEntity(entity.name)}>
                      <Search className="mr-2 h-4 w-4" />
                      {t('dashboard.actions.explore')}
                    </Button>
                  )}
                  {onReimport && (
                    <Button variant="ghost" onClick={onReimport}>
                      {entity.type === 'dataset'
                        ? t('dashboard.actions.updateFile')
                        : t('dashboard.actions.updateLayer')}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <Sheet open={activeTool !== null} onOpenChange={(open) => !open && setActiveTool(null)}>
        <SheetContent className="w-[min(960px,92vw)] sm:max-w-[960px]">
          <SheetHeader className="px-6 pt-6">
            <SheetTitle>{toolMeta?.title}</SheetTitle>
            <SheetDescription>{toolMeta?.description}</SheetDescription>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-110px)] px-6 pb-6">
            <div className="pt-6">{toolMeta?.content}</div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      <Sheet open={editingState !== null} onOpenChange={(open) => !open && closeEditor()}>
        <SheetContent className="w-[min(760px,92vw)] sm:max-w-[760px]">
          <SheetHeader className="px-6 pt-6">
            <SheetTitle>
              {editingState?.entityType === 'dataset'
                ? t('autoConfig.sheetTitles.dataset', { name: editingState.name })
                : editingState?.entityType === 'reference'
                  ? t('autoConfig.sheetTitles.reference', { name: editingState.name })
                  : ''}
            </SheetTitle>
            <SheetDescription>
              {editingState?.entityType === 'dataset'
                ? t('autoConfig.sheetDescriptions.dataset')
                : editingState?.entityType === 'reference'
                  ? t('autoConfig.sheetDescriptions.reference')
                  : ''}
            </SheetDescription>
          </SheetHeader>

          <ScrollArea className="h-[calc(100vh-110px)] px-6 pb-6">
            <div className="pt-6">
              {editorError && (
                <Alert variant="destructive" className="mb-4">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{editorError}</AlertDescription>
                </Alert>
              )}

              {savingConfig || !editingState?.config ? (
                <div className="flex min-h-[240px] items-center justify-center">
                  <div className="flex items-center gap-3 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {savingConfig
                      ? t('dashboard.editor.savingConfig')
                      : t('dashboard.editor.loadingConfig')}
                  </div>
                </div>
              ) : editingState.entityType === 'dataset' ? (
                <EntityConfigEditor
                  entityName={editingState.name}
                  entityType="dataset"
                  config={editingState.config}
                  detectedColumns={editingState.detectedColumns}
                  availableReferences={availableReferences}
                  onSave={(updated) =>
                    void persistDatasetConfig(editingState.name, updated as DatasetConfig)
                  }
                  onCancel={closeEditor}
                />
              ) : (
                <EntityConfigEditor
                  entityName={editingState.name}
                  entityType="reference"
                  config={editingState.config}
                  detectedColumns={editingState.detectedColumns}
                  availableDatasets={availableDatasets}
                  onSave={(updated) =>
                    void persistReferenceConfig(
                      editingState.name,
                      updated as ReferenceConfig
                    )
                  }
                  onCancel={closeEditor}
                />
              )}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </div>
  )
}
