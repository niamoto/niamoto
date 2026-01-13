/**
 * NavigationBuilder - Drag & drop navigation menu editor with sub-menu support
 *
 * Allows:
 * - Reordering menu items via drag & drop
 * - Adding new menu items with page selection
 * - Creating sub-menus (one level deep)
 * - Editing text and URL
 * - Removing items
 */

import { useState, useRef, useCallback } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DraggableAttributes,
} from '@dnd-kit/core'
import type { SyntheticListenerMap } from '@dnd-kit/core/dist/hooks/utilities'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  GripVertical,
  Plus,
  Trash2,
  Navigation,
  FileText,
  Folder,
  ChevronDown,
  ChevronRight,
  Link2,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'
import type { NavigationItem, StaticPage, GroupInfo } from '@/hooks/useSiteConfig'

// Available page for navigation selection
interface AvailablePage {
  name: string
  url: string
  type: 'static' | 'group' | 'custom'
}

interface NavigationBuilderProps {
  items: NavigationItem[]
  onChange: (items: NavigationItem[]) => void
  staticPages?: StaticPage[]
  groups?: GroupInfo[]
  title?: string
  description?: string
  allowSubmenus?: boolean
}

interface NavItemEditorProps {
  item: NavigationItem
  availablePages: AvailablePage[]
  onUpdate: (item: NavigationItem) => void
  onRemove: () => void
  onAddChild?: () => void
  isChild?: boolean
  dragHandleProps?: {
    attributes: DraggableAttributes
    listeners: SyntheticListenerMap | undefined
  }
}

function NavItemEditor({
  item,
  availablePages,
  onUpdate,
  onRemove,
  onAddChild,
  isChild = false,
  dragHandleProps,
}: NavItemEditorProps) {
  const [open, setOpen] = useState(false)
  const hasChildren = item.children && item.children.length > 0

  // Find if current URL matches an available page
  const matchedPage = availablePages.find((p) => p.url === item.url)

  const handleSelectPage = (page: AvailablePage) => {
    onUpdate({
      ...item,
      text: item.text || page.name,
      url: page.url,
    })
    setOpen(false)
  }

  return (
    <div className={cn('flex items-center gap-2', isChild && 'ml-8')}>
      {/* Drag handle */}
      {dragHandleProps && (
        <button
          className="cursor-grab touch-none rounded p-1 hover:bg-muted active:cursor-grabbing"
          {...dragHandleProps.attributes}
          {...(dragHandleProps.listeners ?? {})}
        >
          <GripVertical className="h-4 w-4 text-muted-foreground" />
        </button>
      )}

      {/* Expand indicator for items with children */}
      {!isChild && hasChildren && (
        <ChevronDown className="h-4 w-4 text-muted-foreground" />
      )}
      {!isChild && !hasChildren && onAddChild && (
        <div className="w-4" />
      )}

      {/* Text input */}
      <Input
        value={item.text}
        onChange={(e) => onUpdate({ ...item, text: e.target.value })}
        placeholder={isChild ? 'Sous-menu' : 'Texte du menu'}
        className={cn('flex-1', isChild && 'h-8 text-sm')}
      />

      {/* URL with page selector - only if no children or is child */}
      {(!hasChildren || isChild) && (
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size={isChild ? 'sm' : 'default'}
              className={cn(
                'flex-1 justify-between font-mono text-sm',
                !item.url && 'text-muted-foreground'
              )}
            >
              <span className="flex items-center gap-2 truncate">
                {matchedPage?.type === 'static' && <FileText className="h-3 w-3 shrink-0" />}
                {matchedPage?.type === 'group' && <Folder className="h-3 w-3 shrink-0 text-amber-600" />}
                {!matchedPage && item.url && <Link2 className="h-3 w-3 shrink-0" />}
                {item.url || 'Selectionner...'}
              </span>
              <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[300px] p-0" align="start">
            <div className="max-h-[300px] overflow-auto">
              {/* Static pages */}
              {availablePages.filter((p) => p.type === 'static').length > 0 && (
                <div className="p-2">
                  <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">
                    Pages statiques
                  </p>
                  {availablePages
                    .filter((p) => p.type === 'static')
                    .map((page) => (
                      <button
                        key={page.url}
                        className={cn(
                          'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted',
                          item.url === page.url && 'bg-muted'
                        )}
                        onClick={() => handleSelectPage(page)}
                      >
                        <FileText className="h-4 w-4 shrink-0" />
                        <span className="flex-1 text-left truncate">{page.name}</span>
                        <span className="text-xs text-muted-foreground font-mono">
                          {page.url}
                        </span>
                      </button>
                    ))}
                </div>
              )}

              {/* Group pages */}
              {availablePages.filter((p) => p.type === 'group').length > 0 && (
                <div className="border-t p-2">
                  <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">
                    Pages de groupes
                  </p>
                  {availablePages
                    .filter((p) => p.type === 'group')
                    .map((page) => (
                      <button
                        key={page.url}
                        className={cn(
                          'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted',
                          item.url === page.url && 'bg-muted'
                        )}
                        onClick={() => handleSelectPage(page)}
                      >
                        <Folder className="h-4 w-4 shrink-0 text-amber-600" />
                        <span className="flex-1 text-left truncate">{page.name}</span>
                        <span className="text-xs text-muted-foreground font-mono">
                          {page.url}
                        </span>
                      </button>
                    ))}
                </div>
              )}

              {/* Custom URL option */}
              <div className="border-t p-2">
                <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">
                  URL personnalisee
                </p>
                <div className="flex gap-2 px-2">
                  <Input
                    value={item.url || ''}
                    onChange={(e) => onUpdate({ ...item, url: e.target.value })}
                    placeholder="/page.html"
                    className="flex-1 font-mono text-sm h-8"
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      )}

      {/* Parent indicator if has children */}
      {hasChildren && !isChild && (
        <span className="text-xs text-muted-foreground px-2">
          {item.children?.length} sous-menu{(item.children?.length || 0) > 1 ? 's' : ''}
        </span>
      )}

      {/* Add sub-menu button - only for top-level items */}
      {!isChild && onAddChild && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onAddChild}
          className="h-8 w-8 shrink-0"
          title="Ajouter un sous-menu"
        >
          <Plus className="h-4 w-4 text-muted-foreground" />
        </Button>
      )}

      {/* Remove button */}
      <Button variant="ghost" size="icon" onClick={onRemove} className="h-8 w-8 shrink-0">
        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
      </Button>
    </div>
  )
}

