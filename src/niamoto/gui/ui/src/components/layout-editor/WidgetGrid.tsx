/**
 * WidgetGrid - Draggable grid of widget cards
 *
 * Uses @dnd-kit for drag and drop functionality.
 * Displays widgets in a 12-column grid system.
 */
import { useCallback, useState } from 'react'
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
} from '@dnd-kit/sortable'
import { WidgetCard } from './WidgetCard'
import type { WidgetLayout } from './types'

interface WidgetGridProps {
  groupBy: string
  widgets: WidgetLayout[]
  showPreviews: boolean
  entityId?: string | null  // Selected entity for preview
  onReorder: (newOrder: WidgetLayout[]) => void
  onColspanToggle: (widgetIndex: number) => void
  onTitleChange: (widgetIndex: number, newTitle: string) => void
}

export function WidgetGrid({
  groupBy,
  widgets,
  showPreviews,
  entityId,
  onReorder,
  onColspanToggle,
  onTitleChange,
}: WidgetGridProps) {
  // Track dragging state to disable iframes during drag
  const [isDragging, setIsDragging] = useState(false)
  const [activeId, setActiveId] = useState<string | null>(null)

  // DnD sensors with larger activation distance for reliability
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 10, // Require more movement to start drag
        delay: 100,   // Small delay to prevent accidental drags
        tolerance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Handle drag start - disable iframes
  const handleDragStart = useCallback((event: DragStartEvent) => {
    setIsDragging(true)
    setActiveId(event.active.id as string)
  }, [])

  // Handle drag end
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setIsDragging(false)
      setActiveId(null)

      const { active, over } = event

      if (over && active.id !== over.id) {
        const oldIndex = widgets.findIndex((w) => `widget-${w.index}` === active.id)
        const newIndex = widgets.findIndex((w) => `widget-${w.index}` === over.id)

        if (oldIndex !== -1 && newIndex !== -1) {
          const newWidgets = arrayMove(widgets, oldIndex, newIndex)
          onReorder(newWidgets)
        }
      }
    },
    [widgets, onReorder]
  )

  // Handle drag cancel
  const handleDragCancel = useCallback(() => {
    setIsDragging(false)
    setActiveId(null)
  }, [])

  // Generate unique IDs for sortable context
  const widgetIds = widgets.map((w) => `widget-${w.index}`)

  // Find active widget for drag overlay
  const activeWidget = activeId
    ? widgets.find((w) => `widget-${w.index}` === activeId)
    : null

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <SortableContext items={widgetIds} strategy={rectSortingStrategy}>
        <div className="grid grid-cols-12 gap-4 auto-rows-min">
          {widgets.map((widget) => (
            <WidgetCard
              key={`widget-${widget.index}`}
              id={`widget-${widget.index}`}
              groupBy={groupBy}
              widget={widget}
              showPreview={showPreviews && !isDragging}
              entityId={entityId}
              onColspanToggle={() => onColspanToggle(widget.index)}
              onTitleChange={(title) => onTitleChange(widget.index, title)}
            />
          ))}
        </div>
      </SortableContext>

      {/* Drag overlay - shows a simplified card while dragging */}
      <DragOverlay>
        {activeWidget ? (
          <div className={`${activeWidget.colspan === 1 ? 'w-[calc(50%-0.5rem)]' : 'w-full'} rounded-lg border bg-card shadow-lg opacity-90`}>
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
  )
}
