import type { ImportJobEvent } from '@/features/import/api/import'
import type {
  AutoConfigureProgressEvent,
  AutoConfigureResponse,
  DecisionSummary,
  ReviewLevel,
} from '@/features/import/api/smart-config'
import {
  getFilePreflightKey,
  type FilePreflightSummary,
} from '@/features/import/components/upload/filePreflight'

export type ImportInventoryStatus =
  | 'selected'
  | 'uploading'
  | 'queued'
  | 'checking'
  | 'analysed'
  | 'ready'
  | 'needs_attention'
  | 'not_configured'
  | 'importing'
  | 'imported'
  | 'failed'

export const importInventoryStatuses: ImportInventoryStatus[] = [
  'selected',
  'uploading',
  'queued',
  'checking',
  'analysed',
  'ready',
  'needs_attention',
  'not_configured',
  'importing',
  'imported',
  'failed',
]

export type ImportInventoryRole =
  | 'occurrences'
  | 'sites'
  | 'class_values'
  | 'spatial_layer'
  | 'raster_layer'
  | 'dataset'
  | 'reference'
  | 'auxiliary'
  | 'supporting_table'
  | 'unknown'

export type ImportInventoryFamily = 'csv' | 'vector' | 'raster' | 'zip' | 'other'

export type ImportInventoryQuality = 'good' | 'info' | 'review' | 'error'

export interface ImportInventoryDetail {
  label: string
  value: string
  tone?: ImportInventoryQuality
}

export interface ImportInventoryItem {
  id: string
  name: string
  sourceFileName?: string
  detectedEntityName?: string
  sourcePath?: string
  sourcePaths?: string[]
  family: ImportInventoryFamily
  role: ImportInventoryRole
  status: ImportInventoryStatus
  quality: ImportInventoryQuality
  primaryMessage?: string
  summary?: string
  details: ImportInventoryDetail[]
  badges: string[]
  tips: string[]
}

export interface UploadedInventoryFile {
  filename?: string
  name?: string
  path: string
  size?: number
  type?: string
}

export interface BuildImportInventoryInput {
  selectedFiles?: File[]
  filePreflight?: Record<string, FilePreflightSummary>
  uploadedFiles?: UploadedInventoryFile[]
  autoConfigEvents?: AutoConfigureProgressEvent[]
  autoConfigResult?: AutoConfigureResponse | null
  importEvents?: ImportJobEvent[]
  importing?: boolean
  selectedFilesUploading?: boolean
}

type RecordValue = Record<string, unknown>

function asRecord(value: unknown): RecordValue {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as RecordValue : {}
}

function extensionFromName(name: string) {
  return name.split('.').pop()?.toLowerCase() || ''
}

function baseName(name: string) {
  return name.split('/').pop()?.replace(/\.[^.]+$/, '').toLowerCase() || name.toLowerCase()
}

function familyFromName(name: string): ImportInventoryFamily {
  const extension = extensionFromName(name)
  if (extension === 'csv') return 'csv'
  if (extension === 'gpkg' || extension === 'geojson') return 'vector'
  if (extension === 'tif' || extension === 'tiff') return 'raster'
  if (extension === 'zip') return 'zip'
  return 'other'
}

function roleFromName(name: string, family: ImportInventoryFamily, badges: string[] = []): ImportInventoryRole {
  const normalized = baseName(name)
  if (badges.includes('classObject') || normalized.includes('class_object') || normalized.includes('stats')) {
    return 'class_values'
  }
  if (normalized.includes('occurrence') || normalized.includes('observation')) {
    return 'occurrences'
  }
  if (
    normalized.includes('plot') ||
    normalized.includes('site') ||
    normalized.includes('parcelle') ||
    normalized.includes('placette')
  ) {
    return 'sites'
  }
  if (family === 'vector') return 'spatial_layer'
  if (family === 'raster') return 'raster_layer'
  return family === 'csv' ? 'supporting_table' : 'unknown'
}

function roleFromResultEntry(
  type: 'dataset' | 'reference' | 'auxiliary' | 'layer',
  name: string,
  config: RecordValue,
  summary?: DecisionSummary
): ImportInventoryRole {
  const normalized = name.toLowerCase()
  if (normalized.includes('stats') || normalized.includes('class_object')) return 'class_values'
  if (normalized.includes('occurrence') || normalized.includes('observation')) return 'occurrences'
  if (normalized.includes('plot') || normalized.includes('site') || normalized.includes('parcelle')) return 'sites'

  if (type === 'layer') {
    return config.type === 'raster' ? 'raster_layer' : 'spatial_layer'
  }

  if (type === 'reference') {
    if (config.kind === 'spatial') return 'spatial_layer'
    if (config.kind === 'hierarchical') return 'reference'
    return 'reference'
  }

  if (type === 'auxiliary') return 'auxiliary'

  const finalType = summary?.final_entity_type
  if (finalType === 'reference') return 'reference'
  return type === 'dataset' ? 'dataset' : 'supporting_table'
}

