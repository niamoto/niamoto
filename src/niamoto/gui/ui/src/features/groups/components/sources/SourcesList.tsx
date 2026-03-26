/**
 * Sources List - Display configured data sources
 *
 * Shows a list of sources available for a reference group:
 * - Built-in reference entity sources (from database)
 * - CSV-based pre-calculated sources
 */

import { FileSpreadsheet, Trash2, MoreVertical, Database, Shield, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ConfiguredSource } from '@/features/groups/hooks/useSources'

interface SourcesListProps {
  sources: ConfiguredSource[]
  onRemove: (sourceName: string) => void
  isRemoving?: boolean
}

export function SourcesList({ sources, onRemove, isRemoving }: SourcesListProps) {
  const { t } = useTranslation('sources')
  const [sourceToDelete, setSourceToDelete] = useState<string | null>(null)
  const [expandedSource, setExpandedSource] = useState<string | null>(null)

  const handleConfirmDelete = () => {
    if (sourceToDelete) {
      onRemove(sourceToDelete)
      setSourceToDelete(null)
    }
  }

  if (sources.length === 0) {
    return (
      <div className="flex min-h-[60px] items-center justify-center rounded-md border-2 border-dashed border-muted-foreground/25 p-3">
        <p className="text-sm text-muted-foreground">{t('noSources', 'No sources configured')}</p>
      </div>
    )
  }

  // Separate built-in and custom sources
  const builtinSources = sources.filter(s => s.is_builtin)
  const customSources = sources.filter(s => !s.is_builtin)

  return (
    <>
      <div className="space-y-2">
        {/* Built-in sources first */}
        {builtinSources.map((source) => (
          <Collapsible
            key={source.name}
            open={expandedSource === source.name}
            onOpenChange={(open) => setExpandedSource(open ? source.name : null)}
          >
            <div className="rounded-md border bg-muted/30 p-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-blue-500/10">
                  <Shield className="h-4 w-4 text-blue-500" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">{source.name}</p>
                    <Badge variant="secondary" className="text-xs">
                      {t('builtin', 'Built-in')}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t('referenceData', 'Reference data')}
                  </p>
                </div>

                {source.columns && source.columns.length > 0 && (
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-8 gap-1">
                      <span className="text-xs text-muted-foreground">
                        {source.columns.length} {t('fields', 'fields')}
                      </span>
                      <ChevronDown className={`h-4 w-4 transition-transform ${expandedSource === source.name ? 'rotate-180' : ''}`} />
                    </Button>
                  </CollapsibleTrigger>
                )}
              </div>

              <CollapsibleContent>
                {source.columns && source.columns.length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <p className="text-xs text-muted-foreground mb-2">{t('availableFields', 'Available fields')}:</p>
                    <div className="flex flex-wrap gap-1">
                      {source.columns.map((col) => (
                        <Badge key={col} variant="outline" className="text-xs font-mono">
                          {col}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CollapsibleContent>
            </div>
          </Collapsible>
        ))}

        {/* Custom CSV sources */}
        {customSources.map((source) => (
          <div
            key={source.name}
            className="flex items-center gap-3 rounded-md border bg-card p-3"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10">
              <FileSpreadsheet className="h-4 w-4 text-primary" />
            </div>

            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{source.name}</p>
              <p className="text-xs text-muted-foreground truncate">
                {source.data_path}
              </p>
            </div>

            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Database className="h-3 w-3" />
              <span>{source.relation_plugin}</span>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => setSourceToDelete(source.name)}
                  className="text-destructive focus:text-destructive"
                  disabled={isRemoving}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t('delete', 'Delete')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ))}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!sourceToDelete} onOpenChange={() => setSourceToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('deleteConfirmTitle', 'Delete source?')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('deleteConfirmDescription', 'This will remove the source "{{name}}" configuration. The CSV file will not be deleted.', { name: sourceToDelete })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel', 'Cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('delete', 'Delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
