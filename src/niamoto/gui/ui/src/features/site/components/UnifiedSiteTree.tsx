/**
 * UnifiedSiteTree - Unified page + navigation tree (read-only, Phase B)
 *
 * Displays pages, collections, and external links in a single list.
 * Items in the menu appear first, followed by a "Not in menu" section
 * for orphan pages and unreferenced collections.
 *
 * Phase B: read-only display + selection
 * Phase C: will add drag-and-drop, toggle visibility, edit
 */

import { useTranslation } from 'react-i18next'
import {
  Layers,
  ExternalLink,
  Settings,
  Palette,
  Eye,
  EyeOff,
} from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import type { UnifiedTreeItem } from '../hooks/useUnifiedSiteTree'
import { getTemplateIcon } from './PagesOverview'
import type { Selection, SelectionType } from '../hooks/useSiteBuilderState'

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

function getItemLabel(item: UnifiedTreeItem): string {
  if (typeof item.label === 'string') return item.label
  // LocalizedString can be { fr: "...", en: "..." } — show first available
  if (typeof item.label === 'object' && item.label !== null) {
    const values = Object.values(item.label)
    return (values[0] as string) || '—'
  }
  return '—'
}

// =============================================================================
// TREE ITEM COMPONENT
// =============================================================================

interface TreeItemRowProps {
  item: UnifiedTreeItem
  depth: number
  isSelected: boolean
  onSelect: () => void
  disabled?: boolean
  disabledReason?: string
}

function TreeItemRow({ item, depth, isSelected, onSelect, disabled, disabledReason }: TreeItemRowProps) {
  const content = (
    <button
      className={cn(
        'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
        isSelected
          ? 'bg-primary/10 text-primary'
          : disabled
            ? 'opacity-50 cursor-default'
            : 'hover:bg-muted/50',
      )}
      style={{ paddingLeft: `${8 + depth * 16}px` }}
      onClick={disabled ? undefined : onSelect}
    >
      {getItemIcon(item)}
      <span className={cn('truncate flex-1 text-left', disabled && 'text-muted-foreground')}>
        {getItemLabel(item)}
        {item.type === 'collection' && '/'}
      </span>
      {/* Visibility indicator */}
      {item.visible ? (
        <Eye className="h-3 w-3 text-muted-foreground/40" />
      ) : (
        <EyeOff className="h-3 w-3 text-muted-foreground/30" />
      )}
      {/* Template badge for pages */}
      {item.type === 'page' && item.template && (
        <Badge variant="outline" className="text-[9px] h-4 font-normal px-1">
          {item.template.replace('.html', '')}
        </Badge>
      )}
    </button>
  )

  if (disabled && disabledReason) {
    return (
      <TooltipProvider delayDuration={300}>
        <Tooltip>
          <TooltipTrigger asChild>
            {content}
          </TooltipTrigger>
          <TooltipContent side="right" className="text-xs">
            {disabledReason}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return content
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

interface UnifiedSiteTreeProps {
  items: UnifiedTreeItem[]
  selection: Selection | null
  onSelect: (selection: Selection) => void
  /** Extra buttons for Settings/Appearance (kept during Phase B transition) */
  showSettingsButtons?: boolean
}

export function UnifiedSiteTree({
  items,
  selection,
  onSelect,
  showSettingsButtons = true,
}: UnifiedSiteTreeProps) {
  const { t } = useTranslation(['site', 'common'])

  const isSelected = (type: SelectionType, id?: string) => {
    if (!selection) return false
    if (selection.type !== type) return false
    if (id !== undefined) return selection.id === id
    return true
  }

  // Split items into menu (visible) and not-in-menu (not visible)
  const menuItems = items.filter(item => item.visible)
  const hiddenItems = items.filter(item => !item.visible)

  const mapItemToSelection = (item: UnifiedTreeItem): Selection => {
    switch (item.type) {
      case 'page':
        return { type: 'page', id: item.pageRef }
      case 'collection':
        return { type: 'group', id: item.collectionRef }
      case 'external-link':
        return { type: 'navigation', id: item.id }
    }
  }

  const isItemSelected = (item: UnifiedTreeItem): boolean => {
    if (item.type === 'page') return isSelected('page', item.pageRef)
    if (item.type === 'collection') return isSelected('group', item.collectionRef)
    return false
  }

  const renderItem = (item: UnifiedTreeItem, depth: number = 0) => {
    const isCollectionWithoutIndex = item.type === 'collection' && !item.hasIndex

    return (
      <div key={item.id}>
        <TreeItemRow
          item={item}
          depth={depth}
          isSelected={isItemSelected(item)}
          onSelect={() => onSelect(mapItemToSelection(item))}
          disabled={isCollectionWithoutIndex}
          disabledReason={isCollectionWithoutIndex ? t('unifiedTree.noIndexPage') : undefined}
        />
        {item.children.length > 0 && (
          <div>
            {item.children.map(child => renderItem(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <div className="px-2 py-2 space-y-1">
          {/* Settings buttons (transition: will move to toolbar in Phase C) */}
          {showSettingsButtons && (
            <div className="space-y-1 mb-3 pb-3 border-b">
              <button
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                  isSelected('general')
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-muted/50'
                )}
                onClick={() => onSelect({ type: 'general' })}
              >
                <Settings className="h-4 w-4" />
                {t('tree.general')}
              </button>
              <button
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                  isSelected('appearance')
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-muted/50'
                )}
                onClick={() => onSelect({ type: 'appearance' })}
              >
                <Palette className="h-4 w-4" />
                {t('tree.appearance')}
              </button>
              <button
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                  isSelected('footer')
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-muted/50'
                )}
                onClick={() => onSelect({ type: 'footer' })}
              >
                <Settings className="h-4 w-4" />
                {t('tree.footerMenu')}
              </button>
            </div>
          )}

          {/* Menu items */}
          {menuItems.length === 0 && hiddenItems.length === 0 ? (
            <p className="px-2 py-4 text-xs text-muted-foreground italic text-center">
              {t('tree.noPages')}
            </p>
          ) : (
            <>
              {menuItems.map(item => renderItem(item))}

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
                  {hiddenItems.map(item => renderItem(item))}
                </>
              )}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