interface SortableNavItemProps {
  id: string
  item: NavigationItem
  availablePages: AvailablePage[]
  onUpdate: (item: NavigationItem) => void
  onRemove: () => void
  allowSubmenus?: boolean
}

function SortableNavItem({ id, item, availablePages, onUpdate, onRemove, allowSubmenus = true }: SortableNavItemProps) {
  const [isOpen, setIsOpen] = useState(true)
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const hasChildren = item.children && item.children.length > 0

  const handleAddChild = () => {
    onUpdate({
      ...item,
      children: [...(item.children || []), { text: '', url: '' }],
    })
  }

  const handleUpdateChild = (childIndex: number, updatedChild: NavigationItem) => {
    const newChildren = [...(item.children || [])]
    newChildren[childIndex] = updatedChild
    onUpdate({ ...item, children: newChildren })
  }

  const handleRemoveChild = (childIndex: number) => {
    const newChildren = (item.children || []).filter((_, i) => i !== childIndex)
    onUpdate({ ...item, children: newChildren.length > 0 ? newChildren : undefined })
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'rounded-lg border bg-card',
        isDragging && 'opacity-50 shadow-lg'
      )}
    >
      {hasChildren ? (
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <div className="p-2">
            <div className="flex items-center gap-2">
              <CollapsibleTrigger asChild>
                <button className="p-1 hover:bg-muted rounded">
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
              </CollapsibleTrigger>
              <button
                className="cursor-grab touch-none rounded p-1 hover:bg-muted active:cursor-grabbing"
                {...attributes}
                {...listeners}
              >
                <GripVertical className="h-4 w-4 text-muted-foreground" />
              </button>
              <Input
                value={item.text}
                onChange={(e) => onUpdate({ ...item, text: e.target.value })}
                placeholder="Texte du menu"
                className="flex-1"
              />
              <span className="text-xs text-muted-foreground px-2">
                {item.children?.length} sous-menu{(item.children?.length || 0) > 1 ? 's' : ''}
              </span>
              {allowSubmenus && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleAddChild}
                  className="h-8 w-8 shrink-0"
                  title="Ajouter un sous-menu"
                >
                  <Plus className="h-4 w-4 text-muted-foreground" />
                </Button>
              )}
              <Button variant="ghost" size="icon" onClick={onRemove} className="h-8 w-8 shrink-0">
                <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
              </Button>
            </div>
          </div>
          <CollapsibleContent>
            <div className="border-t bg-muted/30 p-2 space-y-2">
              {item.children?.map((child, childIndex) => (
                <NavItemEditor
                  key={childIndex}
                  item={child}
                  availablePages={availablePages}
                  onUpdate={(updated) => handleUpdateChild(childIndex, updated)}
                  onRemove={() => handleRemoveChild(childIndex)}
                  isChild
                />
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      ) : (
        <div className="p-2">
          <NavItemEditor
            item={item}
            availablePages={availablePages}
            onUpdate={onUpdate}
            onRemove={onRemove}
            onAddChild={allowSubmenus ? handleAddChild : undefined}
            dragHandleProps={{ attributes, listeners }}
          />
        </div>
      )}
    </div>
  )
}

