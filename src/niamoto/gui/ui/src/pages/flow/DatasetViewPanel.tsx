/**
 * DatasetViewPanel - Shows dataset statistics and data preview
 *
 * Used under the "Donnees" section in Flow for viewing imported datasets
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
import { ArrowLeft, ExternalLink, Database, Trash2, Loader2 } from 'lucide-react'
import { TableBrowser, TableStats } from '@/components/data'
import { deleteEntity } from '@/lib/api/import'

interface DatasetViewPanelProps {
  datasetName: string
  tableName: string
  connectorType?: string
  path?: string
  onBack?: () => void
  onDeleted?: () => void
}

export function DatasetViewPanel({
  datasetName,
  tableName,
  connectorType,
  path,
  onBack,
  onDeleted,
}: DatasetViewPanelProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteTable, setDeleteTable] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)

  const openInDataExplorer = () => {
    // Navigate to data explorer with table pre-selected
    navigate(`/data/explorer?table=${encodeURIComponent(tableName)}`)
  }

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      await deleteEntity('dataset', datasetName, deleteTable)
      // Invalidate queries to refresh the sidebar
      queryClient.invalidateQueries({ queryKey: ['entities'] })
      queryClient.invalidateQueries({ queryKey: ['references'] })
      setDialogOpen(false)
      // Navigate back
      onDeleted?.()
      onBack?.()
    } catch (error) {
      console.error('Error deleting dataset:', error)
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
              <Database className="h-6 w-6 text-blue-500" />
              {datasetName}
            </h1>
            <p className="text-muted-foreground">
              Dataset importe{' '}
              {connectorType && (
                <Badge variant="outline" className="ml-2">
                  {connectorType}
                </Badge>
              )}
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
                <AlertDialogTitle>Supprimer le dataset "{datasetName}" ?</AlertDialogTitle>
                <AlertDialogDescription>
                  Cette action supprimera le dataset de la configuration import.yml.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <div className="flex items-center space-x-2 py-4">
                <Checkbox
                  id="delete-table"
                  checked={deleteTable}
                  onCheckedChange={(checked) => setDeleteTable(checked === true)}
                />
                <label
                  htmlFor="delete-table"
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

      {/* Stats */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Statistiques</CardTitle>
          {path && (
            <CardDescription className="font-mono text-xs">{path}</CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <TableStats tableName={tableName} />
        </CardContent>
      </Card>

      {/* Data Preview */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Apercu des donnees</CardTitle>
          <CardDescription>Premieres lignes de la table {tableName}</CardDescription>
        </CardHeader>
        <CardContent>
          <TableBrowser
            tableName={tableName}
            pageSize={15}
            maxColumns={6}
            onOpenInExplorer={openInDataExplorer}
          />
        </CardContent>
      </Card>
    </div>
  )
}
