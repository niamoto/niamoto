/**
 * DataSummaryCard - Summary card for a single entity
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Database,
  Network,
  Layers,
  Search,
  Sparkles,
  ChevronRight,
} from 'lucide-react'

interface EntityData {
  name: string
  entity_type: string
  row_count: number
  column_count: number
  columns: string[]
}

interface DataSummaryCardProps {
  entity: EntityData
  onExplore?: (name: string) => void
  onEnrich?: () => void
}

export function DataSummaryCard({ entity, onExplore, onEnrich }: DataSummaryCardProps) {
  const getIcon = () => {
    switch (entity.entity_type) {
      case 'dataset':
        return <Database className="h-4 w-4 text-blue-500" />
      case 'reference':
        return <Network className="h-4 w-4 text-purple-500" />
      case 'layer':
        return <Layers className="h-4 w-4 text-orange-500" />
      default:
        return <Database className="h-4 w-4" />
    }
  }

  const getTypeBadge = () => {
    const colors: Record<string, string> = {
      dataset: 'bg-blue-100 text-blue-700',
      reference: 'bg-purple-100 text-purple-700',
      layer: 'bg-orange-100 text-orange-700',
    }
    return colors[entity.entity_type] || 'bg-gray-100 text-gray-700'
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            {getIcon()}
            {entity.name}
          </CardTitle>
          <Badge variant="secondary" className={getTypeBadge()}>
            {entity.entity_type}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground text-xs">Rows</p>
            <p className="font-semibold">{entity.row_count.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Columns</p>
            <p className="font-semibold">{entity.column_count}</p>
          </div>
        </div>

        {/* Column preview */}
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">Columns</p>
          <div className="flex flex-wrap gap-1">
            {entity.columns.slice(0, 5).map((col) => (
              <Badge key={col} variant="outline" className="text-xs font-normal">
                {col}
              </Badge>
            ))}
            {entity.columns.length > 5 && (
              <Badge variant="outline" className="text-xs font-normal text-muted-foreground">
                +{entity.columns.length - 5}
              </Badge>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          {onExplore && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => onExplore(entity.name)}
            >
              <Search className="mr-1 h-3 w-3" />
              Explore
            </Button>
          )}
          {onEnrich && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={onEnrich}
            >
              <Sparkles className="mr-1 h-3 w-3" />
              Enrich
            </Button>
          )}
          {!onExplore && !onEnrich && (
            <Button variant="ghost" size="sm" className="w-full" disabled>
              <ChevronRight className="h-3 w-3" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
