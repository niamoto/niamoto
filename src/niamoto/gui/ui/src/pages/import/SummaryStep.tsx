import { useTranslation } from 'react-i18next'
import { useImport } from './ImportContext'
import { useImportProgress } from './ImportProgressContext'
import { ImportStepCard } from './components/ImportStepCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  FileSpreadsheet,
  TreePine,
  MapPin,
  Map,
  Database,
  Info,
  Globe
} from 'lucide-react'

export function SummaryStep() {
  const { t } = useTranslation(['import', 'common'])
  const { state } = useImport()
  const { occurrences, plots, shapes } = state
  const { progress } = useImportProgress()


  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{t('summary.title')}</h2>
        <p className="text-muted-foreground mt-2">
          {t('summary.description')}
        </p>
      </div>

      {/* Import summary cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Occurrences card */}
        <ImportStepCard
          title={t('summary.sections.occurrences.title')}
          icon={<FileSpreadsheet className="w-5 h-5" />}
          status={progress.occurrences}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t('summary.sections.occurrences.file')}</span>
            <span className="text-sm font-medium">{occurrences.file?.name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t('summary.sections.occurrences.rows')}</span>
            <Badge variant="secondary">
              {occurrences.fileAnalysis?.rowCount ||
               occurrences.fileAnalysis?.row_count ||
               occurrences.fileAnalysis?.total_rows ||
               0}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t('summary.sections.occurrences.mappedFields')}</span>
            <Badge variant="secondary">{Object.keys(occurrences.fieldMappings).length}</Badge>
          </div>
        </ImportStepCard>

        {/* Taxonomy card */}
        <ImportStepCard
          title={t('summary.sections.taxonomy.title')}
          icon={<TreePine className="w-5 h-5 text-green-600" />}
          status={progress.taxonomy}
          variant="success"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t('summary.sections.taxonomy.levels')}</span>
            <Badge variant="secondary">{occurrences.taxonomyHierarchy.ranks.length}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t('summary.sections.taxonomy.hierarchy')}</span>
            <span className="text-xs font-mono">
              {occurrences.taxonomyHierarchy.ranks.slice(0, 3).join(' → ')}
              {occurrences.taxonomyHierarchy.ranks.length > 3 && '...'}
            </span>
          </div>
          {occurrences.apiEnrichment?.enabled && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{t('summary.sections.taxonomy.apiEnrichment')}</span>
              <div className="flex items-center gap-1">
                <Globe className="w-3 h-3 text-blue-600" />
                <span className="text-xs">{t('summary.sections.taxonomy.enabled')}</span>
              </div>
            </div>
          )}
        </ImportStepCard>

        {/* Plots card */}
        {plots?.file && (
          <ImportStepCard
            title={t('summary.sections.plots.title')}
            icon={<MapPin className="w-5 h-5" />}
            status={progress.plots}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{t('summary.sections.occurrences.file')}</span>
              <span className="text-sm font-medium">{plots.file.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{t('summary.sections.occurrences.rows')}</span>
              <Badge variant="secondary">
                {plots.fileAnalysis?.rowCount ||
                 plots.fileAnalysis?.row_count ||
                 plots.fileAnalysis?.total_rows ||
                 0}
              </Badge>
            </div>
            {plots.linkField && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('summary.sections.plots.link')}</span>
                <span className="text-xs font-mono">{plots.linkField} ↔ {plots.occurrenceLinkField}</span>
              </div>
            )}
            {plots.hierarchy?.enabled && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('summary.sections.taxonomy.hierarchy')}</span>
                <span className="text-xs">
                  {t('common:units.levels', { count: plots.hierarchy.levels.length })}
                  {plots.hierarchy.aggregate_geometry && t('aggregations.plots.hierarchy.aggregated')}
                </span>
              </div>
            )}
          </ImportStepCard>
        )}

        {/* Shapes card - Show overall progress if multiple shapes */}
        {shapes && shapes.length > 0 && (
          <ImportStepCard
            title={t('summary.sections.shapes.title')}
            icon={<Map className="w-5 h-5" />}
            status={progress.shapes && progress.shapes.length > 0 ? {
              status: progress.shapes.every(s => s.status === 'completed') ? 'completed' :
                     progress.shapes.some(s => s.status === 'failed') ? 'failed' :
                     progress.shapes.some(s => s.status === 'running') ? 'running' : 'pending',
              progress: progress.shapes.reduce((acc, s) => acc + s.progress, 0) / progress.shapes.length,
              count: progress.shapes.filter(s => s.status === 'completed').reduce((acc, s) => acc + (s.count || 0), 0)
            } : undefined}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{t('summary.sections.shapes.totalElements')}</span>
              <Badge variant="secondary">
                {shapes.reduce((total, shape) => total + (shape.fileAnalysis?.feature_count || 0), 0)}
              </Badge>
            </div>
            {shapes.map((shape, i) => shape.file && (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{shape.fieldMappings?.type || shape.type || `Shape ${i + 1}`}</span>
                <div className="flex items-center gap-2">
                  <span className="font-medium truncate max-w-[150px]">{shape.file.name}</span>
                  <span className="text-muted-foreground">
                    {t('summary.sections.shapes.elements', { count: shape.fileAnalysis?.feature_count || 0 })}
                  </span>
                </div>
              </div>
            ))}
          </ImportStepCard>
        )}
      </div>

      {/* Process overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            {t('summary.process.title')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="mt-0.5">
                <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                  1
                </div>
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">{t('summary.process.occurrences.title')}</div>
                <div className="text-sm text-muted-foreground">
                  {t('summary.process.occurrences.description')}
                  {occurrences.apiEnrichment?.enabled && ` ${t('summary.process.occurrences.withApi')}`}
                </div>
              </div>
            </div>

            {plots?.file && (
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                    2
                  </div>
                </div>
                <div className="flex-1">
                  <div className="font-medium text-sm">{t('summary.process.plots.title')}</div>
                  <div className="text-sm text-muted-foreground">
                    {t('summary.process.plots.description')}
                  </div>
                </div>
              </div>
            )}

            {shapes && shapes.length > 0 && (
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                    {plots?.file ? 3 : 2}
                  </div>
                </div>
                <div className="flex-1">
                  <div className="font-medium text-sm">{t('summary.process.shapes.title')}</div>
                  <div className="text-sm text-muted-foreground">
                    {t('summary.process.shapes.description')}
                  </div>
                </div>
              </div>
            )}

          </div>
        </CardContent>
      </Card>

      {/* Import info */}
      <Alert>
        <Info className="w-4 h-4" />
        <AlertDescription>
          {t('summary.warning')}
        </AlertDescription>
      </Alert>
    </div>
  )
}
