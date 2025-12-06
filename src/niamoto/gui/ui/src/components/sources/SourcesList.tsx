/**
 * Sources List - Display configured pre-calculated sources
 *
 * Shows a list of CSV sources configured for a reference group,
 * with options to view details and remove.
 */

import { FileSpreadsheet, Trash2, MoreVertical, Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
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
import { useState } from 'react'
import type { ConfiguredSource } from '@/hooks/useSources'

interface SourcesListProps {
  sources: ConfiguredSource[]
  onRemove: (sourceName: string) => void
  isRemoving?: boolean
}

export function SourcesList({ sources, onRemove, isRemoving }: SourcesListProps) {
  const [sourceToDelete, setSourceToDelete] = useState<string | null>(null)

  const handleConfirmDelete = () => {
    if (sourceToDelete) {
      onRemove(sourceToDelete)
      setSourceToDelete(null)
    }
  }

  if (sources.length === 0) {
    return (
      <div className="flex min-h-[60px] items-center justify-center rounded-md border-2 border-dashed border-muted-foreground/25 p-3">
        <p className="text-sm text-muted-foreground">Aucune source configuree</p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-2">
        {sources.map((source) => (
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
                  Supprimer
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
            <AlertDialogTitle>Supprimer la source ?</AlertDialogTitle>
            <AlertDialogDescription>
              Cette action supprimera la configuration de la source "{sourceToDelete}".
              Le fichier CSV ne sera pas supprime.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
