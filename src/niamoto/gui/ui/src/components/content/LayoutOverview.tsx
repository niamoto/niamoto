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
import { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PreviewPane, injectPreviewOverrides } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { usePreviewFrame, descriptorDeps } from '@/lib/preview/usePreviewFrame'
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
  EyeOff,
  Leaf,
  GripVertical,
  Navigation,
  List,
  MousePointerClick,
  PanelLeftClose,
  PanelLeftOpen,
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
}

function NavigationSidebar({ groupBy, navigationWidget }: NavigationSidebarProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const queryClient = useQueryClient()

  const referential = navigationWidget.params?.referential_data as string || groupBy

  const descriptor: PreviewDescriptor = useMemo(() => ({
    templateId: `${referential}_hierarchical_nav_widget`,
    groupBy,
    mode: 'full' as const,
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
        <PreviewPane descriptor={descriptor} className="w-full h-full" />
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

// Scaled preview for widgets that need a wider render (maps, info grids).
// Renders the iframe at a large native width then CSS-transforms it down.
const SCALED_DIMS: Record<string, { w: number; h: number }> = {
  interactive_map: { w: 800, h: 500 },
}

// Plugins that benefit from scale-down (content designed for full-page width)
const NEEDS_SCALE = new Set(Object.keys(SCALED_DIMS))

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
// nécessaire). On garde les dimensions natives (400x300 par défaut) pour
// profiter du scaling appliqué par `ScaledPreview`.
function injectMiniatureOverrides(html: string): string {
  return injectPreviewOverrides(html, {
    hideLeafletControls: true,
  })
}

function ScaledPreview({ descriptor, plugin }: { descriptor: PreviewDescriptor; plugin: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  const fullDescriptor = useMemo(
    () => ({ ...descriptor, mode: 'full' as const }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    descriptorDeps(descriptor),
  )
  const { html, loading } = usePreviewFrame(fullDescriptor, true)

  const dims = SCALED_DIMS[plugin] ?? { w: 800, h: 400 }

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const containerW = entries[0].contentRect.width
      if (containerW > 0) setScale(containerW / dims.w)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [dims.w])

  const scaledHeight = dims.h * scale

  return (
    <div ref={containerRef} className="w-full overflow-hidden" style={{ height: scaledHeight }}>
      {loading && (
        <div className="flex h-full items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      )}
      {html && !loading && (
        <iframe
          srcDoc={injectMiniatureOverrides(html)}
          title="Widget preview"
          sandbox="allow-scripts"
          style={{
            width: dims.w,
            height: dims.h,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
            border: 'none',
            pointerEvents: 'none',
          }}
        />
      )}
    </div>
  )
}

// Sortable Widget Card with preview and selection
interface SortableWidgetCardProps {
  id: string
  groupBy: string
  widget: WidgetLayout
  showPreview: boolean
  entityId: string | null
  isDragging: boolean
  onColspanToggle: () => void
  onSelect: () => void
}

function SortableWidgetCard({
  id,
  groupBy,
  widget,
  showPreview,
  entityId,
  isDragging,
  onColspanToggle,
  onSelect,
}: SortableWidgetCardProps) {
  const { t } = useTranslation(['widgets', 'common'])

  const descriptor: PreviewDescriptor = useMemo(() => ({
    templateId: widget.data_source,
    groupBy,
    entityId: entityId || undefined,
    mode: 'full' as const,
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

  const shouldRenderPreview = showPreview && !isDragging

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
        className="relative bg-background cursor-pointer"
        onClick={onSelect}
      >
        {shouldRenderPreview ? (
          <>
            {NEEDS_SCALE.has(widget.plugin) ? (
              <ScaledPreview descriptor={descriptor} plugin={widget.plugin} />
            ) : (
              <PreviewPane
                descriptor={descriptor}
                className={cn('w-full', CHART_HEIGHTS[widget.plugin] ?? DEFAULT_CHART_HEIGHT)}
                transformHtml={injectMiniatureOverrides}
              />
            )}
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
              {isDragging ? t('layout.moving') : t('layout.previewDisabled')}
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
  onSelectWidget: (widget: ConfiguredWidget) => void
  onLayoutSaved?: () => void
}

export function LayoutOverview({
  widgets: configuredWidgets,
  groupBy,
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
  const { data: representatives } = useQuery({
    queryKey: ['representatives', groupBy],
    queryFn: () => fetchRepresentatives(groupBy),
  })

  // Local state
  const [localWidgets, setLocalWidgets] = useState<WidgetLayout[]>([])
  const [hasChanges, setHasChanges] = useState(false)
  const [showPreviews, setShowPreviews] = useState(true)
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNavSidebar, setShowNavSidebar] = useState(false)

  // Reset entity selection when group changes
  useEffect(() => {
    setSelectedEntityId(null)
  }, [groupBy])

  // Set default entity when representatives are loaded
  useEffect(() => {
    if (!selectedEntityId && representatives) {
      const fallbackEntityId =
        representatives.default_entity?.id ?? representatives.entities[0]?.id ?? null
      if (fallbackEntityId) {
        setSelectedEntityId(fallbackEntityId)
      }
    }
  }, [representatives, selectedEntityId])

  // Initialize local widgets from layout data
  useEffect(() => {
    if (layout?.widgets) {
      setLocalWidgets([...layout.widgets])
      setHasChanges(false)
    }
  }, [layout])

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (updates: LayoutUpdateRequest) => saveLayout(groupBy, updates),
    onSuccess: () => {
      setHasChanges(false)
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

  const handleDragEnd = useCallback((event: DragEndEvent) => {
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
      setLocalWidgets([...navWidgets, ...updatedContent])
      setHasChanges(true)
    }
  }, [localWidgets])

  const handleDragCancel = useCallback(() => {
    setIsDragging(false)
    setActiveId(null)
  }, [])

  // Colspan toggle
  const handleColspanToggle = useCallback((widgetIndex: number) => {
    setLocalWidgets((prev) =>
      prev.map((w) =>
        w.index === widgetIndex
          ? { ...w, colspan: w.colspan === 1 ? 2 : 1 }
          : w
      )
    )
    setHasChanges(true)
  }, [])

  // Save handler
  const handleSave = useCallback(() => {
    const updates: WidgetLayoutUpdate[] = localWidgets.map((w) => ({
      index: w.index,
      title: w.title,
      description: w.description,
      colspan: w.colspan,
      order: w.order,
    }))
    saveMutation.mutate({ widgets: updates })
  }, [localWidgets, saveMutation])

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

  // Separate navigation from content widgets
  const navigationWidget = localWidgets.find((w) => w.is_navigation)
  const contentWidgets = localWidgets.filter((w) => !w.is_navigation)
  const widgetIds = contentWidgets.map((w) => `widget-${w.index}`)
  const activeWidget = activeId
    ? contentWidgets.find((w) => `widget-${w.index}` === activeId)
    : null

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
        {/* Left: nav toggle + widget count */}
        <div className="flex items-center gap-2">
          {navigationWidget && layout.navigation_widget && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setShowNavSidebar((v) => !v)}
              title={t('layout.toggleNavigation')}
            >
              {showNavSidebar ? (
                <PanelLeftClose className="h-4 w-4" />
              ) : (
                <PanelLeftOpen className="h-4 w-4" />
              )}
            </Button>
          )}
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

        {/* Center: preview toggle + entity selector */}
        <Button
          variant={showPreviews ? 'secondary' : 'outline'}
          size="sm"
          className="h-8"
          onClick={() => setShowPreviews(!showPreviews)}
        >
          {showPreviews ? (
            <Eye className="mr-1.5 h-3.5 w-3.5" />
          ) : (
            <EyeOff className="mr-1.5 h-3.5 w-3.5" />
          )}
          {t('layout.previews')}
        </Button>

        {showPreviews && representatives && representatives.entities.length > 0 && (
          <Select
            value={selectedEntityId || ''}
            onValueChange={setSelectedEntityId}
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

      {/* Main content area */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Navigation sidebar (collapsible) */}
        {navigationWidget && layout.navigation_widget && showNavSidebar && (
          <div className="w-56 p-3 shrink-0 border-r">
            <NavigationSidebar
              groupBy={groupBy}
              navigationWidget={layout.navigation_widget}
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
                      showPreview={showPreviews}
                      entityId={selectedEntityId}
                      isDragging={isDragging}
                      onColspanToggle={() => handleColspanToggle(widget.index)}
                      onSelect={() => handleSelectWidget(widget)}
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
