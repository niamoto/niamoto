/**
 * SiteTreeView - Unified tree view of site pages
 *
 * Displays:
 * - Static pages section
 * - Group pages section (from export.yml groups)
 * - Selection for editing
 */

import { useState } from 'react'
import {
  FileText,
  Folder,
  FolderOpen,
  ChevronRight,
  ChevronDown,
  Plus,
  Pencil,
  Trash2,
  Home,
  Info,
  Book,
  LayoutGrid,
  FileJson,
  Loader2,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { cn } from '@/lib/utils'
import type { StaticPage, GroupInfo } from '@/features/site/hooks/useSiteConfig'

export type SelectionType = 'static' | 'group'

export interface Selection {
  type: SelectionType
  name: string
}

interface SiteTreeViewProps {
  staticPages: StaticPage[]
  groups: GroupInfo[]
  groupsLoading?: boolean
  selection: Selection | null
  onSelect: (selection: Selection | null) => void
  onAddStaticPage: () => void
  onDeleteStaticPage: (pageName: string) => void
}

// Icon mapping for common page names
const PAGE_ICONS: Record<string, typeof FileText> = {
  home: Home,
  index: Home,
  about: Info,
  methodology: Book,
}

function getPageIcon(name: string) {
  const normalizedName = name.toLowerCase()
  for (const [key, Icon] of Object.entries(PAGE_ICONS)) {
    if (normalizedName.includes(key)) {
      return Icon
    }
  }
  return FileText
}

// Static page item
function StaticPageItem({
  page,
  isSelected,
  onSelect,
  onDelete,
}: {
  page: StaticPage
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const Icon = getPageIcon(page.name)
  const hasContent = page.context?.content_markdown || page.context?.content_source

  return (
    <div
      className={cn(
        'group flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
        isSelected ? 'bg-primary/10 text-primary' : 'hover:bg-muted/50'
      )}
      onClick={onSelect}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="flex-1 truncate">{page.name}</span>
      {hasContent && (
        <Badge variant="secondary" className="text-[10px] px-1 py-0">
          MD
        </Badge>
      )}
      <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={(e) => {
            e.stopPropagation()
            onSelect()
          }}
        >
          <Pencil className="h-3 w-3" />
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => e.stopPropagation()}
            >
              <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Supprimer la page ?</AlertDialogTitle>
              <AlertDialogDescription>
                Etes-vous sur de vouloir supprimer la page "{page.name}" ?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Annuler</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => onDelete()}
                className="bg-destructive hover:bg-destructive/90"
              >
                Supprimer
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}

// Group item
function GroupItem({
  group,
  isSelected,
  onSelect,
}: {
  group: GroupInfo
  isSelected: boolean
  onSelect: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const hasIndex = group.index_generator?.enabled

  return (
    <div>
      {/* Group header */}
      <div
        className={cn(
          'group flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
          isSelected ? 'bg-primary/10 text-primary' : 'hover:bg-muted/50'
        )}
        onClick={onSelect}
      >
        <button
          className="shrink-0 p-0.5 hover:bg-muted rounded"
          onClick={(e) => {
            e.stopPropagation()
            setExpanded(!expanded)
          }}
        >
          {expanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
        </button>
        {expanded ? (
          <FolderOpen className="h-4 w-4 shrink-0 text-amber-600" />
        ) : (
          <Folder className="h-4 w-4 shrink-0 text-amber-600" />
        )}
        <span className="flex-1 truncate font-medium">{group.name}/</span>
        <Badge variant="outline" className="text-[10px] px-1 py-0">
          {group.widgets_count} widgets
        </Badge>
      </div>

      {/* Expanded children */}
      {expanded && (
        <div className="ml-6 mt-1 space-y-0.5 border-l pl-2">
          {hasIndex && (
            <div className="flex items-center gap-2 rounded-md px-2 py-1 text-xs text-muted-foreground">
              <LayoutGrid className="h-3 w-3" />
              <span>index.html</span>
              <Badge variant="secondary" className="text-[9px] px-1 py-0">
                {group.index_generator?.page_config?.items_per_page || 24}/page
              </Badge>
            </div>
          )}
          <div className="flex items-center gap-2 rounded-md px-2 py-1 text-xs text-muted-foreground">
            <FileJson className="h-3 w-3" />
            <span>{group.output_pattern}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export function SiteTreeView({
  staticPages,
  groups,
  groupsLoading,
  selection,
  onSelect,
  onAddStaticPage,
  onDeleteStaticPage,
}: SiteTreeViewProps) {
  const isStaticSelected = selection?.type === 'static'
  const isGroupSelected = selection?.type === 'group'

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Folder className="h-4 w-4" />
              Structure du site
            </CardTitle>
            <CardDescription>Pages statiques et pages de groupes</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Static pages section */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Pages statiques
            </h4>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={onAddStaticPage}>
              <Plus className="mr-1 h-3 w-3" />
              Ajouter
            </Button>
          </div>
          {staticPages.length === 0 ? (
            <p className="px-2 py-2 text-xs text-muted-foreground italic">
              Aucune page statique
            </p>
          ) : (
            <div className="space-y-0.5">
              {staticPages.map((page) => (
                <StaticPageItem
                  key={page.name}
                  page={page}
                  isSelected={isStaticSelected && selection?.name === page.name}
                  onSelect={() => onSelect({ type: 'static', name: page.name })}
                  onDelete={() => onDeleteStaticPage(page.name)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Groups section */}
        <div>
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Pages de groupes
          </h4>
          {groupsLoading ? (
            <div className="flex items-center gap-2 px-2 py-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              Chargement...
            </div>
          ) : groups.length === 0 ? (
            <p className="px-2 py-2 text-xs text-muted-foreground italic">
              Aucun groupe configure
            </p>
          ) : (
            <div className="space-y-0.5">
              {groups.map((group) => (
                <GroupItem
                  key={group.name}
                  group={group}
                  isSelected={isGroupSelected && selection?.name === group.name}
                  onSelect={() => onSelect({ type: 'group', name: group.name })}
                />
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
