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
import { useState, useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  Columns,
  Columns2,
  Eye,
  EyeOff,
  Leaf,
  GripVertical,
  Navigation,
  List,
  MousePointerClick,
} from 'lucide-react'
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
  refreshKey?: number
}

function NavigationSidebar({ groupBy, navigationWidget, refreshKey = 0 }: NavigationSidebarProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const [isLoading, setIsLoading] = useState(true)
  const [localRefreshKey, setLocalRefreshKey] = useState(0)

  // Combined key for iframe refresh
  const iframeKey = `${refreshKey}-${localRefreshKey}`

  const handleIframeLoad = useCallback(() => {
    setIsLoading(false)
  }, [])

  const handleRefresh = useCallback(() => {
    setIsLoading(true)
    setLocalRefreshKey((k) => k + 1)
  }, [])

  const referential = navigationWidget.params?.referential_data as string || groupBy
  const previewUrl = `/api/templates/preview/${referential}_hierarchical_nav_widget`

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
          disabled={isLoading}
        >
          <RefreshCw
            className={cn(
              'h-4 w-4 text-muted-foreground',
              isLoading && 'animate-spin'
            )}
          />
        </Button>
      </div>

      {/* Preview iframe */}
      <div className="relative flex-1 min-h-0 bg-background">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}
        <iframe
          key={iframeKey}
          src={previewUrl}
          className="w-full h-full border-0"
          onLoad={handleIframeLoad}
          title={navigationWidget.title}
        />
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

