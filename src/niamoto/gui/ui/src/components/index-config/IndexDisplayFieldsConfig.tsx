/**
 * IndexDisplayFieldsConfig - Display fields configuration with drag-and-drop
 *
 * Allows adding/editing/removing/reordering display fields for the index generator.
 */
import { useState } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, Plus, Trash2, Pencil, Search, Badge as BadgeIcon, EyeOff } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { IndexDisplayField } from './useIndexConfig'
import { DisplayFieldEditor } from './DisplayFieldEditor'

interface IndexDisplayFieldsConfigProps {
  fields: IndexDisplayField[]
  onAdd: () => void
  onUpdate: (index: number, field: Partial<IndexDisplayField>) => void
  onRemove: (index: number) => void
  onReorder: (fromIndex: number, toIndex: number) => void
}

// Individual sortable field item
interface SortableFieldItemProps {
  field: IndexDisplayField
  index: number
  onEdit: () => void
  onRemove: () => void
}

function SortableFieldItem({ field, index, onEdit, onRemove }: SortableFieldItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `field-${index}` })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-2 p-3 rounded-lg border bg-card',
        isDragging && 'opacity-50 shadow-lg'
      )}
    >
      {/* Drag handle */}
      <button
        type="button"
        className="touch-none cursor-grab active:cursor-grabbing p-1 text-muted-foreground hover:text-foreground"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4" />
      </button>

      {/* Field info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{field.name || '(sans nom)'}</span>

          {/* Badges for field properties */}
          {field.searchable && (
            <Badge variant="outline" className="h-5 text-[10px] px-1.5 shrink-0">
              <Search className="h-3 w-3 mr-1" />
              Recherche
            </Badge>
          )}

          {field.inline_badge && (
            <Badge variant="outline" className="h-5 text-[10px] px-1.5 shrink-0">
              <BadgeIcon className="h-3 w-3 mr-1" />
              Badge
            </Badge>
          )}

          {field.display === 'hidden' && (
            <Badge variant="outline" className="h-5 text-[10px] px-1.5 shrink-0 text-muted-foreground">
              <EyeOff className="h-3 w-3 mr-1" />
              Cache
            </Badge>
          )}
        </div>

        <p className="text-xs text-muted-foreground font-mono truncate mt-0.5">
          {field.source || '(source non definie)'}
        </p>
      </div>

      {/* Type badge */}
      <Badge variant="secondary" className="shrink-0 text-xs">
        {field.type}
      </Badge>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onEdit}
        >
          <Pencil className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-destructive hover:text-destructive"
          onClick={onRemove}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

export function IndexDisplayFieldsConfig({
  fields,
  onAdd,
  onUpdate,
  onRemove,
  onReorder,
}: IndexDisplayFieldsConfigProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      const oldIndex = parseInt(String(active.id).replace('field-', ''))
      const newIndex = parseInt(String(over.id).replace('field-', ''))
      onReorder(oldIndex, newIndex)
    }
  }

  // Handle edit
  const handleEdit = (index: number) => {
    setEditingIndex(index)
  }

  // Handle save from editor
  const handleSaveField = (field: Partial<IndexDisplayField>) => {
    if (editingIndex !== null) {
      onUpdate(editingIndex, field)
      setEditingIndex(null)
    }
  }

  if (fields.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-sm text-muted-foreground mb-4">
          Aucun champ configure. Les champs definissent les colonnes affichees dans l'index.
        </p>
        <Button variant="outline" size="sm" onClick={onAdd}>
          <Plus className="mr-2 h-4 w-4" />
          Ajouter un champ
        </Button>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground mb-3">
          Glissez-deposez pour reordonner les champs
        </p>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={fields.map((_, i) => `field-${i}`)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-2">
              {fields.map((field, index) => (
                <SortableFieldItem
                  key={`field-${index}`}
                  field={field}
                  index={index}
                  onEdit={() => handleEdit(index)}
                  onRemove={() => onRemove(index)}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>

        <Button variant="outline" size="sm" onClick={onAdd} className="mt-4">
          <Plus className="mr-2 h-4 w-4" />
          Ajouter un champ
        </Button>
      </div>

      {/* Field editor modal */}
      {editingIndex !== null && fields[editingIndex] && (
        <DisplayFieldEditor
          field={fields[editingIndex]}
          open={true}
          onOpenChange={(open) => {
            if (!open) setEditingIndex(null)
          }}
          onSave={handleSaveField}
        />
      )}
    </>
  )
}
