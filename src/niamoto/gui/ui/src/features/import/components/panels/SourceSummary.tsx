import { useQuery } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  GitBranch,
  Loader2,
  Map,
  MapPin,
  Settings,
  Table2,
  Zap,
} from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import type { SpatialMapInspection } from '@/features/import/api/spatial-map'
import { hasHierarchyInspection } from '@/features/import/referenceKinds'
import { tablesQueryOptions } from '@/features/import/queryUtils'
import { apiClient } from '@/shared/lib/api/client'

interface EnrichmentConfigSource {
  id: string
  label: string
  enabled: boolean
}

interface EnrichmentSourceStats {
  source_id: string
  label: string
  enabled?: boolean
  total: number
  enriched: number
  pending: number
  status: string
}

interface EnrichmentStats {
  entity_total?: number
  source_total?: number
  total: number
  enriched: number
  pending: number
  sources: EnrichmentSourceStats[]
}

interface EnrichmentJob {
  status: 'pending' | 'running' | 'paused' | 'paused_offline' | 'completed' | 'failed' | 'cancelled'
  total: number
  processed: number
  pending_total?: number
  pending_processed?: number
  current_source_label?: string | null
  current_entity?: string | null
}

interface SourceSummaryProps {
  entityType: 'dataset' | 'reference'
  name: string
  tableName: string
  rowCount?: number
  kind?: string
  connectorType?: string
  path?: string
  hasEnrichment?: boolean
  enrichmentSources?: EnrichmentConfigSource[]
  hasHierarchy?: boolean
  hasSpatialMap?: boolean
  spatialMap?: SpatialMapInspection
  onPreview: () => void
  onConfigure: () => void
  onOpenExplorer: () => void
  onOpenHierarchy?: () => void
  onOpenMap?: () => void
  onOpenEnrichment?: () => void
}

function formatCount(value: number | undefined) {
  return value == null ? '-' : value.toLocaleString()
}

function hasGeographicColumns(columns: string[]) {
  return columns.some((column) => {
    const lower = column.toLowerCase()
    return (
      lower.includes('geom') ||
      lower.includes('geo') ||
      lower === 'lat' ||
      lower === 'latitude' ||
      lower === 'lon' ||
      lower === 'lng' ||
      lower === 'longitude'
    )
  })
}

function getEnrichmentProgress(stats: EnrichmentStats | undefined) {
  if (!stats || stats.total <= 0) {
    return 0
  }

  return Math.min(100, Math.round((stats.enriched / stats.total) * 100))
}

function getJobProgress(job: EnrichmentJob | null | undefined) {
  if (!job) {
    return null
  }

  const total = Math.max(job.pending_total ?? job.total, 0)
  const processed = Math.min(Math.max(job.pending_processed ?? job.processed, 0), total)
  const percentage = total > 0 ? Math.round((processed / total) * 100) : 0

  return { total, processed, percentage }
}

