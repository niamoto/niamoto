/**
 * GroupPageViewer - Read-only view of a group configuration
 *
 * Displays:
 * - Group name and output patterns
 * - Index generator configuration (if enabled)
 * - Widget count
 * - Link to edit in Transform/Export
 */

import { ExternalLink, Folder, LayoutGrid, Filter, List, Eye, Settings2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import type { GroupInfo } from '@/hooks/useSiteConfig'

interface GroupPageViewerProps {
  group: GroupInfo
  onBack: () => void
}

export function GroupPageViewer({ group, onBack }: GroupPageViewerProps) {
  const hasIndex = group.index_generator?.enabled
  const indexConfig = group.index_generator

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
            <Folder className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">{group.name}/</h2>
            <p className="text-sm text-muted-foreground">Groupe de pages</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={onBack}>
          Retour
        </Button>
      </div>

      {/* Output patterns */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Settings2 className="h-4 w-4" />
            Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Pattern de sortie</span>
              <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                {group.output_pattern}
              </code>
            </div>
            {group.index_output_pattern && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Page d'index</span>
                <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                  {group.index_output_pattern}
                </code>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Widgets configurés</span>
              <Badge variant="secondary">{group.widgets_count}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Index generator */}
      {hasIndex && indexConfig && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm">
                <LayoutGrid className="h-4 w-4" />
                Générateur d'index
              </CardTitle>
              <Badge variant="default" className="bg-green-500/10 text-green-600">
                Active
              </Badge>
            </div>
            <CardDescription>
              Page de liste avec filtres et affichage configurable
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Page config */}
            <div className="grid gap-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Titre</span>
                <span>{indexConfig.page_config?.title || '-'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Items par page</span>
                <Badge variant="outline">{indexConfig.page_config?.items_per_page || 24}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Template</span>
                <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                  {indexConfig.template}
                </code>
              </div>
            </div>

            <Separator />

            {/* Filters */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Filtres</span>
                <Badge variant="secondary" className="text-xs">
                  {indexConfig.filters?.length || 0}
                </Badge>
              </div>
              {indexConfig.filters && indexConfig.filters.length > 0 ? (
                <div className="space-y-1.5">
                  {indexConfig.filters.map((filter, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 rounded-md bg-muted/50 px-2 py-1.5 text-xs"
                    >
                      <code className="text-muted-foreground">{filter.field}</code>
                      <span className="text-muted-foreground">{filter.operator}</span>
                      <div className="flex flex-wrap gap-1">
                        {filter.values?.slice(0, 3).map((v, i) => (
                          <Badge key={i} variant="outline" className="text-[10px]">
                            {String(v)}
                          </Badge>
                        ))}
                        {filter.values?.length > 3 && (
                          <Badge variant="outline" className="text-[10px]">
                            +{filter.values.length - 3}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground italic">Aucun filtre</p>
              )}
            </div>

            <Separator />

            {/* Display fields */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <List className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Champs affiches</span>
                <Badge variant="secondary" className="text-xs">
                  {indexConfig.display_fields?.length || 0}
                </Badge>
              </div>
              {indexConfig.display_fields && indexConfig.display_fields.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {indexConfig.display_fields.map((field, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className={field.searchable ? 'border-blue-200 bg-blue-50' : ''}
                    >
                      {field.label || field.name}
                      {field.searchable && (
                        <span className="ml-1 text-[10px] text-blue-500">recherche</span>
                      )}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground italic">Aucun champ</p>
              )}
            </div>

            <Separator />

            {/* Views */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <Eye className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Modes d'affichage</span>
              </div>
              <div className="flex gap-2">
                {indexConfig.views?.map((view, idx) => (
                  <Badge
                    key={idx}
                    variant={view.default ? 'default' : 'outline'}
                    className="capitalize"
                  >
                    {view.type}
                    {view.default && <span className="ml-1 text-[10px]">(défaut)</span>}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* No index generator */}
      {!hasIndex && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <LayoutGrid className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <h3 className="font-medium">Pas de page d'index</h3>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              Ce groupe ne genere pas de page d'index. Seules les pages de detail sont creees pour
              chaque entite.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Link to Transform/Export */}
      <Card className="border-dashed">
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <Settings2 className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">Modifier les widgets</p>
              <p className="text-xs text-muted-foreground">
                Configurez les widgets dans l'onglet Transform/Export
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" asChild>
            <a href={`/flow?tab=export&group=${group.name}`}>
              Ouvrir
              <ExternalLink className="ml-2 h-3 w-3" />
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
