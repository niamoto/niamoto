import { AlertTriangle, BarChart3, CheckCircle2, CircleAlert, Loader2, Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type {
  ImpactCheckResult,
  ImpactItem,
  WidgetImpact,
  WidgetImpactStatus,
} from '@/features/import/api/compatibility'
import type { CompatibilityCheckFailure } from '@/features/import/hooks/useCompatibilityCheck'

interface ImportImpactPanelProps {
  reports: ImpactCheckResult[]
  failedChecks?: CompatibilityCheckFailure[]
  isChecking?: boolean
  onReviewCollection?: (collection: string) => void
}

const widgetStatusOrder: WidgetImpactStatus[] = [
  'broken',
  'degraded',
  'unknown',
  'newly_available',
  'still_valid',
]

function widgetStatusClass(status: WidgetImpactStatus) {
  switch (status) {
    case 'broken':
      return 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200'
    case 'degraded':
      return 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'
    case 'newly_available':
      return 'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200'
    case 'still_valid':
      return 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200'
    default:
      return 'border-border bg-muted/60 text-muted-foreground'
  }
}

function pipelineImpactClass(level: ImpactItem['level']) {
  switch (level) {
    case 'blocks_import':
      return 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200'
    case 'breaks_transform':
    case 'warning':
      return 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'
    default:
      return 'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200'
  }
}

function sortWidgetImpacts(left: WidgetImpact, right: WidgetImpact) {
  const leftIndex = widgetStatusOrder.indexOf(left.status)
  const rightIndex = widgetStatusOrder.indexOf(right.status)
  if (leftIndex !== rightIndex) return leftIndex - rightIndex
  return `${left.collection}:${left.widget_id}`.localeCompare(`${right.collection}:${right.widget_id}`)
}

function sumWidgetStatus(reports: ImpactCheckResult[], status: WidgetImpactStatus) {
  return reports.reduce((total, report) => total + (report.widget_impact_summary?.[status] ?? 0), 0)
}

function translatePipelineDetail(
  detail: string,
  t: (key: string, options?: Record<string, string>) => string
) {
  const missingColumn = detail.match(/^Column '(.+)' missing in new file$/)
  if (missingColumn) {
    return t('impact.details.missingColumn', { column: missingColumn[1] })
  }

  const newColumn = detail.match(/^New column '(.+)' not yet in config$/)
  if (newColumn) {
    return t('impact.details.newColumn', { column: newColumn[1] })
  }

  const typeChanged = detail.match(/^Type changed: (.+) → (.+)$/)
  if (typeChanged) {
    return t('impact.details.typeChanged', {
      from: typeChanged[1],
      to: typeChanged[2],
    })
  }

  return detail
}

function translateWidgetDetail(
  detail: string,
  t: (key: string) => string
) {
  if (detail === 'Incoming field is not used by current widget recipes.') {
    return t('impact.widgetDetails.incomingFieldUnused')
  }

  if (detail.startsWith('Incoming cardinality is too high for a readable donut chart')) {
    return t('impact.widgetDetails.donutTooManyCategories')
  }

  if (detail.startsWith('Incoming cardinality is high enough to require ranking')) {
    return t('impact.widgetDetails.barRequiresRanking')
  }

  if (detail === 'Incoming labels may be too long for the configured chart.') {
    return t('impact.widgetDetails.longLabels')
  }

  if (detail === 'Incoming field coverage is too low for a useful widget.') {
    return t('impact.widgetDetails.lowCoverage')
  }

  if (detail === 'Required source fields are present and chart readability checks passed.') {
    return t('impact.widgetDetails.stillValid')
  }

  return detail
}

export function ImportImpactPanel({
  reports,
  failedChecks = [],
  isChecking = false,
  onReviewCollection,
}: ImportImpactPanelProps) {
  const { t } = useTranslation(['sources'])
  const widgetImpacts = reports.flatMap((report) => report.widget_impacts ?? []).sort(sortWidgetImpacts)
  const pipelineImpacts = reports.flatMap((report) => report.impacts ?? [])
  const brokenWidgets = sumWidgetStatus(reports, 'broken')
  const degradedWidgets = sumWidgetStatus(reports, 'degraded')
  const newWidgetFields = sumWidgetStatus(reports, 'newly_available')
  const stillValidWidgets = sumWidgetStatus(reports, 'still_valid')
  const hasWidgetRisk = brokenWidgets > 0 || degradedWidgets > 0
  const visibleWidgetImpacts = widgetImpacts.filter((impact) => impact.status !== 'still_valid').slice(0, 6)
  const visiblePipelineImpacts = pipelineImpacts.slice(0, 4)

  if (!isChecking && reports.length === 0 && failedChecks.length === 0) {
    return null
  }

  return (
    <section className="rounded-lg border bg-background p-3" data-testid="import-impact-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          {isChecking ? (
            <Loader2 className="mt-0.5 h-4 w-4 animate-spin text-primary" />
          ) : hasWidgetRisk || pipelineImpacts.length > 0 || failedChecks.length > 0 ? (
            <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-600" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
          )}
          <div className="min-w-0">
            <h3 className="text-sm font-medium">{t('impact.title')}</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              {isChecking
                ? t('impact.checking')
                : t('impact.description', { count: reports.length })}
            </p>
          </div>
        </div>

        {!isChecking && (
          <div className="flex flex-wrap gap-1.5">
            {brokenWidgets > 0 && (
              <Badge className={widgetStatusClass('broken')} variant="outline">
                {t('impact.widgets.broken', { count: brokenWidgets })}
              </Badge>
            )}
            {degradedWidgets > 0 && (
              <Badge className={widgetStatusClass('degraded')} variant="outline">
                {t('impact.widgets.degraded', { count: degradedWidgets })}
              </Badge>
            )}
            {newWidgetFields > 0 && (
              <Badge className={widgetStatusClass('newly_available')} variant="outline">
                {t('impact.widgets.newlyAvailable', { count: newWidgetFields })}
              </Badge>
            )}
            {stillValidWidgets > 0 && (
              <Badge className={widgetStatusClass('still_valid')} variant="outline">
                {t('impact.widgets.stillValid', { count: stillValidWidgets })}
              </Badge>
            )}
          </div>
        )}
      </div>

      {!isChecking && (failedChecks.length > 0 || visiblePipelineImpacts.length > 0 || visibleWidgetImpacts.length > 0) && (
        <div className="mt-3 grid gap-2 lg:grid-cols-2">
          {failedChecks.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-medium uppercase text-muted-foreground">
                <CircleAlert className="h-3.5 w-3.5" />
                {t('impact.failedChecksTitle')}
              </div>
              {failedChecks.slice(0, 4).map((failure) => (
                <div key={failure.file} className="rounded-md border border-red-200 bg-red-50 p-2 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">
                  <div className="text-xs font-medium">{failure.file}</div>
                  <p className="mt-1 text-xs">{failure.error}</p>
                </div>
              ))}
            </div>
          )}

          {visiblePipelineImpacts.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-medium uppercase text-muted-foreground">
                <CircleAlert className="h-3.5 w-3.5" />
                {t('impact.pipelineTitle')}
              </div>
              {visiblePipelineImpacts.map((impact) => (
                <div key={`${impact.column}:${impact.level}:${impact.detail}`} className="rounded-md border bg-muted/20 p-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-medium">{impact.column}</span>
                    <Badge className={pipelineImpactClass(impact.level)} variant="outline">
                      {t(`impact.level.${impact.level}`)}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {translatePipelineDetail(impact.detail, t)}
                  </p>
                </div>
              ))}
            </div>
          )}

          {visibleWidgetImpacts.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-medium uppercase text-muted-foreground">
                <BarChart3 className="h-3.5 w-3.5" />
                {t('impact.widgetsTitle')}
              </div>
              {visibleWidgetImpacts.map((impact) => (
                <div key={`${impact.collection}:${impact.widget_id}`} className="rounded-md border bg-muted/20 p-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="min-w-0 truncate text-xs font-medium">
                      {impact.widget_id}
                    </span>
                    <Badge className={widgetStatusClass(impact.status)} variant="outline">
                      {t(`impact.widgetStatus.${impact.status}`)}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {translateWidgetDetail(impact.detail, t)}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <Badge variant="secondary" className="text-[10px]">
                      {impact.collection}
                    </Badge>
                    {impact.widget_plugin && (
                      <Badge variant="outline" className="text-[10px]">
                        {impact.widget_plugin}
                      </Badge>
                    )}
                    {impact.affected_columns.map((column) => (
                      <Badge key={column} variant="outline" className="text-[10px]">
                        {column}
                      </Badge>
                    ))}
                  </div>
                  {onReviewCollection && impact.status !== 'still_valid' && (
                    <Button
                      type="button"
                      variant="link"
                      size="sm"
                      className={cn('mt-1 h-auto p-0 text-xs', impact.status === 'broken' && 'text-red-700 dark:text-red-300')}
                      onClick={() => onReviewCollection(impact.collection)}
                    >
                      <Sparkles className="mr-1 h-3.5 w-3.5" />
                      {t('impact.reviewWidgets')}
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
