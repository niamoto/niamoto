/**
 * AutoConfigDisplay - Shows auto-configuration results with Sheet editing
 *
 * Displays detected datasets, references, links, and metadata layers
 * Supports:
 * - Reclassification via buttons
 * - Sheet-based editing for each entity (not inline)
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Database,
  Network,
  Map,
  TrendingUp,
  Loader2,
  Sparkles,
  Globe2,
  Layers,
  ArrowRightLeft,
  FileSpreadsheet,
  Key,
  GitBranch,
  Link2,
  HelpCircle,
  Pencil,
} from 'lucide-react'
import type {
  AutoConfigureResponse,
  AuxiliarySource,
  AutoConfigureProgressEvent,
  DecisionAlignment,
  DecisionSummary,
  ReviewLevel,
} from '@/lib/api/smart-config'
import { EntityConfigEditor } from './EntityConfigEditor'
import type { DatasetConfig, ReferenceConfig, LayerConfig } from './EntityConfigEditor'

interface AutoConfigDisplayProps {
  result: AutoConfigureResponse | null
  isLoading?: boolean
  /** Callback when entities are reclassified or edited */
  onReclassify?: (updatedEntities: AutoConfigureResponse['entities']) => void
  /** Whether editing is enabled */
  editable?: boolean
  /** Detected columns per file (for form dropdowns) */
  detectedColumns?: Record<string, string[]>
  /** Real-time analysis events emitted while auto-config is running */
  analysisEvents?: AutoConfigureProgressEvent[]
  /** Current analysis stage, derived from the latest stage event */
  analysisStage?: string | null
}

// Types for editing state
type EditingEntity =
  | { type: 'dataset'; name: string; config: DatasetConfig; columns: string[] }
  | { type: 'reference'; name: string; config: ReferenceConfig; columns: string[] }
  | { type: 'layer'; index: number; config: LayerConfig }
  | null

