/**
 * ReferenceViewPanel - Shows reference statistics and data preview
 *
 * Used under the "Donnees" section in Flow for viewing imported references
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
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
import { ArrowLeft, ExternalLink, Network, Trash2, Loader2 } from 'lucide-react'
import { TableBrowser, TableStats } from '@/components/data'
import { deleteEntity } from '@/lib/api/import'

interface ReferenceViewPanelProps {
  referenceName: string
  tableName: string
  kind?: string
  hierarchyLevels?: string[]
  description?: string
  onBack?: () => void
  onDeleted?: () => void
}

export function ReferenceViewPanel({
  referenceName,
  tableName,
  kind,
  hierarchyLevels,
  description,
  onBack,
  onDeleted,
}: ReferenceViewPanelProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteTable, setDeleteTable] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Use the table name passed from parent (from EntityRegistry)
  const actualTableName = tableName

  const openInDataExplorer = () => {
    navigate(`/data/explorer?table=${encodeURIComponent(actualTableName)}`)
  }

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      await deleteEntity('reference', referenceName, deleteTable)
      // Invalidate queries to refresh the sidebar
      queryClient.invalidateQueries({ queryKey: ['entities'] })
      queryClient.invalidateQueries({ queryKey: ['references'] })
      setDialogOpen(false)
      // Navigate back
      onDeleted?.()
      onBack?.()
    } catch (error) {
      console.error('Error deleting reference:', error)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="ghost" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              <Network className="h-6 w-6 text-green-500" />
              {referenceName}
              {kind && (
                <Badge variant="secondary" className="ml-2">
                  {kind}
                </Badge>
              )}
            </h1>
            <p className="text-muted-foreground">
              {description || `Reference ${kind || 'flat'}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={openInDataExplorer}>
            <ExternalLink className="mr-2 h-4 w-4" />
            Ouvrir dans Data Explorer
          </Button>

          <AlertDialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <AlertDialogTrigger asChild>
              <Button variant="outline" className="text-destructive hover:bg-destructive/10">
                <Trash2 className="mr-2 h-4 w-4" />
                Supprimer
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Supprimer la reference "{referenceName}" ?</AlertDialogTitle>
                <AlertDialogDescription>
                  Cette action supprimera la reference de la configuration import.yml.
                  {kind === 'hierarchical' && (
                    <span className="mt-2 block text-amber-600">
                      Attention : les datasets lies a cette reference pourraient ne plus fonctionner.
                    </span>
                  )}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <div className="flex items-center space-x-2 py-4">
                <Checkbox
                  id="delete-table-ref"
                  checked={deleteTable}
                  onCheckedChange={(checked) => setDeleteTable(checked === true)}
                />
                <label
                  htmlFor="delete-table-ref"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Supprimer aussi la table de la base de donnees
                </label>
              </div>
              <AlertDialogFooter>
                <AlertDialogCancel>Annuler</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Suppression...
                    </>
                  ) : (
                    'Supprimer'
                  )}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Hierarchy info if applicable */}
      {kind === 'hierarchical' && hierarchyLevels && hierarchyLevels.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Hierarchie</CardTitle>
            <CardDescription>Structure taxonomique a {hierarchyLevels.length} niveaux</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {hierarchyLevels.map((level, idx) => (
                <div key={level} className="flex items-center gap-2">
                  <Badge variant="outline">{level}</Badge>
                  {idx < hierarchyLevels.length - 1 && (
                    <span className="text-muted-foreground">→</span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Statistiques</CardTitle>
          <CardDescription>Table: {actualTableName}</CardDescription>
        </CardHeader>
        <CardContent>
          <TableStats
            tableName={actualTableName}
            kind={kind}
            hierarchyLevels={hierarchyLevels}
          />
        </CardContent>
      </Card>

      {/* Data Preview */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Apercu des donnees</CardTitle>
          <CardDescription>
            Premieres lignes de la reference {referenceName}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TableBrowser
            tableName={actualTableName}
            pageSize={15}
            maxColumns={6}
            onOpenInExplorer={openInDataExplorer}
          />
        </CardContent>
      </Card>
    </div>
  )
}
