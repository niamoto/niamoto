import { useMemo, type ReactNode } from 'react'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { useQuery } from '@tanstack/react-query'
import { CSS } from '@dnd-kit/utilities'
import { useTranslation } from 'react-i18next'
import {
  ArrowDown,
  ArrowUp,
  GripVertical,
  Layers3,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
} from 'lucide-react'

import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

type FieldFormat = 'text' | 'number' | 'badge' | 'link' | 'image' | 'list'

interface EnrichmentFieldCatalogItem {
  source_id: string
  source_label: string
  path: string
  label: string
  format: FieldFormat
  section_hint: string
  sample_values: unknown[]
}

interface EnrichmentSourceCatalog {
  id: string
  label: string
  field_count: number
  fields: EnrichmentFieldCatalogItem[]
}

interface EnrichmentProfileItemConfig {
  label: string
  path: string
  source_id?: string
  format?: FieldFormat
}

interface EnrichmentProfileSectionConfig {
  id: string
  title: string
  source_id?: string
  collapsed?: boolean
  items: EnrichmentProfileItemConfig[]
}

interface EnrichmentPanelEditorProps {
  groupBy: string
  transformerParams: Record<string, unknown>
  widgetParams: Record<string, unknown>
  onTransformerChange: (next: Record<string, unknown>) => void
  onWidgetChange: (next: Record<string, unknown>) => void
}

const IMAGE_VARIANT_TOKENS = new Set([
  'big',
  'full',
  'hires',
  'icon',
  'large',
  'original',
  'preview',
  'small',
  'src',
  'thumb',
  'thumbnail',
  'tiny',
  'url',
])

const IMAGE_GENERIC_TOKENS = new Set([
  'gallery',
  'galleries',
  'image',
  'images',
  'illustration',
  'illustrations',
  'media',
  'photo',
  'photos',
  'picture',
  'pictures',
])

async function fetchEnrichmentCatalog(groupBy: string): Promise<EnrichmentSourceCatalog[]> {
  const response = await fetch(`/api/templates/${encodeURIComponent(groupBy)}/enrichment-catalog`)
  if (!response.ok) {
    throw new Error(`Failed to load enrichment catalog: ${response.statusText}`)
  }
  return response.json()
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function normalizeItem(
  value: unknown,
  fallbackSourceId?: string
): EnrichmentProfileItemConfig | null {
  if (!isRecord(value) || typeof value.path !== 'string') {
    return null
  }
  return {
    label: typeof value.label === 'string' ? value.label : value.path,
    path: value.path,
    source_id: typeof value.source_id === 'string' ? value.source_id : fallbackSourceId,
    format: typeof value.format === 'string' ? (value.format as FieldFormat) : undefined,
  }
}

function normalizeSections(value: unknown): EnrichmentProfileSectionConfig[] {
  if (!Array.isArray(value)) return []

  return value
    .map((entry, index): EnrichmentProfileSectionConfig | null => {
      if (!isRecord(entry)) return null
      const sourceId = typeof entry.source_id === 'string' ? entry.source_id : undefined
      return {
        id: typeof entry.id === 'string' ? entry.id : `section_${index + 1}`,
        title: typeof entry.title === 'string' ? entry.title : `Section ${index + 1}`,
        source_id: sourceId,
        collapsed: Boolean(entry.collapsed),
        items: Array.isArray(entry.items)
          ? entry.items
              .map((item) => normalizeItem(item, sourceId))
              .filter((item): item is EnrichmentProfileItemConfig => item !== null)
          : [],
      }
    })
    .filter((section): section is EnrichmentProfileSectionConfig => section !== null)
}

function normalizeSummary(value: unknown): EnrichmentProfileItemConfig[] {
  if (!Array.isArray(value)) return []
  return value
    .map((entry) => normalizeItem(entry))
    .filter((item): item is EnrichmentProfileItemConfig => item !== null)
}

function slugifySectionId(value: string, index: number): string {
  const slug = value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
  return slug || `section_${index + 1}`
}

function stringifySampleValue(value: unknown): string {
  if (value == null) return '-'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  if (Array.isArray(value)) {
    return value.map((item) => stringifySampleValue(item)).join(', ')
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function truncateText(value: string, maxLength = 96): string {
  if (value.length <= maxLength) return value
  return `${value.slice(0, maxLength - 1)}…`
}

function formatSampleScalar(value: unknown): string {
  if (value == null) return '-'
  if (typeof value === 'string') return truncateText(value, 48)
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return `${value.length} item(s)`
  if (isRecord(value)) return `${Object.keys(value).length} keys`
  return truncateText(String(value), 48)
}

function formatSamplePreview(value: unknown): string {
  if (value == null) return '-'

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return truncateText(String(value), 120)
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return '[]'
    const preview = value.slice(0, 3).map((item) => formatSampleScalar(item)).join(', ')
    return value.length > 3 ? `${preview} (+${value.length - 3})` : preview
  }

  if (isRecord(value)) {
    const entries = Object.entries(value)
    const preview = entries
      .slice(0, 3)
      .map(([key, entryValue]) => `${key}: ${formatSampleScalar(entryValue)}`)
      .join(', ')
    return entries.length > 3 ? `{ ${preview}, +${entries.length - 3} }` : `{ ${preview} }`
  }

  return truncateText(stringifySampleValue(value), 120)
}

function tokenizeFieldPath(path: string): string[] {
  return path
    .toLowerCase()
    .split(/[^a-z0-9]+/g)
    .filter(Boolean)
}

function humanizeTokens(tokens: string[]): string {
  return tokens
    .map((token) => {
      if (token === 'url') return 'URL'
      if (token === 'id') return 'ID'
      return token.charAt(0).toUpperCase() + token.slice(1)
    })
    .join(' ')
}

function moveItem<T>(items: T[], fromIndex: number, delta: number): T[] {
  const toIndex = fromIndex + delta
  if (toIndex < 0 || toIndex >= items.length) {
    return items
  }
  const nextItems = [...items]
  const [moved] = nextItems.splice(fromIndex, 1)
  nextItems.splice(toIndex, 0, moved)
  return nextItems
}

interface SortableEditorItemProps {
  id: string
  className?: string
  dragLabel: string
  children: ReactNode
}

function SortableEditorItem({
  id,
  className,
  dragLabel,
  children,
}: SortableEditorItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        className,
        isDragging && 'opacity-60 shadow-lg ring-1 ring-primary/30 bg-background'
      )}
    >
      <div className="flex items-start gap-3">
        <button
          type="button"
          className="mt-1 shrink-0 cursor-grab rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground active:cursor-grabbing"
          aria-label={dragLabel}
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  )
}

