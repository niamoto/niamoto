/**
 * ImportDashboard - Main dashboard view after import
 *
 * Tabs:
 * 1. Summary - Global stats + priority alerts
 * 2. Field availability - Heatmap of % non-null per column
 * 3. Spatial - Map with occurrence distribution
 * 4. Taxonomy - Hierarchy tree + orphans
 * 5. Validation - Outliers + value ranges
 * 6. Coverage - Occurrences × shapes cross-analysis
 */

import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  LayoutDashboard,
  BarChart3,
  Map,
  GitBranch,
  AlertTriangle,
  Layers,
  RefreshCw,
  Download,
  Database,
  Network,
} from 'lucide-react'
import { DataSummaryCard } from './DataSummaryCard'
import { DataCompletenessView } from './DataCompletenessView'
import { SpatialDistributionMap } from './SpatialDistributionMap'
import { TaxonomicConsistencyView } from './TaxonomicConsistencyView'
import { ValueValidationView } from './ValueValidationView'
import { GeoCoverageView } from './GeoCoverageView'

interface ImportSummary {
  total_entities: number
  total_rows: number
  entities: Array<{
    name: string
    entity_type: string
    row_count: number
    column_count: number
    columns: string[]
  }>
  alerts: Array<{
    level: string
    entity: string
    message: string
  }>
}

interface ImportDashboardProps {
  onExploreEntity?: (name: string) => void
  onEnrich?: (refName: string) => void
  onReimport?: () => void
}

export function ImportDashboard({
  onExploreEntity,
  onEnrich,
  onReimport,
}: ImportDashboardProps) {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<ImportSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('summary')

  const fetchSummary = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/stats/summary')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      setSummary(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load summary')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSummary()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Error loading dashboard</AlertTitle>
        <AlertDescription>
          {error}
          <Button variant="link" onClick={fetchSummary} className="p-0 h-auto ml-2">
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  if (!summary) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>No data imported yet</p>
      </div>
    )
  }

  const datasetCount = summary.entities.filter((entity) => entity.entity_type === 'dataset').length
  const referenceCount = summary.entities.filter((entity) => entity.entity_type === 'reference').length
  const layerCount = summary.entities.filter((entity) => entity.entity_type === 'layer').length

  return (
    <div className="space-y-4">
      {/* Header with global stats */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold">Import Dashboard</h2>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchSummary}>
            <RefreshCw className="mr-1 h-3 w-3" />
            Refresh
          </Button>
          {onReimport && (
            <Button variant="outline" size="sm" onClick={onReimport}>
              <Download className="mr-1 h-3 w-3" />
              Re-import
            </Button>
          )}
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-5">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-blue-500" />
              <div className="text-2xl font-bold">{datasetCount}</div>
            </div>
            <p className="text-xs text-muted-foreground">Datasets</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-purple-500" />
              <div className="text-2xl font-bold">{referenceCount}</div>
            </div>
            <p className="text-xs text-muted-foreground">References</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-orange-500" />
              <div className="text-2xl font-bold">{layerCount}</div>
            </div>
            <p className="text-xs text-muted-foreground">Spatial layers</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">
              {summary.total_rows.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">Total rows</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{summary.alerts.length}</div>
            <p className="text-xs text-muted-foreground">Actionable alerts</p>
          </CardContent>
        </Card>
      </div>

      {/* Alerts if any */}
      {summary.alerts.length > 0 && (
        <div className="space-y-2">
          {summary.alerts.slice(0, 3).map((alert, idx) => (
            <Alert
              key={idx}
              variant={alert.level === 'error' ? 'destructive' : 'default'}
              className={alert.level === 'warning' ? 'border-yellow-300 bg-yellow-50' : ''}
            >
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>{alert.message}</span>
                {onExploreEntity && (
                  <Button
                    variant="link"
                    size="sm"
                    onClick={() => onExploreEntity(alert.entity)}
                    className="p-0 h-auto"
                  >
                    Explore
                  </Button>
                )}
              </AlertDescription>
            </Alert>
          ))}
          {summary.alerts.length > 3 && (
            <p className="text-xs text-muted-foreground">
              +{summary.alerts.length - 3} more alerts
            </p>
          )}
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="summary" className="gap-1">
            <LayoutDashboard className="h-3 w-3" />
            Summary
          </TabsTrigger>
          <TabsTrigger value="completeness" className="gap-1">
            <BarChart3 className="h-3 w-3" />
            Field availability
          </TabsTrigger>
          <TabsTrigger value="spatial" className="gap-1">
            <Map className="h-3 w-3" />
            Spatial
          </TabsTrigger>
          <TabsTrigger value="taxonomy" className="gap-1">
            <GitBranch className="h-3 w-3" />
            Taxonomy
          </TabsTrigger>
          <TabsTrigger value="validation" className="gap-1">
            <AlertTriangle className="h-3 w-3" />
            Validation
          </TabsTrigger>
          <TabsTrigger value="coverage" className="gap-1">
            <Layers className="h-3 w-3" />
            Coverage
          </TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="mt-4">
          <div className="grid grid-cols-2 gap-4">
            {summary.entities.map((entity) => (
              <DataSummaryCard
                key={entity.name}
                entity={entity}
                onExplore={onExploreEntity}
                onEnrich={
                  entity.entity_type === 'reference' && onEnrich
                    ? () => onEnrich(entity.name)
                    : undefined
                }
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="completeness" className="mt-4">
          <DataCompletenessView entities={summary.entities} />
        </TabsContent>

        <TabsContent value="spatial" className="mt-4">
          <SpatialDistributionMap />
        </TabsContent>

        <TabsContent value="taxonomy" className="mt-4">
          <TaxonomicConsistencyView />
        </TabsContent>

        <TabsContent value="validation" className="mt-4">
          <ValueValidationView entities={summary.entities} />
        </TabsContent>

        <TabsContent value="coverage" className="mt-4">
          <GeoCoverageView />
        </TabsContent>
      </Tabs>
    </div>
  )
}
