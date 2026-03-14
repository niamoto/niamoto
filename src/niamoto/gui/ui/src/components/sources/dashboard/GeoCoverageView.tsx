/**
 * GeoCoverageView - Geographic coverage analysis
 *
 * Shows quick FK-based coverage + on-demand spatial analysis button
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Layers,
  MapPin,
  AlertTriangle,
  CheckCircle2,
  Play,
  Loader2,
  Clock,
  Database,
  BarChart3,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'

interface ShapeInfo {
  table_name: string
  display_name: string
  shape_count: number
  has_geometry: boolean
  shape_types: string[]
}

interface GeoCoverage {
  total_occurrences: number
  occurrences_with_geo: number
  geo_column: string | null
  available_shapes: ShapeInfo[]
  ready_for_analysis: boolean
}

interface ShapeCoverageDetail {
  shape_type: string
  shape_table: string
  total_shapes: number
  occurrences_covered: number
  coverage_percent: number
}

interface SpatialAnalysisResult {
  total_occurrences: number
  occurrences_with_geo: number
  occurrences_without_geo: number
  shape_coverage: ShapeCoverageDetail[]
  analysis_time_seconds: number
  geo_column: string | null
  status: 'success' | 'no_geo_column' | 'no_shapes' | 'error'
  message: string | null
}

interface ShapeOccurrenceCount {
  shape_id: number
  shape_name: string
  shape_type: string
  occurrence_count: number
  percent_of_total: number
}

interface ShapeDistributionResult {
  total_occurrences_with_geo: number
  shapes: ShapeOccurrenceCount[]
  analysis_time_seconds: number
  status: string
  message: string | null
}

export function GeoCoverageView() {
  const { t } = useTranslation(['sources', 'common'])
  const [quickData, setQuickData] = useState<GeoCoverage | null>(null)
  const [analysisResult, setAnalysisResult] = useState<SpatialAnalysisResult | null>(null)
  const [distribution, setDistribution] = useState<ShapeDistributionResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [loadingDistribution, setLoadingDistribution] = useState(false)
  const [showDistribution, setShowDistribution] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch quick coverage data on mount
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const response = await fetch('/api/stats/geo-coverage')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const result = await response.json()
        setQuickData(result)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load coverage data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // Run spatial analysis on demand
  const runAnalysis = async () => {
    setAnalyzing(true)
    setError(null)
    setDistribution(null)
    setShowDistribution(false)
    try {
      const response = await fetch('/api/stats/geo-coverage/analyze', {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const result = await response.json()
      setAnalysisResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  // Fetch distribution by individual shape
  const fetchDistribution = async () => {
    setLoadingDistribution(true)
    setError(null)
    try {
      const response = await fetch('/api/stats/geo-coverage/distribution', {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const result = await response.json()
      setDistribution(result)
      setShowDistribution(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load distribution')
    } finally {
      setLoadingDistribution(false)
    }
  }

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

  if (error && !quickData && !analysisResult) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  // Colors for shape types
  const colors = [
    'bg-blue-500',
    'bg-green-500',
    'bg-purple-500',
    'bg-orange-500',
    'bg-pink-500',
    'bg-cyan-500',
  ]

  // Show analysis results if available, otherwise show quick data
  if (analysisResult) {
    return (
      <div className="space-y-4">
        {/* Analysis status */}
        {analysisResult.status === 'error' && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{analysisResult.message}</AlertDescription>
          </Alert>
        )}

        {analysisResult.status === 'no_geo_column' && (
          <Alert className="border-yellow-300 bg-yellow-50">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="text-yellow-700">
              {analysisResult.message}
            </AlertDescription>
          </Alert>
        )}

        {analysisResult.status === 'no_shapes' && (
          <Alert>
            <Layers className="h-4 w-4" />
            <AlertDescription>{analysisResult.message}</AlertDescription>
          </Alert>
        )}

        {/* Stats cards */}
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-blue-500" />
                <div>
                  <div className="text-xl font-bold">
                    {analysisResult.total_occurrences.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">{t('geoCoverage.totalOccurrences')}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <div>
                  <div className="text-xl font-bold">
                    {analysisResult.occurrences_with_geo.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">{t('geoCoverage.withGeometry')}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <div>
                  <div className="text-xl font-bold">
                    {analysisResult.occurrences_without_geo.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">{t('geoCoverage.withoutGeometry')}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-purple-500" />
                <div>
                  <div className="text-xl font-bold">
                    {analysisResult.analysis_time_seconds}s
                  </div>
                  <p className="text-xs text-muted-foreground">{t('geoCoverage.analysisTime')}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Geo column info */}
        {analysisResult.geo_column && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Database className="h-4 w-4" />
            <span>{t('geoCoverage.geoColumnDetected')}</span>
            <Badge variant="outline" className="font-mono">
              {analysisResult.geo_column}
            </Badge>
          </div>
        )}

        {/* Shape coverage details */}
        {analysisResult.shape_coverage.length > 0 && (
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Layers className="h-4 w-4" />
                {t('geoCoverage.coverageByShapeType')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analysisResult.shape_coverage.map((shape, idx) => {
                  const colorClass = colors[idx % colors.length]

                  return (
                    <div key={shape.shape_table} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded ${colorClass}`} />
                          <span>{shape.shape_type}</span>
                          <Badge variant="secondary" className="text-xs">
                            {shape.total_shapes} {t('geoCoverage.shapes')}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">
                            {shape.occurrences_covered.toLocaleString()} {t('geoCoverage.occurrences')}
                          </span>
                          <Badge
                            variant="outline"
                            className={
                              shape.coverage_percent >= 80
                                ? 'bg-green-50 text-green-700 border-green-300'
                                : shape.coverage_percent >= 50
                                  ? 'bg-yellow-50 text-yellow-700 border-yellow-300'
                                  : 'bg-red-50 text-red-700 border-red-300'
                            }
                          >
                            {shape.coverage_percent}%
                          </Badge>
                        </div>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full ${colorClass} transition-all`}
                          style={{ width: `${Math.min(100, shape.coverage_percent)}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Distribution by individual shape */}
        {analysisResult.status === 'success' && (
          <Card>
            <CardHeader className="py-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <BarChart3 className="h-4 w-4" />
                  {t('geoCoverage.distributionByShape')}
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (!distribution && !loadingDistribution) {
                      fetchDistribution()
                    } else {
                      setShowDistribution(!showDistribution)
                    }
                  }}
                  disabled={loadingDistribution}
                >
                  {loadingDistribution ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : showDistribution ? (
                    <ChevronUp className="mr-2 h-4 w-4" />
                  ) : (
                    <ChevronDown className="mr-2 h-4 w-4" />
                  )}
                  {loadingDistribution
                    ? t('common:status.loading')
                    : distribution
                      ? showDistribution
                        ? t('geoCoverage.hide')
                        : t('geoCoverage.show')
                      : t('geoCoverage.loadDistribution')}
                </Button>
              </div>
            </CardHeader>
            {showDistribution && distribution && (
              <CardContent>
                {distribution.status === 'error' ? (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>{distribution.message}</AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                      <span>{t('geoCoverage.shapesAnalyzed', { count: distribution.shapes.length })}</span>
                      <span>{t('geoCoverage.time')}: {distribution.analysis_time_seconds}s</span>
                    </div>
                    <ScrollArea className="h-[300px] pr-4">
                      <div className="space-y-2">
                        {distribution.shapes
                          .filter((s) => s.occurrence_count > 0)
                          .map((shape, idx) => {
                            const colorClass = colors[idx % colors.length]
                            return (
                              <div
                                key={shape.shape_id}
                                className="flex items-center gap-3 py-1.5 border-b border-muted/50 last:border-0"
                              >
                                <div className={`w-2 h-2 rounded-full ${colorClass} flex-shrink-0`} />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium truncate">{shape.shape_name}</span>
                                    <Badge variant="secondary" className="text-xs flex-shrink-0">
                                      {shape.shape_type}
                                    </Badge>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                  <span className="text-sm text-muted-foreground">
                                    {shape.occurrence_count.toLocaleString()}
                                  </span>
                                  <Badge
                                    variant="outline"
                                    className={`text-xs ${
                                      shape.percent_of_total >= 10
                                        ? 'bg-blue-50 text-blue-700 border-blue-300'
                                        : shape.percent_of_total >= 5
                                          ? 'bg-green-50 text-green-700 border-green-300'
                                          : ''
                                    }`}
                                  >
                                    {shape.percent_of_total}%
                                  </Badge>
                                </div>
                              </div>
                            )
                          })}
                      </div>
                    </ScrollArea>
                    {distribution.shapes.filter((s) => s.occurrence_count === 0).length > 0 && (
                      <p className="text-xs text-muted-foreground mt-2">
                        {t('geoCoverage.shapesWithoutOccurrences', { count: distribution.shapes.filter((s) => s.occurrence_count === 0).length })}
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        )}

        {/* Re-run button */}
        <div className="flex justify-end">
          <Button variant="outline" onClick={runAnalysis} disabled={analyzing}>
            {analyzing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            {t('geoCoverage.rerunAnalysis')}
          </Button>
        </div>
      </div>
    )
  }

  // Initial view with quick data and analysis button
  const hasQuickData = quickData && quickData.total_occurrences > 0

  return (
    <div className="space-y-4">
      {/* Quick stats if available */}
      {hasQuickData && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-blue-500" />
                  <div>
                    <div className="text-xl font-bold">
                      {quickData.total_occurrences.toLocaleString()}
                    </div>
                    <p className="text-xs text-muted-foreground">{t('geoCoverage.totalOccurrences')}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <div>
                    <div className="text-xl font-bold">
                      {quickData.occurrences_with_geo.toLocaleString()}
                    </div>
                    <p className="text-xs text-muted-foreground">{t('geoCoverage.withGeometry')}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-purple-500" />
                  <div>
                    <div className="text-xl font-bold">
                      {quickData.available_shapes.reduce((sum, s) => sum + s.shape_count, 0)}
                    </div>
                    <p className="text-xs text-muted-foreground">{t('geoCoverage.availableShapes')}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Geo column info */}
          {quickData.geo_column && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Database className="h-4 w-4" />
              <span>{t('geoCoverage.geoColumn')}</span>
              <Badge variant="outline" className="font-mono">
                {quickData.geo_column}
              </Badge>
            </div>
          )}

          {/* Available shapes */}
          {quickData.available_shapes.length > 0 && (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Layers className="h-4 w-4" />
                  {t('geoCoverage.shapesAvailableForAnalysis')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {quickData.available_shapes.map((shape, idx) => {
                    const colorClass = colors[idx % colors.length]

                    return (
                      <div
                        key={shape.table_name}
                        className="flex items-center justify-between py-2 border-b last:border-0"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded ${colorClass}`} />
                          <div>
                            <span className="font-medium">{shape.display_name}</span>
                            {shape.shape_types.length > 0 && (
                              <div className="flex gap-1 mt-1">
                                {shape.shape_types.slice(0, 3).map((type) => (
                                  <Badge key={type} variant="secondary" className="text-xs">
                                    {type}
                                  </Badge>
                                ))}
                                {shape.shape_types.length > 3 && (
                                  <Badge variant="secondary" className="text-xs">
                                    +{shape.shape_types.length - 3}
                                  </Badge>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{shape.shape_count} {t('geoCoverage.shapes')}</Badge>
                          {shape.has_geometry ? (
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          ) : (
                            <AlertTriangle className="h-4 w-4 text-yellow-500" />
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Spatial analysis section */}
      <Card className={quickData?.ready_for_analysis ? 'border-green-200 bg-green-50/30' : 'border-dashed'}>
        <CardContent className="py-8 text-center">
          <Layers className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="font-medium mb-2">{t('geoCoverage.spatialAnalysis')}</h3>
          <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
            {t('geoCoverage.spatialAnalysisDescription')}
          </p>
          <Button onClick={runAnalysis} disabled={analyzing}>
            {analyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('geoCoverage.analysisInProgress')}
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                {t('geoCoverage.runSpatialAnalysis')}
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Error display */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
