/**
 * TableStats - Shows statistics for a database table
 */

import { useQuery } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Loader2, Database, Columns, Hash } from 'lucide-react'
import { listTables } from '@/features/import/api/data-explorer'

interface TableStatsProps {
  tableName: string
  kind?: string
  hierarchyLevels?: string[]
}

export function TableStats({ tableName, kind, hierarchyLevels }: TableStatsProps) {
  const { data: tables, isLoading } = useQuery({
    queryKey: ['tables'],
    queryFn: listTables,
    staleTime: 60000,
  })

  const tableInfo = tables?.find((t) => t.name === tableName)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!tableInfo) {
    return (
      <div className="text-sm text-muted-foreground">Table non trouvee: {tableName}</div>
    )
  }

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <Database className="h-8 w-8 text-blue-500" />
          <div>
            <div className="text-xl font-semibold">{tableInfo.count.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">Lignes</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <Columns className="h-8 w-8 text-green-500" />
          <div>
            <div className="text-xl font-semibold">{tableInfo.columns.length}</div>
            <div className="text-xs text-muted-foreground">Colonnes</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <Hash className="h-8 w-8 text-purple-500" />
          <div>
            <div className="flex items-center gap-2">
              {kind && <Badge variant="secondary">{kind}</Badge>}
              {!kind && <span className="text-lg font-medium">Dataset</span>}
            </div>
            {hierarchyLevels && hierarchyLevels.length > 0 && (
              <div className="mt-1 text-xs text-muted-foreground">
                {hierarchyLevels.join(' → ')}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
