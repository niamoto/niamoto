/**
 * StaticPagesList - List of static pages with CRUD operations
 *
 * Displays:
 * - List of configured static pages
 * - Edit and delete actions
 * - Add new page button
 */

import { FileText, Plus, Pencil, Trash2, FileCode, Home, Info, Book } from 'lucide-react'
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
import type { StaticPage } from '@/features/site/hooks/useSiteConfig'

interface StaticPagesListProps {
  pages: StaticPage[]
  onEdit: (pageName: string) => void
  onAdd: () => void
  onDelete: (pageName: string) => void
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

function PageCard({
  page,
  onEdit,
  onDelete,
}: {
  page: StaticPage
  onEdit: () => void
  onDelete: () => void
}) {
  const Icon = getPageIcon(page.name)
  const hasContent = page.context?.content_markdown || page.context?.content_source

  return (
    <div className="group flex items-start gap-3 rounded-lg border bg-card p-4 transition-colors hover:bg-muted/50">
      {/* Icon */}
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
        <Icon className="h-5 w-5 text-primary" />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">{page.name}</h3>
          {hasContent && (
            <Badge variant="secondary" className="text-xs">
              Contenu
            </Badge>
          )}
        </div>
        <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
          <FileCode className="h-3.5 w-3.5" />
          <span className="truncate">{page.template}</span>
          <span className="text-muted-foreground/50">→</span>
          <span className="truncate font-mono text-xs">{page.output_file}</span>
        </div>
        {page.context?.content_source && (
          <p className="mt-1 text-xs text-muted-foreground">
            Source: {page.context.content_source}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onEdit}>
          <Pencil className="h-4 w-4" />
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Supprimer la page ?</AlertDialogTitle>
              <AlertDialogDescription>
                Etes-vous sur de vouloir supprimer la page "{page.name}" ? Cette action est
                irreversible.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Annuler</AlertDialogCancel>
              <AlertDialogAction onClick={onDelete} className="bg-destructive hover:bg-destructive/90">
                Supprimer
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}

export function StaticPagesList({ pages, onEdit, onAdd, onDelete }: StaticPagesListProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              Pages statiques
            </CardTitle>
            <CardDescription>
              Pages de contenu personnalisees (accueil, methodologie, etc.)
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onAdd}>
            <Plus className="mr-1 h-4 w-4" />
            Nouvelle page
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {pages.length === 0 ? (
          <div className="flex min-h-[150px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-6 text-center">
            <FileText className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <h3 className="font-medium">Aucune page configuree</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Creez des pages statiques pour votre site
            </p>
            <Button variant="outline" size="sm" onClick={onAdd} className="mt-4">
              <Plus className="mr-1 h-4 w-4" />
              Creer une page
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            {pages.map((page) => (
              <PageCard
                key={page.name}
                page={page}
                onEdit={() => onEdit(page.name)}
                onDelete={() => onDelete(page.name)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
