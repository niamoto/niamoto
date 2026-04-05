import { useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  AlertTriangle,
  Database,
  Layers,
  Pencil,
  RefreshCw,
  Search,
  Sparkles,
} from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DashboardConfigEditorSheet } from './DashboardConfigEditorSheet'
import { EnrichmentWorkspaceSheet } from './EnrichmentWorkspaceSheet'
import { MetricCard } from './MetricCard'
import { SourceRow } from './SourceRow'
import type { EditingState } from './dashboardConfigEditorTypes'
import { useDatasets, type DatasetInfo } from '@/hooks/useDatasets'
import { useImportSummaryDetailed } from '@/hooks/useImportSummaryDetailed'
import { useReferences, type ReferenceInfo } from '@/hooks/useReferences'
import { apiClient } from '@/shared/lib/api/client'
import type {
  DatasetConfig,
  ReferenceConfig,
} from '@/features/import/components/editors/EntityConfigEditor'

type ReferenceStatus = 'structural_alert' | 'enrichment_available' | 'enrichment_configured' | 'imported'

interface SourcesOverviewProps {
  onExploreDataset: (name: string) => void
  onExploreReference: (name: string) => void
  onOpenGroups: () => void
  onOpenGroup: (name: string) => void
  onReimport: () => void
  onOpenVerification: () => void
  onOpenEnrichment: () => void
}

function getReferenceStatus(
  reference: ReferenceInfo,
  issueCount: number
): ReferenceStatus {
  if (issueCount > 0) return 'structural_alert'
  if (reference.can_enrich && !reference.enrichment_enabled) return 'enrichment_available'
  if (reference.enrichment_enabled) return 'enrichment_configured'
  return 'imported'
}

