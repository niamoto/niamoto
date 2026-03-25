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

import { useState, useRef, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
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
  Sparkles,
  Loader2,
  Home,
  BookOpen,
  Users,
  Mail,
  Download,
  List,
  Newspaper,
  ScrollText,
  type LucideIcon,
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
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import type {
  NavigationItem,
  StaticPage,
  GroupInfo,
  TemplateInfo,
} from '@/features/site/hooks/useSiteConfig'
import { useLanguages } from '@/shared/contexts/LanguageContext'

// =============================================================================
// Template Configuration (shared with TemplateList)
// =============================================================================

type TemplateCategory = 'landing' | 'content' | 'project' | 'reference'

const CATEGORY_ORDER: Record<TemplateCategory, number> = {
  landing: 0,
  content: 1,
  project: 2,
  reference: 3,
}

interface TemplateDefinition {
  icon: LucideIcon
  category: TemplateCategory
}

const TEMPLATE_CONFIG: Record<string, TemplateDefinition> = {
  'index.html': { icon: Home, category: 'landing' },
  'page.html': { icon: FileText, category: 'content' },
  'article.html': { icon: Newspaper, category: 'content' },
  'documentation.html': { icon: ScrollText, category: 'content' },
  'team.html': { icon: Users, category: 'project' },
  'contact.html': { icon: Mail, category: 'project' },
  'resources.html': { icon: Download, category: 'reference' },
  'bibliography.html': { icon: BookOpen, category: 'reference' },
  'glossary.html': { icon: List, category: 'reference' },
}

// Group templates by category
function groupTemplatesByCategory(templates: TemplateInfo[]): Map<TemplateCategory, TemplateInfo[]> {
  const groups = new Map<TemplateCategory, TemplateInfo[]>()

  // Initialize groups in order
  for (const category of Object.keys(CATEGORY_ORDER) as TemplateCategory[]) {
    groups.set(category, [])
  }

  // Group templates
  for (const template of templates) {
    const config = TEMPLATE_CONFIG[template.name]
    const category = config?.category || 'content'
    groups.get(category)?.push(template)
  }

  // Remove empty groups
  for (const [category, items] of groups) {
    if (items.length === 0) {
      groups.delete(category)
    }
  }

  return groups
}

// =============================================================================
// Types
// =============================================================================

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
  templates?: TemplateInfo[]
  onCreatePage?: (name: string, template: string) => Promise<StaticPage | null>
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
  // For inline page creation
  templates?: TemplateInfo[]
  onCreatePage?: (name: string, template: string) => Promise<StaticPage | null>
}

