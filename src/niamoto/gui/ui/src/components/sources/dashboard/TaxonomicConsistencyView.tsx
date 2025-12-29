/**
 * TaxonomicConsistencyView - Taxonomy hierarchy analysis
 *
 * Shows hierarchy levels, orphans, and duplicate detection.
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  GitBranch,
  AlertTriangle,
  Users,
  Copy,
  CheckCircle2,
  Layers,
} from 'lucide-react'

interface TaxonomyLevel {
  level: string
  count: number
  orphan_count: number
}

interface TaxonomyConsistency {
  total_taxa: number
  levels: TaxonomyLevel[]
  orphan_records: Array<Record<string, any>>
  duplicate_names: Array<{ name: string; count: number }>
  hierarchy_depth: number
}

export function TaxonomicConsistencyView() {
  const [data, setData] = useState<TaxonomyConsistency | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const response = await fetch('/api/stats/taxonomy-consistency')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const result = await response.json()
        setData(result)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load taxonomy data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  if (!data || data.total_taxa === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <GitBranch className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="text-muted-foreground">No taxonomy data found</p>
          <p className="text-xs text-muted-foreground mt-1">
            Import a taxonomic reference to see hierarchy analysis
          </p>
        </CardContent>
      </Card>
    )
  }

  const totalOrphans = data.levels.reduce((sum, l) => sum + l.orphan_count, 0)
  const hasIssues = totalOrphans > 0 || data.duplicate_names.length > 0

  return (
    <div className="space-y-4">
      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-purple-500" />
              <div>
                <div className="text-xl font-bold">
                  {data.total_taxa.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground">Total taxa</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-blue-500" />
              <div>
                <div className="text-xl font-bold">{data.hierarchy_depth}</div>
                <p className="text-xs text-muted-foreground">Hierarchy levels</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              {totalOrphans === 0 ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
              )}
              <div>
                <div className="text-xl font-bold">{totalOrphans}</div>
                <p className="text-xs text-muted-foreground">Orphans</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              {data.duplicate_names.length === 0 ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4 text-yellow-500" />
              )}
              <div>
                <div className="text-xl font-bold">{data.duplicate_names.length}</div>
                <p className="text-xs text-muted-foreground">Duplicates</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Status alert */}
      {!hasIssues && (
        <Alert className="border-green-300 bg-green-50">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-700">
            Taxonomy hierarchy is consistent - no orphans or duplicates detected.
          </AlertDescription>
        </Alert>
      )}

      {/* Hierarchy levels */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <GitBranch className="h-4 w-4" />
            Hierarchy Levels
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.levels.length > 0 ? (
            <div className="space-y-3">
              {data.levels.map((level, idx) => (
                <div key={level.level} className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-medium">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-medium capitalize">{level.level}</span>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">
                          {level.count.toLocaleString()} taxa
                        </Badge>
                        {level.orphan_count > 0 && (
                          <Badge variant="outline" className="text-yellow-700 border-yellow-300">
                            {level.orphan_count} orphans
                          </Badge>
                        )}
                      </div>
                    </div>
                    {/* Progress bar showing relative size */}
                    <div className="mt-1 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500"
                        style={{
                          width: `${Math.min(100, (level.count / data.total_taxa) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No hierarchy levels detected
            </p>
          )}
        </CardContent>
      </Card>

      {/* Duplicates table */}
      {data.duplicate_names.length > 0 && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Copy className="h-4 w-4 text-yellow-500" />
              Duplicate Names ({data.duplicate_names.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead className="text-right">Occurrences</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.duplicate_names.slice(0, 10).map((dup) => (
                  <TableRow key={dup.name}>
                    <TableCell className="font-mono text-sm">{dup.name}</TableCell>
                    <TableCell className="text-right">
                      <Badge variant="outline">{dup.count}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {data.duplicate_names.length > 10 && (
              <p className="text-xs text-muted-foreground mt-2">
                +{data.duplicate_names.length - 10} more duplicates
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
