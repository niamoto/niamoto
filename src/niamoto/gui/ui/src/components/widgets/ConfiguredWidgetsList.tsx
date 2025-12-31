/**
 * ConfiguredWidgetsList - Display list of widgets already in transform.yml
 *
 * Shows configured widgets with their current settings and actions:
 * - Click to select and preview/edit
 * - Delete button to remove
 * - Visual indication of widget type and transformer
 */
import { useState } from 'react'
import {
  BarChart3,
  Activity,
  PieChart,
  Map,
  Info,
  FolderTree,
  Layers,
  Trash2,
  Copy,
  Loader2,
  Settings2,
  AlertTriangle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
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
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { ConfiguredWidget } from './useWidgetConfig'

// Category icons
const CATEGORY_ICONS: Record<string, React.ElementType> = {
  navigation: FolderTree,
  info: Info,
  map: Map,
  chart: BarChart3,
  gauge: Activity,
  donut: PieChart,
  table: Layers,
}

// Category colors
const CATEGORY_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  navigation: { text: 'text-violet-600', bg: 'bg-violet-50', border: 'border-violet-200' },
  info: { text: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  map: { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  chart: { text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' },
  gauge: { text: 'text-teal-600', bg: 'bg-teal-50', border: 'border-teal-200' },
  donut: { text: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
  table: { text: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200' },
}

interface ConfiguredWidgetsListProps {
  widgets: ConfiguredWidget[]
  selectedId?: string
  loading?: boolean
  onSelect: (widget: ConfiguredWidget) => void
  onDelete: (widgetId: string) => Promise<boolean>
  onDuplicate?: (widgetId: string, newId: string) => Promise<boolean>
}

export function ConfiguredWidgetsList({
  widgets,
  selectedId,
  loading,
  onSelect,
  onDelete,
  onDuplicate,
}: ConfiguredWidgetsListProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false)
  const [targetWidget, setTargetWidget] = useState<ConfiguredWidget | null>(null)
  const [newWidgetId, setNewWidgetId] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [isDuplicating, setIsDuplicating] = useState(false)

  const handleDeleteClick = (e: React.MouseEvent, widget: ConfiguredWidget) => {
    e.stopPropagation()
    setTargetWidget(widget)
    setDeleteDialogOpen(true)
  }

  const handleDuplicateClick = (e: React.MouseEvent, widget: ConfiguredWidget) => {
    e.stopPropagation()
    setTargetWidget(widget)
    setNewWidgetId(`${widget.id}_copy`)
    setDuplicateDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!targetWidget) return
    setIsDeleting(true)
    await onDelete(targetWidget.id)
    setIsDeleting(false)
    setDeleteDialogOpen(false)
    setTargetWidget(null)
  }

  const handleConfirmDuplicate = async () => {
    if (!targetWidget || !onDuplicate || !newWidgetId.trim()) return
    setIsDuplicating(true)
    await onDuplicate(targetWidget.id, newWidgetId.trim())
    setIsDuplicating(false)
    setDuplicateDialogOpen(false)
    setTargetWidget(null)
    setNewWidgetId('')
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="mt-4 text-sm text-muted-foreground">
          Chargement des widgets...
        </p>
      </div>
    )
  }

  // Empty state
  if (widgets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Settings2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="font-medium text-muted-foreground">Aucun widget configure</h3>
        <p className="mt-2 text-sm text-muted-foreground max-w-[250px]">
          Selectionnez des widgets dans l'onglet "Disponibles" puis sauvegardez pour les voir ici.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-2 p-4">
        <div className="text-sm text-muted-foreground mb-4">
          {widgets.length} widget{widgets.length > 1 ? 's' : ''} configure{widgets.length > 1 ? 's' : ''}
        </div>

        {widgets.map((widget) => {
          const category = widget.category || 'chart'
          const Icon = CATEGORY_ICONS[category] || BarChart3
          const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.chart
          const isSelected = widget.id === selectedId

          return (
            <div
              key={widget.id}
              className={cn(
                'group relative flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition-all',
                'hover:border-primary/50 hover:bg-accent/30',
                isSelected && 'border-primary bg-primary/5 ring-1 ring-primary/20'
              )}
              onClick={() => onSelect(widget)}
            >
              {/* Category icon */}
              <div className={cn(
                'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                colors.bg,
                colors.border,
                'border'
              )}>
                <Icon className={cn('h-5 w-5', colors.text)} />
              </div>

              {/* Widget info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium truncate">{widget.title}</span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="secondary" className="text-xs">
                    {widget.transformerPlugin}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {widget.widgetPlugin}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {onDuplicate && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={(e) => handleDuplicateClick(e, widget)}
                    title="Dupliquer"
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={(e) => handleDeleteClick(e, widget)}
                  title="Supprimer"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Supprimer le widget ?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Cela supprimera <strong>"{targetWidget?.title}"</strong> de transform.yml et export.yml.
              Cette action est irreversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
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

      {/* Duplicate dialog */}
      <Dialog open={duplicateDialogOpen} onOpenChange={setDuplicateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dupliquer le widget</DialogTitle>
            <DialogDescription>
              Creez une copie de "{targetWidget?.title}" avec un nouvel identifiant.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="new-widget-id">Nouvel identifiant</Label>
            <Input
              id="new-widget-id"
              value={newWidgetId}
              onChange={(e) => setNewWidgetId(e.target.value)}
              placeholder="ex: dbh_distribution_copy"
              className="mt-2"
            />
            <p className="text-xs text-muted-foreground mt-2">
              L'identifiant doit etre unique et ne contenir que des lettres, chiffres et underscores.
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDuplicateDialogOpen(false)}
              disabled={isDuplicating}
            >
              Annuler
            </Button>
            <Button
              onClick={handleConfirmDuplicate}
              disabled={isDuplicating || !newWidgetId.trim()}
            >
              {isDuplicating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Duplication...
                </>
              ) : (
                <>
                  <Copy className="mr-2 h-4 w-4" />
                  Dupliquer
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