export function NavigationBuilder({
  items,
  onChange,
  staticPages = [],
  groups = [],
  title = 'Navigation',
  description = 'Menu de navigation principal du site',
  allowSubmenus = true,
}: NavigationBuilderProps) {
  // Build available pages list from static pages and groups
  const availablePages: AvailablePage[] = [
    // Static pages
    ...staticPages.map((page) => ({
      name: page.name,
      url: `/${page.output_file}`,
      type: 'static' as const,
    })),
    // Group index pages
    ...groups
      .filter((g) => g.index_output_pattern)
      .map((group) => ({
        name: `${group.name} (index)`,
        url: `/${group.index_output_pattern}`,
        type: 'group' as const,
      })),
  ]

  // Generate stable IDs for sortable items using WeakMap
  // This ensures each item object gets a consistent ID
  const idCounterRef = useRef(0)
  const itemIdMapRef = useRef(new WeakMap<NavigationItem, string>())

  // Get or create stable ID for an item
  const getId = useCallback((item: NavigationItem): string => {
    if (!itemIdMapRef.current.has(item)) {
      idCounterRef.current += 1
      itemIdMapRef.current.set(item, `nav-${idCounterRef.current}`)
    }
    return itemIdMapRef.current.get(item)!
  }, [])

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((item) => getId(item) === active.id)
      const newIndex = items.findIndex((item) => getId(item) === over.id)

      if (oldIndex !== -1 && newIndex !== -1) {
        onChange(arrayMove(items, oldIndex, newIndex))
      }
    }
  }

  const handleAdd = () => {
    onChange([...items, { text: '', url: '' }])
  }

  const handleUpdate = (index: number, item: NavigationItem) => {
    const newItems = [...items]
    newItems[index] = item
    onChange(newItems)
  }

  const handleRemove = (index: number) => {
    onChange(items.filter((_, i) => i !== index))
  }

  // Render preview item with potential children
  const renderPreviewItem = (item: NavigationItem, index: number) => {
    const hasChildren = item.children && item.children.length > 0
    return (
      <div key={index} className="flex items-center gap-1">
        <span className="rounded-md bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
          {item.text || 'Sans titre'}
          {hasChildren && <ChevronDown className="inline-block ml-1 h-3 w-3" />}
        </span>
      </div>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Navigation className="h-4 w-4" />
              {title}
            </CardTitle>
            <CardDescription>{description}</CardDescription>
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
              items={items.map((item) => getId(item))}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {items.map((item, index) => (
                  <SortableNavItem
                    key={getId(item)}
                    id={getId(item)}
                    item={item}
                    availablePages={availablePages}
                    onUpdate={(updated) => handleUpdate(index, updated)}
                    onRemove={() => handleRemove(index)}
                    allowSubmenus={allowSubmenus}
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
              {items.map((item, index) => renderPreviewItem(item, index))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