export function SourceSummary({
  entityType,
  name,
  tableName,
  rowCount,
  kind,
  connectorType,
  path,
  hasEnrichment = false,
  enrichmentSources = [],
  hasHierarchy = false,
  hasSpatialMap = false,
  spatialMap,
  onPreview,
  onConfigure,
  onOpenExplorer,
  onOpenHierarchy,
  onOpenMap,
  onOpenEnrichment,
}: SourceSummaryProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { data: tables } = useQuery(tablesQueryOptions())
  const tableInfo = tables?.find((table) => table.name === tableName)
  const effectiveRowCount = rowCount ?? tableInfo?.count
  const columnCount = tableInfo?.columns.length
  const hasGeoColumns = hasGeographicColumns(tableInfo?.columns ?? [])
  const isEmpty = effectiveRowCount === 0
  const showEnrichmentCard = entityType === 'reference' && Boolean(onOpenEnrichment)
  const showSpatialMapCard = entityType === 'reference' && hasSpatialMap && Boolean(onOpenMap)
  const enabledEnrichmentSources = enrichmentSources.filter((source) => source.enabled)

  const { data: enrichmentStats, isFetching: enrichmentStatsFetching } = useQuery({
    queryKey: ['import', 'summary', 'enrichment-stats', name],
    queryFn: () =>
      apiClient
        .get<EnrichmentStats>(`/enrichment/stats/${encodeURIComponent(name)}`)
        .then((response) => response.data),
    enabled: showEnrichmentCard && hasEnrichment,
    staleTime: 30_000,
  })

  const { data: enrichmentJob } = useQuery({
    queryKey: ['import', 'summary', 'enrichment-job', name],
    queryFn: async () => {
      try {
        const response = await apiClient.get<EnrichmentJob>(
          `/enrichment/job/${encodeURIComponent(name)}`
        )
        return response.data
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          return null
        }
        throw error
      }
    },
    enabled: showEnrichmentCard && hasEnrichment,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' || status === 'pending' ? 3_000 : false
    },
    retry: false,
    staleTime: 10_000,
  })

  const typeLabel =
    entityType === 'dataset'
      ? t('summary.datasetType', 'Dataset')
      : hasHierarchy || hasHierarchyInspection(kind)
        ? t('reference.hierarchical')
        : kind === 'spatial'
          ? t('reference.spatial')
          : t('reference.file')

  const enrichmentProgress = getEnrichmentProgress(enrichmentStats)
  const jobProgress = getJobProgress(enrichmentJob)
  const enrichmentStatus = !hasEnrichment
    ? 'notConfigured'
    : enrichmentJob?.status === 'running' || enrichmentJob?.status === 'pending'
      ? 'running'
      : enrichmentJob?.status === 'failed'
        ? 'failed'
        : enrichmentJob?.status === 'paused' || enrichmentJob?.status === 'paused_offline'
          ? 'paused'
          : enrichmentStats && enrichmentStats.total > 0 && enrichmentStats.pending === 0
            ? 'completed'
            : enrichmentStats && enrichmentStats.enriched > 0
              ? 'partial'
              : 'ready'

  const enrichmentStatusBadge =
    enrichmentStatus === 'notConfigured' ? (
      <Badge variant="outline">{t('summary.enrichment.notConfigured', 'Not configured')}</Badge>
    ) : enrichmentStatus === 'running' ? (
      <Badge className="bg-blue-500">
        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
        {t('enrichmentTab.status.running', 'Running')}
      </Badge>
    ) : enrichmentStatus === 'paused' ? (
      <Badge variant="secondary">{t('enrichmentTab.status.paused', 'Paused')}</Badge>
    ) : enrichmentStatus === 'failed' ? (
      <Badge variant="destructive">
        <AlertCircle className="mr-1 h-3 w-3" />
        {t('enrichmentTab.status.failed', 'Failed')}
      </Badge>
    ) : enrichmentStatus === 'completed' ? (
      <Badge className="bg-green-600">
        <CheckCircle2 className="mr-1 h-3 w-3" />
        {t('enrichmentTab.status.completed', 'Completed')}
      </Badge>
    ) : enrichmentStatus === 'partial' ? (
      <Badge variant="secondary">{t('summary.enrichment.partial', 'Partial')}</Badge>
    ) : (
      <Badge variant="outline">{t('enrichmentTab.status.ready', 'Ready')}</Badge>
    )

  const enrichmentDescription =
    enrichmentStatus === 'notConfigured'
      ? t(
          'summary.enrichment.notConfiguredDescription',
          'Configure external APIs before enriching this reference.'
        )
      : enrichmentStatus === 'running' && jobProgress
        ? t('summary.enrichment.runningDescription', '{{processed}} / {{total}} processed', {
            processed: jobProgress.processed.toLocaleString(),
            total: jobProgress.total.toLocaleString(),
          })
        : enrichmentStatus === 'failed'
          ? t('summary.enrichment.failedDescription', 'The latest enrichment job needs attention.')
          : enrichmentStats && enrichmentStats.total > 0
            ? t('summary.enrichment.coverageDescription', '{{enriched}} / {{total}} enriched', {
                enriched: enrichmentStats.enriched.toLocaleString(),
                total: enrichmentStats.total.toLocaleString(),
              })
            : t('summary.enrichment.readyDescription', 'Sources are configured and ready to run.')

  const enrichmentActionLabel =
    enrichmentStatus === 'notConfigured'
      ? t('summary.enrichment.configureAction', 'Configure enrichment')
      : enrichmentStatus === 'running'
        ? t('summary.enrichment.viewJobAction', 'View job')
        : enrichmentStatus === 'failed'
          ? t('summary.enrichment.viewErrorsAction', 'View errors')
          : enrichmentStatus === 'completed'
            ? t('summary.enrichment.viewResultsAction', 'View results')
            : t('summary.enrichment.manageAction', 'Manage enrichment')

  return (
    <div className="space-y-4">
      <div className="grid gap-3 lg:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            {entityType === 'dataset' ? (
              <Table2 className="h-7 w-7 text-primary" />
            ) : (
              <Database className="h-7 w-7 text-primary" />
            )}
            <div className="min-w-0">
              <div className="text-lg font-semibold">{typeLabel}</div>
              <div className="truncate text-xs text-muted-foreground">{name}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Database className="h-7 w-7 text-blue-500" />
            <div>
              <div className="text-lg font-semibold">{formatCount(effectiveRowCount)}</div>
              <div className="text-xs text-muted-foreground">{t('summary.rows', 'Rows')}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Settings className="h-7 w-7 text-emerald-600" />
            <div>
              <div className="text-lg font-semibold">{formatCount(columnCount)}</div>
              <div className="text-xs text-muted-foreground">{t('summary.columns', 'Columns')}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {isEmpty && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {t(
              'summary.emptyTable',
              'This imported table is empty. Review the import configuration before using it downstream.'
            )}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{t('summary.identity', 'Identity')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid gap-2 sm:grid-cols-2">
            <div>
              <div className="text-xs text-muted-foreground">{t('summary.table', 'Table')}</div>
              <div className="font-mono text-xs">{tableName}</div>
            </div>
            {connectorType && (
              <div>
                <div className="text-xs text-muted-foreground">
                  {t('summary.connector', 'Connector')}
                </div>
                <Badge variant="secondary">{connectorType}</Badge>
              </div>
            )}
            {path && (
              <div className="sm:col-span-2">
                <div className="text-xs text-muted-foreground">
                  {t('summary.sourcePath', 'Source path')}
                </div>
                <div className="truncate font-mono text-xs">{path}</div>
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {hasHierarchy && (
              <Badge variant="outline" className="gap-1">
                <GitBranch className="h-3 w-3" />
                {t('summary.hierarchyAvailable', 'Hierarchy available')}
              </Badge>
            )}
            {hasEnrichment && (
              <Badge variant="outline" className="gap-1">
                <Zap className="h-3 w-3" />
                {t('summary.enrichmentConfigured', 'Enrichment configured')}
              </Badge>
            )}
            {hasGeoColumns && (
              <Badge variant="outline" className="gap-1">
                <MapPin className="h-3 w-3" />
                {t('summary.geographicFields', 'Geographic fields detected')}
              </Badge>
            )}
            {hasSpatialMap && (
              <Badge variant="outline" className="gap-1">
                <Map className="h-3 w-3" />
                {t('summary.mapAvailable', 'Map available')}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {showSpatialMapCard && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Map className="h-4 w-4 text-primary" />
                  {t('summary.map.title', 'Map')}
                </CardTitle>
                <CardDescription>
                  {spatialMap
                    ? t('summary.map.description', '{{mapped}} / {{total}} geometries available', {
                        mapped: spatialMap.with_geometry.toLocaleString(),
                        total: spatialMap.total_features.toLocaleString(),
                      })
                    : t('summary.map.loadingDescription', 'Spatial data detected.')}
                </CardDescription>
              </div>
              {spatialMap?.geometry_kind && (
                <Badge variant="secondary">
                  {t(`spatialMap.kind.${spatialMap.geometry_kind}`, spatialMap.geometry_kind)}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <div className="text-xs text-muted-foreground">
                  {t('summary.map.geometryColumn', 'Geometry column')}
                </div>
                <div className="font-mono text-xs">{spatialMap?.geometry_column ?? '-'}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">
                  {t('summary.map.storage', 'Storage')}
                </div>
                <div className="text-xs">{spatialMap?.geometry_storage ?? '-'}</div>
              </div>
            </div>
            {onOpenMap && (
              <Button onClick={onOpenMap}>
                <Map className="mr-2 h-4 w-4" />
                {t('summary.map.openAction', 'Open map')}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {showEnrichmentCard && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Zap className="h-4 w-4 text-primary" />
                  {t('summary.enrichment.title', 'API enrichment')}
                </CardTitle>
                <CardDescription>{enrichmentDescription}</CardDescription>
              </div>
              {enrichmentStatusBadge}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {hasEnrichment && enrichmentStats && enrichmentStats.total > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{t('summary.enrichment.coverage', 'Coverage')}</span>
                  <span>{enrichmentProgress}%</span>
                </div>
                <Progress value={enrichmentProgress} />
              </div>
            )}

            {hasEnrichment && jobProgress && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>
                  {t('summary.enrichment.jobProgress', '{{processed}} / {{total}} this run', {
                    processed: jobProgress.processed.toLocaleString(),
                    total: jobProgress.total.toLocaleString(),
                  })}
                </span>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {enabledEnrichmentSources.length > 0 ? (
                enabledEnrichmentSources.slice(0, 4).map((source) => (
                  <Badge key={source.id} variant="outline">
                    {source.label}
                  </Badge>
                ))
              ) : (
                <span className="text-xs text-muted-foreground">
                  {t('summary.enrichment.noActiveSources', 'No active source')}
                </span>
              )}
              {enabledEnrichmentSources.length > 4 && (
                <Badge variant="secondary">
                  +{enabledEnrichmentSources.length - 4}
                </Badge>
              )}
              {enrichmentStatsFetching && (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              )}
            </div>

            {onOpenEnrichment && (
              <Button onClick={onOpenEnrichment}>
                <Zap className="mr-2 h-4 w-4" />
                {enrichmentActionLabel}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={onPreview}>
          <Table2 className="mr-2 h-4 w-4" />
          {t('summary.previewData', 'Preview data')}
        </Button>
        {hasHierarchy && onOpenHierarchy && (
          <Button variant="outline" onClick={onOpenHierarchy}>
            <GitBranch className="mr-2 h-4 w-4" />
            {t('summary.inspectHierarchy', 'Inspect hierarchy')}
          </Button>
        )}
        {hasSpatialMap && onOpenMap && (
          <Button variant="outline" onClick={onOpenMap}>
            <Map className="mr-2 h-4 w-4" />
            {t('summary.openMap', 'Open map')}
          </Button>
        )}
        {hasEnrichment && onOpenEnrichment && (
          <Button variant="outline" onClick={onOpenEnrichment}>
            <Zap className="mr-2 h-4 w-4" />
            {t('summary.openEnrichment', 'Open enrichment')}
          </Button>
        )}
        <Button variant="outline" onClick={onConfigure}>
          <Settings className="mr-2 h-4 w-4" />
          {t('summary.configure', 'Configure')}
        </Button>
        <Button variant="outline" onClick={onOpenExplorer}>
          <ExternalLink className="mr-2 h-4 w-4" />
          Data Explorer
        </Button>
      </div>
    </div>
  )
}
