import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Layers, Loader2, Map, MapPin } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { getSpatialMapRenderUrl } from '@/features/import/api/spatial-map'
import {
  spatialMapLayerSummaryQueryOptions,
  spatialMapSummaryQueryOptions,
} from '@/features/import/queryUtils'

const ALL_LAYERS_VALUE = '__all_layers__'
const MAP_RENDER_LIMIT = 1000

interface SpatialMapViewProps {
  referenceName: string
}

function formatCount(value: number | undefined) {
  return value == null ? '-' : value.toLocaleString()
}

export function SpatialMapView({ referenceName }: SpatialMapViewProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [selectedLayerState, setSelectedLayerState] = useState<{
    referenceName: string
    value: string
  } | null>(null)
  const [loadedMapUrl, setLoadedMapUrl] = useState<string | null>(null)

  const summaryQuery = useQuery(spatialMapSummaryQueryOptions(referenceName))
  const summary = summaryQuery.data
  const selectedLayerValue =
    selectedLayerState?.referenceName === referenceName ? selectedLayerState.value : null
  const selectedValue = selectedLayerValue ?? ALL_LAYERS_VALUE
  const effectiveLayer = selectedValue === ALL_LAYERS_VALUE ? null : selectedValue
  const layerSummaryQuery = useQuery({
    ...spatialMapLayerSummaryQueryOptions(referenceName, effectiveLayer),
    enabled: Boolean(summary?.is_mappable && effectiveLayer),
  })
  const inspection = effectiveLayer ? (layerSummaryQuery.data ?? summary) : summary
  const selectedLayerLabel =
    effectiveLayer == null
      ? t('spatialMap.allLayers', 'All layers')
      : summary?.layers.find((layer) => layer.value === effectiveLayer)?.label ?? effectiveLayer
  const mapUrl = useMemo(
    () =>
      getSpatialMapRenderUrl(referenceName, {
        layer: effectiveLayer,
        limit: MAP_RENDER_LIMIT,
      }),
    [effectiveLayer, referenceName]
  )

  if (summaryQuery.isLoading) {
    return (
      <Card>
        <CardContent className="flex min-h-[260px] items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('spatialMap.loading', 'Loading map...')}
        </CardContent>
      </Card>
    )
  }

  if (summaryQuery.isError) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>{t('spatialMap.loadErrorTitle', 'Map unavailable')}</AlertTitle>
        <AlertDescription>
          {summaryQuery.error instanceof Error
            ? summaryQuery.error.message
            : t('spatialMap.loadErrorDescription', 'Unable to load spatial data.')}
        </AlertDescription>
      </Alert>
    )
  }

  if (!summary?.is_mappable) {
    return (
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>{t('spatialMap.notMappableTitle', 'No map data')}</AlertTitle>
        <AlertDescription>
          {t(
            'spatialMap.notMappableDescription',
            'This reference does not expose a geometry column that can be mapped.'
          )}
        </AlertDescription>
      </Alert>
    )
  }

  const isLayerLoading = Boolean(effectiveLayer && layerSummaryQuery.isFetching)
  const layers = summary.layers
  const showLayerOverview = layers.length > 1 && effectiveLayer == null
  const isMapLoading = !showLayerOverview && loadedMapUrl !== mapUrl

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Layers className="h-7 w-7 text-primary" />
            <div>
              <div className="text-lg font-semibold">{formatCount(inspection?.with_geometry)}</div>
              <div className="text-xs text-muted-foreground">
                {t('spatialMap.withGeometry', 'With geometry')}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Map className="h-7 w-7 text-emerald-600" />
            <div>
              <div className="text-lg font-semibold">
                {inspection
                  ? t(`spatialMap.kind.${inspection.geometry_kind}`, inspection.geometry_kind)
                  : '-'}
              </div>
              <div className="text-xs text-muted-foreground">
                {inspection?.geometry_column ?? '-'}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <MapPin className="h-7 w-7 text-amber-600" />
            <div>
              <div className="text-lg font-semibold">
                {formatCount(inspection?.without_geometry)}
              </div>
              <div className="text-xs text-muted-foreground">
                {t('spatialMap.withoutGeometry', 'Without geometry')}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base">{t('spatialMap.title', 'Map')}</CardTitle>
              <CardDescription>
                {t('spatialMap.plotlyDescription', '{{mapped}} mapped features in {{layer}}', {
                  mapped: formatCount(inspection?.with_geometry),
                  layer: selectedLayerLabel,
                })}
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {isLayerLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
              {layers.length > 1 && (
                <Select
                  value={selectedValue}
                  onValueChange={(value) => setSelectedLayerState({ referenceName, value })}
                >
                  <SelectTrigger className="w-[240px]">
                    <SelectValue placeholder={t('spatialMap.layer', 'Layer')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_LAYERS_VALUE}>
                      {t('spatialMap.allLayers', 'All layers')}
                    </SelectItem>
                    {layers.map((layer) => (
                      <SelectItem key={layer.value} value={layer.value}>
                        {t('spatialMap.layerOption', '{{label}} · {{mappedCount}}', {
                          label: layer.label,
                          mappedCount: layer.with_geometry.toLocaleString(),
                        })}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              {inspection?.geometry_types.map((geometryType) => (
                <Badge key={geometryType} variant="outline">
                  {geometryType}
                </Badge>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {showLayerOverview ? (
            <div className="rounded-md border bg-muted/20 p-4">
              <div className="mb-4">
                <div className="text-sm font-medium">
                  {t('spatialMap.layerOverviewTitle', 'Layer overview')}
                </div>
                <div className="text-xs text-muted-foreground">
                  {t(
                    'spatialMap.layerOverviewDescription',
                    'Select a layer to load the interactive map.'
                  )}
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {layers.map((layer) => (
                  <Button
                    key={layer.value}
                    type="button"
                    variant="outline"
                    className="h-auto justify-start px-3 py-2 text-left"
                    onClick={() => setSelectedLayerState({ referenceName, value: layer.value })}
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">{layer.label}</span>
                      <span className="block text-xs text-muted-foreground">
                        {t('spatialMap.layerFeatureCount', '{{mapped}} / {{total}} geometries', {
                          mapped: layer.with_geometry.toLocaleString(),
                          total: layer.feature_count.toLocaleString(),
                        })}
                      </span>
                    </span>
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <div className="relative overflow-hidden rounded-md border bg-muted/30">
              {isMapLoading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-background/80 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('spatialMap.renderLoading', 'Rendering map...')}
                </div>
              )}
              <iframe
                key={mapUrl}
                title={t('spatialMap.mapFrameTitle', 'Spatial feature map')}
                src={mapUrl}
                className="h-[520px] w-full bg-background"
                onLoad={() => setLoadedMapUrl(mapUrl)}
              />
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
            <span>
              {inspection?.bounding_box
                ? t(
                    'spatialMap.bounds',
                    'Bounds: {{minX}}, {{minY}} → {{maxX}}, {{maxY}}',
                    {
                      minX: inspection.bounding_box.min_x.toFixed(4),
                      minY: inspection.bounding_box.min_y.toFixed(4),
                      maxX: inspection.bounding_box.max_x.toFixed(4),
                      maxY: inspection.bounding_box.max_y.toFixed(4),
                    }
                  )
                : t('spatialMap.noBounds', 'No bounds available')}
            </span>
            {summary.layer_column && (
              <span>
                {t('spatialMap.layerColumn', 'Layer column: {{column}}', {
                  column: summary.layer_column,
                })}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
