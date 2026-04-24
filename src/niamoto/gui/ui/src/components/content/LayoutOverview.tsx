/**
 * LayoutOverview - Full layout editor with widget selection
 *
 * Shows when no widget is selected in the content tab.
 * Features:
 * - Navigation sidebar preview (left)
 * - Drag & drop reordering
 * - Iframe widget previews
 * - Colspan toggle (1 or 2 columns)
 * - Click to select widget for details
 * - Save changes to layout API
 */
import { useState, useCallback, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PreviewPane, injectPreviewOverrides } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { invalidateAllPreviews } from '@/lib/preview/usePreviewFrame'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  arrayMove,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  Loader2,
  Save,
  RefreshCw,
  AlertCircle,
  Settings2,
  Eye,
  Leaf,
  GripVertical,
  Navigation,
  List,
  MousePointerClick,
  RectangleHorizontal,
  Square,
} from 'lucide-react'
import { getPluginLabel } from '@/components/widgets/types'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ConfiguredWidget } from '@/components/widgets'
import {
  classifyCollectionsPerformanceTier,
  resolveCollectionsPreviewMode,
  type CollectionsPreviewPreference,
  type ResolvedCollectionsPreviewMode,
} from './previewPolicy'
import {
  measureCollectionsContentSwitch,
  recordCollectionsPerf,
} from '@/features/collections/performance/collectionsPerf'

// Types matching layout-editor/types.ts
interface WidgetLayout {
  index: number
  plugin: string
  title: string
  description?: string
  data_source: string
  colspan: 1 | 2
  order: number
  is_navigation: boolean
}

interface NavigationWidgetInfo {
  plugin: string
  title: string
  params: Record<string, unknown>
  is_hierarchical: boolean
}

interface LayoutResponse {
  group_by: string
  widgets: WidgetLayout[]
  navigation_widget: NavigationWidgetInfo | null
  total_widgets: number
}

interface WidgetLayoutUpdate {
  index: number
  title?: string
  description?: string
  colspan?: 1 | 2
  order: number
}

interface LayoutUpdateRequest {
  widgets: WidgetLayoutUpdate[]
}

interface RepresentativeEntity {
  id: string
  name: string
  count: number
}

interface RepresentativesResponse {
  group_by: string
  default_entity: RepresentativeEntity | null
  entities: RepresentativeEntity[]
  total: number
}

// API functions
async function fetchLayout(groupBy: string): Promise<LayoutResponse> {
  const response = await fetch(`/api/layout/${groupBy}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error ${response.status}`)
  }
  return response.json()
}

async function saveLayout(
  groupBy: string,
  updates: LayoutUpdateRequest
): Promise<{ success: boolean; message: string; widgets_updated: number }> {
  const response = await fetch(`/api/layout/${groupBy}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error ${response.status}`)
  }
  return response.json()
}