export function AutoConfigDisplay({
  result,
  isLoading = false,
  onReclassify,
  editable = false,
  detectedColumns = {},
  analysisEvents = [],
  analysisStage = null,
}: AutoConfigDisplayProps) {
  const { t } = useTranslation('sources')
  // Single editing state - opens in Sheet
  const [editingEntity, setEditingEntity] = useState<EditingEntity>(null)

  const openDatasetEditor = (name: string, config: DatasetConfig) => {
    const columns = detectedColumns[name] || []
    setEditingEntity({ type: 'dataset', name, config, columns })
  }

  const openRefEditor = (name: string, config: ReferenceConfig) => {
    // For derived references, get columns from the source dataset
    let columns: string[] = []
    if (config.connector?.type === 'derived' && config.connector?.source) {
      columns = detectedColumns[config.connector.source] || []
    } else {
      columns = detectedColumns[name] || []
    }
    setEditingEntity({ type: 'reference', name, config, columns })
  }

  const openLayerEditor = (index: number, config: LayerConfig) => {
    setEditingEntity({ type: 'layer', index, config })
  }

  const closeEditor = () => {
    setEditingEntity(null)
  }

  // Handle moving entity from dataset to reference
  const moveToReference = (name: string) => {
    if (!result || !onReclassify) return

    const datasetConfig = result.entities.datasets?.[name]
    if (!datasetConfig) return

    const newDatasets = { ...result.entities.datasets }
    delete newDatasets[name]

    const newReferences = {
      ...result.entities.references,
      [name]: {
        kind: 'generic',
        connector: datasetConfig.connector,
        schema: datasetConfig.schema || { id_field: 'id', fields: [] },
      },
    }

    onReclassify({
      ...result.entities,
      datasets: newDatasets,
      references: newReferences,
    })
  }

  // Handle moving entity from reference to dataset
  const moveToDataset = (name: string) => {
    if (!result || !onReclassify) return

    const refConfig = result.entities.references?.[name]
    if (!refConfig) return

    const newReferences = { ...result.entities.references }
    delete newReferences[name]

    const newDatasets = {
      ...result.entities.datasets,
      [name]: { connector: refConfig.connector },
    }

    onReclassify({
      ...result.entities,
      datasets: newDatasets,
      references: newReferences,
    })
  }

  // Handle dataset config update
  const handleDatasetUpdate = (name: string, updated: DatasetConfig) => {
    if (!result || !onReclassify) return

    onReclassify({
      ...result.entities,
      datasets: {
        ...result.entities.datasets,
        [name]: updated,
      },
    })
    closeEditor()
  }

  // Handle reference config update
  const handleReferenceUpdate = (name: string, updated: ReferenceConfig) => {
    if (!result || !onReclassify) return

    onReclassify({
      ...result.entities,
      references: {
        ...result.entities.references,
        [name]: updated,
      },
    })
    closeEditor()
  }

  // Handle layer config update
  const handleLayerUpdate = (idx: number, updated: LayerConfig) => {
    if (!result || !onReclassify) return

    const layers = [...(result.entities.metadata?.layers || [])]
    layers[idx] = updated

    onReclassify({
      ...result.entities,
      metadata: {
        ...result.entities.metadata,
        layers,
      },
    })
    closeEditor()
  }

  if (isLoading) {
    const latestEvents = analysisEvents.slice(-8)
    return (
      <div className="space-y-6 py-8">
        <div className="flex flex-col items-center justify-center">
          <div className="relative mb-4">
            <Sparkles className="h-12 w-12 animate-pulse text-primary" />
          </div>
          <h3 className="mb-2 text-lg font-semibold">{t('autoConfig.loading.title')}</h3>
          <p className="text-center text-sm text-muted-foreground">
            {analysisStage || t('autoConfig.loading.description')}
          </p>
        </div>

        <div className="mx-auto w-full max-w-2xl rounded-lg border bg-muted/30 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-medium">{t('autoConfig.loading.liveFeed')}</div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {t('autoConfig.loading.step')}
            </div>
          </div>
          <div className="space-y-2">
            {latestEvents.length > 0 ? (
              latestEvents.map((event, index) => (
                <div
                  key={`${event.timestamp}-${index}`}
                  className="flex items-start gap-3 rounded-md bg-background/80 px-3 py-2 text-sm"
                >
                  <div className="pt-0.5">
                    {event.kind === 'finding' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : event.kind === 'error' ? (
                      <AlertCircle className="h-4 w-4 text-destructive" />
                    ) : (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-foreground">{event.message}</div>
                    {(event.file || event.entity) && (
                      <div className="text-xs text-muted-foreground">
                        {[event.entity, event.file].filter(Boolean).join(' • ')}
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('autoConfig.loading.waitingForEvents')}
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (!result) {
    return null
  }

  const datasetCount = Object.keys(result.entities.datasets || {}).length
  const referenceCount = Object.keys(result.entities.references || {}).length
  const layerCount = result.entities.metadata?.layers?.length || 0
  const auxiliarySources = result.auxiliary_sources || []
  const decisionSummaries = result.decision_summary || {}
  const semanticEvidence = result.semantic_evidence || {}
  const reviewCount = Object.values(decisionSummaries).filter(
    (summary) => summary?.review_required && summary?.final_entity_type !== 'auxiliary_source'
  ).length

  // Build available references for dataset FK dropdowns
  const availableReferences = Object.entries(result.entities.references || {}).map(
    ([name, _config]: [string, unknown]) => ({
      name,
      columns: detectedColumns[name] || [],
    })
  )

  // Build available datasets for derived reference source dropdown
  const availableDatasets = Object.keys(result.entities.datasets || {})

  const getAlignmentLabel = (alignment?: DecisionAlignment) => {
    switch (alignment) {
      case 'aligned':
        return t('autoConfig.alignment.aligned')
      case 'heuristic_only':
        return t('autoConfig.alignment.heuristicOnly')
      case 'ml_override':
        return t('autoConfig.alignment.mlOverride')
      case 'conflict':
        return t('autoConfig.alignment.conflict')
      case 'mixed':
        return t('autoConfig.alignment.mixed')
      default:
        return t('autoConfig.alignment.heuristicOnly')
    }
  }

  const getSummaryBadgeLabel = (summary?: DecisionSummary) =>
    summary?.review_level === 'review'
      ? t('autoConfig.badges.reviewRequired')
      : summary?.review_level === 'notice'
        ? t('autoConfig.badges.notice')
        : summary?.review_level === 'info'
          ? t('autoConfig.badges.info')
          : t('autoConfig.badges.stable')

  const getSummaryBadgeVariant = (level?: ReviewLevel) => {
    switch (level) {
      case 'review':
        return 'destructive' as const
      case 'notice':
        return 'secondary' as const
      default:
        return 'outline' as const
    }
  }

  const getReasonToneClass = (level?: ReviewLevel) => {
    switch (level) {
      case 'review':
        return 'text-amber-700 dark:text-amber-400'
      case 'notice':
        return 'text-blue-700 dark:text-blue-300'
      case 'info':
        return 'text-muted-foreground'
      default:
        return 'text-muted-foreground'
    }
  }

  const getEntityStatusBadge = (summary?: DecisionSummary) => {
    if (!summary || summary.review_level === 'stable' || summary.review_level === 'info') {
      return null
    }

    return (
      <Badge
        variant={summary.review_level === 'review' ? 'destructive' : 'secondary'}
        className="text-[10px]"
      >
        {summary.review_level === 'review'
          ? t('autoConfig.badges.review')
          : t('autoConfig.badges.notice')}
      </Badge>
    )
  }

  const renderDecisionInsight = (name: string) => {
    const summary = decisionSummaries[name]
    const evidence = semanticEvidence[name]
    if (!summary && !evidence) return null

    const topPrediction = evidence?.top_predictions?.[0]

    return (
        <div className="mt-2 rounded border border-border/70 bg-background/70 p-2 text-[11px]">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={getSummaryBadgeVariant(summary?.review_level)} className="text-[10px]">
            {getSummaryBadgeLabel(summary)}
          </Badge>
          {summary?.alignment && (
            <Badge variant="secondary" className="text-[10px]">
              {getAlignmentLabel(summary.alignment)}
            </Badge>
          )}
          {summary?.ml_entity_type && (
            <Badge variant="outline" className="text-[10px]">
              ML: {summary.ml_entity_type}
              {typeof summary.ml_confidence === 'number'
                ? ` ${Math.round(summary.ml_confidence * 100)}%`
                : ''}
            </Badge>
          )}
        </div>

        {(summary?.heuristic_entity_type || summary?.final_entity_type) && (
          <div className="mt-2 text-muted-foreground">
            {t('autoConfig.labels.heuristic')}:{' '}
            <span className="text-foreground">{summary?.heuristic_entity_type}</span>
            {' · '}
            {t('autoConfig.labels.final')}:{' '}
            <span className="text-foreground">{summary?.final_entity_type}</span>
          </div>
        )}

        {summary?.review_reasons && summary.review_reasons.length > 0 && (
          <ul className={`mt-1 space-y-0.5 ${getReasonToneClass(summary?.review_level)}`}>
            {summary.review_reasons.map((reason) => (
              <li key={reason}>• {reason}</li>
            ))}
          </ul>
        )}

        {topPrediction && (
          <div className="mt-1 text-muted-foreground">
            {t('autoConfig.labels.primarySignal')}:{' '}
            <span className="text-foreground">{topPrediction.column}</span>
            {' → '}
            <span className="text-foreground">{topPrediction.concept}</span>
            {' '}
            ({Math.round(topPrediction.confidence * 100)}%)
          </div>
        )}
      </div>
    )
  }

  // Build detection details
  const buildDetectionDetails = () => {
    const details: Array<{
      icon: React.ReactNode
      text: string
      status: 'success' | 'warning' | 'info'
    }> = []

    const datasets = result.entities.datasets || {}
    Object.entries(datasets).forEach(([name, config]: [string, any]) => {
      const format = config.connector?.format || config.connector?.type || 'file'
      details.push({
        icon: <FileSpreadsheet className="h-4 w-4" />,
        text: t('autoConfig.detection.fileFormatRecognized', {
          format: format.toUpperCase(),
          name,
        }),
        status: 'success',
      })

      if (config.schema?.id_field) {
        details.push({
          icon: <Key className="h-4 w-4" />,
          text: t('autoConfig.detection.idColumnFound', {
            field: config.schema.id_field,
          }),
          status: 'success',
        })
      }

      if (config.links && config.links.length > 0) {
        config.links.forEach((link: any) => {
          const confidence = link.confidence || 0
          details.push({
            icon: <Link2 className="h-4 w-4" />,
            text: t('autoConfig.detection.relationshipDetected', {
              source: `${name}.${link.field}`,
              target: link.entity,
            }),
            status: confidence >= 0.7 ? 'success' : 'warning',
          })
        })
      }

      const predictions = result.ml_predictions?.[name] || []
      const confidentPredictions = predictions.filter((p) => p.confidence >= 0.7)
      if (confidentPredictions.length > 0) {
        details.push({
          icon: <TrendingUp className="h-4 w-4" />,
          text: t('autoConfig.detection.mlConfidentColumns', {
            count: confidentPredictions.length,
            name,
          }),
          status: 'info',
        })
      }

      const summary = decisionSummaries[name]
      if (summary?.review_required) {
        details.push({
          icon: <AlertTriangle className="h-4 w-4" />,
          text: t('autoConfig.detection.manualReviewRequired', { name }),
          status: 'warning',
        })
      }
    })

    const references = result.entities.references || {}
    Object.entries(references).forEach(([name, config]: [string, any]) => {
      if (config.kind) {
        details.push({
          icon: <Database className="h-4 w-4" />,
          text: t('autoConfig.detection.referenceOfKind', { name, kind: config.kind }),
          status: 'success',
        })
      }

      if (config.hierarchy?.levels && config.hierarchy.levels.length > 0) {
        details.push({
          icon: <GitBranch className="h-4 w-4" />,
          text: t('autoConfig.detection.hierarchyDetected', {
            levels: config.hierarchy.levels.join(' → '),
          }),
          status: 'success',
        })
      }

      if (config.connector?.type === 'derived') {
        details.push({
          icon: <Network className="h-4 w-4" />,
          text: t('autoConfig.detection.derivedReference', {
            source: config.connector.source,
          }),
          status: 'info',
        })
      }

      if (config.connector?.type === 'file_multi_feature') {
        const sourceCount = config.connector.sources?.length || 0
        details.push({
          icon: <Map className="h-4 w-4" />,
          text: t('autoConfig.detection.spatialLayersDetected', {
            count: sourceCount,
          }),
          status: 'success',
        })
      }
    })

    if (layerCount > 0) {
      details.push({
        icon: <Globe2 className="h-4 w-4" />,
        text: t('autoConfig.detection.metadataLayersDetected', { count: layerCount }),
        status: 'success',
      })
    }

    if (auxiliarySources.length > 0) {
      details.push({
        icon: <FileSpreadsheet className="h-4 w-4" />,
        text: t('autoConfig.detection.auxiliarySourcesDetected', {
          count: auxiliarySources.length,
        }),
        status: 'info',
      })
    }

    return details
  }

  const detectionDetails = buildDetectionDetails()
  const successCount = detectionDetails.filter((d) => d.status === 'success').length
  const warningCount = detectionDetails.filter((d) => d.status === 'warning').length

  // Get sheet title/description based on editing entity
  const getSheetInfo = () => {
    if (!editingEntity) return { title: '', description: '' }

    switch (editingEntity.type) {
      case 'dataset':
        return {
          title: t('autoConfig.sheetTitles.dataset', { name: editingEntity.name }),
          description: t('autoConfig.sheetDescriptions.dataset'),
        }
      case 'reference':
        return {
          title: t('autoConfig.sheetTitles.reference', { name: editingEntity.name }),
          description: t('autoConfig.sheetDescriptions.reference'),
        }
      case 'layer':
        return {
          title: t('autoConfig.sheetTitles.layer', { name: editingEntity.config.name }),
          description: t('autoConfig.sheetDescriptions.layer'),
        }
    }
  }

  const sheetInfo = getSheetInfo()

  return (
    <>
      <div className="space-y-4">
        {/* Detection details panel */}
        <div className="rounded-lg border bg-muted/30 p-3">
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <Sparkles className="h-4 w-4 text-primary" />
            {t('autoConfig.sections.autoDetection')}
            <span className="ml-auto text-xs font-normal text-muted-foreground">
              {t('autoConfig.summary.detectedElements', { count: successCount })}
              {warningCount > 0 &&
                `, ${t('autoConfig.summary.itemsToReview', { count: warningCount })}`}
            </span>
          </h4>
          <div className="space-y-1.5">
            {detectionDetails.map((detail, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm">
                <span
                  className={
                    detail.status === 'success'
                      ? 'text-green-600'
                      : detail.status === 'warning'
                        ? 'text-amber-600'
                        : 'text-blue-600'
                  }
                >
                  {detail.status === 'success' ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : detail.status === 'warning' ? (
                    <AlertTriangle className="h-4 w-4" />
                  ) : (
                    <HelpCircle className="h-4 w-4" />
                  )}
                </span>
                <span
                  className={
                    detail.status === 'warning' ? 'text-amber-700 dark:text-amber-400' : ''
                  }
                >
                  {detail.text}
                </span>
              </div>
            ))}
            {detectionDetails.length === 0 && (
              <p className="text-sm text-muted-foreground">
                {t('autoConfig.detection.noStructureDetected')}
              </p>
            )}
          </div>
        </div>

        {/* Warnings */}
        {result.warnings && result.warnings.length > 0 && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <ul className="list-inside list-disc space-y-1">
                {result.warnings.map((warning, i) => (
                  <li key={i} className="text-sm">
                    {warning}
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {reviewCount > 0 && (
          <Alert className="border-amber-200 bg-amber-50/70 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-sm">
              {t('autoConfig.summary.reviewAlert', { count: reviewCount })}
            </AlertDescription>
          </Alert>
        )}

        {/* Entities grid */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Datasets */}
          <div className="rounded-lg border p-3">
            <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Database className="h-4 w-4 text-blue-500" />
              {t('autoConfig.sections.datasets', { count: datasetCount })}
            </h4>
            <div className="space-y-2">
              {Object.entries(result.entities.datasets || {}).map(
                ([name, config]: [string, any]) => (
                  <div key={name} className="group rounded bg-accent p-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{name}</span>
                        {getEntityStatusBadge(decisionSummaries[name])}
                      </div>
                      <div className="flex items-center gap-1">
                        {editable && onReclassify && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 gap-1 px-2 text-xs opacity-0 transition-opacity group-hover:opacity-100"
                              onClick={() => moveToReference(name)}
                              title={t('autoConfig.actions.moveToReferences')}
                            >
                              <ArrowRightLeft className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 gap-1 px-2 text-xs"
                              onClick={() => openDatasetEditor(name, config as DatasetConfig)}
                            >
                              <Pencil className="h-3 w-3" />
                              {t('autoConfig.actions.edit')}
                            </Button>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Summary - datasets only have connector */}
                    <div className="mt-1 text-xs text-muted-foreground">
                      <div>{config.connector?.format?.toUpperCase() || 'CSV'}</div>
                      <div className="truncate opacity-70">{config.connector?.path}</div>
                      {result.ml_predictions?.[name] && result.ml_predictions[name].length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {result.ml_predictions[name].slice(0, 3).map((prediction) => (
                            <Badge
                              key={`${name}-${prediction.column}`}
                              variant="secondary"
                              className="text-[10px]"
                              title={`${prediction.column} → ${prediction.concept} (${Math.round(prediction.confidence * 100)}%)`}
                            >
                              {prediction.column}: {Math.round(prediction.confidence * 100)}%
                            </Badge>
                          ))}
                        </div>
                      )}
                      {renderDecisionInsight(name)}
                    </div>
                  </div>
                )
              )}
              {datasetCount === 0 && (
                <p className="py-2 text-center text-xs text-muted-foreground">
                  {t('autoConfig.empty.noDatasetsDetected')}
                </p>
              )}
            </div>
          </div>

          {/* References */}
          <div className="rounded-lg border p-3">
            <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Network className="h-4 w-4 text-green-500" />
              {t('autoConfig.sections.references', { count: referenceCount })}
            </h4>
            <div className="space-y-2">
              {Object.entries(result.entities.references || {}).map(
                ([name, config]: [string, any]) => {
                  const referenceUsageCount = decisionSummaries[name]?.referenced_by?.length || 0
                  const canMove =
                    editable &&
                    onReclassify &&
                    config.connector?.type !== 'derived' &&
                    config.kind !== 'hierarchical'

                  return (
                    <div key={name} className="group rounded bg-accent p-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{name}</span>
                          {config.kind && (
                            <Badge variant="outline" className="text-xs">
                              {config.kind}
                            </Badge>
                          )}
                          {getEntityStatusBadge(decisionSummaries[name])}
                        </div>
                        <div className="flex items-center gap-1">
                          {canMove && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 gap-1 px-2 text-xs opacity-0 transition-opacity group-hover:opacity-100"
                              onClick={() => moveToDataset(name)}
                              title={t('autoConfig.actions.moveToDatasets')}
                            >
                              <ArrowRightLeft className="h-3 w-3" />
                            </Button>
                          )}
                          {editable && onReclassify && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 gap-1 px-2 text-xs"
                              onClick={() => openRefEditor(name, config as ReferenceConfig)}
                            >
                              <Pencil className="h-3 w-3" />
                              {t('autoConfig.actions.edit')}
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Summary */}
                      <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                        {config.connector?.type === 'derived' && (
                          <div className="text-blue-600">
                            {t('autoConfig.reference.derivedFrom', {
                              source: config.connector.source,
                            })}
                          </div>
                        )}
                        {config.connector?.type === 'file_multi_feature' && (
                          <div className="text-purple-600">
                            {t('autoConfig.reference.sourceCount', {
                              count: config.connector.sources?.length || 0,
                            })}
                          </div>
                        )}
                        {config.hierarchy?.levels && (
                          <div>
                            {t('autoConfig.reference.levels', {
                              levels: config.hierarchy.levels.join(' → '),
                            })}
                          </div>
                        )}
                        {config.enrichment?.[0]?.enabled && (
                          <div className="flex items-center gap-1 text-amber-600">
                            <Sparkles className="h-3 w-3" />
                            {t('autoConfig.reference.enrichmentEnabled')}
                          </div>
                        )}
                        {referenceUsageCount > 0 && (
                          <div className="mt-1 border-t pt-1">
                            <span className="text-blue-600">
                              {t('autoConfig.reference.referencedByDatasets', {
                                count: referenceUsageCount,
                              })}
                            </span>
                          </div>
                        )}
                        {renderDecisionInsight(name)}
                      </div>
                    </div>
                  )
                }
              )}
              {referenceCount === 0 && (
                <p className="py-2 text-center text-xs text-muted-foreground">
                  {t('autoConfig.empty.noReferencesDetected')}
                </p>
              )}
            </div>
          </div>
        </div>

        {auxiliarySources.length > 0 && (
          <div className="rounded-lg border p-3">
            <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <FileSpreadsheet className="h-4 w-4 text-violet-500" />
              {t('autoConfig.sections.auxiliarySources', { count: auxiliarySources.length })}
            </h4>
            <div className="space-y-2">
              {auxiliarySources.map((source: AuxiliarySource) => (
                <div key={`${source.grouping}-${source.name}`} className="rounded bg-accent p-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{source.name}</span>
                    <Badge variant="outline" className="text-[10px]">
                      {t('autoConfig.badges.auxiliary')}
                    </Badge>
                  </div>
                  <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                    <div className="truncate">{source.data}</div>
                    <div className="text-violet-600">
                      {t('autoConfig.auxiliary.attachedTo', { target: source.grouping })}
                    </div>
                    <div>
                      {t('autoConfig.auxiliary.relation', {
                        field: source.relation.match_field,
                        refField: source.relation.ref_field,
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Metadata Layers */}
        {layerCount > 0 && (
          <div className="rounded-lg border p-3">
            <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Map className="h-4 w-4 text-purple-500" />
              {t('autoConfig.sections.metadataLayers', { count: layerCount })}
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {result.entities.metadata?.layers?.map((layer: any, idx: number) => (
                <div key={idx} className="group rounded bg-accent p-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 font-medium">
                      {layer.type === 'raster' ? (
                        <Globe2 className="h-4 w-4 text-orange-500" />
                      ) : (
                        <Layers className="h-4 w-4 text-purple-500" />
                      )}
                      <span className="truncate">{layer.name}</span>
                    </div>
                    {editable && onReclassify && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 gap-1 px-2 text-xs"
                        onClick={() => openLayerEditor(idx, layer as LayerConfig)}
                      >
                        <Pencil className="h-3 w-3" />
                        {t('autoConfig.actions.edit')}
                      </Button>
                    )}
                  </div>

                  <div className="mt-1 text-xs text-muted-foreground">
                    {layer.type}
                    {layer.format && ` (${layer.format})`}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary */}
        <div className="rounded-lg border bg-muted/20 p-3">
          <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <TrendingUp className="h-4 w-4" />
            {t('autoConfig.sections.summary')}
          </h4>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-xl font-bold text-blue-500">{datasetCount}</div>
              <div className="text-xs text-muted-foreground">{t('autoConfig.summary.datasets')}</div>
            </div>
            <div>
              <div className="text-xl font-bold text-green-500">{referenceCount}</div>
              <div className="text-xs text-muted-foreground">{t('autoConfig.summary.references')}</div>
            </div>
            <div>
              <div className="text-xl font-bold text-purple-500">{layerCount}</div>
              <div className="text-xs text-muted-foreground">{t('autoConfig.summary.layers')}</div>
            </div>
          </div>
          {reviewCount > 0 && (
            <div className="mt-3 border-t pt-3 text-center">
              <div className="text-xl font-bold text-amber-500">{reviewCount}</div>
              <div className="text-xs text-muted-foreground">
                {t('autoConfig.summary.entitiesToReview')}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Edit Sheet */}
      <Sheet open={editingEntity !== null} onOpenChange={() => closeEditor()}>
        <SheetContent className="w-[500px] sm:max-w-[500px]">
          <SheetHeader>
            <SheetTitle>{sheetInfo.title}</SheetTitle>
            <SheetDescription>{sheetInfo.description}</SheetDescription>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-120px)] pr-4">
            {editingEntity?.type === 'dataset' && (
              <EntityConfigEditor
                entityName={editingEntity.name}
                entityType="dataset"
                config={editingEntity.config}
                detectedColumns={editingEntity.columns}
                availableReferences={availableReferences}
                onSave={(updated) =>
                  handleDatasetUpdate(editingEntity.name, updated as DatasetConfig)
                }
                onCancel={closeEditor}
              />
            )}
            {editingEntity?.type === 'reference' && (
              <EntityConfigEditor
                entityName={editingEntity.name}
                entityType="reference"
                config={editingEntity.config}
                detectedColumns={editingEntity.columns}
                availableDatasets={availableDatasets}
                onSave={(updated) =>
                  handleReferenceUpdate(editingEntity.name, updated as ReferenceConfig)
                }
                onCancel={closeEditor}
              />
            )}
            {editingEntity?.type === 'layer' && (
              <EntityConfigEditor
                entityName={editingEntity.config.name}
                entityType="layer"
                config={editingEntity.config}
                onSave={(updated) =>
                  handleLayerUpdate(editingEntity.index, updated as LayerConfig)
                }
                onCancel={closeEditor}
              />
            )}
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </>
  )
}
