import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Database, Layers, Pencil, Search } from 'lucide-react'

interface SupportingSourceCardProps {
  entity: {
    type: 'dataset' | 'layer'
    name: string
    tableName: string
    description?: string
    rowCount: number
    columnCount: number
    columns: string[]
  }
  datasetLabel: string
  layerLabel: string
  rowsLabel: string
  fieldsLabel: string
  fallbackDescription: string
  editConfigAction?: string
  exploreAction?: string
  updateAction: string
  onEdit?: () => void
  onExplore?: () => void
  onUpdate?: () => void
}

export function SupportingSourceCard({
  entity,
  datasetLabel,
  layerLabel,
  rowsLabel,
  fieldsLabel,
  fallbackDescription,
  editConfigAction,
  exploreAction,
  updateAction,
  onEdit,
  onExplore,
  onUpdate,
}: SupportingSourceCardProps) {
  return (
    <Card className="border-border/70">
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              {entity.type === 'dataset' ? (
                <Database className="h-4 w-4 text-blue-500" />
              ) : (
                <Layers className="h-4 w-4 text-orange-500" />
              )}
              <div className="font-medium">{entity.name}</div>
              <Badge variant="outline">
                {entity.type === 'dataset' ? datasetLabel : layerLabel}
              </Badge>
            </div>
            <div className="text-xs text-muted-foreground">{entity.tableName}</div>
          </div>
          {onEdit && editConfigAction && (
            <Button variant="outline" size="sm" onClick={onEdit}>
              <Pencil className="mr-2 h-4 w-4" />
              {editConfigAction}
            </Button>
          )}
        </div>

        <p className="text-sm text-muted-foreground">
          {entity.description || fallbackDescription}
        </p>

        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">{rowsLabel}</Badge>
          <Badge variant="secondary">{fieldsLabel}</Badge>
          {entity.columns.slice(0, 4).map((column) => (
            <Badge key={column} variant="outline" className="font-normal">
              {column}
            </Badge>
          ))}
          {entity.columns.length > 4 && (
            <Badge variant="outline" className="font-normal text-muted-foreground">
              +{entity.columns.length - 4}
            </Badge>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {onExplore && exploreAction && (
            <Button variant="outline" onClick={onExplore}>
              <Search className="mr-2 h-4 w-4" />
              {exploreAction}
            </Button>
          )}
          {onUpdate && <Button variant="ghost" onClick={onUpdate}>{updateAction}</Button>}
        </div>
      </CardContent>
    </Card>
  )
}