function qualityFromPreflight(status?: FilePreflightSummary['status']): ImportInventoryQuality {
  if (status === 'review') return 'review'
  if (status === 'ready') return 'good'
  return 'info'
}

function statusFromPreflight(status?: FilePreflightSummary['status']): ImportInventoryStatus {
  if (status === 'review') return 'needs_attention'
  if (status === 'ready') return 'ready'
  return 'selected'
}

function qualityFromReview(level?: ReviewLevel, reviewRequired?: boolean): ImportInventoryQuality {
  if (reviewRequired || level === 'review') return 'review'
  if (level === 'notice' || level === 'info') return 'info'
  return 'good'
}

function statusFromReview(level?: ReviewLevel, reviewRequired?: boolean): ImportInventoryStatus {
  return reviewRequired || level === 'review' ? 'needs_attention' : 'analysed'
}

function reviewDetailLabel(level?: ReviewLevel): 'notice' | 'review' {
  return level === 'notice' ? 'notice' : 'review'
}

function reviewDetailTone(level?: ReviewLevel, quality?: ImportInventoryQuality) {
  if (level === 'notice') return 'info'
  return quality === 'review' ? 'review' : undefined
}

function detail(label: string, value: unknown, tone?: ImportInventoryQuality): ImportInventoryDetail | null {
  if (value === undefined || value === null || value === '') return null
  return { label, value: String(value), tone }
}

function compactPath(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}

function sourcePathFromConnector(config: RecordValue): string | undefined {
  const connector = asRecord(config.connector)
  if (typeof connector.path === 'string') return connector.path
  if (typeof connector.source === 'string') return connector.source
  const sources = Array.isArray(connector.sources) ? connector.sources : []
  const firstSource = asRecord(sources[0])
  return compactPath(firstSource.path)
}

function sourcePathsFromConnector(config: RecordValue): string[] {
  const connector = asRecord(config.connector)
  const paths = [
    compactPath(connector.path),
    compactPath(connector.source),
    ...(Array.isArray(connector.sources)
      ? connector.sources.map((source) => compactPath(asRecord(source).path))
      : []),
  ].filter(Boolean) as string[]
  return [...new Set(paths)]
}

function sourceFileName(value?: string): string | undefined {
  return value?.split('/').pop()
}

function normalizedPath(value?: string): string | undefined {
  return value?.replace(/\\/g, '/').toLowerCase()
}

function normalizedFileName(value?: string): string | undefined {
  return sourceFileName(value)?.toLowerCase()
}

function inventoryFileNames(item: ImportInventoryItem) {
  return [item.sourcePath, item.sourceFileName, item.name]
    .map(normalizedFileName)
    .filter(Boolean) as string[]
}

function sameSourceFile(left: ImportInventoryItem, right: ImportInventoryItem): boolean {
  const leftPath = normalizedPath(left.sourcePath)
  const rightPaths = [right.sourcePath, ...(right.sourcePaths ?? [])]
    .map(normalizedPath)
    .filter(Boolean) as string[]

  if (leftPath && rightPaths.length > 0) {
    return rightPaths.includes(leftPath)
  }

  const leftNames = inventoryFileNames(left)
  const rightNames = inventoryFileNames(right)

  return leftNames.some((leftName) => rightNames.includes(leftName))
}

function canReuseDetectedItem(item: ImportInventoryItem): boolean {
  return (item.sourcePaths?.length ?? 0) > 1
}

function withAnalysisFallback(item: ImportInventoryItem): ImportInventoryItem {
  return {
    ...item,
    status: 'not_configured',
    quality: 'info',
    primaryMessage: 'not_configured',
    details: [
      ...item.details,
      {
        label: 'analysis',
        value: 'No generated configuration uses this file.',
      },
    ],
  }
}