async function fetchRepresentatives(groupBy: string): Promise<RepresentativesResponse> {
  const response = await fetch(`/api/layout/${groupBy}/representatives`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error ${response.status}`)
  }
  return response.json()
}

// Navigation Sidebar Component
interface NavigationSidebarProps {
  groupBy: string
  navigationWidget: NavigationWidgetInfo
  previewMode: 'off' | 'thumbnail'
}

function NavigationSidebar({
  groupBy,
  navigationWidget,
  previewMode,
}: NavigationSidebarProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const queryClient = useQueryClient()

  const referential = navigationWidget.params?.referential_data as string || groupBy

  const descriptor: PreviewDescriptor = useMemo(() => ({
    templateId: `${referential}_hierarchical_nav_widget`,
    groupBy,
    mode: 'thumbnail' as const,
  }), [referential, groupBy])

  const handleRefresh = useCallback(() => {
    invalidateAllPreviews(queryClient)
  }, [queryClient])

  return (
    <div className="h-full flex flex-col rounded-lg border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 border-b shrink-0">
        {navigationWidget.is_hierarchical ? (
          <Navigation className="h-4 w-4 text-muted-foreground" />
        ) : (
          <List className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="flex-1 font-medium text-sm truncate">
          {navigationWidget.title}
        </span>
        <Badge variant="outline" className="text-xs shrink-0">
          {navigationWidget.is_hierarchical ? t('layout.hierarchical') : t('layout.list')}
        </Badge>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={handleRefresh}
        >
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
        </Button>
      </div>

      {/* Preview */}
      <div className="relative flex-1 min-h-0 bg-background">
        {previewMode === 'off' ? (
          <div className="flex h-full items-center justify-center bg-muted/20 text-center text-muted-foreground">
            <div className="space-y-1 px-3">
              <Badge variant="outline" className="text-xs">
                {t('layout.previewMode.off')}
              </Badge>
              <p className="text-xs">{t('layout.previewDisabled')}</p>
            </div>
          </div>
        ) : (
          <PreviewPane descriptor={descriptor} className="w-full h-full" />
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t bg-muted/30 shrink-0">
        <p className="text-xs text-muted-foreground">
          {t('layout.reference')}: <code className="font-mono">{referential}</code>
        </p>
      </div>
    </div>
  )
}

// Height hints for chart widgets rendered at native container width
const CHART_HEIGHTS: Record<string, string> = {
  bar_plot:      'h-72',
  donut_chart:   'h-72',
  radial_gauge:  'h-64',
  info_grid:     'h-64',
}
const DEFAULT_CHART_HEIGHT = 'h-64'

// Overrides spécifiques aux miniatures : masquer les contrôles Leaflet
// (ces miniatures sont en lecture seule, donc pas d'interaction zoom/pan
// nécessaire).
function injectMiniatureOverrides(html: string): string {
  return injectPreviewOverrides(html, {
    hideLeafletControls: true,
  })
}

// Sortable Widget Card with preview and selection
interface SortableWidgetCardProps {
  id: string
  groupBy: string
  widget: WidgetLayout
  previewMode: ResolvedCollectionsPreviewMode
  isPreviewFocused: boolean
  entityId: string | null
  isDragging: boolean
  onColspanToggle: () => void
  onSelect: () => void
  onPreviewFocus: () => void
}

function SortableWidgetCard({
  id,
  groupBy,
  widget,
  previewMode,
  isPreviewFocused,
  entityId,
  isDragging,
  onColspanToggle,
  onSelect,
  onPreviewFocus,
}: SortableWidgetCardProps) {
  const { t } = useTranslation(['widgets', 'common'])

  const descriptor: PreviewDescriptor = useMemo(() => ({
    templateId: widget.data_source,
    groupBy,
    entityId: entityId || undefined,
    mode: 'thumbnail' as const,
  }), [widget.data_source, groupBy, entityId])

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isThisDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  // Column span class
  const colSpanClass = widget.colspan === 1 ? 'col-span-6' : 'col-span-12'

  const shouldRenderPreview =
    !isDragging
    && (previewMode === 'thumbnail' || (previewMode === 'focused' && isPreviewFocused))

  const previewMessage = isDragging
    ? t('layout.moving')
    : previewMode === 'focused' && !isPreviewFocused
      ? t('layout.previewOnDemand')
      : t('layout.previewDisabled')

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        colSpanClass,
        'group rounded-lg border bg-card overflow-hidden transition-all',
        isThisDragging && 'opacity-50 shadow-lg ring-2 ring-primary'
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 border-b">
        {/* Drag handle */}
        <button
          className="touch-none cursor-grab active:cursor-grabbing p-1 rounded hover:bg-muted"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4 text-muted-foreground" />
        </button>

        {/* Title */}
        <span className="flex-1 font-medium text-sm truncate">{widget.title}</span>

        {/* Plugin badge */}
        <Badge variant="secondary" className="text-[10px] shrink-0">
          {getPluginLabel(widget.plugin)}
        </Badge>

        {/* Colspan toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={(e) => {
            e.stopPropagation()
            onColspanToggle()
          }}
          title={widget.colspan === 1 ? t('layout.columns.expandTo2') : t('layout.columns.reduceTo1')}
        >
          {widget.colspan === 1 ? (
            <RectangleHorizontal className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Square className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </div>

      {/* Preview area - clickable for selection */}
      <div
        className="relative bg-background cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
        onClick={onSelect}
        onMouseEnter={onPreviewFocus}
        onFocus={onPreviewFocus}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onSelect()
          }
        }}
        role="button"
        tabIndex={0}
      >
        {shouldRenderPreview ? (
          <>
            <PreviewPane
              descriptor={descriptor}
              className={cn('w-full', CHART_HEIGHTS[widget.plugin] ?? DEFAULT_CHART_HEIGHT)}
              transformHtml={injectMiniatureOverrides}
            />
            {/* Selection overlay on hover */}
            <div className="absolute inset-0 bg-primary/0 hover:bg-primary/10 transition-colors flex items-center justify-center opacity-0 hover:opacity-100">
              <div className="bg-background/90 px-3 py-1.5 rounded-full flex items-center gap-2 shadow-sm">
                <MousePointerClick className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium text-primary">{t('layout.seeDetails')}</span>
              </div>
            </div>
          </>
        ) : (
          <div className="flex h-32 flex-col items-center justify-center text-muted-foreground bg-muted/20">
            <Badge variant="outline" className="text-xs">
              {getPluginLabel(widget.plugin)}
            </Badge>
            <span className="mt-2 text-xs">
              {previewMessage}
            </span>
          </div>
        )}
      </div>

      {/* Description footer */}
      {widget.description && (
        <div className="px-3 py-2 border-t bg-muted/30">
          <p className="text-xs text-muted-foreground truncate">{widget.description}</p>
        </div>
      )}
    </div>
  )
}

// Main Layout Overview Component
interface LayoutOverviewProps {
  widgets: ConfiguredWidget[]
  groupBy: string
  previewPreference: CollectionsPreviewPreference
  onPreviewPreferenceChange: (preference: CollectionsPreviewPreference) => void
  hardwareConcurrency: number | null
  onSelectWidget: (widget: ConfiguredWidget) => void
  onLayoutSaved?: () => void
}

export function LayoutOverview({
  widgets: configuredWidgets,
  groupBy,
  previewPreference,
  onPreviewPreferenceChange,
  hardwareConcurrency,
  onSelectWidget,
  onLayoutSaved,
}: LayoutOverviewProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const queryClient = useQueryClient()

  // Fetch layout data
  const {
    data: layout,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['layout', groupBy],
    queryFn: () => fetchLayout(groupBy),
  })

  // Fetch representative entities
  const {
    data: representatives,
    error: representativesError,
    refetch: refetchRepresentatives,
  } = useQuery({
    queryKey: ['representatives', groupBy],
    queryFn: () => fetchRepresentatives(groupBy),
  })

  // Local state
  const [layoutDraftState, setLayoutDraftState] = useState<{
    layoutSignature: string | null
    widgets: WidgetLayout[]
    hasChanges: boolean
  }>({
    layoutSignature: null,
    widgets: [],
    hasChanges: false,
  })
  const [selectedEntityState, setSelectedEntityState] = useState<{
    groupBy: string
    entityId: string | null
  }>({
    groupBy,
    entityId: null,
  })
  const [isDragging, setIsDragging] = useState(false)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [focusedPreviewCardId, setFocusedPreviewCardId] = useState<string | null>(null)

  const layoutSignature = layout?.widgets ? JSON.stringify(layout.widgets) : null

  const localWidgets = useMemo(
    () =>
      layoutDraftState.layoutSignature === layoutSignature
        ? layoutDraftState.widgets
        : (layout?.widgets ? [...layout.widgets] : []),
    [layout, layoutDraftState.layoutSignature, layoutDraftState.widgets, layoutSignature],
  )
  const hasChanges =
    layoutDraftState.layoutSignature === layoutSignature
      ? layoutDraftState.hasChanges
      : false

  const contentWidgetCount = useMemo(
    () => localWidgets.filter((w) => !w.is_navigation).length,
    [localWidgets],
  )
  const performanceTier = useMemo(
    () =>
      classifyCollectionsPerformanceTier({
        widgetCount: contentWidgetCount,
        hardwareConcurrency,
      }),
    [contentWidgetCount, hardwareConcurrency],
  )
  const resolvedPreviewMode = useMemo(
    () =>
      resolveCollectionsPreviewMode({
        preference: previewPreference,
        widgetCount: contentWidgetCount,
        hardwareConcurrency,
        isDragging,
      }),
    [contentWidgetCount, hardwareConcurrency, isDragging, previewPreference],
  )
  const navigationPreviewMode = resolvedPreviewMode === 'thumbnail' ? 'thumbnail' : 'off'

  const selectedEntityId = useMemo(() => {
    const explicitEntityId =
      selectedEntityState.groupBy === groupBy ? selectedEntityState.entityId : null

    if (explicitEntityId) {
      return explicitEntityId
    }

    return representatives?.default_entity?.id ?? representatives?.entities[0]?.id ?? null
  }, [groupBy, representatives, selectedEntityState.entityId, selectedEntityState.groupBy])

  const updateLocalWidgets = (
    updater: WidgetLayout[] | ((widgets: WidgetLayout[]) => WidgetLayout[]),
    nextHasChanges: boolean,
  ) => {
    if (!layoutSignature) {
      return
    }

    setLayoutDraftState((prev) => {
      const baseWidgets =
        prev.layoutSignature === layoutSignature
          ? prev.widgets
          : (layout?.widgets ? [...layout.widgets] : [])
      const widgets =
        typeof updater === 'function'
          ? updater(baseWidgets)
          : updater

      return {
        layoutSignature,
        widgets,
        hasChanges: nextHasChanges,
      }
    })
  }

  const handleSelectedEntityChange = useCallback((entityId: string) => {
    setSelectedEntityState((current) => {
      if (current.groupBy === groupBy && current.entityId === entityId) {
        return current
      }

      return {
        groupBy,
        entityId,
      }
    })
  }, [groupBy])

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (updates: LayoutUpdateRequest) => saveLayout(groupBy, updates),
    onSuccess: () => {
      setLayoutDraftState((prev) => ({ ...prev, hasChanges: false }))
      queryClient.invalidateQueries({ queryKey: ['layout', groupBy] })
      queryClient.invalidateQueries({ queryKey: ['widget-config', groupBy] })
      // Notify parent to refresh widget list
      onLayoutSaved?.()
    },
  })

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 10,
        delay: 100,
        tolerance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Drag handlers
  const handleDragStart = useCallback((event: DragStartEvent) => {
    setIsDragging(true)
    setActiveId(event.active.id as string)
  }, [])

  const handleDragEnd = (event: DragEndEvent) => {
    setIsDragging(false)
    setActiveId(null)

    const { active, over } = event
    if (!over || active.id === over.id) return

    const contentWidgets = localWidgets.filter((w) => !w.is_navigation)
    const oldIndex = contentWidgets.findIndex((w) => `widget-${w.index}` === active.id)
    const newIndex = contentWidgets.findIndex((w) => `widget-${w.index}` === over.id)

    if (oldIndex !== -1 && newIndex !== -1) {
      const newOrder = arrayMove(contentWidgets, oldIndex, newIndex)
      const updatedContent = newOrder.map((widget, idx) => ({
        ...widget,
        order: idx,
      }))
      const navWidgets = localWidgets.filter((w) => w.is_navigation)
      updateLocalWidgets([...navWidgets, ...updatedContent], true)
    }
  }

  const handleDragCancel = useCallback(() => {
    setIsDragging(false)
    setActiveId(null)
  }, [])

  // Colspan toggle
  const handleColspanToggle = (widgetIndex: number) => {
    updateLocalWidgets((prev) =>
      prev.map((w) =>
        w.index === widgetIndex
          ? { ...w, colspan: w.colspan === 1 ? 2 : 1 }
          : w
      )
    , true)
  }

  // Save handler
  const handleSave = () => {
    const updates: WidgetLayoutUpdate[] = localWidgets.map((w) => ({
      index: w.index,
      title: w.title,
      description: w.description,
      colspan: w.colspan,
      order: w.order,
    }))
    saveMutation.mutate({ widgets: updates })
  }

  // Handle widget selection - find the matching ConfiguredWidget
  const handleSelectWidget = useCallback((layoutWidget: WidgetLayout) => {
    // Try to find matching ConfiguredWidget by data_source or title
    const configuredWidget = configuredWidgets.find(
      (w) => w.dataSource === layoutWidget.data_source || w.title === layoutWidget.title
    )
    if (configuredWidget) {
      onSelectWidget(configuredWidget)
    }
  }, [configuredWidgets, onSelectWidget])

  const handlePreviewFocus = useCallback((cardId: string) => {
    setFocusedPreviewCardId((current) => current === cardId ? current : cardId)
  }, [])

  const navigationWidget = localWidgets.find((w) => w.is_navigation)
  const contentWidgets = localWidgets.filter((w) => !w.is_navigation)
  const widgetIds = contentWidgets.map((w) => `widget-${w.index}`)
  const activeWidget = activeId
    ? contentWidgets.find((w) => `widget-${w.index}` === activeId)
    : null
  const effectiveFocusedPreviewCardId =
    focusedPreviewCardId ?? (resolvedPreviewMode === 'focused' && contentWidgets[0]
      ? `widget-${contentWidgets[0].index}`
      : null)
  const activePreviewCount = resolvedPreviewMode === 'thumbnail'
    ? contentWidgets.length
    : resolvedPreviewMode === 'focused' && effectiveFocusedPreviewCardId
      ? 1
      : 0

  useEffect(() => {
    const durationMs = measureCollectionsContentSwitch(groupBy, {
      widgetCount: contentWidgets.length,
      previewMode: resolvedPreviewMode,
      performanceTier,
    })
    recordCollectionsPerf('collections.layout.state', {
      activePreviewCount,
      durationMs,
      groupBy,
      performanceTier,
      previewMode: resolvedPreviewMode,
      widgetCount: contentWidgets.length,
    })
  }, [
    activePreviewCount,
    contentWidgets.length,
    groupBy,
    performanceTier,
    resolvedPreviewMode,
  ])

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="mt-4 text-sm text-muted-foreground">
          {t('layout.loadingLayout')}
        </p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <AlertCircle className="h-12 w-12 text-destructive/50" />
        <h3 className="mt-4 font-medium">{t('layout.loadError')}</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {error instanceof Error ? error.message : t('layout.unknownError')}
        </p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          {t('common:actions.retry')}
        </Button>
      </div>
    )
  }

  // Empty state
  if (!layout || layout.widgets.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Settings2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="font-medium text-lg">{t('layout.noWidgets')}</h3>
        <p className="mt-2 text-sm text-muted-foreground text-center max-w-[300px]">
          {t('layout.noWidgetsHintAdd')}
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
        {/* Left: widget count */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {t('layout.widgetsConfigured', { count: layout.total_widgets })}
          </span>
          {hasChanges && (
            <Badge variant="outline" className="text-warning border-warning text-xs">
              {t('layout.unsavedChanges')}
            </Badge>
          )}
        </div>

        <div className="flex-1" />

        {/* Center: preview policy + entity selector */}
        <Select
          value={previewPreference}
          onValueChange={(value) =>
            onPreviewPreferenceChange(value as CollectionsPreviewPreference)
          }
        >
          <SelectTrigger className="w-[190px] h-8">
            <Eye className="mr-2 h-3.5 w-3.5 text-muted-foreground" />
            <SelectValue placeholder={t('layout.previews')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">{t('layout.previewMode.auto')}</SelectItem>
            <SelectItem value="thumbnail">{t('layout.previewMode.thumbnail')}</SelectItem>
            <SelectItem value="focused">{t('layout.previewMode.focused')}</SelectItem>
            <SelectItem value="off">{t('layout.previewMode.off')}</SelectItem>
          </SelectContent>
        </Select>

        {previewPreference === 'auto' && performanceTier === 'low' && (
          <Badge variant="outline" className="text-xs">
            {t('layout.performanceModeLow')}
          </Badge>
        )}

        {resolvedPreviewMode !== 'off' && representatives && representatives.entities.length > 0 && (
          <Select
            value={selectedEntityId || ''}
            onValueChange={handleSelectedEntityChange}
          >
            <SelectTrigger className="w-[180px] h-8">
              <Leaf className="mr-2 h-3.5 w-3.5 text-muted-foreground" />
              <SelectValue placeholder={t('layout.entity')} />
            </SelectTrigger>
            <SelectContent>
              {representatives.entities.map((entity) => (
                <SelectItem key={entity.id} value={entity.id}>
                  {entity.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <div className="mx-1 h-4 w-px bg-border" />

        {/* Right: refresh + save */}
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => {
            refetch()
            void refetchRepresentatives()
            invalidateAllPreviews(queryClient)
          }}
          disabled={saveMutation.isPending}
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>

        <Button
          size="sm"
          className="h-8"
          onClick={handleSave}
          disabled={!hasChanges || saveMutation.isPending}
        >
          {saveMutation.isPending ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Save className="mr-1.5 h-3.5 w-3.5" />
          )}
          {t('layout.save')}
        </Button>
      </div>

      {/* Success/Error messages */}
      {saveMutation.isSuccess && (
        <div className="mx-4 mt-2 bg-success/10 text-success border border-success/30 px-3 py-2 rounded-lg text-sm">
          {t('layout.saveSuccess')}
        </div>
      )}
      {saveMutation.error && (
        <div className="mx-4 mt-2 bg-destructive/10 text-destructive border border-destructive/30 px-3 py-2 rounded-lg text-sm">
          {saveMutation.error instanceof Error
            ? saveMutation.error.message
            : t('layout.saveError')}
        </div>
      )}
      {resolvedPreviewMode !== 'off' && representativesError && (
        <div className="mx-4 mt-2 bg-warning/10 text-warning border border-warning/30 px-3 py-2 rounded-lg text-sm">
          {t('layout.previewEntitiesUnavailable')}
        </div>
      )}

      {/* Main content area */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Navigation sidebar */}
        {navigationWidget && layout.navigation_widget && (
          <div className="w-56 p-3 shrink-0 border-r">
            <NavigationSidebar
              groupBy={groupBy}
              navigationWidget={layout.navigation_widget}
              previewMode={navigationPreviewMode}
            />
          </div>
        )}

        {/* Widget grid */}
        <ScrollArea className="flex-1">
          <div className="p-4">
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
              onDragCancel={handleDragCancel}
            >
              <SortableContext items={widgetIds} strategy={rectSortingStrategy}>
                <div className="grid grid-cols-12 gap-4 auto-rows-min">
                  {contentWidgets.map((widget) => (
                    <SortableWidgetCard
                      key={`widget-${widget.index}`}
                      id={`widget-${widget.index}`}
                      groupBy={groupBy}
                      widget={widget}
                      previewMode={resolvedPreviewMode}
                      isPreviewFocused={effectiveFocusedPreviewCardId === `widget-${widget.index}`}
                      entityId={selectedEntityId}
                      isDragging={isDragging}
                      onColspanToggle={() => handleColspanToggle(widget.index)}
                      onSelect={() => handleSelectWidget(widget)}
                      onPreviewFocus={() => handlePreviewFocus(`widget-${widget.index}`)}
                    />
                  ))}
                </div>
              </SortableContext>

              {/* Drag overlay */}
              <DragOverlay>
                {activeWidget ? (
                  <div
                    className={cn(
                      'rounded-lg border bg-card shadow-lg opacity-90',
                      activeWidget.colspan === 1 ? 'w-[calc(50%-0.5rem)]' : 'w-full'
                    )}
                  >
                    <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 border-b">
                      <span className="font-medium text-sm">{activeWidget.title}</span>
                    </div>
                    <div className="h-16 bg-muted/30 flex items-center justify-center text-muted-foreground text-sm">
                      {getPluginLabel(activeWidget.plugin)}
                    </div>
                  </div>
                ) : null}
              </DragOverlay>
            </DndContext>
          </div>
        </ScrollArea>
      </div>

      {/* Legend footer */}
      <div className="px-4 py-2 border-t flex items-center gap-4 text-xs text-muted-foreground shrink-0">
        <div className="flex items-center gap-1">
          <Square className="h-3.5 w-3.5" />
          <span>{t('layout.columns.one')}</span>
        </div>
        <div className="flex items-center gap-1">
          <RectangleHorizontal className="h-3.5 w-3.5" />
          <span>{t('layout.columns.two')}</span>
        </div>
        <span className="text-muted-foreground/50">|</span>
        <div className="flex items-center gap-1">
          <GripVertical className="h-3.5 w-3.5" />
          <span>{t('layout.dragDrop')}</span>
        </div>
      </div>
    </div>
  )
}