// Sortable Widget Card with iframe preview and selection
interface SortableWidgetCardProps {
  id: string
  groupBy: string
  widget: WidgetLayout
  showPreview: boolean
  entityId: string | null
  isDragging: boolean
  onColspanToggle: () => void
  onSelect: () => void
  refreshKey?: number
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
  refreshKey = 0,
}: SortableWidgetCardProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const [isLoading, setIsLoading] = useState(true)
  const [localRefreshKey, setLocalRefreshKey] = useState(0)
  const [isVisible, setIsVisible] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)

  // Combined key for iframe refresh
  const iframeKey = `${refreshKey}-${localRefreshKey}`

  // Track previous values to avoid unnecessary reloads
  const prevColspanRef = useRef(widget.colspan)
  const prevEntityIdRef = useRef(entityId)
  const prevShowPreviewRef = useRef(showPreview)

  // Lazy loading: only load preview when card is visible in viewport
  useEffect(() => {
    const element = cardRef.current
    if (!element) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        // Once visible, stay visible (don't unload when scrolling away)
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      {
        root: null, // viewport
        rootMargin: '100px', // Start loading slightly before visible
        threshold: 0,
      }
    )

    observer.observe(element)
    return () => observer.disconnect()
  }, [])

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

  // Handle iframe load
  const handleIframeLoad = useCallback(() => {
    setIsLoading(false)
  }, [])

  // Only reload preview when specific conditions change
  useEffect(() => {
    const colspanChanged = prevColspanRef.current !== widget.colspan
    const entityIdChanged = prevEntityIdRef.current !== entityId
    const previewTurnedOn = !prevShowPreviewRef.current && showPreview

    // Update refs
    prevColspanRef.current = widget.colspan
    prevEntityIdRef.current = entityId
    prevShowPreviewRef.current = showPreview

    // Only reload if something actually changed that requires reload
    if (showPreview && (colspanChanged || entityIdChanged || previewTurnedOn)) {
      setIsLoading(true)
      setLocalRefreshKey((k) => k + 1)
    }
  }, [widget.colspan, entityId, showPreview])

  // Preview URL
  const previewUrl = entityId
    ? `/api/layout/${groupBy}/preview/${widget.index}?entity_id=${entityId}`
    : `/api/layout/${groupBy}/preview/${widget.index}`

  // Column span class
  const colSpanClass = widget.colspan === 1 ? 'col-span-6' : 'col-span-12'

  // Height class based on widget type
  const getHeightClass = () => {
    switch (widget.plugin) {
      case 'interactive_map':
        return 'h-80'
      case 'bar_plot':
        return 'h-64'
      case 'donut_chart':
        return 'h-56'
      case 'radial_gauge':
        return 'h-64'
      default:
        return 'h-56'
    }
  }

  // Combine refs for both sortable and intersection observer
  const combinedRef = useCallback(
    (node: HTMLDivElement | null) => {
      setNodeRef(node)
      ;(cardRef as React.MutableRefObject<HTMLDivElement | null>).current = node
    },
    [setNodeRef]
  )

  return (
    <div
      ref={combinedRef}
      style={style}
      className={cn(
        colSpanClass,
        'group rounded-lg border bg-card overflow-hidden transition-all',
        isThisDragging && 'opacity-50 shadow-lg ring-2 ring-primary'
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 border-b">
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
        <Badge variant="secondary" className="text-xs shrink-0">
          {widget.plugin}
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
            <Columns2 className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Columns className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </div>

      {/* Preview area - clickable for selection */}
      <div
        className={cn('relative bg-background cursor-pointer', getHeightClass())}
        onClick={onSelect}
      >
        {/* Lazy load: wait for visibility AND entityId before loading preview */}
        {showPreview && !isDragging && entityId && isVisible ? (
          <>
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            )}
            <iframe
              key={iframeKey}
              src={previewUrl}
              className="w-full h-full border-0 pointer-events-none"
              onLoad={handleIframeLoad}
              title={widget.title}
              loading="lazy"
            />
            {/* Selection overlay on hover */}
            <div className="absolute inset-0 bg-primary/0 hover:bg-primary/10 transition-colors flex items-center justify-center opacity-0 hover:opacity-100">
              <div className="bg-background/90 px-3 py-1.5 rounded-full flex items-center gap-2 shadow-sm">
                <MousePointerClick className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium text-primary">{t('layout.seeDetails')}</span>
              </div>
            </div>
          </>
        ) : showPreview && !isDragging && (!entityId || !isVisible) ? (
          /* Loading state while waiting for entityId or visibility */
          <div className="h-full flex items-center justify-center bg-muted/20">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground bg-muted/20">
            <Badge variant="outline" className="text-xs">
              {widget.plugin}
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
  const [globalRefreshKey, setGlobalRefreshKey] = useState(0)

  // Reset entity selection when group changes
  useEffect(() => {
    setSelectedEntityId(null)
  }, [groupBy])

  // Set default entity when representatives are loaded
  useEffect(() => {
    if (representatives?.default_entity && !selectedEntityId) {
      setSelectedEntityId(representatives.default_entity.id)
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
      {/* Header */}
      <div className="px-4 py-3 border-b shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold">{t('layout.layoutPreview')}</h2>
            <p className="text-sm text-muted-foreground">
              {t('layout.widgetsConfigured', { count: layout.total_widgets })} - {t('layout.clickToEdit')}
              {hasChanges && (
                <Badge variant="outline" className="ml-2 text-warning border-warning">
                  {t('layout.unsavedChanges')}
                </Badge>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Preview toggle */}
            <Button
              variant={showPreviews ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setShowPreviews(!showPreviews)}
            >
              {showPreviews ? (
                <Eye className="mr-1.5 h-4 w-4" />
              ) : (
                <EyeOff className="mr-1.5 h-4 w-4" />
              )}
              {t('layout.previews')}
            </Button>

            {/* Entity selector */}
            {showPreviews && representatives && representatives.entities.length > 0 && (
              <Select
                value={selectedEntityId || ''}
                onValueChange={setSelectedEntityId}
              >
                <SelectTrigger className="w-[180px] h-8">
                  <Leaf className="mr-2 h-4 w-4 text-muted-foreground" />
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

            {/* Refresh */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetch()
                setGlobalRefreshKey((k) => k + 1)
              }}
              disabled={saveMutation.isPending}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>

            {/* Save */}
            <Button
              size="sm"
              onClick={handleSave}
              disabled={!hasChanges || saveMutation.isPending}
            >
              {saveMutation.isPending ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-1.5 h-4 w-4" />
              )}
              {t('layout.save')}
            </Button>
          </div>
        </div>
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
        {/* Navigation sidebar */}
        {navigationWidget && layout.navigation_widget && (
          <div className="w-64 p-4 shrink-0 border-r">
            <NavigationSidebar
              groupBy={groupBy}
              navigationWidget={layout.navigation_widget}
              refreshKey={globalRefreshKey}
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
                      refreshKey={globalRefreshKey}
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
                      {activeWidget.plugin}
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
          <Columns className="h-3.5 w-3.5" />
          <span>{t('layout.columns.one')}</span>
        </div>
        <div className="flex items-center gap-1">
          <Columns2 className="h-3.5 w-3.5" />
          <span>{t('layout.columns.two')}</span>
        </div>
        <span className="text-muted-foreground/50">|</span>
        <span>{t('layout.dragDrop')}</span>
      </div>
    </div>
  )
}