function buildSelectedItem(
  file: File,
  preflight?: FilePreflightSummary,
  uploading = false
): ImportInventoryItem {
  const family = familyFromName(file.name)
  const role = roleFromName(file.name, family, preflight?.badges)
  const quality = uploading ? 'info' : qualityFromPreflight(preflight?.status)
  const status = uploading ? 'uploading' : statusFromPreflight(preflight?.status)
  const extension = extensionFromName(file.name).toUpperCase() || 'FILE'
  const details = [
    detail('format', extension),
    detail('size', file.size > 0 ? `${Math.max(file.size / 1024, 0.1).toFixed(1)} KB` : undefined),
    detail('checks', preflight?.badges.join(', ')),
    detail('tips', preflight?.tips.join(', '), preflight?.tips.length ? 'review' : undefined),
  ].filter(Boolean) as ImportInventoryDetail[]

  return {
    id: `selected:${file.name}:${file.size}:${file.lastModified}`,
    name: file.name,
    sourceFileName: file.name,
    family,
    role,
    status,
    quality,
    primaryMessage: uploading ? 'uploading' : preflight ? preflight.status : 'selected',
    summary: extension,
    details,
    badges: preflight?.badges ?? [],
    tips: preflight?.tips ?? [],
  }
}

function buildUploadedItem(file: UploadedInventoryFile): ImportInventoryItem {
  const filename = file.filename || file.name || file.path.split('/').pop() || file.path
  const family = familyFromName(filename)
  const role = roleFromName(filename, family)
  return {
    id: `uploaded:${file.path || file.filename}`,
    name: filename,
    sourceFileName: filename,
    sourcePath: file.path,
    sourcePaths: [file.path],
    family,
    role,
    status: 'queued',
    quality: 'info',
    primaryMessage: 'queued',
    summary: file.type?.toUpperCase() || extensionFromName(filename).toUpperCase(),
    details: [
      detail('path', file.path),
      detail('size', typeof file.size === 'number' && file.size > 0 ? `${Math.max(file.size / 1024, 0.1).toFixed(1)} KB` : undefined),
    ].filter(Boolean) as ImportInventoryDetail[],
    badges: [],
    tips: [],
  }
}

function matchEventToItem(event: AutoConfigureProgressEvent, item: ImportInventoryItem) {
  const eventFile = event.file?.split('/').pop()
  if (eventFile && eventFile === item.sourceFileName) return true
  if (eventFile && baseName(eventFile) === baseName(item.sourceFileName || item.name)) return true
  if (event.entity && baseName(event.entity) === baseName(item.detectedEntityName || item.name)) return true
  return false
}

function applyAutoConfigEvents(
  items: ImportInventoryItem[],
  events: AutoConfigureProgressEvent[] = []
): ImportInventoryItem[] {
  if (items.length === 0 || events.length === 0) return items

  const next = items.map((item) => ({ ...item, details: [...item.details] }))

  for (const event of events) {
    if (event.kind === 'complete') {
      for (const item of next) {
        if (item.status !== 'needs_attention' && item.status !== 'failed') {
          item.status = 'analysed'
          item.quality = 'good'
          item.primaryMessage = event.message
        }
      }
      continue
    }

    const target = next.find((item) => matchEventToItem(event, item))
    if (!target) continue

    if (event.kind === 'error') {
      target.status = 'failed'
      target.quality = 'error'
      target.primaryMessage = event.message
    } else if (event.kind === 'finding' && event.message.toLowerCase().includes('review')) {
      target.status = 'needs_attention'
      target.quality = 'review'
      target.primaryMessage = event.message
    } else if (event.kind === 'finding') {
      target.status = 'analysed'
      target.quality = 'good'
      target.primaryMessage = event.message
    } else {
      target.status = 'checking'
      target.quality = 'info'
      target.primaryMessage = event.message
    }

    target.details.push({ label: 'event', value: event.message })
  }

  return next
}

function buildDatasetItem(
  name: string,
  config: RecordValue,
  summary?: DecisionSummary
): ImportInventoryItem {
  const sourcePath = sourcePathFromConnector(config)
  const sourcePaths = sourcePathsFromConnector(config)
  const family = familyFromName(sourcePath || name)
  const role = roleFromResultEntry('dataset', name, config, summary)
  const quality = qualityFromReview(summary?.review_level, summary?.review_required)
  const status = statusFromReview(summary?.review_level, summary?.review_required)
  const schema = asRecord(config.schema)
  const connector = asRecord(config.connector)
  const rowCount = summary?.row_count ?? summary?.analysis_snapshot?.row_count

  return {
    id: `dataset:${name}`,
    name,
    sourceFileName: sourcePath?.split('/').pop(),
    sourcePath,
    sourcePaths,
    family,
    role,
    status,
    quality,
    primaryMessage: summary?.review_reasons?.[0] || 'analysed',
    summary: [connector.format, rowCount ? `${rowCount} rows` : undefined].filter(Boolean).join(' • '),
    details: [
      detail('source', sourcePath),
      detail('id field', schema.id_field),
      detail('format', connector.format),
      detail('rows', rowCount),
      detail('decision', summary?.alignment),
      detail(
        reviewDetailLabel(summary?.review_level),
        summary?.review_reasons?.join(', '),
        reviewDetailTone(summary?.review_level, quality)
      ),
    ].filter(Boolean) as ImportInventoryDetail[],
    badges: summary?.review_reasons ?? [],
    tips: summary?.review_required ? summary.review_reasons ?? [] : [],
  }
}

