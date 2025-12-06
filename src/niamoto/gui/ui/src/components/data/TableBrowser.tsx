/**
 * TableBrowser - Simple table data viewer with pagination
 *
 * Displays table data with:
 * - Paginated view
 * - Column display
 * - Link to full Data Explorer
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ChevronLeft, ChevronRight, Loader2, ExternalLink } from 'lucide-react'
import { queryTable } from '@/lib/api/data-explorer'

interface TableBrowserProps {
  tableName: string
  pageSize?: number
  maxColumns?: number
  onOpenInExplorer?: () => void
}

export function TableBrowser({
  tableName,
  pageSize = 20,
  maxColumns = 8,
  onOpenInExplorer,
}: TableBrowserProps) {
  const [page, setPage] = useState(0)

  const { data, isLoading, error } = useQuery({
    queryKey: ['table-data', tableName, page, pageSize],
    queryFn: () =>
      queryTable({
        table: tableName,
        limit: pageSize,
        offset: page * pageSize,
      }),
    staleTime: 30000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
        Erreur lors du chargement des donnees: {(error as Error).message}
      </div>
    )
  }

  if (!data || data.rows.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">Aucune donnee</div>
    )
  }

  // Limit columns for display
  const displayColumns = data.columns.slice(0, maxColumns)
  const hasMoreColumns = data.columns.length > maxColumns

  // Pagination
  const totalPages = Math.ceil(data.total_count / pageSize)
  const canPrevious = page > 0
  const canNext = page < totalPages - 1

  // Truncate long values
  const truncateValue = (value: any, maxLength: number = 50) => {
    if (value === null || value === undefined) return '-'
    const str = String(value)
    if (str.length > maxLength) {
      return str.substring(0, maxLength) + '...'
    }
    return str
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {displayColumns.map((col) => (
                <TableHead key={col} className="whitespace-nowrap text-xs">
                  {col}
                </TableHead>
              ))}
              {hasMoreColumns && (
                <TableHead className="text-xs text-muted-foreground">
                  +{data.columns.length - maxColumns}
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((row, idx) => (
              <TableRow key={idx}>
                {displayColumns.map((col) => (
                  <TableCell key={col} className="max-w-[200px] truncate text-xs">
                    {truncateValue(row[col])}
                  </TableCell>
                ))}
                {hasMoreColumns && <TableCell className="text-xs text-muted-foreground">...</TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          {page * pageSize + 1}-{Math.min((page + 1) * pageSize, data.total_count)} sur{' '}
          {data.total_count.toLocaleString()}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p - 1)}
            disabled={!canPrevious}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-xs">
            Page {page + 1} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={!canNext}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {onOpenInExplorer && (
          <Button variant="outline" size="sm" onClick={onOpenInExplorer}>
            <ExternalLink className="mr-2 h-4 w-4" />
            Data Explorer
          </Button>
        )}
      </div>
    </div>
  )
}
