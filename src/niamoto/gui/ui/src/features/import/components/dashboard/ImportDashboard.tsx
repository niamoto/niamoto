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
import {
  AlertTriangle,
  Download,
  FileBarChart2,
  GitBranch,
  Map as MapIcon,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react'
import { useDatasets, type DatasetInfo } from '@/hooks/useDatasets'
import { useReferences, type ReferenceInfo } from '@/hooks/useReferences'
import type {
  DatasetConfig,
  ReferenceConfig,
} from '@/features/import/components/editors/EntityConfigEditor'
import { apiClient } from '@/shared/lib/api/client'
import { AggregationGroupCard } from './AggregationGroupCard'
import { AnalysisToolSheet } from './AnalysisToolSheet'
import { DataCompletenessView } from './DataCompletenessView'
import { DashboardConfigEditorSheet } from './DashboardConfigEditorSheet'
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
      const response = await apiClient.get<ReferenceConfig>(
        `/config/references/${encodeURIComponent(reference.name)}/config`
      )
      const config = response.data
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
      await apiClient.put(
        `/config/datasets/${encodeURIComponent(name)}/config`,
        config
      )

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
      await apiClient.put(
        `/config/references/${encodeURIComponent(name)}/config`,
        config
      )

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
            return (
              <AggregationGroupCard
                key={group.name}
                group={group}
                kindLabel={getAggregationKindLabel(t, group.kind)}
                description={group.description || getAggregationDescription(t, group.kind)}
                rowsLabel={t('dashboard.rows', { count: group.metrics?.row_count ?? group.entity_count ?? 0 })}
                fieldsLabel={t('dashboard.fields', { count: group.metrics?.column_count ?? group.schema_fields?.length ?? 0 })}
                roleLabel={
                  group.kind === 'spatial'
                    ? t('dashboard.card.spatialReference')
                    : group.kind === 'hierarchical'
                      ? t('dashboard.card.taxonomicReference')
                      : t('dashboard.card.genericReference')
                }
                fieldPreviewLabel={t('dashboard.card.fieldPreview')}
                importedLabel={t('dashboard.importedState')}
                enrichmentEnabledLabel={t('dashboard.badges.enrichmentEnabled')}
                enrichmentAvailableLabel={t('dashboard.badges.enrichmentAvailable')}
                nextStepLabel={t('dashboard.nextStep.label')}
                enrichmentTitle={t('dashboard.nextStep.enrichmentTitle')}
                enrichmentDescription={t('dashboard.nextStep.enrichmentDescription')}
                enrichmentConfiguredTitle={t('dashboard.nextStep.enrichmentConfiguredTitle')}
                enrichmentConfiguredDescription={t('dashboard.nextStep.enrichmentConfiguredDescription')}
                readyLabel={t('dashboard.nextStep.readyLabel')}
                exploreTitle={t('dashboard.nextStep.exploreTitle')}
                exploreDescription={t('dashboard.nextStep.exploreDescription')}
                exploreAction={t('dashboard.actions.explore')}
                editConfigAction={t('dashboard.actions.editConfig')}
                addSourceAction={t('dashboard.actions.addSource')}
                openGroupAction={t('dashboard.actions.openGroup')}
                enrichAction={t('dashboard.actions.enrichNow')}
                manageEnrichmentAction={t('dashboard.actions.manageEnrichment')}
                onExplore={onExploreReference}
                onEdit={() => void openReferenceEditor(group)}
                onAddSource={group.canAddSource && onReimport ? onReimport : undefined}
                onOpenGroup={onOpenGroup}
                onEnrich={onEnrich}
              />
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
              editConfigAction={entity.type === 'dataset' ? t('dashboard.actions.editConfig') : undefined}
              exploreAction={entity.type === 'dataset' ? t('dashboard.actions.explore') : undefined}
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

      <AnalysisToolSheet
        open={activeTool !== null}
        title={toolMeta?.title}
        description={toolMeta?.description}
        content={toolMeta?.content}
        onOpenChange={(open) => !open && setActiveTool(null)}
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
        onReferenceSave={(name, updated) => persistReferenceConfig(name, updated)}
      />
    </div>
  )
}
