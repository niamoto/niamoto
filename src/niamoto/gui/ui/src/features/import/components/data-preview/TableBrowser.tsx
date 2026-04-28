/**
 * TableBrowser - Simple table data viewer with pagination
 *
 * Displays table data with:
 * - Paginated view
 * - Column display
 * - Link to full Data Explorer
 */

import { useState } from 'react'
import { isAxiosError } from 'axios'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
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
import {
  getPreviewColumnNames,
  tableColumnsQueryOptions,
  tablePreviewQueryOptions,
} from '@/features/import/queryUtils'

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

  const {
    data: tableColumns,
    isLoading: isColumnsLoading,
    error: columnsError,
  } = useQuery(tableColumnsQueryOptions(tableName))

  const previewColumns = tableColumns
    ? getPreviewColumnNames(
        tableColumns.columns.map((column) => column.name),
        maxColumns
      )
    : undefined

  const { data, isLoading, isFetching, error: previewError } = useQuery({
    ...tablePreviewQueryOptions(tableName, page, pageSize, previewColumns),
    enabled: !isColumnsLoading && !columnsError,
    placeholderData: keepPreviousData,
  })

  const isInitialLoading = isColumnsLoading || isLoading
  const isPageFetching = isFetching && !isInitialLoading
  const error = columnsError || previewError

  if (isInitialLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    const is404 = isAxiosError(error) && error.response?.status === 404
    if (is404) {
      return (
        <div className="py-4 text-center text-sm text-muted-foreground">
          Table not available — run an import to create the data.
        </div>
      )
    }
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
        Erreur lors du chargement des données : {(error as Error).message}
      </div>
    )
  }

  if (!data || data.rows.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">Aucune donnee</div>
    )
  }

  // Limit columns for display
  const totalColumnCount = tableColumns?.columns.length ?? data.columns.length
  const displayColumns = previewColumns?.length
    ? previewColumns
    : data.columns.slice(0, maxColumns)
  const hasMoreColumns = totalColumnCount > displayColumns.length
  const dataColumnWidthClass = hasMoreColumns ? 'w-[10rem]' : 'w-[11.5rem]'

  // Pagination
  const totalPages = Math.ceil(data.total_count / pageSize)
  const canPrevious = page > 0
  const canNext = page < totalPages - 1

  // Truncate long values
  const truncateValue = (value: unknown, maxLength: number = 50) => {
    if (value === null || value === undefined) return '-'
    const str = String(value)
    if (str.length > maxLength) {
      return str.substring(0, maxLength) + '...'
    }
    return str
  }

  return (
    <div className="space-y-3">
      <div
        className="relative overflow-x-auto rounded-md border"
        aria-busy={isPageFetching}
      >
        {isPageFetching && (
          <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-background/70 text-xs text-muted-foreground backdrop-blur-[1px]">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="sr-only">Chargement de la page</span>
          </div>
        )}
        <Table className="min-w-full table-fixed">
          <colgroup>
            {displayColumns.map((col) => (
              <col key={col} className={dataColumnWidthClass} />
            ))}
            {hasMoreColumns && <col className="w-[3rem]" />}
          </colgroup>
          <TableHeader>
            <TableRow>
              {displayColumns.map((col) => (
                <TableHead key={col} className="truncate text-xs">
                  {col}
                </TableHead>
              ))}
              {hasMoreColumns && (
                <TableHead className="w-[3rem] text-center text-xs text-muted-foreground">
                  +{totalColumnCount - displayColumns.length}
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((row, idx) => (
              <TableRow key={idx}>
                {displayColumns.map((col) => (
                  <TableCell key={col} className="truncate text-xs">
                    {truncateValue(row[col])}
                  </TableCell>
                ))}
                {hasMoreColumns && (
                  <TableCell className="text-center text-xs text-muted-foreground">
                    ...
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3">
        <div className="min-w-0 text-xs text-muted-foreground">
          {page * pageSize + 1}-{Math.min((page + 1) * pageSize, data.total_count)} sur{' '}
          {data.total_count.toLocaleString()}
        </div>

        <div className="justify-self-center">
          <div className="grid grid-cols-[2rem_8.5rem_2rem] items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 w-8 px-0"
              onClick={() => setPage((p) => p - 1)}
              disabled={!canPrevious || isPageFetching}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="relative w-[8.5rem] px-5 text-center">
              <span className="text-xs tabular-nums">
                Page {page + 1} / {totalPages}
              </span>
              {isPageFetching && (
                <span className="absolute right-0 top-1/2 inline-flex -translate-y-1/2 items-center text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span className="sr-only">Chargement de la page</span>
                </span>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              className="h-8 w-8 px-0"
              onClick={() => setPage((p) => p + 1)}
              disabled={!canNext || isPageFetching}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {onOpenInExplorer && (
          <Button
            variant="outline"
            size="sm"
            className="justify-self-end"
            onClick={onOpenInExplorer}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            Data Explorer
          </Button>
        )}
      </div>
    </div>
  )
}
