/**
 * DataCompletenessView - Heatmap of column completeness
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { BarChart3 } from 'lucide-react'

interface EntityInfo {
  name: string
  entity_type: string
  row_count: number
  column_count: number
  columns: string[]
  quality_score: number
}

interface ColumnCompleteness {
  column: string
  type: string
  total_count: number
  null_count: number
  non_null_count: number
  completeness: number
  unique_count: number
}

interface EntityCompleteness {
  entity: string
  columns: ColumnCompleteness[]
  overall_completeness: number
}

interface DataCompletenessViewProps {
  entities: EntityInfo[]
}

export function DataCompletenessView({ entities }: DataCompletenessViewProps) {
  const [selectedEntity, setSelectedEntity] = useState<string>(
    entities[0]?.name || ''
  )
  const [completeness, setCompleteness] = useState<EntityCompleteness | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!selectedEntity) return

    const fetchCompleteness = async () => {
      setLoading(true)
      try {
        const response = await fetch(`/api/stats/completeness/${selectedEntity}`)
        if (response.ok) {
          const data = await response.json()
          setCompleteness(data)
        }
      } catch (err) {
        console.error('Failed to fetch completeness:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchCompleteness()
  }, [selectedEntity])

  const getCompletenessColor = (value: number) => {
    if (value >= 0.95) return 'bg-green-500'
    if (value >= 0.8) return 'bg-green-400'
    if (value >= 0.6) return 'bg-yellow-400'
    if (value >= 0.4) return 'bg-orange-400'
    return 'bg-red-400'
  }

  const getCompletenessTextColor = (value: number) => {
    if (value >= 0.95) return 'text-green-700'
    if (value >= 0.8) return 'text-green-600'
    if (value >= 0.6) return 'text-yellow-700'
    if (value >= 0.4) return 'text-orange-700'
    return 'text-red-700'
  }

  return (
    <div className="space-y-4">
      {/* Entity selector */}
      <div className="flex items-center gap-4">
        <Select value={selectedEntity} onValueChange={setSelectedEntity}>
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Select entity" />
          </SelectTrigger>
          <SelectContent>
            {entities.map((e) => (
              <SelectItem key={e.name} value={e.name}>
                {e.name} ({e.row_count.toLocaleString()} rows)
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {completeness && (
          <Badge variant="outline" className="ml-auto">
            Overall: {Math.round(completeness.overall_completeness * 100)}%
          </Badge>
        )}
      </div>

      {/* Completeness grid */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart3 className="h-4 w-4" />
            Column Completeness
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : completeness ? (
            <TooltipProvider>
              <div className="space-y-2">
                {completeness.columns.map((col) => (
                  <Tooltip key={col.column}>
                    <TooltipTrigger asChild>
                      <div className="flex items-center gap-3">
                        <div className="w-32 text-sm truncate" title={col.column}>
                          {col.column}
                        </div>
                        <div className="flex-1 h-6 bg-muted rounded overflow-hidden">
                          <div
                            className={`h-full ${getCompletenessColor(col.completeness)} transition-all`}
                            style={{ width: `${col.completeness * 100}%` }}
                          />
                        </div>
                        <div
                          className={`w-12 text-right text-sm font-medium ${getCompletenessTextColor(col.completeness)}`}
                        >
                          {Math.round(col.completeness * 100)}%
                        </div>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className="text-xs space-y-1">
                        <p>
                          <strong>{col.column}</strong> ({col.type})
                        </p>
                        <p>Total: {col.total_count.toLocaleString()}</p>
                        <p>Non-null: {col.non_null_count.toLocaleString()}</p>
                        <p>Null: {col.null_count.toLocaleString()}</p>
                        <p>Unique values: {col.unique_count.toLocaleString()}</p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </TooltipProvider>
          ) : (
            <p className="text-sm text-muted-foreground">Select an entity to view completeness</p>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span>Completeness:</span>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-red-400" />
          <span>&lt;40%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-orange-400" />
          <span>40-60%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-yellow-400" />
          <span>60-80%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-green-400" />
          <span>80-95%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-green-500" />
          <span>&gt;95%</span>
        </div>
      </div>
    </div>
  )
}