function buildReferenceItem(
  name: string,
  config: RecordValue,
  summary?: DecisionSummary
): ImportInventoryItem {
  const sourcePath = sourcePathFromConnector(config)
  const sourcePaths = sourcePathsFromConnector(config)
  const family = familyFromName(sourcePath || name)
  const role = roleFromResultEntry('reference', name, config, summary)
  const quality = qualityFromReview(summary?.review_level, summary?.review_required)
  const status = statusFromReview(summary?.review_level, summary?.review_required)
  const hierarchy = asRecord(config.hierarchy)
  const levels = Array.isArray(hierarchy.levels) ? hierarchy.levels.join(' > ') : undefined
  const connector = asRecord(config.connector)

  return {
    id: `reference:${name}`,
    name,
    sourceFileName: sourcePath?.split('/').pop(),
    sourcePath,
    sourcePaths,
    family,
    role,
    status,
    quality,
    primaryMessage: summary?.review_reasons?.[0] || 'analysed',
    summary: [config.kind, connector.type === 'derived' ? 'derived' : connector.format].filter(Boolean).join(' • '),
    details: [
      detail('source', sourcePath),
      detail('kind', config.kind),
      detail('hierarchy', levels),
      detail('decision', summary?.alignment),
      detail(
        reviewDetailLabel(summary?.review_level),
        summary?.review_reasons?.join(', '),
        reviewDetailTone(summary?.review_level, quality)
      ),
    ].filter(Boolean) as ImportInventoryDetail[],
    badges: summary?.review_reasons ?? [],
    tips: summary?.review_required ? summary.review_reasons ?? [] : [],
  }
}

function buildAuxiliaryItem(source: unknown, index: number): ImportInventoryItem {
  const config = asRecord(source)
  const path = compactPath(config.data)
  const name = compactPath(config.name) || path?.split('/').pop()?.replace(/\.[^.]+$/, '') || `auxiliary-${index + 1}`
  const family = familyFromName(path || name)

  return {
    id: `auxiliary:${name}:${index}`,
    name,
    sourceFileName: path?.split('/').pop(),
    sourcePath: path,
    sourcePaths: path ? [path] : [],
    family,
    role: roleFromResultEntry('auxiliary', name, config),
    status: 'analysed',
    quality: 'info',
    primaryMessage: 'analysed',
    summary: compactPath(config.grouping),
    details: [
      detail('source', path),
      detail('attached to', config.grouping),
      detail('relation', compactPath(asRecord(config.relation).match_field)),
    ].filter(Boolean) as ImportInventoryDetail[],
    badges: [],
    tips: [],
  }
}

function buildLayerItem(layer: unknown, index: number): ImportInventoryItem {
  const config = asRecord(layer)
  const path = compactPath(config.path)
  const name = compactPath(config.name) || path?.split('/').pop()?.replace(/\.[^.]+$/, '') || `layer-${index + 1}`
  const family = familyFromName(path || name)

  return {
    id: `layer:${name}:${index}`,
    name,
    sourceFileName: path?.split('/').pop(),
    sourcePath: path,
    sourcePaths: path ? [path] : [],
    family,
    role: roleFromResultEntry('layer', name, config),
    status: 'analysed',
    quality: 'good',
    primaryMessage: 'analysed',
    summary: [config.type, config.format].filter(Boolean).join(' • '),
    details: [
      detail('source', path),
      detail('type', config.type),
      detail('format', config.format),
      detail('description', config.description),
    ].filter(Boolean) as ImportInventoryDetail[],
    badges: [],
    tips: [],
  }
}

function buildAutoConfigResultItems(autoConfigResult: AutoConfigureResponse): ImportInventoryItem[] {
  const decisionSummaries = autoConfigResult.decision_summary || {}
  const datasets = Object.entries(autoConfigResult.entities.datasets || {}).map(([name, config]) =>
    buildDatasetItem(name, asRecord(config), decisionSummaries[name])
  )
  const references = Object.entries(autoConfigResult.entities.references || {}).map(([name, config]) =>
    buildReferenceItem(name, asRecord(config), decisionSummaries[name])
  )
  const auxiliary = (autoConfigResult.auxiliary_sources || []).map(buildAuxiliaryItem)
  const layers = (autoConfigResult.entities.metadata?.layers || []).map(buildLayerItem)
  return [...datasets, ...references, ...auxiliary, ...layers]
}

