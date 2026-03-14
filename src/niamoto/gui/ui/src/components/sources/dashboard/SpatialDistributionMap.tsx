/**
 * SpatialDistributionMap - Map view for occurrence distribution
 *
 * Shows bounding box, coordinate coverage, and spatial statistics.
 * Full Leaflet map can be added later.
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Map,
  MapPin,
  AlertTriangle,
  CheckCircle2,
  Globe2,
  Navigation,
} from 'lucide-react'

interface SpatialStats {
  total_points: number
  with_coordinates: number
  without_coordinates: number
  bounding_box: {
    min_x: number
    min_y: number
    max_x: number
    max_y: number
  } | null
  points_outside_bounds: number
  coordinate_columns: Record<string, string>
}

export function SpatialDistributionMap() {
  const [stats, setStats] = useState<SpatialStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true)
      try {
        const response = await fetch('/api/stats/spatial')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const data = await response.json()
        setStats(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load spatial stats')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-64 w-full" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
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

  if (!stats || stats.total_points === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Map className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="text-muted-foreground">No spatial data found</p>
          <p className="text-xs text-muted-foreground mt-1">
            Import data with coordinate columns (x/y, lon/lat) to see spatial distribution
          </p>
        </CardContent>
      </Card>
    )
  }

  const coveragePercent = stats.total_points > 0
    ? Math.round((stats.with_coordinates / stats.total_points) * 100)
    : 0

  return (
    <div className="space-y-4">
      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-blue-500" />
              <div>
                <div className="text-xl font-bold">
                  {stats.with_coordinates.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground">With coordinates</p>
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
                  {stats.without_coordinates.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground">Missing coordinates</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              {coveragePercent >= 80 ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
              )}
              <div>
                <div className="text-xl font-bold">{coveragePercent}%</div>
                <p className="text-xs text-muted-foreground">Coverage</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Globe2 className="h-4 w-4 text-purple-500" />
              <div>
                <div className="text-xl font-bold">
                  {stats.points_outside_bounds}
                </div>
                <p className="text-xs text-muted-foreground">Outside bounds</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Map placeholder with bounding box info */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Navigation className="h-4 w-4" />
            Bounding Box
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stats.bounding_box ? (
            <div className="space-y-4">
              {/* Visual bounding box representation */}
              <div className="relative bg-gradient-to-br from-blue-50 to-green-50 rounded-lg p-8 border-2 border-dashed border-blue-200">
                <div className="absolute top-2 left-2 text-xs text-muted-foreground">
                  NW: {stats.bounding_box.min_x.toFixed(4)}, {stats.bounding_box.max_y.toFixed(4)}
                </div>
                <div className="absolute top-2 right-2 text-xs text-muted-foreground">
                  NE: {stats.bounding_box.max_x.toFixed(4)}, {stats.bounding_box.max_y.toFixed(4)}
                </div>
                <div className="absolute bottom-2 left-2 text-xs text-muted-foreground">
                  SW: {stats.bounding_box.min_x.toFixed(4)}, {stats.bounding_box.min_y.toFixed(4)}
                </div>
                <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
                  SE: {stats.bounding_box.max_x.toFixed(4)}, {stats.bounding_box.min_y.toFixed(4)}
                </div>

                <div className="text-center py-8">
                  <Map className="h-16 w-16 mx-auto text-blue-300 mb-4" />
                  <p className="text-sm text-muted-foreground">
                    {stats.with_coordinates.toLocaleString()} points in this area
                  </p>
                </div>
              </div>

              {/* Coordinate details */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">Longitude Range</p>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">
                      {stats.bounding_box.min_x.toFixed(4)}
                    </Badge>
                    <span className="text-muted-foreground">to</span>
                    <Badge variant="outline">
                      {stats.bounding_box.max_x.toFixed(4)}
                    </Badge>
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">Latitude Range</p>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">
                      {stats.bounding_box.min_y.toFixed(4)}
                    </Badge>
                    <span className="text-muted-foreground">to</span>
                    <Badge variant="outline">
                      {stats.bounding_box.max_y.toFixed(4)}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No bounding box available - coordinates may be missing or invalid
            </p>
          )}
        </CardContent>
      </Card>

      {/* Coordinate columns info */}
      {Object.keys(stats.coordinate_columns).length > 0 && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Detected columns:</span>
          {Object.entries(stats.coordinate_columns).map(([key, col]) => (
            <Badge key={key} variant="outline" className="font-mono">
              {key}: {col}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
