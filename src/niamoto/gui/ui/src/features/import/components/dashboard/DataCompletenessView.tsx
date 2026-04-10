/**
 * DataCompletenessView - Heatmap of column fill rate
 */

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
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
import { getEntityCompleteness } from '@/features/import/api/dashboard'
import { importQueryKeys } from '@/features/import/queryKeys'

interface EntityInfo {
  name: string
  entity_type: string
  row_count: number
  column_count: number
  columns: string[]
}

interface DataCompletenessViewProps {
  entities: EntityInfo[]
}

export function DataCompletenessView({ entities }: DataCompletenessViewProps) {
  const { t } = useTranslation('sources')
  const [selectedEntity, setSelectedEntity] = useState<string>(
    entities[0]?.name || ''
  )
  const resolvedSelectedEntity = useMemo(() => {
    if (entities.some((entity) => entity.name === selectedEntity)) {
      return selectedEntity
    }

    return entities[0]?.name || ''
  }, [entities, selectedEntity])

  const { data: completeness, isLoading: loading } = useQuery({
    queryKey: importQueryKeys.dashboard.completeness(resolvedSelectedEntity),
    queryFn: () => getEntityCompleteness(resolvedSelectedEntity),
    enabled: resolvedSelectedEntity.length > 0,
  })

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
        <Select value={resolvedSelectedEntity} onValueChange={setSelectedEntity}>
          <SelectTrigger className="w-64">
            <SelectValue
              placeholder={t('dashboard.completeness.selectEntity', 'Select entity')}
            />
          </SelectTrigger>
          <SelectContent>
            {entities.map((e) => (
              <SelectItem key={e.name} value={e.name}>
                {t('dashboard.completeness.entityOption', '{{name}} ({{count}} rows)', {
                  name: e.name,
                  count: e.row_count,
                })}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {completeness && (
          <Badge variant="outline" className="ml-auto">
            {t('dashboard.completeness.averageFillRate', 'Average fill rate: {{value}}%', {
              value: Math.round(completeness.overall_completeness * 100),
            })}
          </Badge>
        )}
      </div>

      {/* Availability grid */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart3 className="h-4 w-4" />
            {t('dashboard.completeness.fieldAvailability', 'Field availability')}
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
                        <p>
                          {t('dashboard.completeness.total', 'Total')}: {col.total_count.toLocaleString()}
                        </p>
                        <p>
                          {t('dashboard.completeness.nonNull', 'Non-null')}:{' '}
                          {col.non_null_count.toLocaleString()}
                        </p>
                        <p>
                          {t('dashboard.completeness.null', 'Null')}: {col.null_count.toLocaleString()}
                        </p>
                        <p>
                          {t('dashboard.completeness.uniqueValues', 'Unique values')}:{' '}
                          {col.unique_count.toLocaleString()}
                        </p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </TooltipProvider>
          ) : (
            <p className="text-sm text-muted-foreground">
              {t(
                'dashboard.completeness.selectEntityHint',
                'Select an entity to inspect field availability'
              )}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span>{t('dashboard.completeness.fillRate', 'Fill rate:')}</span>
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