export function SourcesOverview({
  onExploreDataset,
  onExploreReference,
  onOpenGroups,
  onOpenGroup,
  onReimport,
  onOpenVerification,
  onOpenEnrichment,
}: SourcesOverviewProps) {
  const { t } = useTranslation('sources')
  const queryClient = useQueryClient()
  const { data: summary, isLoading, error } = useImportSummaryDetailed()
  const { data: referencesData } = useReferences()
  const { data: datasetsData } = useDatasets()

  const references = referencesData?.references ?? []
  const datasets = datasetsData?.datasets ?? []
  const [activeReference, setActiveReference] = useState<ReferenceInfo | null>(null)
  const [editingState, setEditingState] = useState<EditingState>(null)
  const [editorError, setEditorError] = useState<string | null>(null)
  const [savingConfig, setSavingConfig] = useState(false)

  const alertsByEntity = useMemo(() => {
    const grouped = new Map<string, number>()
    for (const alert of summary?.alerts ?? []) {
      grouped.set(alert.entity, (grouped.get(alert.entity) ?? 0) + 1)
    }
    return grouped
  }, [summary?.alerts])

  const entityMetrics = useMemo(
    () => new Map(summary?.entities.map((entity) => [entity.name, entity]) ?? []),
    [summary?.entities]
  )

  const layers = useMemo(
    () => (summary?.entities ?? []).filter((entity) => entity.entity_type === 'layer'),
    [summary?.entities]
  )

  const sourceCount = datasets.length + references.length + layers.length
  const alertCount = summary?.alerts.length ?? 0
  const enrichableReferences = references.filter((reference) => reference.can_enrich)
  const configuredEnrichmentCount = enrichableReferences.filter(
    (reference) => reference.enrichment_enabled
  ).length
  const availableEnrichmentCount = enrichableReferences.length - configuredEnrichmentCount

  const availableReferences = references.map((reference) => ({
    name: reference.name,
    columns: reference.schema_fields?.map((field) => field.name) ?? [],
  }))

  const availableDatasets = datasets.map((dataset) => dataset.name)
  const nextStep =
    alertCount > 0
      ? {
          title: t('dashboard.readiness.nextStep.reviewTitle', 'Review known alerts first'),
          description: t(
            'dashboard.readiness.nextStep.reviewDescription',
            '{{count}} structural alerts were detected in imported sources. Start in Verification before configuring pages or enrichment.',
            { count: alertCount }
          ),
          actionLabel: t('dashboard.actions.openVerification', 'Open verification'),
          onClick: onOpenVerification,
        }
      : availableEnrichmentCount > 0
        ? {
            title: t(
              'dashboard.readiness.nextStep.enrichmentTitle',
              'Configure enrichment where it adds value'
            ),
            description: t(
              'dashboard.readiness.nextStep.enrichmentDescription',
              '{{count}} reference(s) can be enriched from external APIs. Configure them now, or continue directly to collections.',
              { count: availableEnrichmentCount }
            ),
            actionLabel: t('dashboard.actions.openEnrichment', 'Open enrichment'),
            onClick: onOpenEnrichment,
          }
        : references.length > 0
          ? {
              title: t(
                'dashboard.readiness.nextStep.collectionsTitle',
                'Collections are ready to configure'
              ),
              description: t(
                'dashboard.readiness.nextStep.collectionsDescription',
                'Your imported references already define collections. Open them when you are ready to configure pages, widgets, and navigation.'
              ),
              actionLabel: t('dashboard.actions.openCollections'),
              onClick: onOpenGroups,
            }
          : null

  const refreshAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['datasets'] }),
      queryClient.invalidateQueries({ queryKey: ['references'] }),
      queryClient.invalidateQueries({ queryKey: ['import-summary'] }),
    ])
  }

  const openDatasetEditor = async (dataset: DatasetInfo) => {
    setEditorError(null)
    setEditingState({
      entityType: 'dataset',
      name: dataset.name,
      config: null,
      detectedColumns: dataset.schema_fields?.map((field) => field.name) ?? [],
    })

    try {
      const response = await apiClient.get<DatasetConfig>(
        `/config/datasets/${encodeURIComponent(dataset.name)}/config`
      )
      setEditingState({
        entityType: 'dataset',
        name: dataset.name,
        config: response.data,
        detectedColumns: dataset.schema_fields?.map((field) => field.name) ?? [],
      })
    } catch (err) {
      setEditorError(err instanceof Error ? err.message : t('dashboard.errors.loadConfig'))
    }
  }

  const persistDatasetConfig = async (name: string, config: DatasetConfig) => {
    setSavingConfig(true)
    setEditorError(null)
    try {
      await apiClient.put(`/config/datasets/${encodeURIComponent(name)}/config`, config)
      await refreshAll()
      setEditingState(null)
    } catch (err) {
      setEditorError(err instanceof Error ? err.message : t('dashboard.errors.saveConfig'))
    } finally {
      setSavingConfig(false)
    }
  }

  const persistReferenceConfig = async (name: string, config: ReferenceConfig) => {
    setSavingConfig(true)
    setEditorError(null)
    try {
      await apiClient.put(`/config/references/${encodeURIComponent(name)}/config`, config)
      await refreshAll()
      setEditingState(null)
    } catch (err) {
      setEditorError(err instanceof Error ? err.message : t('dashboard.errors.saveConfig'))
    } finally {
      setSavingConfig(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !summary) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>{t('dashboard.errors.loadTitle')}</AlertTitle>
        <AlertDescription>
          {error instanceof Error ? error.message : t('dashboard.errors.loadSummary')}
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t('dashboard.readiness.title', 'Imported data')}
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => void refreshAll()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('dashboard.actions.refresh')}
          </Button>
          <Button variant="outline" size="sm" onClick={onReimport}>
            {t('dashboard.actions.reimport')}
          </Button>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <MetricCard
          value={summary.total_rows.toLocaleString()}
          label={t('dashboard.readiness.metrics.rowsLabel', 'Rows imported')}
          sublabel={t('dashboard.readiness.metrics.rowsSublabel', 'Across {{count}} sources', {
            count: sourceCount,
          })}
          ariaLabel={t('dashboard.readiness.metrics.rowsLabel', 'Rows imported')}
        />
        <MetricCard
          value={alertCount}
          label={t('dashboard.readiness.metrics.alertsLabel', 'Known alerts')}
          sublabel={
            alertCount > 0
              ? t('dashboard.readiness.metrics.alertsDetected', '{{count}} detected', {
                  count: alertCount,
                })
              : t('dashboard.readiness.metrics.alertsNone', 'None detected')
          }
          variant={alertCount > 0 ? 'warning' : 'default'}
          onClick={onOpenVerification}
          actionLabel={t('dashboard.actions.openVerification', 'Open verification')}
          ariaLabel={t('dashboard.actions.openVerification', 'Open verification')}
        />
        <MetricCard
          value={configuredEnrichmentCount > 0 ? configuredEnrichmentCount : enrichableReferences.length}
          label={t('dashboard.readiness.metrics.enrichmentLabel', 'Enrichment')}
          sublabel={
            configuredEnrichmentCount > 0
              ? t('dashboard.readiness.metrics.enrichmentConfigured', '{{count}} configured', {
                  count: configuredEnrichmentCount,
                })
              : t('dashboard.readiness.metrics.enrichmentAvailable', '{{count}} available', {
                  count: enrichableReferences.length,
                })
          }
          variant={configuredEnrichmentCount > 0 || enrichableReferences.length > 0 ? 'success' : 'default'}
          onClick={onOpenEnrichment}
          actionLabel={t('dashboard.actions.openEnrichment', 'Open enrichment')}
          ariaLabel={t('dashboard.actions.openEnrichment', 'Open enrichment')}
        />
      </section>

      <p className="text-xs text-muted-foreground">
        {t(
          'dashboard.readiness.caption',
          'Detailed checks live in Verification. The overview only summarizes automatically computed structural signals.'
        )}
      </p>

      {nextStep ? (
        <Alert className="border-border/70 bg-muted/30">
          <AlertTitle>{nextStep.title}</AlertTitle>
          <AlertDescription className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>{nextStep.description}</span>
            <Button type="button" size="sm" onClick={nextStep.onClick}>
              {nextStep.actionLabel}
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              {t('tree.references', 'References')}
            </h2>
            <Badge variant="secondary">{references.length}</Badge>
          </div>
        </div>
        <div className="space-y-3">
          {references.map((reference) => {
            const metrics =
              entityMetrics.get(reference.table_name) ?? entityMetrics.get(reference.name)
            const issueCount =
              (alertsByEntity.get(reference.name) ?? 0) +
              (alertsByEntity.get(reference.table_name) ?? 0)
            const status = getReferenceStatus(reference, issueCount)
            const statusVariant =
              status === 'structural_alert'
                ? 'destructive'
                : status === 'enrichment_available'
                  ? 'default'
                  : status === 'enrichment_configured'
                    ? 'secondary'
                    : 'outline'
            const statusLabel = t(`dashboard.status.${status}`, {
              defaultValue:
                {
                  structural_alert: 'Structural alert',
                  enrichment_available: 'Enrichment available',
                  enrichment_configured: 'Enrichment configured',
                  imported: 'Imported',
                }[status],
            })

            const primaryAction =
              status === 'structural_alert'
                ? {
                    label: t('dashboard.actions.openVerification', 'Open verification'),
                    onClick: onOpenVerification,
                    variant: 'default' as const,
                  }
                : status === 'enrichment_available' || status === 'enrichment_configured'
                  ? {
                      label:
                        status === 'enrichment_configured'
                          ? t('dashboard.actions.manageEnrichment')
                          : t('dashboard.actions.configureEnrichment'),
                      onClick: () => setActiveReference(reference),
                      variant: 'default' as const,
                    }
                  : {
                      label: t('dashboard.actions.open'),
                      onClick: () => onOpenGroup(reference.name),
                      variant: 'default' as const,
                    }

            const secondaryActions = [
              ...(status === 'imported'
                ? []
                : [{
                    label: t('dashboard.actions.open'),
                    onClick: () => onOpenGroup(reference.name),
                    variant: 'ghost' as const,
                  }]),
              {
                label: t('dashboard.actions.details', 'Details'),
                onClick: () => onExploreReference(reference.name),
                variant: 'ghost' as const,
              },
            ]

            return (
              <SourceRow
                key={reference.name}
                icon={Sparkles}
                name={reference.name}
                typeLabel={t(`dashboard.referenceKinds.${reference.kind}`, {
                  defaultValue: reference.kind,
                })}
                metrics={t('dashboard.readiness.referenceMetrics', '{{rows}} · {{fields}}', {
                  rows: t('dashboard.rows', '{{count}} rows', {
                    count: metrics?.row_count ?? reference.entity_count ?? 0,
                  }),
                  fields: t('dashboard.fields', '{{count}} fields', {
                    count: metrics?.column_count ?? reference.schema_fields.length,
                  }),
                })}
                statusBadge={{ label: statusLabel, variant: statusVariant }}
                onNameClick={() => onExploreReference(reference.name)}
                actions={[
                  {
                    label: primaryAction.label,
                    onClick: primaryAction.onClick,
                    variant: primaryAction.variant,
                  },
                  ...secondaryActions,
                ]}
              />
            )
          })}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            {t('tree.datasets', 'Datasets')}
          </h2>
          <Badge variant="secondary">{datasets.length}</Badge>
        </div>
        <div className="space-y-3">
          {datasets.map((dataset) => {
            const metrics =
              entityMetrics.get(dataset.table_name) ?? entityMetrics.get(dataset.name)
            return (
              <SourceRow
                key={dataset.name}
                icon={Database}
                name={dataset.name}
                typeLabel={t('dashboard.kinds.dataset')}
                metrics={t('dashboard.readiness.datasetMetrics', '{{rows}} · {{fields}}', {
                  rows: t('dashboard.rows', '{{count}} rows', {
                    count: metrics?.row_count ?? dataset.entity_count ?? 0,
                  }),
                  fields: t('dashboard.fields', '{{count}} fields', {
                    count: metrics?.column_count ?? dataset.schema_fields.length,
                  }),
                })}
                onNameClick={() => onExploreDataset(dataset.name)}
                actions={[
                  {
                    label: t('dashboard.actions.explore'),
                    icon: Search,
                    onClick: () => onExploreDataset(dataset.name),
                    variant: 'default',
                  },
                  {
                    label: t('dashboard.actions.editConfig'),
                    icon: Pencil,
                    onClick: () => void openDatasetEditor(dataset),
                    variant: 'ghost',
                  },
                  {
                    label: t('dashboard.actions.updateFile'),
                    onClick: onReimport,
                    variant: 'ghost',
                  },
                ]}
              />
            )
          })}
        </div>
      </section>

      {layers.length > 0 ? (
        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              {t('dashboard.readiness.layersTitle', 'Layers')}
            </h2>
            <Badge variant="secondary">{layers.length}</Badge>
          </div>
          <div className="space-y-3">
            {layers.map((layer) => (
              <SourceRow
                key={layer.name}
                icon={Layers}
                name={layer.name}
                typeLabel={t('dashboard.kinds.layer')}
                metrics={t(
                  'dashboard.readiness.layerMetrics',
                  '{{rows}} · {{fields}}',
                  {
                    rows: t('dashboard.rows', '{{count}} rows', { count: layer.row_count }),
                    fields: t('dashboard.fields', '{{count}} fields', {
                      count: layer.column_count,
                    }),
                  }
                )}
                actions={[
                  {
                    label: t('dashboard.actions.updateLayer'),
                    onClick: onReimport,
                    variant: 'ghost',
                  },
                ]}
              />
            ))}
          </div>
        </section>
      ) : null}

      <EnrichmentWorkspaceSheet
        open={activeReference !== null}
        reference={activeReference}
        onOpenChange={(open) => !open && setActiveReference(null)}
        onConfigSaved={() => void refreshAll()}
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
        onClose={() => {
          setEditingState(null)
          setEditorError(null)
        }}
        onDatasetSave={(name, updated) => persistDatasetConfig(name, updated)}
        onReferenceSave={(name, updated) => persistReferenceConfig(name, updated)}
      />
    </div>
  )
}
