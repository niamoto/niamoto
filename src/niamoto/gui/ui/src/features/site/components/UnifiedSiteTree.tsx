/**
 * UnifiedSiteTree - Unified page + navigation tree with drag-and-drop
 *
 * Displays pages, collections, and external links in a single list.
 * Menu items are draggable with 1-level nesting support.
 * Hidden items appear in a "Not in menu" section (not draggable).
 */

import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
  DragOverlay,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  Layers,
  ExternalLink,
  Settings,
  Palette,
  PanelBottom,
  Eye,
  EyeOff,
  Plus,
  Trash2,
  GripVertical,
} from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { useLanguages } from '@/shared/contexts/LanguageContext'
import type { UnifiedTreeItem } from '../hooks/useUnifiedSiteTree'
import { getTemplateIcon } from './PagesOverview'
import type { Selection, SelectionType } from '../hooks/useSiteBuilderState'
import {
  flattenTree,
  getProjection,
  applyDragMove,
  INDENTATION_WIDTH,
  type FlatItem,
  type Projection,
} from '../utils/treeDnd'

// =============================================================================
// HELPERS
// =============================================================================

function getItemIcon(item: UnifiedTreeItem) {
  if (item.type === 'page') {
    const Icon = getTemplateIcon(item.template)
    return <Icon className="h-4 w-4 shrink-0" />
  }
  if (item.type === 'collection') {
    return <Layers className={cn('h-4 w-4 shrink-0', item.hasIndex ? 'text-amber-600' : 'text-muted-foreground/50')} />
  }
  return <ExternalLink className="h-4 w-4 shrink-0 text-blue-500" />
}

/** Resolve a LocalizedString to a display string in the given language */
export function resolveLabel(label: import('@/components/ui/localized-input').LocalizedString | undefined, lang?: string): string {
  if (!label) return '—'
  if (typeof label === 'string') return label
  if (typeof label === 'object' && label !== null) {
    if (lang && label[lang]) return label[lang]
    const values = Object.values(label)
    return (values[0] as string) || '—'
  }
  return '—'
}

// =============================================================================
// SORTABLE TREE ITEM
// =============================================================================

interface SortableTreeItemProps {
  flatItem: FlatItem
  isSelected: boolean
  onSelect: () => void
  onToggleVisibility?: () => void
  onDelete?: () => void
  disabled?: boolean
  disabledReason?: string
  isOverlay?: boolean
  projectedDepth?: number
  lang?: string
}