function mergeDetectedResultIntoFile(
  fileItem: ImportInventoryItem,
  detectedItem: ImportInventoryItem
): ImportInventoryItem {
  return {
    ...fileItem,
    role: detectedItem.role,
    status: detectedItem.status,
    quality: detectedItem.quality,
    primaryMessage: detectedItem.primaryMessage,
    summary: detectedItem.summary || fileItem.summary,
    sourceFileName: fileItem.sourceFileName || detectedItem.sourceFileName,
    detectedEntityName: detectedItem.name,
    sourcePath: fileItem.sourcePath || detectedItem.sourcePath,
    sourcePaths: fileItem.sourcePaths,
    details: [
      { label: 'detected_as', value: detectedItem.name },
      ...fileItem.details,
      ...detectedItem.details.filter((entry) => entry.label !== 'source'),
    ],
    badges: detectedItem.badges,
    tips: detectedItem.tips,
  }
}

function applyImportEvents(
  items: ImportInventoryItem[],
  events: ImportJobEvent[] = [],
  importing = false
): ImportInventoryItem[] {
  const next = items.map((item) => ({
    ...item,
    status: importing && item.status !== 'not_configured'
      ? 'queued' as ImportInventoryStatus
      : item.status,
    quality: importing && item.status !== 'not_configured'
      ? 'info' as ImportInventoryQuality
      : item.quality,
    details: [...item.details],
  }))

  for (const event of events) {
    if (!event.entity_name) continue

    const targets = next.filter((item) =>
      item.name === event.entity_name
      || item.detectedEntityName === event.entity_name
      || baseName(item.name) === baseName(event.entity_name || '')
      || baseName(item.detectedEntityName || '') === baseName(event.entity_name || '')
    )
    if (targets.length === 0) continue

    for (const target of targets) {
      if (event.kind === 'error') {
        target.status = 'failed'
        target.quality = 'error'
        target.primaryMessage = event.message
      } else if (event.kind === 'finding' || event.kind === 'complete') {
        const lowered = event.message.toLowerCase()
        if (lowered.includes('imported') || lowered.includes('completed')) {
          target.status = 'imported'
          target.quality = 'good'
          target.primaryMessage = event.message
        }
      } else if (event.kind === 'detail' || event.kind === 'stage') {
        target.status = 'importing'
        target.quality = 'info'
        target.primaryMessage = event.message
      }
    }
  }

  return next
}

export function buildImportInventory({
  selectedFiles = [],
  filePreflight = {},
  uploadedFiles = [],
  autoConfigEvents = [],
  autoConfigResult,
  importEvents = [],
  importing = false,
  selectedFilesUploading = false,
}: BuildImportInventoryInput): ImportInventoryItem[] {
  if (autoConfigResult) {
    const detectedItems = buildAutoConfigResultItems(autoConfigResult)

    if (uploadedFiles.length > 0) {
      const usedDetectedIds = new Set<string>()
      const fileItems = uploadedFiles.map(buildUploadedItem).map((fileItem) => {
        const detectedItem = detectedItems.find(
          (candidate) => (canReuseDetectedItem(candidate) || !usedDetectedIds.has(candidate.id))
            && sameSourceFile(fileItem, candidate)
        )

        if (!detectedItem) {
          return withAnalysisFallback(fileItem)
        }

        if (!canReuseDetectedItem(detectedItem)) usedDetectedIds.add(detectedItem.id)
        return mergeDetectedResultIntoFile(fileItem, detectedItem)
      })

      return applyImportEvents(fileItems, importEvents, importing)
    }

    return applyImportEvents(detectedItems, importEvents, importing)
  }

  if (uploadedFiles.length > 0) {
    return applyAutoConfigEvents(uploadedFiles.map(buildUploadedItem), autoConfigEvents)
  }

  return selectedFiles.map((file) =>
    buildSelectedItem(file, filePreflight[getFilePreflightKey(file)], selectedFilesUploading)
  )
}

export function summarizeInventory(items: ImportInventoryItem[]) {
  return items.reduce(
    (summary, item) => {
      summary.total += 1
      summary[item.status] += 1
      if (item.quality === 'review' || item.quality === 'error') summary.attention += 1
      return summary
    },
    {
      total: 0,
      selected: 0,
      uploading: 0,
      queued: 0,
      checking: 0,
      analysed: 0,
      ready: 0,
      needs_attention: 0,
      not_configured: 0,
      importing: 0,
      imported: 0,
      failed: 0,
      attention: 0,
    }
  )
}
