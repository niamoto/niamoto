/**
 * ConfiguredWidgetsList - Display list of widgets already in transform.yml
 *
 * Shows configured widgets with their current settings and actions:
 * - Drag and drop to reorder
 * - Click to select and preview/edit
 * - Delete button to remove
 * - Visual indication of widget type and transformer
 */
import { useState, useCallback } from 'react'
import { useTranslation, Trans } from 'react-i18next'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  BarChart3,
  Activity,
  PieChart,
  Map,
  Info,
  FolderTree,
  Layers,
  Trash2,
  Copy,
  Loader2,
  Settings2,
  AlertTriangle,
  GripVertical,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { ConfiguredWidget } from './useWidgetConfig'

// Category icons
const CATEGORY_ICONS: Record<string, React.ElementType> = {
  navigation: FolderTree,
  info: Info,
  map: Map,
  chart: BarChart3,
  gauge: Activity,
  donut: PieChart,
  table: Layers,
}

// Category colors
const CATEGORY_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  navigation: { text: 'text-violet-600', bg: 'bg-violet-50', border: 'border-violet-200' },
  info: { text: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  map: { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  chart: { text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' },
  gauge: { text: 'text-teal-600', bg: 'bg-teal-50', border: 'border-teal-200' },
  donut: { text: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
  table: { text: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200' },
}

interface SortableWidgetItemProps {
  widget: ConfiguredWidget
  isSelected: boolean
  onSelect: () => void
  onDeleteClick: (e: React.MouseEvent) => void
  onDuplicateClick?: (e: React.MouseEvent) => void
}

function SortableWidgetItem({
  widget,
  isSelected,
  onSelect,
  onDeleteClick,
  onDuplicateClick,
}: SortableWidgetItemProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widget.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const category = widget.category || 'chart'
  const Icon = CATEGORY_ICONS[category] || BarChart3
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.chart

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group relative flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition-all bg-background',
        'hover:border-primary/50 hover:bg-accent/30',
        isSelected && 'border-primary bg-primary/5 ring-1 ring-primary/20',
        isDragging && 'opacity-50 shadow-lg z-50'
      )}
      onClick={onSelect}
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        className="flex-shrink-0 cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground"
        onClick={(e) => e.stopPropagation()}
      >
        <GripVertical className="h-5 w-5" />
      </div>

      {/* Category icon */}
      <div className={cn(
        'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
        colors.bg,
        colors.border,
        'border'
      )}>
        <Icon className={cn('h-5 w-5', colors.text)} />
      </div>

      {/* Widget info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{widget.title}</span>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <Badge variant="secondary" className="text-xs">
            {widget.transformerPlugin}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {widget.widgetPlugin}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {onDuplicateClick && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onDuplicateClick}
            title={t('common:aria.duplicate')}
          >
            <Copy className="h-4 w-4" />
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
          onClick={onDeleteClick}
          title={t('common:actions.delete')}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

interface ConfiguredWidgetsListProps {
  widgets: ConfiguredWidget[]
  selectedId?: string
  loading?: boolean
  onSelect: (widget: ConfiguredWidget) => void
  onDelete: (widgetId: string) => Promise<boolean>
  onDuplicate?: (widgetId: string, newId: string) => Promise<boolean>
  onReorder?: (widgetIds: string[]) => Promise<boolean>
}

export function ConfiguredWidgetsList({
  widgets,
  selectedId,
  loading,
  onSelect,
  onDelete,
  onDuplicate,
  onReorder,
}: ConfiguredWidgetsListProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false)
  const [targetWidget, setTargetWidget] = useState<ConfiguredWidget | null>(null)
  const [newWidgetId, setNewWidgetId] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [isDuplicating, setIsDuplicating] = useState(false)

  // DnD sensors
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

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event

      if (over && active.id !== over.id) {
        const oldIndex = widgets.findIndex((w) => w.id === active.id)
        const newIndex = widgets.findIndex((w) => w.id === over.id)

        if (oldIndex !== -1 && newIndex !== -1 && onReorder) {
          const reorderedWidgets = arrayMove(widgets, oldIndex, newIndex)
          const widgetIds = reorderedWidgets.map((w) => w.id)
          await onReorder(widgetIds)
        }
      }
    },
    [widgets, onReorder]
  )

  const handleDeleteClick = (e: React.MouseEvent, widget: ConfiguredWidget) => {
    e.stopPropagation()
    setTargetWidget(widget)
    setDeleteDialogOpen(true)
  }

  const handleDuplicateClick = (e: React.MouseEvent, widget: ConfiguredWidget) => {
    e.stopPropagation()
    setTargetWidget(widget)
    setNewWidgetId(`${widget.id}_copy`)
    setDuplicateDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!targetWidget) return
    setIsDeleting(true)
    await onDelete(targetWidget.id)
    setIsDeleting(false)
    setDeleteDialogOpen(false)
    setTargetWidget(null)
  }

  const handleConfirmDuplicate = async () => {
    if (!targetWidget || !onDuplicate || !newWidgetId.trim()) return
    setIsDuplicating(true)
    await onDuplicate(targetWidget.id, newWidgetId.trim())
    setIsDuplicating(false)
    setDuplicateDialogOpen(false)
    setTargetWidget(null)
    setNewWidgetId('')
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="mt-4 text-sm text-muted-foreground">
          {t('listPanel.loading')}
        </p>
      </div>
    )
  }

  // Empty state
  if (widgets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Settings2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="font-medium text-muted-foreground">{t('list.noWidgets')}</h3>
        <p className="mt-2 text-sm text-muted-foreground max-w-[250px]">
          {t('list.clickToAdd')}
        </p>
      </div>
    )
  }

  const widgetIds = widgets.map((w) => w.id)

  return (
    <>
      <div className="h-full overflow-auto">
        <div className="p-4">
          <div className="text-sm text-muted-foreground mb-4">
            {t('list.widgetsCount', { count: widgets.length })}
            {onReorder && (
              <span className="text-xs ml-2">{t('listPanel.dragToReorder')}</span>
            )}
          </div>

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={widgetIds} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {widgets.map((widget) => (
                  <SortableWidgetItem
                    key={widget.id}
                    widget={widget}
                    isSelected={widget.id === selectedId}
                    onSelect={() => onSelect(widget)}
                    onDeleteClick={(e) => handleDeleteClick(e, widget)}
                    onDuplicateClick={onDuplicate ? (e) => handleDuplicateClick(e, widget) : undefined}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              {t('dialogs.deleteWidget')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              <Trans
                i18nKey="listPanel.deleteDescription"
                t={t}
                values={{ title: targetWidget?.title }}
                components={{ strong: <strong /> }}
              />
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>{t('common:actions.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common:status.deleting')}
                </>
              ) : (
                t('common:actions.delete')
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Duplicate dialog */}
      <Dialog open={duplicateDialogOpen} onOpenChange={setDuplicateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('dialogs.duplicateWidget')}</DialogTitle>
            <DialogDescription>
              {t('listPanel.duplicateDescription', { title: targetWidget?.title })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="new-widget-id">{t('listPanel.newId')}</Label>
            <Input
              id="new-widget-id"
              value={newWidgetId}
              onChange={(e) => setNewWidgetId(e.target.value)}
              placeholder={t('dialogs.duplicatePlaceholder')}
              className="mt-2"
            />
            <p className="text-xs text-muted-foreground mt-2">
              {t('listPanel.newIdHint')}
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDuplicateDialogOpen(false)}
              disabled={isDuplicating}
            >
              {t('common:actions.cancel')}
            </Button>
            <Button
              onClick={handleConfirmDuplicate}
              disabled={isDuplicating || !newWidgetId.trim()}
            >
              {isDuplicating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('listPanel.duplicating')}
                </>
              ) : (
                <>
                  <Copy className="mr-2 h-4 w-4" />
                  {t('common:actions.duplicate')}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
