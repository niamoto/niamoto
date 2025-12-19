/**
 * NavigationBuilder - Drag & drop navigation menu editor
 *
 * Allows:
 * - Reordering menu items via drag & drop
 * - Adding new menu items
 * - Editing text and URL
 * - Removing items
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
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, Plus, Trash2, Navigation } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { NavigationItem } from '@/hooks/useSiteConfig'

interface NavigationBuilderProps {
  items: NavigationItem[]
  onChange: (items: NavigationItem[]) => void
}

interface SortableItemProps {
  id: string
  item: NavigationItem
  onUpdate: (item: NavigationItem) => void
  onRemove: () => void
}

function SortableNavItem({ id, item, onUpdate, onRemove }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 rounded-lg border bg-card p-2 ${
        isDragging ? 'opacity-50 shadow-lg' : ''
      }`}
    >
      {/* Drag handle */}
      <button
        className="cursor-grab touch-none rounded p-1 hover:bg-muted active:cursor-grabbing"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </button>

      {/* Text input */}
      <Input
        value={item.text}
        onChange={(e) => onUpdate({ ...item, text: e.target.value })}
        placeholder="Texte du menu"
        className="flex-1"
      />

      {/* URL input */}
      <Input
        value={item.url}
        onChange={(e) => onUpdate({ ...item, url: e.target.value })}
        placeholder="/page.html"
        className="flex-1 font-mono text-sm"
      />

      {/* Remove button */}
      <Button variant="ghost" size="icon" onClick={onRemove} className="h-8 w-8 shrink-0">
        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
      </Button>
    </div>
  )
}

export function NavigationBuilder({ items, onChange }: NavigationBuilderProps) {
  // Generate stable IDs for sortable items
  const [idMap] = useState(() => {
    const map = new Map<number, string>()
    items.forEach((_, index) => {
      map.set(index, `nav-${index}-${Date.now()}`)
    })
    return map
  })

  // Get or create ID for an index
  const getId = (index: number): string => {
    if (!idMap.has(index)) {
      idMap.set(index, `nav-${index}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`)
    }
    return idMap.get(index)!
  }

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((_, i) => getId(i) === active.id)
      const newIndex = items.findIndex((_, i) => getId(i) === over.id)

      if (oldIndex !== -1 && newIndex !== -1) {
        onChange(arrayMove(items, oldIndex, newIndex))
      }
    }
  }

  const handleAdd = () => {
    onChange([...items, { text: 'Nouvelle page', url: '/nouvelle.html' }])
  }

  const handleUpdate = (index: number, item: NavigationItem) => {
    const newItems = [...items]
    newItems[index] = item
    onChange(newItems)
  }

  const handleRemove = (index: number) => {
    onChange(items.filter((_, i) => i !== index))
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Navigation className="h-4 w-4" />
              Navigation
            </CardTitle>
            <CardDescription>Menu de navigation principal du site</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleAdd}>
            <Plus className="mr-1 h-4 w-4" />
            Ajouter
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <div className="flex min-h-[100px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-4 text-center">
            <Navigation className="mb-2 h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">Aucun menu configure</p>
            <Button variant="link" size="sm" onClick={handleAdd} className="mt-2">
              <Plus className="mr-1 h-4 w-4" />
              Ajouter un premier element
            </Button>
          </div>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext
              items={items.map((_, i) => getId(i))}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {items.map((item, index) => (
                  <SortableNavItem
                    key={getId(index)}
                    id={getId(index)}
                    item={item}
                    onUpdate={(updated) => handleUpdate(index, updated)}
                    onRemove={() => handleRemove(index)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}

        {/* Preview */}
        {items.length > 0 && (
          <div className="mt-4 rounded-lg border bg-muted/30 p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Apercu</p>
            <div className="flex flex-wrap gap-2">
              {items.map((item, index) => (
                <span
                  key={index}
                  className="rounded-md bg-primary/10 px-3 py-1 text-sm font-medium text-primary"
                >
                  {item.text || 'Sans titre'}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