function NavItemEditor({
  item,
  availablePages,
  onUpdate,
  onRemove,
  onAddChild,
  isChild = false,
  dragHandleProps,
  templates,
  onCreatePage,
}: NavItemEditorProps) {
  const { t } = useTranslation(['site', 'common'])
  const [open, setOpen] = useState(false)
  const hasChildren = item.children && item.children.length > 0

  // State for inline page creation
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newPageName, setNewPageName] = useState('')
  const [newPageTemplate, setNewPageTemplate] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  // Group templates by category for display
  const groupedTemplates = useMemo(
    () => groupTemplatesByCategory(templates || []),
    [templates]
  )

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

  const handleCreatePage = async () => {
    if (!newPageName.trim() || !newPageTemplate || !onCreatePage) return

    setIsCreating(true)
    try {
      const createdPage = await onCreatePage(newPageName.trim(), newPageTemplate)
      if (createdPage) {
        // Auto-link to the newly created page
        onUpdate({
          ...item,
          text: item.text || createdPage.name,
          url: `/${createdPage.output_file}`,
        })
        // Reset form and close
        setNewPageName('')
        setNewPageTemplate('')
        setShowCreateForm(false)
        setOpen(false)
      }
    } finally {
      setIsCreating(false)
    }
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

      {/* Text input with i18n support */}
      <LocalizedInput
        value={item.text}
        onChange={(text) => onUpdate({ ...item, text: text || '' })}
        placeholder={isChild ? t('navigation.submenu') : t('navigation.menuText')}
        className={cn('flex-1 min-w-0', isChild && '[&_input]:h-8 [&_input]:text-sm')}
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
                {item.url || t('common:placeholders.selectOption')}
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
                    {t('navigation.staticPages')}
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
                    {t('navigation.groupPages')}
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
                  {t('navigation.customUrl')}
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

              {/* Create new page option */}
              {onCreatePage && groupedTemplates.size > 0 && (
                <div className="border-t p-2">
                  {!showCreateForm ? (
                    <button
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted text-primary"
                      onClick={() => setShowCreateForm(true)}
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>{t('navigation.createNewPage')}</span>
                    </button>
                  ) : (
                    <div className="space-y-2 px-2">
                      <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                        <Sparkles className="h-3 w-3" />
                        {t('navigation.createNewPage')}
                      </p>
                      <Input
                        value={newPageName}
                        onChange={(e) => setNewPageName(e.target.value)}
                        placeholder={t('navigation.pageName')}
                        className="h-8 text-sm"
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                      />
                      <Select value={newPageTemplate} onValueChange={setNewPageTemplate}>
                        <SelectTrigger className="h-8 text-sm">
                          <SelectValue placeholder={t('navigation.selectTemplate')}>
                            {newPageTemplate && (() => {
                              const config = TEMPLATE_CONFIG[newPageTemplate]
                              const Icon = config?.icon || FileText
                              return (
                                <span className="flex items-center gap-2">
                                  <Icon className="h-3 w-3" />
                                  {newPageTemplate.replace('.html', '')}
                                </span>
                              )
                            })()}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {Array.from(groupedTemplates.entries()).map(([category, items]) => (
                            <SelectGroup key={category}>
                              <SelectLabel className="text-xs uppercase text-muted-foreground">
                                {t(`templates.categories.${category}`)}
                              </SelectLabel>
                              {items.map((template) => {
                                const config = TEMPLATE_CONFIG[template.name]
                                const Icon = config?.icon || FileText
                                return (
                                  <SelectItem key={template.name} value={template.name}>
                                    <span className="flex items-center gap-2">
                                      <Icon className="h-4 w-4" />
                                      {template.name.replace('.html', '')}
                                    </span>
                                  </SelectItem>
                                )
                              })}
                            </SelectGroup>
                          ))}
                        </SelectContent>
                      </Select>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          className="flex-1 h-8"
                          onClick={handleCreatePage}
                          disabled={!newPageName.trim() || !newPageTemplate || isCreating}
                        >
                          {isCreating ? (
                            <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          ) : (
                            <Plus className="h-3 w-3 mr-1" />
                          )}
                          {t('navigation.createAndLink')}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8"
                          onClick={() => {
                            setShowCreateForm(false)
                            setNewPageName('')
                            setNewPageTemplate('')
                          }}
                        >
                          {t('common:actions.cancel')}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </PopoverContent>
        </Popover>
      )}

      {/* Parent indicator if has children */}
      {hasChildren && !isChild && (
        <span className="text-xs text-muted-foreground px-2">
          {item.children?.length} {t('navigation.submenus')}
        </span>
      )}

      {/* Add sub-menu button - only for top-level items */}
      {!isChild && onAddChild && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onAddChild}
          className="h-8 w-8 shrink-0"
          title={t('navigation.addSubmenu')}
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
  templates?: TemplateInfo[]
  onCreatePage?: (name: string, template: string) => Promise<StaticPage | null>
}

function SortableNavItem({ id, item, availablePages, onUpdate, onRemove, allowSubmenus = true, templates, onCreatePage }: SortableNavItemProps) {
  const { t } = useTranslation(['site', 'common'])
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
              <LocalizedInput
                value={item.text}
                onChange={(text) => onUpdate({ ...item, text: text || '' })}
                placeholder={t('navigation.menuText')}
                className="flex-1 min-w-0"
              />
              <span className="text-xs text-muted-foreground px-2">
                {item.children?.length} {t('navigation.submenus')}
              </span>
              {allowSubmenus && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleAddChild}
                  className="h-8 w-8 shrink-0"
                  title={t('navigation.addSubmenu')}
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
                  templates={templates}
                  onCreatePage={onCreatePage}
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
            templates={templates}
            onCreatePage={onCreatePage}
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
  templates = [],
  onCreatePage,
  title,
  description,
  allowSubmenus = true,
}: NavigationBuilderProps) {
  const { t } = useTranslation(['site', 'common'])
  const { defaultLang } = useLanguages()
  const effectiveTitle = title || t('tree.navigation')
  const effectiveDescription = description || t('navigation.mainDescription')
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

  // Generate stable IDs for sortable items
  // We maintain a stable array of IDs that grows with the items array
  // IDs are only added, never removed (until component unmounts)
  const idCounterRef = useRef(0)
  const stableIdsRef = useRef<string[]>([])

  // Ensure we have enough stable IDs for all items
  const itemIds = useMemo(() => {
    // Grow the ID array if needed (when items are added)
    while (stableIdsRef.current.length < items.length) {
      idCounterRef.current += 1
      stableIdsRef.current.push(`nav-${idCounterRef.current}`)
    }
    // Return IDs for current items (slice to match current length)
    return stableIdsRef.current.slice(0, items.length)
  }, [items.length])

  // Get stable ID for an item by index
  const getId = (index: number): string => {
    return itemIds[index]
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
      const oldIndex = itemIds.findIndex((id) => id === active.id)
      const newIndex = itemIds.findIndex((id) => id === over.id)

      if (oldIndex !== -1 && newIndex !== -1) {
        // Reorder both items and their IDs to maintain stability
        const newItems = arrayMove(items, oldIndex, newIndex)
        stableIdsRef.current = arrayMove(stableIdsRef.current, oldIndex, newIndex)
        onChange(newItems)
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
    // Remove both the item and its ID to maintain synchronization
    stableIdsRef.current = stableIdsRef.current.filter((_, i) => i !== index)
    onChange(items.filter((_, i) => i !== index))
  }

  // Helper to resolve LocalizedString for preview
  const resolveText = (text: LocalizedString | undefined): string => {
    if (!text) return ''
    if (typeof text === 'string') return text
    return text[defaultLang] || Object.values(text)[0] || ''
  }

  // Render preview item with potential children
  const renderPreviewItem = (item: NavigationItem, index: number) => {
    const hasChildren = item.children && item.children.length > 0
    const displayText = resolveText(item.text) || t('navigation.untitled')
    return (
      <div key={index} className="flex items-center gap-1">
        <span className="rounded-md bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
          {displayText}
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
              {effectiveTitle}
            </CardTitle>
            <CardDescription>{effectiveDescription}</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleAdd}>
            <Plus className="mr-1 h-4 w-4" />
            {t('common:actions.add')}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <div className="flex min-h-[100px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-4 text-center">
            <Navigation className="mb-2 h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">{t('navigation.noMenuConfigured')}</p>
            <Button variant="link" size="sm" onClick={handleAdd} className="mt-2">
              <Plus className="mr-1 h-4 w-4" />
              {t('navigation.addFirstElement')}
            </Button>
          </div>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext
              items={itemIds}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {items.map((item, index) => (
                  <SortableNavItem
                    key={getId(index)}
                    id={getId(index)}
                    item={item}
                    availablePages={availablePages}
                    onUpdate={(updated) => handleUpdate(index, updated)}
                    onRemove={() => handleRemove(index)}
                    allowSubmenus={allowSubmenus}
                    templates={templates}
                    onCreatePage={onCreatePage}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}

        {/* Preview */}
        {items.length > 0 && (
          <div className="mt-4 rounded-lg border bg-muted/30 p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">{t('preview.title')}</p>
            <div className="flex flex-wrap gap-2">
              {items.map((item, index) => renderPreviewItem(item, index))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
