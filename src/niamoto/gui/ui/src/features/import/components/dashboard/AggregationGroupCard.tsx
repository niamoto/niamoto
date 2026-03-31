import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  CheckCircle2,
  GitBranch,
  Globe2,
  Network,
  Pencil,
  PlusCircle,
  Search,
  Sparkles,
} from 'lucide-react'

interface AggregationCollectionCardProps {
  group: {
    name: string
    table_name: string
    kind?: string
    description?: string
    enrichment_enabled?: boolean
    can_enrich?: boolean
    canAddSource?: boolean
    entity_count?: number
    schema_fields?: Array<{ name: string }>
    columnNames: string[]
    metrics?: {
      row_count: number
      column_count: number
    }
  }
  kindLabel: string
  description: string
  rowsLabel: string
  fieldsLabel: string
  roleLabel: string
  fieldPreviewLabel: string
  importedLabel: string
  enrichmentEnabledLabel: string
  enrichmentAvailableLabel: string
  nextStepLabel: string
  enrichmentTitle: string
  enrichmentDescription: string
  enrichmentConfiguredTitle: string
  enrichmentConfiguredDescription: string
  readyLabel: string
  exploreTitle: string
  exploreDescription: string
  exploreAction: string
  editConfigAction: string
  addSourceAction: string
  openCollectionAction: string
  enrichAction: string
  manageEnrichmentAction: string
  onExplore?: (name: string) => void
  onEdit?: () => void
  onAddSource?: () => void
  onOpenGroup?: (name: string) => void
  onEnrich?: (name: string, targetTab: 'config' | 'enrichment') => void
}

export function AggregationCollectionCard({
  group,
  kindLabel,
  description,
  rowsLabel,
  fieldsLabel,
  roleLabel,
  fieldPreviewLabel,
  importedLabel,
  enrichmentEnabledLabel,
  enrichmentAvailableLabel,
  nextStepLabel,
  enrichmentTitle,
  enrichmentDescription,
  enrichmentConfiguredTitle,
  enrichmentConfiguredDescription,
  readyLabel,
  exploreTitle,
  exploreDescription,
  exploreAction,
  editConfigAction,
  addSourceAction,
  openCollectionAction,
  enrichAction,
  manageEnrichmentAction,
  onExplore,
  onEdit,
  onAddSource,
  onOpenGroup,
  onEnrich,
}: AggregationCollectionCardProps) {
  const Icon =
    group.kind === 'spatial'
      ? Globe2
      : group.kind === 'hierarchical'
        ? GitBranch
        : Network
  const canEnrich = Boolean(group.can_enrich)

  return (
    <Card className="overflow-hidden border-border/70">
      <CardContent className="p-0">
        <div className="space-y-5 p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                  <Icon className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-lg font-semibold">{group.name}</h3>
                    <Badge variant="outline">{importedLabel}</Badge>
                    <Badge variant="secondary">{kindLabel}</Badge>
                    {group.enrichment_enabled && (
                      <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">
                        {enrichmentEnabledLabel}
                      </Badge>
                    )}
                    {!group.enrichment_enabled && canEnrich && (
                      <Badge variant="outline">{enrichmentAvailableLabel}</Badge>
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground">{group.table_name}</div>
                </div>
              </div>

              <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
            </div>

            <div className="flex flex-wrap gap-2 lg:justify-end">
              {onExplore && (
                <Button onClick={() => onExplore(group.name)}>
                  <Search className="mr-2 h-4 w-4" />
                  {exploreAction}
                </Button>
              )}
              {onEdit && (
                <Button variant="outline" onClick={onEdit}>
                  <Pencil className="mr-2 h-4 w-4" />
                  {editConfigAction}
                </Button>
              )}
              {onAddSource && (
                <Button variant="outline" onClick={onAddSource}>
                  <PlusCircle className="mr-2 h-4 w-4" />
                  {addSourceAction}
                </Button>
              )}
              {onOpenGroup && (
                <Button variant="ghost" onClick={() => onOpenGroup(group.name)}>
                  {openCollectionAction}
                </Button>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            <span>{rowsLabel}</span>
            <span className="text-muted-foreground/60">•</span>
            <span>{fieldsLabel}</span>
            <span className="text-muted-foreground/60">•</span>
            <span>{roleLabel}</span>
          </div>

          <div className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              {fieldPreviewLabel}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {group.columnNames.slice(0, 6).map((column) => (
                <Badge key={column} variant="outline" className="font-normal">
                  {column}
                </Badge>
              ))}
              {group.columnNames.length > 6 && (
                <Badge variant="outline" className="font-normal text-muted-foreground">
                  +{group.columnNames.length - 6}
                </Badge>
              )}
            </div>
          </div>
        </div>

        <div className="border-t bg-muted/25 p-6">
          {canEnrich ? (
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-primary">
                  <Sparkles className="h-4 w-4" />
                  {nextStepLabel}
                </div>
                <div className="text-base font-semibold">
                  {group.enrichment_enabled
                    ? enrichmentConfiguredTitle
                    : enrichmentTitle}
                </div>
                <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                  {group.enrichment_enabled
                    ? enrichmentConfiguredDescription
                    : enrichmentDescription}
                </p>
              </div>
              {onEnrich && (
                <Button
                  size="lg"
                  onClick={() =>
                    onEnrich(group.name, group.enrichment_enabled ? 'enrichment' : 'config')
                  }
                >
                  <Sparkles className="mr-2 h-4 w-4" />
                  {group.enrichment_enabled ? manageEnrichmentAction : enrichAction}
                </Button>
              )}
            </div>
          ) : (
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  {readyLabel}
                </div>
                <div className="text-base font-semibold">{exploreTitle}</div>
                <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                  {exploreDescription}
                </p>
              </div>
              {onExplore && (
                <Button size="lg" onClick={() => onExplore(group.name)}>
                  <Search className="mr-2 h-4 w-4" />
                  {exploreAction}
                </Button>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
