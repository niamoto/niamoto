/**
 * WidgetCard - Draggable widget card with preview
 *
 * Features:
 * - Drag handle for reordering
 * - Iframe preview of widget
 * - Colspan toggle button
 * - Editable title
 */
import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useQueryClient } from '@tanstack/react-query'
import {
  GripVertical,
  RefreshCw,
  Pencil,
  Check,
  X,
  RectangleHorizontal,
  Square,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { PreviewPane } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { invalidateAllPreviews } from '@/lib/preview/usePreviewFrame'
import type { WidgetLayout } from './types'

interface WidgetCardProps {
  id: string
  groupBy: string
  widget: WidgetLayout
  showPreview: boolean
  entityId?: string | null  // Selected entity for preview
  onColspanToggle: () => void
  onTitleChange: (title: string) => void
}

export function WidgetCard({
  id,
  groupBy,
  widget,
  showPreview,
  entityId,
  onColspanToggle,
  onTitleChange,
}: WidgetCardProps) {
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [editedTitle, setEditedTitle] = useState(widget.title)
  const inputRef = useRef<HTMLInputElement>(null)

  const descriptor: PreviewDescriptor = useMemo(() => ({
    templateId: widget.data_source,
    groupBy,
    entityId: entityId || undefined,
    mode: 'full' as const,
  }), [widget.data_source, groupBy, entityId])

  // Sortable hook
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  // Handle refresh
  const handleRefresh = useCallback(() => {
    invalidateAllPreviews(queryClient)
  }, [queryClient])

  // Handle title edit
  const startEditing = useCallback(() => {
    setEditedTitle(widget.title)
    setIsEditing(true)
  }, [widget.title])

  const cancelEditing = useCallback(() => {
    setEditedTitle(widget.title)
    setIsEditing(false)
  }, [widget.title])

  const saveTitle = useCallback(() => {
    if (editedTitle.trim() && editedTitle !== widget.title) {
      onTitleChange(editedTitle.trim())
    }
    setIsEditing(false)
  }, [editedTitle, widget.title, onTitleChange])

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  // Handle keyboard in edit mode
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        saveTitle()
      } else if (e.key === 'Escape') {
        cancelEditing()
      }
    },
    [saveTitle, cancelEditing]
  )

  // Column span class - default to half width (2 widgets per row)
  const colSpanClass = widget.colspan === 1 ? 'col-span-6' : 'col-span-12'

  // Height class based on widget type - matching original template proportions
  const getHeightClass = () => {
    switch (widget.plugin) {
      case 'interactive_map':
        return 'h-96' // 384px - maps need significant vertical space
      case 'bar_plot':
        return 'h-72' // 288px - bar plots need good height for readability
      case 'donut_chart':
        return 'h-64' // 256px
      case 'radial_gauge':
        return 'h-72' // 288px - gauges need space for the arc + value
      default:
        return 'h-64' // 256px default
    }
  }
  const heightClass = getHeightClass()

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        colSpanClass,
        'rounded-lg border bg-card overflow-hidden transition-all',
        isDragging && 'opacity-50 shadow-lg ring-2 ring-primary'
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
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="flex items-center gap-1">
              <Input
                ref={inputRef}
                value={editedTitle}
                onChange={(e) => setEditedTitle(e.target.value)}
                onKeyDown={handleKeyDown}
                className="h-7 text-sm"
              />
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0"
                onClick={saveTitle}
              >
                <Check className="h-3.5 w-3.5 text-success" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0"
                onClick={cancelEditing}
              >
                <X className="h-3.5 w-3.5 text-muted-foreground" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm truncate">{widget.title}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0 opacity-0 group-hover:opacity-100 hover:opacity-100"
                onClick={startEditing}
              >
                <Pencil className="h-3 w-3 text-muted-foreground" />
              </Button>
            </div>
          )}
        </div>

        {/* Plugin badge */}
        <Badge variant="secondary" className="text-xs shrink-0">
          {widget.plugin}
        </Badge>

        {/* Colspan toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={onColspanToggle}
          title={widget.colspan === 1 ? 'Etendre sur 2 colonnes' : 'Reduire a 1 colonne'}
        >
          {widget.colspan === 1 ? (
            <RectangleHorizontal className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Square className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>

        {/* Refresh */}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={handleRefresh}
        >
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
        </Button>
      </div>

      {/* Preview or placeholder */}
      <div className={cn('relative bg-background', heightClass)}>
        {showPreview ? (
          <PreviewPane descriptor={descriptor} className="w-full h-full" />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground bg-muted/20">
            <Badge variant="outline" className="text-xs">
              {widget.plugin}
            </Badge>
            <span className="mt-2 text-xs">Preview désactivée</span>
          </div>
        )}
      </div>

      {/* Footer - description */}
      {widget.description && (
        <div className="px-3 py-2 border-t bg-muted/30">
          <p className="text-xs text-muted-foreground truncate">
            {widget.description}
          </p>
        </div>
      )}
    </div>
  )
}