export function EnrichmentPanelEditor({
  groupBy,
  transformerParams,
  widgetParams,
  onTransformerChange,
  onWidgetChange,
}: EnrichmentPanelEditorProps) {
  const { t } = useTranslation('widgets')
  const { data: sourceCatalogs = [], isLoading, error } = useQuery({
    queryKey: ['template-enrichment-catalog', groupBy],
    queryFn: () => fetchEnrichmentCatalog(groupBy),
    enabled: Boolean(groupBy),
    staleTime: 30_000,
  })

  const summaryItems = useMemo(
    () => normalizeSummary(transformerParams.summary_items),
    [transformerParams.summary_items]
  )
  const sections = useMemo(
    () => normalizeSections(transformerParams.sections),
    [transformerParams.sections]
  )
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const firstSourceId = sourceCatalogs[0]?.id
  const summaryIds = useMemo(
    () =>
      summaryItems.map(
        (item, index) => `summary:${index}:${item.source_id ?? 'none'}:${item.path}`
      ),
    [summaryItems]
  )
  const sectionIds = useMemo(
    () => sections.map((section, index) => `section:${index}:${section.id}`),
    [sections]
  )

  const catalogById = useMemo(() => {
    return new Map(sourceCatalogs.map((catalog) => [catalog.id, catalog]))
  }, [sourceCatalogs])

  const getSourceFields = (sourceId?: string) => {
    if (!sourceId) return []
    return catalogById.get(sourceId)?.fields ?? []
  }

  const getFieldMetadata = (sourceId: string | undefined, path: string) => {
    return getSourceFields(sourceId).find((field) => field.path === path)
  }

  const getImageVariantLabel = (path: string) => {
    const tokens = tokenizeFieldPath(path)
    if (tokens.includes('original')) return t('enrichmentEditor.imageVariantOriginal')
    if (tokens.includes('hires')) return t('enrichmentEditor.imageVariantHighRes')
    if (tokens.includes('full')) return t('enrichmentEditor.imageVariantFull')
    if (tokens.includes('large') || tokens.includes('big')) {
      return t('enrichmentEditor.imageVariantLarge')
    }
    if (tokens.includes('thumbnail') || tokens.includes('thumb')) {
      return t('enrichmentEditor.imageVariantThumbnail')
    }
    if (tokens.includes('small')) return t('enrichmentEditor.imageVariantSmall')
    if (tokens.includes('preview')) return t('enrichmentEditor.imageVariantPreview')
    if (tokens.includes('icon')) return t('enrichmentEditor.imageVariantIcon')
    if (tokens.includes('tiny')) return t('enrichmentEditor.imageVariantTiny')
    return undefined
  }

  const getImageGroupKey = (path: string) => {
    if (path === '.') return '.'
    const tokens = tokenizeFieldPath(path).filter(
      (token) => token !== 'items' && !IMAGE_VARIANT_TOKENS.has(token)
    )
    return tokens.join('.') || path
  }

  const getImageBaseLabel = (field: Pick<EnrichmentFieldCatalogItem, 'path' | 'label'>) => {
    const baseTokens = tokenizeFieldPath(field.path).filter(
      (token) =>
        token !== 'items' &&
        !IMAGE_VARIANT_TOKENS.has(token) &&
        !IMAGE_GENERIC_TOKENS.has(token)
    )

    if (baseTokens.length > 0) {
      return humanizeTokens(baseTokens)
    }

    if (tokenizeFieldPath(field.path).includes('items')) {
      return t('enrichmentEditor.imageCollection')
    }

    return t('enrichmentEditor.imageField')
  }

  const getFieldVariantLabel = (
    field: Pick<EnrichmentFieldCatalogItem, 'path' | 'format'>
  ) => {
    if (field.format !== 'image' || field.path === '.') {
      return undefined
    }
    return getImageVariantLabel(field.path)
  }

  const getFieldDisplayLabel = (field: Pick<EnrichmentFieldCatalogItem, 'path' | 'format' | 'label'>) => {
    if (field.path === '.' && field.format === 'image') {
      return t('enrichmentEditor.sourceMedia')
    }
    if (field.path === '.' && field.format === 'link') {
      return t('enrichmentEditor.sourceLink')
    }
    if (field.path === '.') {
      return t('enrichmentEditor.sourceData')
    }
    if (field.format === 'image') {
      const variantLabel = getFieldVariantLabel(field)
      const baseLabel = getImageBaseLabel(field)
      return variantLabel
        ? t('enrichmentEditor.imageFieldWithVariant', {
            label: baseLabel,
            variant: variantLabel,
          })
        : baseLabel
    }
    return field.label
  }

  const getSiblingImageFields = (sourceId: string | undefined, path: string) => {
    if (!sourceId) return []
    const metadata = getFieldMetadata(sourceId, path)
    if (!metadata || metadata.format !== 'image' || path === '.') {
      return []
    }

    const groupKey = getImageGroupKey(path)
    return getSourceFields(sourceId).filter(
      (field) =>
        field.format === 'image' &&
        field.path !== '.' &&
        getImageGroupKey(field.path) === groupKey
    )
  }

  const getSourceSectionHints = (sourceId?: string) => {
    const groups = getSourceFields(sourceId).reduce<Record<string, EnrichmentFieldCatalogItem[]>>(
      (acc, field) => {
        const key = field.section_hint || t('enrichmentEditor.miscSection')
        acc[key] = acc[key] || []
        acc[key].push(field)
        return acc
      },
      {}
    )

    return Object.entries(groups).sort(([leftLabel], [rightLabel]) => leftLabel.localeCompare(rightLabel))
  }

  const updateTransformer = (
    nextSummary: EnrichmentProfileItemConfig[],
    nextSections: EnrichmentProfileSectionConfig[]
  ) => {
    onTransformerChange({
      ...transformerParams,
      source: typeof transformerParams.source === 'string' ? transformerParams.source : groupBy,
      summary_items: nextSummary,
      sections: nextSections.map((section, index) => ({
        ...section,
        id: slugifySectionId(section.id || section.title, index),
      })),
    })
  }

  const updateSummaryItems = (nextSummary: EnrichmentProfileItemConfig[]) => {
    updateTransformer(nextSummary, sections)
  }

  const updateSections = (nextSections: EnrichmentProfileSectionConfig[]) => {
    updateTransformer(summaryItems, nextSections)
  }

  const updateWidgetParam = (key: string, value: unknown) => {
    onWidgetChange({
      ...widgetParams,
      [key]: value,
    })
  }

  const createDefaultItem = (sourceId?: string): EnrichmentProfileItemConfig | null => {
    const resolvedSourceId = sourceId || firstSourceId
    if (!resolvedSourceId) return null
    const field = getSourceFields(resolvedSourceId)[0]
    if (!field) return null
    return {
      source_id: resolvedSourceId,
      path: field.path,
      label: getFieldDisplayLabel(field),
      format: field.format,
    }
  }

  const createDefaultSection = (): EnrichmentProfileSectionConfig => {
    return {
      id: `section_${sections.length + 1}`,
      title: sourceCatalogs[0]?.label || t('enrichmentEditor.defaultSection'),
      source_id: firstSourceId,
      collapsed: false,
      items: [],
    }
  }

  const createSectionFromHint = (
    sourceId: string,
    sectionHint: string
  ): EnrichmentProfileSectionConfig => {
    const sectionFields = getSourceFields(sourceId)
      .filter((field) => field.section_hint === sectionHint)
      .slice(0, 8)

    return {
      id: `${sourceId}_${sectionHint}_${sections.length + 1}`,
      title: sectionHint,
      source_id: sourceId,
      collapsed: ['Links', 'Media', 'Provenance'].includes(sectionHint),
      items: sectionFields.map((field) => ({
        source_id: sourceId,
        path: field.path,
        label: getFieldDisplayLabel(field),
        format: field.format,
      })),
    }
  }

  const renderFieldSelect = (
    sourceId: string | undefined,
    path: string,
    onPathChange: (nextPath: string) => void
  ) => {
    const fields = getSourceFields(sourceId)
    const groups = fields.reduce<Record<string, EnrichmentFieldCatalogItem[]>>((acc, field) => {
      const key = field.section_hint || t('enrichmentEditor.miscSection')
      acc[key] = acc[key] || []
      acc[key].push(field)
      return acc
    }, {})

    return (
      <Select
        value={path}
        onValueChange={onPathChange}
        disabled={!sourceId || fields.length === 0}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder={t('enrichmentEditor.selectField')} />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(groups).map(([sectionHint, groupedFields]) => (
            <SelectGroup key={sectionHint}>
              <SelectLabel>{sectionHint}</SelectLabel>
              {groupedFields.map((field) => (
                <SelectItem key={`${field.source_id}:${field.path}`} value={field.path}>
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate">{getFieldDisplayLabel(field)}</span>
                    {getFieldVariantLabel(field) && (
                      <span className="rounded-sm border border-border/60 bg-muted/50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                        {getFieldVariantLabel(field)}
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectGroup>
          ))}
        </SelectContent>
      </Select>
    )
  }

  const handleSummaryDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = summaryIds.indexOf(String(active.id))
    const newIndex = summaryIds.indexOf(String(over.id))
    if (oldIndex === -1 || newIndex === -1) return

    updateSummaryItems(arrayMove(summaryItems, oldIndex, newIndex))
  }

  const handleSectionsDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = sectionIds.indexOf(String(active.id))
    const newIndex = sectionIds.indexOf(String(over.id))
    if (oldIndex === -1 || newIndex === -1) return

    updateSections(arrayMove(sections, oldIndex, newIndex))
  }

  const handleSectionItemsDragEnd = (
    sectionId: string,
    itemIds: string[],
    event: DragEndEvent
  ) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = itemIds.indexOf(String(active.id))
    const newIndex = itemIds.indexOf(String(over.id))
    if (oldIndex === -1 || newIndex === -1) return

    updateSections(
      sections.map((section) =>
        section.id === sectionId
          ? {
              ...section,
              items: arrayMove(section.items, oldIndex, newIndex),
            }
          : section
      )
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-600" />
            {t('enrichmentEditor.title')}
          </CardTitle>
          <CardDescription>{t('enrichmentEditor.description')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="enrichment-summary-columns">
                {t('enrichmentEditor.summaryColumns')}
              </Label>
              <Select
                value={String(widgetParams.summary_columns ?? 3)}
                onValueChange={(value) => updateWidgetParam('summary_columns', Number(value))}
              >
                <SelectTrigger id="enrichment-summary-columns" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {['1', '2', '3', '4'].map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t('enrichmentEditor.sourceBadges')}</Label>
              <label className="flex min-h-10 items-start gap-2 rounded-md border px-3 py-2 text-sm leading-snug">
                <Checkbox
                  className="mt-0.5 shrink-0"
                  checked={Boolean(widgetParams.show_source_badges ?? true)}
                  onCheckedChange={(checked) =>
                    updateWidgetParam('show_source_badges', checked === true)
                  }
                />
                <span>{t('enrichmentEditor.sourceBadgesHint')}</span>
              </label>
            </div>
          </div>
        </CardContent>
      </Card>

      {sourceCatalogs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('enrichmentEditor.availableSourcesTitle')}</CardTitle>
            <CardDescription>{t('enrichmentEditor.availableSourcesDescription')}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {sourceCatalogs.map((catalog) => (
              <div
                key={catalog.id}
                className="rounded-lg border bg-muted/20 px-3 py-3 text-sm"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{catalog.label}</span>
                  <Badge variant="secondary">
                    {t('enrichmentEditor.fieldsCount', { count: catalog.field_count })}
                  </Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {getSourceSectionHints(catalog.id).map(([sectionHint, fields]) => (
                    <Button
                      key={`${catalog.id}-${sectionHint}`}
                      variant="outline"
                      size="sm"
                      className="h-8"
                      onClick={() =>
                        updateSections([...sections, createSectionFromHint(catalog.id, sectionHint)])
                      }
                    >
                      <Plus className="mr-1 h-3.5 w-3.5" />
                      {t('enrichmentEditor.addSectionFromHint', {
                        hint: sectionHint,
                        count: fields.length,
                      })}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{t('enrichmentEditor.summaryTitle')}</CardTitle>
          <CardDescription>{t('enrichmentEditor.summaryDescription')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            {t('enrichmentEditor.orderHint')} {t('enrichmentEditor.dragHint')}
          </p>

          {summaryItems.length === 0 && (
            <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              {t('enrichmentEditor.emptySummary')}
            </div>
          )}

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleSummaryDragEnd}
          >
            <SortableContext items={summaryIds} strategy={verticalListSortingStrategy}>
              <div className="space-y-3">
                {summaryItems.map((item, index) => {
                  const metadata = item.source_id
                    ? getFieldMetadata(item.source_id, item.path)
                    : undefined
                  const siblingImageFields = getSiblingImageFields(item.source_id, item.path)

                  return (
                    <SortableEditorItem
                      key={summaryIds[index]}
                      id={summaryIds[index]}
                      className="rounded-lg border p-3"
                      dragLabel={t('enrichmentEditor.dragSummaryItem')}
                    >
                      <div className="grid gap-3 md:grid-cols-[160px_minmax(0,1fr)_minmax(0,1fr)_auto]">
                        <div className="space-y-2">
                          <Label>{t('enrichmentEditor.source')}</Label>
                          <Select
                            value={item.source_id || ''}
                            onValueChange={(sourceId) => {
                              const nextItem = createDefaultItem(sourceId)
                              if (!nextItem) return
                              updateSummaryItems(
                                summaryItems.map((entry, itemIndex) =>
                                  itemIndex === index ? nextItem : entry
                                )
                              )
                            }}
                          >
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder={t('enrichmentEditor.selectSource')} />
                            </SelectTrigger>
                            <SelectContent>
                              {sourceCatalogs.map((catalog) => (
                                <SelectItem key={catalog.id} value={catalog.id}>
                                  {catalog.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>{t('enrichmentEditor.field')}</Label>
                          {renderFieldSelect(item.source_id, item.path, (nextPath) => {
                            const field = getFieldMetadata(item.source_id, nextPath)
                            updateSummaryItems(
                              summaryItems.map((entry, itemIndex) =>
                                itemIndex === index
                                  ? {
                                      ...entry,
                                      path: nextPath,
                                      label: field ? getFieldDisplayLabel(field) : entry.label,
                                      format: field?.format || entry.format,
                                    }
                                  : entry
                              )
                            )
                          })}
                        </div>
                        <div className="space-y-2">
                          <Label>{t('enrichmentEditor.label')}</Label>
                          <Input
                            value={item.label}
                            onChange={(event) =>
                              updateSummaryItems(
                                summaryItems.map((entry, itemIndex) =>
                                  itemIndex === index
                                    ? { ...entry, label: event.target.value }
                                    : entry
                                )
                              )
                            }
                          />
                        </div>
                        <div className="flex items-end">
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => updateSummaryItems(moveItem(summaryItems, index, -1))}
                              disabled={index === 0}
                              title={t('enrichmentEditor.moveUp')}
                            >
                              <ArrowUp className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => updateSummaryItems(moveItem(summaryItems, index, 1))}
                              disabled={index === summaryItems.length - 1}
                              title={t('enrichmentEditor.moveDown')}
                            >
                              <ArrowDown className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                updateSummaryItems(
                                  summaryItems.filter((_, itemIndex) => itemIndex !== index)
                                )
                              }
                              title={t('common:actions.delete')}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                      {metadata && (
                        <div className="mt-3 space-y-2 text-xs text-muted-foreground">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline">{metadata.format}</Badge>
                            <span>{metadata.section_hint}</span>
                            {getFieldVariantLabel(metadata) && (
                              <Badge variant="outline">
                                {t('enrichmentEditor.variantBadge', {
                                  variant: getFieldVariantLabel(metadata),
                                })}
                              </Badge>
                            )}
                          </div>
                          {siblingImageFields.length > 1 && (
                            <div className="rounded-md border border-dashed bg-muted/20 px-2 py-1.5">
                              <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                                {t('enrichmentEditor.availableVariants', {
                                  count: siblingImageFields.length,
                                })}
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {siblingImageFields.map((field) => (
                                  <Badge
                                    key={`${field.source_id}:${field.path}`}
                                    variant={field.path === item.path ? 'secondary' : 'outline'}
                                  >
                                    {getFieldDisplayLabel(field)}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                          {metadata.sample_values.length > 0 && (
                            <div
                              className="w-full max-w-full overflow-hidden text-ellipsis whitespace-nowrap rounded-md bg-muted/40 px-2 py-1 font-mono text-[11px]"
                              title={`${t('enrichmentEditor.sample')}: ${formatSamplePreview(metadata.sample_values[0])}`}
                            >
                              {t('enrichmentEditor.sample')}: {formatSamplePreview(metadata.sample_values[0])}
                            </div>
                          )}
                        </div>
                      )}
                    </SortableEditorItem>
                  )
                })}
              </div>
            </SortableContext>
          </DndContext>

          <Button
            variant="outline"
            onClick={() => {
              const nextItem = createDefaultItem()
              if (!nextItem) return
              updateSummaryItems([...summaryItems, nextItem])
            }}
            disabled={sourceCatalogs.length === 0}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t('enrichmentEditor.addSummaryItem')}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers3 className="h-4 w-4 text-sky-600" />
            {t('enrichmentEditor.sectionsTitle')}
          </CardTitle>
          <CardDescription>{t('enrichmentEditor.sectionsDescription')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            {t('enrichmentEditor.orderHint')} {t('enrichmentEditor.dragHint')}
          </p>

          {sections.length === 0 && (
            <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              {t('enrichmentEditor.emptySections')}
            </div>
          )}

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleSectionsDragEnd}
          >
            <SortableContext items={sectionIds} strategy={verticalListSortingStrategy}>
              <div className="space-y-3">
                {sections.map((section, sectionIndex) => {
                  const sectionItemIds = section.items.map(
                    (item, itemIndex) =>
                      `section-item:${section.id}:${itemIndex}:${item.path}:${item.source_id ?? 'none'}`
                  )

                  return (
                    <SortableEditorItem
                      key={sectionIds[sectionIndex]}
                      id={sectionIds[sectionIndex]}
                      className="rounded-xl border p-4"
                      dragLabel={t('enrichmentEditor.dragSection')}
                    >
                      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_120px_auto]">
                        <div className="space-y-2">
                          <Label>{t('enrichmentEditor.sectionTitle')}</Label>
                          <Input
                            value={section.title}
                            onChange={(event) =>
                              updateSections(
                                sections.map((entry, index) =>
                                  index === sectionIndex
                                    ? { ...entry, title: event.target.value }
                                    : entry
                                )
                              )
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>{t('enrichmentEditor.source')}</Label>
                          <Select
                            value={section.source_id || ''}
                            onValueChange={(sourceId) =>
                              updateSections(
                                sections.map((entry, index) =>
                                  index === sectionIndex
                                    ? { ...entry, source_id: sourceId, items: [] }
                                    : entry
                                )
                              )
                            }
                          >
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder={t('enrichmentEditor.selectSource')} />
                            </SelectTrigger>
                            <SelectContent>
                              {sourceCatalogs.map((catalog) => (
                                <SelectItem key={catalog.id} value={catalog.id}>
                                  {catalog.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>{t('enrichmentEditor.collapsed')}</Label>
                          <label className="flex min-h-10 items-start gap-2 rounded-md border px-3 py-2 text-sm leading-snug">
                            <Checkbox
                              className="mt-0.5 shrink-0"
                              checked={Boolean(section.collapsed)}
                              onCheckedChange={(checked) =>
                                updateSections(
                                  sections.map((entry, index) =>
                                    index === sectionIndex
                                      ? { ...entry, collapsed: checked === true }
                                      : entry
                                  )
                                )
                              }
                            />
                            <span>{t('enrichmentEditor.collapsedHint')}</span>
                          </label>
                        </div>
                        <div className="flex items-end">
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => updateSections(moveItem(sections, sectionIndex, -1))}
                              disabled={sectionIndex === 0}
                              title={t('enrichmentEditor.moveUp')}
                            >
                              <ArrowUp className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => updateSections(moveItem(sections, sectionIndex, 1))}
                              disabled={sectionIndex === sections.length - 1}
                              title={t('enrichmentEditor.moveDown')}
                            >
                              <ArrowDown className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                updateSections(sections.filter((_, index) => index !== sectionIndex))
                              }
                              title={t('common:actions.delete')}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 space-y-3">
                        {section.items.length === 0 && (
                          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                            {t('enrichmentEditor.emptySectionFields')}
                          </div>
                        )}

                        <DndContext
                          sensors={sensors}
                          collisionDetection={closestCenter}
                          onDragEnd={(event) =>
                            handleSectionItemsDragEnd(section.id, sectionItemIds, event)
                          }
                        >
                          <SortableContext
                            items={sectionItemIds}
                            strategy={verticalListSortingStrategy}
                          >
                            <div className="space-y-3">
                              {section.items.map((item, itemIndex) => {
                                const metadata = getFieldMetadata(section.source_id, item.path)
                                const siblingImageFields = getSiblingImageFields(
                                  section.source_id,
                                  item.path
                                )

                                return (
                                  <SortableEditorItem
                                    key={sectionItemIds[itemIndex]}
                                    id={sectionItemIds[itemIndex]}
                                    className="rounded-lg border bg-muted/20 p-3"
                                    dragLabel={t('enrichmentEditor.dragSectionField')}
                                  >
                                    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
                                      <div className="space-y-2">
                                        <Label>{t('enrichmentEditor.field')}</Label>
                                        {renderFieldSelect(section.source_id, item.path, (nextPath) => {
                                          const field = getFieldMetadata(section.source_id, nextPath)
                                          updateSections(
                                            sections.map((entry, index) =>
                                              index === sectionIndex
                                                ? {
                                                    ...entry,
                                                    items: entry.items.map(
                                                      (sectionItem, currentItemIndex) =>
                                                        currentItemIndex === itemIndex
                                                          ? {
                                                              ...sectionItem,
                                                              path: nextPath,
                                                              label:
                                                                field
                                                                  ? getFieldDisplayLabel(field)
                                                                  : sectionItem.label,
                                                              format:
                                                                field?.format || sectionItem.format,
                                                            }
                                                          : sectionItem
                                                    ),
                                                  }
                                                : entry
                                            )
                                          )
                                        })}
                                      </div>
                                      <div className="space-y-2">
                                        <Label>{t('enrichmentEditor.label')}</Label>
                                        <Input
                                          value={item.label}
                                          onChange={(event) =>
                                            updateSections(
                                              sections.map((entry, index) =>
                                                index === sectionIndex
                                                  ? {
                                                      ...entry,
                                                      items: entry.items.map(
                                                        (sectionItem, currentItemIndex) =>
                                                          currentItemIndex === itemIndex
                                                            ? {
                                                                ...sectionItem,
                                                                label: event.target.value,
                                                              }
                                                            : sectionItem
                                                      ),
                                                    }
                                                  : entry
                                              )
                                            )
                                          }
                                        />
                                      </div>
                                      <div className="flex items-end">
                                        <div className="flex items-center gap-1">
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() =>
                                              updateSections(
                                                sections.map((entry, index) =>
                                                  index === sectionIndex
                                                    ? {
                                                        ...entry,
                                                        items: moveItem(entry.items, itemIndex, -1),
                                                      }
                                                    : entry
                                                )
                                              )
                                            }
                                            disabled={itemIndex === 0}
                                            title={t('enrichmentEditor.moveUp')}
                                          >
                                            <ArrowUp className="h-4 w-4" />
                                          </Button>
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() =>
                                              updateSections(
                                                sections.map((entry, index) =>
                                                  index === sectionIndex
                                                    ? {
                                                        ...entry,
                                                        items: moveItem(entry.items, itemIndex, 1),
                                                      }
                                                    : entry
                                                )
                                              )
                                            }
                                            disabled={itemIndex === section.items.length - 1}
                                            title={t('enrichmentEditor.moveDown')}
                                          >
                                            <ArrowDown className="h-4 w-4" />
                                          </Button>
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() =>
                                              updateSections(
                                                sections.map((entry, index) =>
                                                  index === sectionIndex
                                                    ? {
                                                        ...entry,
                                                        items: entry.items.filter(
                                                          (_, currentItemIndex) =>
                                                            currentItemIndex !== itemIndex
                                                        ),
                                                      }
                                                    : entry
                                                )
                                              )
                                            }
                                            title={t('common:actions.delete')}
                                          >
                                            <Trash2 className="h-4 w-4" />
                                          </Button>
                                        </div>
                                      </div>
                                      {metadata && (
                                        <div className="md:col-span-3 space-y-2 text-xs text-muted-foreground">
                                          <div className="flex flex-wrap items-center gap-2">
                                            <Badge variant="outline">{metadata.format}</Badge>
                                            <span>{metadata.section_hint}</span>
                                            {getFieldVariantLabel(metadata) && (
                                              <Badge variant="outline">
                                                {t('enrichmentEditor.variantBadge', {
                                                  variant: getFieldVariantLabel(metadata),
                                                })}
                                              </Badge>
                                            )}
                                          </div>
                                          {siblingImageFields.length > 1 && (
                                            <div className="rounded-md border border-dashed bg-muted/20 px-2 py-1.5">
                                              <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                                                {t('enrichmentEditor.availableVariants', {
                                                  count: siblingImageFields.length,
                                                })}
                                              </div>
                                              <div className="flex flex-wrap gap-1.5">
                                                {siblingImageFields.map((field) => (
                                                  <Badge
                                                    key={`${field.source_id}:${field.path}`}
                                                    variant={
                                                      field.path === item.path
                                                        ? 'secondary'
                                                        : 'outline'
                                                    }
                                                  >
                                                    {getFieldDisplayLabel(field)}
                                                  </Badge>
                                                ))}
                                              </div>
                                            </div>
                                          )}
                                          {metadata.sample_values.length > 0 && (
                                            <div
                                              className="w-full max-w-full overflow-hidden text-ellipsis whitespace-nowrap rounded-md bg-muted/40 px-2 py-1 font-mono text-[11px]"
                                              title={`${t('enrichmentEditor.sample')}: ${formatSamplePreview(metadata.sample_values[0])}`}
                                            >
                                              {t('enrichmentEditor.sample')}:{' '}
                                              {formatSamplePreview(metadata.sample_values[0])}
                                            </div>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  </SortableEditorItem>
                                )
                              })}
                            </div>
                          </SortableContext>
                        </DndContext>

                        <Button
                          variant="outline"
                          onClick={() => {
                            const nextItem = createDefaultItem(section.source_id)
                            if (!nextItem) return
                            updateSections(
                              sections.map((entry, index) =>
                                index === sectionIndex
                                  ? { ...entry, items: [...entry.items, nextItem] }
                                  : entry
                              )
                            )
                          }}
                          disabled={
                            !section.source_id || getSourceFields(section.source_id).length === 0
                          }
                        >
                          <Plus className="mr-2 h-4 w-4" />
                          {t('enrichmentEditor.addSectionField')}
                        </Button>
                      </div>
                    </SortableEditorItem>
                  )
                })}
              </div>
            </SortableContext>
          </DndContext>

          <Button
            variant="outline"
            onClick={() => updateSections([...sections, createDefaultSection()])}
            disabled={sourceCatalogs.length === 0}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t('enrichmentEditor.addSection')}
          </Button>
        </CardContent>
      </Card>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('enrichmentEditor.loading')}
        </div>
      )}

      {!isLoading && sourceCatalogs.length === 0 && (
        <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
          {t('enrichmentEditor.emptyCatalog')}
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
          {t('enrichmentEditor.loadError')}
        </div>
      )}
    </div>
  )
}
