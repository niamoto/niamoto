import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  AlertTriangle,
  Database,
  ExternalLink,
  GitBranch,
  MapPin,
  Settings,
  Table2,
  Zap,
} from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { tablesQueryOptions } from '@/features/import/queryUtils'

interface SourceSummaryProps {
  entityType: 'dataset' | 'reference'
  name: string
  tableName: string
  rowCount?: number
  kind?: string
  connectorType?: string
  path?: string
  hasEnrichment?: boolean
  hasHierarchy?: boolean
  onPreview: () => void
  onConfigure: () => void
  onOpenExplorer: () => void
  onOpenHierarchy?: () => void
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

export function SourceSummary({
  entityType,
  name,
  tableName,
  rowCount,
  kind,
  connectorType,
  path,
  hasEnrichment = false,
  hasHierarchy = false,
  onPreview,
  onConfigure,
  onOpenExplorer,
  onOpenHierarchy,
  onOpenEnrichment,
}: SourceSummaryProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { data: tables } = useQuery(tablesQueryOptions())
  const tableInfo = tables?.find((table) => table.name === tableName)
  const effectiveRowCount = rowCount ?? tableInfo?.count
  const columnCount = tableInfo?.columns.length
  const hasGeoColumns = hasGeographicColumns(tableInfo?.columns ?? [])
  const isEmpty = effectiveRowCount === 0

  const typeLabel =
    entityType === 'dataset'
      ? t('summary.datasetType', 'Dataset')
      : kind === 'hierarchical'
        ? t('reference.hierarchical')
        : kind === 'spatial'
          ? t('reference.spatial')
          : t('reference.file')

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
          </div>
        </CardContent>
      </Card>

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
