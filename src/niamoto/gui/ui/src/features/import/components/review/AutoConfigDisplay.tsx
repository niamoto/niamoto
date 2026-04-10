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
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Database,
  Network,
  Loader2,
  Sparkles,
  Globe2,
  Layers,
  ArrowRightLeft,
  FileSpreadsheet,
  Key,
  GitBranch,
  Link2,
} from 'lucide-react'
import type {
  AutoConfigureResponse,
  AuxiliarySource,
  AutoConfigureProgressEvent,
  DecisionAlignment,
  DecisionSummary,
  ReviewLevel,
} from '@/features/import/api/smart-config'
import type { ImportJobEvent } from '@/features/import/api/import'
import type {
  DatasetConfig,
  ReferenceConfig,
  LayerConfig,
} from '@/features/import/components/editors/EntityConfigEditor'
import { AutoConfigEditorSheet } from '@/features/import/components/auto-config/AutoConfigEditorSheet'
import { AutoConfigEntryCard } from '@/features/import/components/auto-config/AutoConfigEntryCard'
import { AutoConfigLoadingState } from '@/features/import/components/auto-config/AutoConfigLoadingState'

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
  /** Live import status while staying on the review screen */
  importState?: {
    active: boolean
    phase?: string | null
    message?: string
    progress?: number
    processedEntities?: number
    totalEntities?: number
    currentEntity?: string | null
    currentEntityType?: string | null
    events?: ImportJobEvent[]
  }
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
  importState,
}: AutoConfigDisplayProps) {
  const { t } = useTranslation('sources')
  // Single editing state - opens in Sheet
  const [editingEntity, setEditingEntity] = useState<EditingEntity>(null)
  const [expandedEntries, setExpandedEntries] = useState<Record<string, boolean>>({})

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

  const toggleEntry = (entryId: string) => {
    setExpandedEntries((previous) => ({
      ...previous,
      [entryId]: !previous[entryId],
    }))
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
    return <AutoConfigLoadingState analysisEvents={analysisEvents} analysisStage={analysisStage} />
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
  const isImporting = Boolean(importState?.active)
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

  type ListEntry =
    | {
        id: string
        type: 'dataset'
        name: string
        config: DatasetConfig
        summary?: DecisionSummary
      }
    | {
        id: string
        type: 'reference'
        name: string
        config: ReferenceConfig
        summary?: DecisionSummary
      }
    | {
        id: string
        type: 'auxiliary'
        name: string
        source: AuxiliarySource
      }
    | {
        id: string
        type: 'layer'
        name: string
        index: number
        config: LayerConfig
      }

  const entries: ListEntry[] = [
    ...Object.entries(result.entities.datasets || {}).map(([name, config]) => ({
      id: `dataset:${name}`,
      type: 'dataset' as const,
      name,
      config: config as DatasetConfig,
      summary: decisionSummaries[name],
    })),
    ...Object.entries(result.entities.references || {}).map(([name, config]) => ({
      id: `reference:${name}`,
      type: 'reference' as const,
      name,
      config: config as ReferenceConfig,
      summary: decisionSummaries[name],
    })),
    ...auxiliarySources.map((source) => ({
      id: `aux:${source.name}`,
      type: 'auxiliary' as const,
      name: source.name,
      source,
    })),
    ...(result.entities.metadata?.layers || []).map((layer, index) => ({
      id: `layer:${layer.name}:${index}`,
      type: 'layer' as const,
      name: layer.name,
      index,
      config: layer as LayerConfig,
    })),
  ]

  const reviewPriority = (level?: ReviewLevel) => {
    switch (level) {
      case 'review':
        return 0
      case 'notice':
        return 1
      case 'info':
        return 2
      default:
        return 3
    }
  }

  const typePriority = (type: ListEntry['type']) => {
    switch (type) {
      case 'dataset':
        return 0
      case 'reference':
        return 1
      case 'auxiliary':
        return 2
      case 'layer':
        return 3
    }
  }

  const sortedEntries = [...entries].sort((a, b) => {
    const reviewDelta =
      reviewPriority('summary' in a ? a.summary?.review_level : undefined) -
      reviewPriority('summary' in b ? b.summary?.review_level : undefined)
    if (reviewDelta !== 0) return reviewDelta

    const typeDelta = typePriority(a.type) - typePriority(b.type)
    if (typeDelta !== 0) return typeDelta

    return a.name.localeCompare(b.name)
  })

  const aggregationEntries = sortedEntries.filter(
    (entry): entry is Extract<ListEntry, { type: 'reference' }> =>
      entry.type === 'reference'
  )
  const supportingEntries = sortedEntries.filter((entry) => entry.type !== 'reference')

  const getReferenceAssociations = (referenceName: string) => ({
    datasets: decisionSummaries[referenceName]?.referenced_by?.map((item) => item.from) || [],
    auxiliary: auxiliarySources.filter((source) => source.grouping === referenceName),
  })

  const getTypeIcon = (entry: ListEntry) => {
    switch (entry.type) {
      case 'dataset':
        return <Database className="h-4 w-4 text-blue-500" />
      case 'reference':
        return <Network className="h-4 w-4 text-green-500" />
      case 'auxiliary':
        return <FileSpreadsheet className="h-4 w-4 text-violet-500" />
      case 'layer':
        return entry.config.type === 'raster' ? (
          <Globe2 className="h-4 w-4 text-orange-500" />
        ) : (
          <Layers className="h-4 w-4 text-purple-500" />
        )
    }
  }

  const getTypeLabel = (entry: ListEntry) => {
    switch (entry.type) {
      case 'dataset':
        return t('autoConfig.itemTypes.dataset')
      case 'reference':
        return t('autoConfig.itemTypes.reference')
      case 'auxiliary':
        return t('autoConfig.itemTypes.auxiliary')
      case 'layer':
        return t('autoConfig.itemTypes.layer')
    }
  }

  type ImportEntryState = 'queued' | 'importing' | 'done' | 'failed'

  const getImportStatesByEntry = (): Record<string, ImportEntryState> => {
    if (!isImporting) return {}

    const states: Record<string, ImportEntryState> = {}
    for (const entry of entries) {
      states[entry.id] = 'queued'
    }

    for (const event of importState?.events || []) {
      if (!event.entity_name) continue

      const targetEntry = entries.find((entry) => entry.name === event.entity_name)
      if (!targetEntry) continue

      if (event.kind === 'error') {
        states[targetEntry.id] = 'failed'
        continue
      }

      if (event.kind === 'finding' || event.kind === 'complete') {
        const lowered = event.message.toLowerCase()
        if (lowered.includes('imported') || lowered.includes('completed')) {
          states[targetEntry.id] = 'done'
          continue
        }
      }

      if (event.kind === 'detail' || event.kind === 'stage') {
        states[targetEntry.id] = 'importing'
      }
    }

    if (importState?.currentEntity) {
      const currentEntry = entries.find((entry) => entry.name === importState.currentEntity)
      if (currentEntry && states[currentEntry.id] !== 'done') {
        states[currentEntry.id] = 'importing'
      }
    }

    return states
  }

  const importStatesByEntry = getImportStatesByEntry()

  const getImportStatusBadge = (entryId: string) => {
    if (!isImporting) return null

    switch (importStatesByEntry[entryId]) {
      case 'importing':
        return (
          <Badge variant="secondary" className="gap-1 text-[10px]">
            <Loader2 className="h-3 w-3 animate-spin" />
            {t('autoConfig.importStatus.importing')}
          </Badge>
        )
      case 'done':
        return (
          <Badge variant="outline" className="gap-1 text-[10px] text-green-700">
            <CheckCircle2 className="h-3 w-3" />
            {t('autoConfig.importStatus.done')}
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="destructive" className="gap-1 text-[10px]">
            <AlertCircle className="h-3 w-3" />
            {t('autoConfig.importStatus.failed')}
          </Badge>
        )
      case 'queued':
      default:
        return (
          <Badge variant="outline" className="text-[10px] text-muted-foreground">
            {t('autoConfig.importStatus.queued')}
          </Badge>
        )
    }
  }

  const getReferenceKindLabel = (kind?: string) => {
    switch (kind) {
      case 'hierarchical':
        return t('reference.hierarchical')
      case 'spatial':
        return t('reference.spatial')
      case 'generic':
        return t('autoConfig.itemTypes.reference')
      default:
        return kind || t('autoConfig.itemTypes.reference')
    }
  }

  const getCompactSummary = (entry: ListEntry) => {
    switch (entry.type) {
      case 'dataset': {
        const format = entry.config.connector?.format?.toUpperCase() || 'CSV'
        const fields = detectedColumns[entry.name]?.length || 0
        const relatedCount = entry.summary?.referenced_by?.length || 0
        const parts = [format]
        if (fields > 0) {
          parts.push(t('autoConfig.list.fieldsCount', { count: fields }))
        }
        if (relatedCount > 0) {
          parts.push(
            t('autoConfig.list.supportsAggregationsCount', {
              count: relatedCount,
            })
          )
        }
        return parts.join(' • ')
      }
      case 'reference': {
        const parts = []
        if (entry.config.kind) {
          parts.push(getReferenceKindLabel(entry.config.kind))
        }
        if (entry.config.connector?.type === 'derived' && entry.config.connector?.source) {
          parts.push(
            t('autoConfig.list.derivedFrom', {
              source: entry.config.connector.source,
            })
          )
        }
        if (entry.config.connector?.type === 'file_multi_feature') {
          parts.push(
            t('autoConfig.list.sourceCount', {
              count: entry.config.connector.sources?.length || 0,
            })
          )
        }
        const associations = getReferenceAssociations(entry.name)
        if (associations.datasets.length > 0) {
          parts.push(
            t('autoConfig.list.linkedDatasetsCount', {
              count: associations.datasets.length,
            })
          )
        }
        if (associations.auxiliary.length > 0) {
          parts.push(
            t('autoConfig.list.linkedAuxiliaryCount', {
              count: associations.auxiliary.length,
            })
          )
        }
        return parts.join(' • ')
      }
      case 'auxiliary':
        return t('autoConfig.auxiliary.relationCompact', {
          target: entry.source.grouping,
          field: entry.source.relation.match_field,
          refField: entry.source.relation.ref_field,
        })
      case 'layer':
        return [entry.config.type, entry.config.format].filter(Boolean).join(' • ')
    }
  }

  const renderEntryDetails = (entry: ListEntry) => {
    const datasetLinks: Array<{ field: string; entity: string }> =
      entry.type === 'dataset'
        ? ((entry.config as { links?: Array<{ field: string; entity: string }> }).links ?? [])
        : []

    if (entry.type === 'auxiliary') {
      return (
        <div className="space-y-2 text-xs text-muted-foreground">
          <div className="truncate">{entry.source.data}</div>
          <div className="text-violet-600">
            {t('autoConfig.auxiliary.attachedTo', { target: entry.source.grouping })}
          </div>
          <div>
            {t('autoConfig.auxiliary.relation', {
              field: entry.source.relation.match_field,
              refField: entry.source.relation.ref_field,
            })}
          </div>
        </div>
      )
    }

    if (entry.type === 'layer') {
      return (
        <div className="space-y-2 text-xs text-muted-foreground">
          <div>{entry.config.path}</div>
          {entry.config.description && <div>{entry.config.description}</div>}
        </div>
      )
    }

    return (
        <div className="space-y-3">
        {entry.type === 'reference' && (
          <div className="rounded-md border border-green-200 bg-green-50/70 px-2 py-1 text-xs text-green-800 dark:border-green-900 dark:bg-green-950/30 dark:text-green-200">
            {t('autoConfig.reference.aggregationReady')}
          </div>
        )}
        <div className="space-y-1 text-xs text-muted-foreground">
          {entry.config.connector?.path && <div>{entry.config.connector.path}</div>}
          {'schema' in entry.config && entry.config.schema?.id_field && (
            <div className="flex items-center gap-1">
              <Key className="h-3.5 w-3.5" />
              {entry.config.schema.id_field}
            </div>
          )}
          {entry.type === 'reference' && entry.config.hierarchy?.levels && (
            <div className="flex items-center gap-1">
              <GitBranch className="h-3.5 w-3.5" />
              {entry.config.hierarchy.levels.join(' → ')}
            </div>
          )}
          {entry.type === 'reference' && entry.config.enrichment?.[0]?.enabled && (
            <div className="flex items-center gap-1 text-amber-600">
              <Sparkles className="h-3.5 w-3.5" />
              {t('autoConfig.reference.enrichmentEnabled')}
            </div>
          )}
          {entry.type === 'reference' && (() => {
            const associations = getReferenceAssociations(entry.name)
            return (
              <>
                {associations.datasets.length > 0 && (
                  <div>
                    {t('autoConfig.reference.linkedDatasets', {
                      datasets: associations.datasets.join(', '),
                    })}
                  </div>
                )}
                {associations.auxiliary.length > 0 && (
                  <div>
                    {t('autoConfig.reference.linkedAuxiliary', {
                      names: associations.auxiliary.map((source) => source.name).join(', '),
                    })}
                  </div>
                )}
              </>
            )
          })()}
          {entry.type === 'dataset' && datasetLinks.length > 0 && (
              <div className="space-y-1">
                {datasetLinks.map((link) => (
                  <div key={`${entry.name}-${link.field}-${link.entity}`} className="flex items-center gap-1">
                    <Link2 className="h-3.5 w-3.5" />
                    {link.field} → {link.entity}
                  </div>
                ))}
              </div>
            )}
        </div>
        {renderDecisionInsight(entry.name)}
        {editable && onReclassify && !isImporting && entry.type === 'dataset' && (
          <div className="border-t pt-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 px-2 text-xs"
              onClick={() => moveToReference(entry.name)}
            >
              <ArrowRightLeft className="h-3 w-3" />
              {t('autoConfig.actions.moveToReferences')}
            </Button>
          </div>
        )}
        {editable &&
          onReclassify &&
          !isImporting &&
          entry.type === 'reference' &&
          entry.config.connector?.type !== 'derived' &&
          entry.config.kind !== 'hierarchical' && (
            <div className="border-t pt-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 px-2 text-xs"
                onClick={() => moveToDataset(entry.name)}
              >
                <ArrowRightLeft className="h-3 w-3" />
                {t('autoConfig.actions.moveToDatasets')}
              </Button>
            </div>
          )}
      </div>
    )
  }

  return (
    <>
      <div className="space-y-4">
        {isImporting && (
          <Alert className="border-primary/20 bg-primary/5">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <AlertDescription className="space-y-1">
              <div className="font-medium text-foreground">
                {importState?.message || t('wizard.importingData')}
              </div>
              <div className="text-sm text-muted-foreground">
                {importState?.currentEntity
                  ? t('wizard.importingEntity', { entity: importState.currentEntity })
                  : t('wizard.processingEntities')}
                {typeof importState?.processedEntities === 'number' &&
                  typeof importState?.totalEntities === 'number' &&
                  importState.totalEntities > 0 && (
                    <span className="ml-1">
                      ({importState.processedEntities}/{importState.totalEntities})
                    </span>
                  )}
                {typeof importState?.progress === 'number' && importState.progress > 0 && (
                  <span className="ml-1">· {importState.progress}%</span>
                )}
              </div>
            </AlertDescription>
          </Alert>
        )}

        <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/20 p-3 text-sm">
          <Badge variant="outline">
            {t('autoConfig.sections.aggregationCandidates', { count: aggregationEntries.length })}
          </Badge>
          <Badge variant="outline">{t('autoConfig.summary.datasets')}: {datasetCount}</Badge>
          <Badge variant="outline">{t('autoConfig.summary.references')}: {referenceCount}</Badge>
          {auxiliarySources.length > 0 && (
            <Badge variant="outline">
              {t('autoConfig.sections.auxiliarySources', { count: auxiliarySources.length })}
            </Badge>
          )}
          {layerCount > 0 && (
            <Badge variant="outline">{t('autoConfig.summary.layers')}: {layerCount}</Badge>
          )}
          {reviewCount > 0 && (
            <Badge variant="secondary" className="border-amber-200 bg-amber-50 text-amber-800">
              {t('autoConfig.summary.itemsToReview', { count: reviewCount })}
            </Badge>
          )}
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

        {aggregationEntries.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
              <Network className="h-4 w-4 text-green-500" />
              <h4 className="text-sm font-semibold">
                {t('autoConfig.sections.aggregationCandidates', {
                  count: aggregationEntries.length,
                })}
              </h4>
            </div>
            {aggregationEntries.map((entry) => {
              const summary = entry.summary
              const isExpanded = expandedEntries[entry.id] ?? false

              return (
                <AutoConfigEntryCard
                  key={entry.id}
                  className="rounded-lg border border-green-200/70 bg-green-50/30 dark:border-green-950 dark:bg-green-950/10"
                  name={entry.name}
                  compactSummary={getCompactSummary(entry)}
                  isExpanded={isExpanded}
                  onToggle={() => toggleEntry(entry.id)}
                  onEdit={
                    editable && onReclassify && !isImporting
                      ? () => openRefEditor(entry.name, entry.config)
                      : undefined
                  }
                  icon={getTypeIcon(entry)}
                  badges={
                    <>
                      <Badge variant="outline" className="text-[10px]">
                        {getReferenceKindLabel(entry.config.kind)}
                      </Badge>
                      {getEntityStatusBadge(summary)}
                      {getImportStatusBadge(entry.id)}
                    </>
                  }
                  details={renderEntryDetails(entry)}
                />
              )
            })}
          </div>
        )}

        {supportingEntries.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
              <Database className="h-4 w-4 text-blue-500" />
              <h4 className="text-sm font-semibold">
                {t('autoConfig.sections.supportingSources', { count: supportingEntries.length })}
              </h4>
            </div>
            {supportingEntries.map((entry) => {
            const summary = 'summary' in entry ? entry.summary : undefined
            const isExpanded = expandedEntries[entry.id] ?? false
            const canEdit = editable && onReclassify && entry.type !== 'auxiliary'

            return (
              <AutoConfigEntryCard
                key={entry.id}
                className="rounded-lg border bg-background"
                name={entry.name}
                compactSummary={getCompactSummary(entry)}
                isExpanded={isExpanded}
                onToggle={() => toggleEntry(entry.id)}
                onEdit={
                  canEdit && !isImporting
                    ? entry.type === 'dataset'
                      ? () => openDatasetEditor(entry.name, entry.config)
                      : entry.type === 'layer'
                        ? () => openLayerEditor(entry.index, entry.config)
                        : undefined
                    : undefined
                }
                icon={getTypeIcon(entry)}
                badges={
                  <>
                    <Badge variant="outline" className="text-[10px]">
                      {getTypeLabel(entry)}
                    </Badge>
                    {getEntityStatusBadge(summary)}
                    {getImportStatusBadge(entry.id)}
                  </>
                }
                details={renderEntryDetails(entry)}
              />
            )
            })}
          </div>
        )}
      </div>

      <AutoConfigEditorSheet
        editingEntity={editingEntity}
        open={editingEntity !== null}
        title={sheetInfo.title}
        description={sheetInfo.description}
        availableReferences={availableReferences}
        availableDatasets={availableDatasets}
        onClose={closeEditor}
        onDatasetSave={handleDatasetUpdate}
        onReferenceSave={handleReferenceUpdate}
        onLayerSave={handleLayerUpdate}
      />
    </>
  )
}