function SortableTreeItem({
  flatItem,
  isSelected,
  onSelect,
  onToggleVisibility,
  onDelete,
  disabled,
  disabledReason,
  isOverlay,
  projectedDepth,
  lang,
}: SortableTreeItemProps) {
  const { item } = flatItem
  const depth = projectedDepth ?? flatItem.depth

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id, disabled })

  const style = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
    paddingLeft: `${4 + depth * INDENTATION_WIDTH}px`,
  }

  const row = (
    <div
      ref={setNodeRef}
      style={isOverlay ? { paddingLeft: `${4 + depth * INDENTATION_WIDTH}px` } : style}
      className={cn(
        'group flex w-full items-center gap-1 rounded-md px-1 py-1 text-sm transition-colors',
        isOverlay && 'bg-background shadow-md border rounded-md',
        isSelected && !isOverlay
          ? 'bg-primary/10 text-primary'
          : disabled
            ? 'opacity-50'
            : 'hover:bg-muted/50',
      )}
    >
      {/* Drag handle */}
      {!disabled && (
        <button
          className="shrink-0 p-0.5 cursor-grab active:cursor-grabbing touch-none"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-3 w-3 text-muted-foreground/40" />
        </button>
      )}

      {/* Main clickable area — always clickable even when drag is disabled
           (collections without index open GroupPageViewer to enable index) */}
      <button
        className="flex items-center gap-2 flex-1 min-w-0"
        onClick={onSelect}
      >
        {getItemIcon(item)}
        <span className={cn('truncate text-left', disabled && 'text-muted-foreground/70')}>
          {resolveLabel(item.label, lang)}
          {item.type === 'collection' && '/'}
        </span>
      </button>

      {/* Template badge */}
      {item.type === 'page' && item.template && (
        <Badge variant="outline" className="text-[9px] h-4 font-normal px-1 shrink-0">
          {item.template.replace('.html', '')}
        </Badge>
      )}

      {/* Toggle visibility */}
      {onToggleVisibility && !disabled && (
        <button
          className="shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:bg-muted"
          onClick={(e) => { e.stopPropagation(); onToggleVisibility() }}
        >
          {item.visible ? (
            <Eye className="h-3 w-3 text-muted-foreground" />
          ) : (
            <EyeOff className="h-3 w-3 text-muted-foreground/50" />
          )}
        </button>
      )}

      {/* Delete (external links) */}
      {onDelete && (
        <button
          className="shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive/10"
          onClick={(e) => { e.stopPropagation(); onDelete() }}
        >
          <Trash2 className="h-3 w-3 text-destructive/70" />
        </button>
      )}
    </div>
  )

  if (disabled && disabledReason) {
    return (
      <TooltipProvider delayDuration={300}>
        <Tooltip>
          <TooltipTrigger asChild>{row}</TooltipTrigger>
          <TooltipContent side="right" className="text-xs">{disabledReason}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return row
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

interface UnifiedSiteTreeProps {
  items: UnifiedTreeItem[]
  selection: Selection | null
  onSelect: (selection: Selection) => void
  onToggleVisibility?: (itemId: string) => void
  onTreeChange?: (newTree: UnifiedTreeItem[]) => void
  onAddPage?: () => void
  onAddExternalLink?: () => void
  onRemoveExternalLink?: (itemId: string) => void
}

export function UnifiedSiteTree({
  items,
  selection,
  onSelect,
  onToggleVisibility,
  onTreeChange,
  onAddPage,
  onAddExternalLink,
  onRemoveExternalLink,
}: UnifiedSiteTreeProps) {
  const { t } = useTranslation(['site', 'common'])
  const { defaultLang } = useLanguages()

  const [activeId, setActiveId] = useState<string | null>(null)
  const [overId, setOverId] = useState<string | null>(null)
  const [offsetLeft, setOffsetLeft] = useState(0)

  const isSelected = (type: SelectionType, id?: string) => {
    if (!selection) return false
    if (selection.type !== type) return false
    if (id !== undefined) return selection.id === id
    return true
  }

  // Split visible (menu) and hidden items
  const menuItems = items.filter(item => item.visible)
  const hiddenItems = items.filter(item => !item.visible)

  // Flatten menu items for DnD (hidden items are not draggable)
  const flatMenuItems = useMemo(() => flattenTree(menuItems), [menuItems])
  const sortableIds = useMemo(() => flatMenuItems.map(f => f.item.id), [flatMenuItems])

  // Projection for drop indicator
  const projection = useMemo<Projection | null>(() => {
    if (!activeId || !overId) return null
    return getProjection(flatMenuItems, activeId, overId, offsetLeft)
  }, [flatMenuItems, activeId, overId, offsetLeft])

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id))
  }

  const handleDragOver = (event: DragOverEvent) => {
    const { over, delta } = event
    setOverId(over ? String(over.id) : null)
    setOffsetLeft(delta.x)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id && projection && onTreeChange) {
      const newTree = applyDragMove(
        items,
        String(active.id),
        String(over.id),
        projection,
      )
      onTreeChange(newTree)
    }

    setActiveId(null)
    setOverId(null)
    setOffsetLeft(0)
  }

  const handleDragCancel = () => {
    setActiveId(null)
    setOverId(null)
    setOffsetLeft(0)
  }

  const mapItemToSelection = (item: UnifiedTreeItem): Selection => {
    switch (item.type) {
      case 'page':
        return { type: 'page', id: item.pageRef }
      case 'collection':
        return { type: 'group', id: item.collectionRef }
      case 'external-link':
        return { type: 'external-link', id: item.id }
    }
  }

  const isItemSelected = (item: UnifiedTreeItem): boolean => {
    if (item.type === 'page') return isSelected('page', item.pageRef)
    if (item.type === 'collection') return isSelected('group', item.collectionRef)
    if (item.type === 'external-link') return isSelected('external-link', item.id)
    return false
  }

  // Active drag item for overlay
  const activeItem = activeId
    ? flatMenuItems.find(f => f.item.id === activeId)
    : null

  // Render a hidden (non-draggable) item
  // Collections without index are visually dimmed but still clickable
  // (opens GroupPageViewer where the user can enable the index page)
  const renderHiddenItem = (item: UnifiedTreeItem) => {
    const isCollectionWithoutIndex = item.type === 'collection' && !item.hasIndex

    return (
      <div
        key={item.id}
        className={cn(
          'group flex w-full items-center gap-1 rounded-md px-2 py-1 text-sm transition-colors',
          isItemSelected(item)
            ? 'bg-primary/10 text-primary'
            : 'hover:bg-muted/50',
        )}
      >
        <button
          className="flex items-center gap-2 flex-1 min-w-0"
          onClick={() => onSelect(mapItemToSelection(item))}
        >
          {getItemIcon(item)}
          <span className={cn('truncate text-left', isCollectionWithoutIndex && 'text-muted-foreground/70')}>
            {resolveLabel(item.label, defaultLang)}
            {item.type === 'collection' && '/'}
          </span>
          {isCollectionWithoutIndex && (
            <span className="text-[10px] text-muted-foreground/50 shrink-0">
              {t('unifiedTree.noIndexPage')}
            </span>
          )}
        </button>
        {/* Toggle visibility: only for items that can be made visible */}
        {onToggleVisibility && !isCollectionWithoutIndex && (
          <button
            className="shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:bg-muted"
            onClick={() => onToggleVisibility(item.id)}
          >
            <EyeOff className="h-3 w-3 text-muted-foreground/50" />
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <div className="px-2 py-2 space-y-1">
          {/* Settings / Appearance / Footer */}
          <div className="space-y-1 mb-3 pb-3 border-b">
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                isSelected('general') ? 'bg-primary/10 text-primary' : 'hover:bg-muted/50'
              )}
              onClick={() => onSelect({ type: 'general' })}
            >
              <Settings className="h-4 w-4" />
              {t('tree.general')}
            </button>
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                isSelected('appearance') ? 'bg-primary/10 text-primary' : 'hover:bg-muted/50'
              )}
              onClick={() => onSelect({ type: 'appearance' })}
            >
              <Palette className="h-4 w-4" />
              {t('tree.appearance')}
            </button>
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                isSelected('footer') ? 'bg-primary/10 text-primary' : 'hover:bg-muted/50'
              )}
              onClick={() => onSelect({ type: 'footer' })}
            >
              <PanelBottom className="h-4 w-4" />
              {t('tree.footerMenu')}
            </button>
          </div>

          {/* Draggable menu items */}
          {menuItems.length === 0 && hiddenItems.length === 0 ? (
            <p className="px-2 py-4 text-xs text-muted-foreground italic text-center">
              {t('tree.noPages')}
            </p>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDragEnd={handleDragEnd}
              onDragCancel={handleDragCancel}
            >
              <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
                {flatMenuItems.map(flatItem => {
                  const { item } = flatItem
                  const isCollectionWithoutIndex = item.type === 'collection' && !item.hasIndex

                  return (
                    <SortableTreeItem
                      key={item.id}
                      flatItem={flatItem}
                      isSelected={isItemSelected(item)}
                      onSelect={() => onSelect(mapItemToSelection(item))}
                      onToggleVisibility={
                        onToggleVisibility && !isCollectionWithoutIndex && item.type !== 'external-link'
                          ? () => onToggleVisibility(item.id)
                          : undefined
                      }
                      onDelete={
                        item.type === 'external-link' && onRemoveExternalLink
                          ? () => onRemoveExternalLink(item.id)
                          : undefined
                      }
                      disabled={isCollectionWithoutIndex}
                      disabledReason={isCollectionWithoutIndex ? t('unifiedTree.noIndexPage') : undefined}
                      projectedDepth={
                        activeId && projection && item.id === overId
                          ? projection.depth
                          : undefined
                      }
                      lang={defaultLang}
                    />
                  )
                })}
              </SortableContext>

              {/* Drag overlay */}
              <DragOverlay>
                {activeItem && (
                  <SortableTreeItem
                    flatItem={activeItem}
                    isSelected={false}
                    onSelect={() => {}}
                    isOverlay
                    projectedDepth={projection?.depth}
                    lang={defaultLang}
                  />
                )}
              </DragOverlay>
            </DndContext>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-1 pt-1">
            {onAddPage && (
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 justify-start text-xs text-muted-foreground hover:text-foreground h-7"
                onClick={onAddPage}
              >
                <Plus className="h-3 w-3 mr-1" />
                Page
              </Button>
            )}
            {onAddExternalLink && (
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 justify-start text-xs text-muted-foreground hover:text-foreground h-7"
                onClick={onAddExternalLink}
              >
                <ExternalLink className="h-3 w-3 mr-1" />
                Link
              </Button>
            )}
          </div>

          {/* Not in menu section */}
          {hiddenItems.length > 0 && (
            <>
              <div className="flex items-center gap-2 px-2 pt-4 pb-1">
                <div className="h-px flex-1 bg-border" />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {t('unifiedTree.notInMenu')}
                </span>
                <div className="h-px flex-1 bg-border" />
              </div>
              {hiddenItems.map(item => renderHiddenItem(item))}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
