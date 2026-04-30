import { AlertTriangle, CheckCircle, CircleSlash, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import type { StandardValidationReport } from '@/features/collections/hooks/useStandardProfiles'

interface ProfileValidationReportProps {
  report?: StandardValidationReport
  isLoading?: boolean
  error?: unknown
}

export function ProfileValidationReport({
  report,
  isLoading = false,
  error,
}: ProfileValidationReportProps) {
  const { t } = useTranslation(['sources', 'common'])

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('common:status.loading')}
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-destructive/30">
        <CardContent className="p-4 text-sm text-destructive">
          {error instanceof Error
            ? error.message
            : t('collections.standards.validationLoadFailed')}
        </CardContent>
      </Card>
    )
  }

  if (!report) {
    return null
  }

  const hasCritical = report.summary.critical > 0
  const StatusIcon = hasCritical
    ? CircleSlash
    : report.status === 'conformant'
      ? CheckCircle
      : AlertTriangle

  return (
    <Card>
      <CardHeader className="space-y-2 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatusIcon className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">
            {t('collections.standards.validation')}
          </h3>
          <Badge variant={report.status === 'conformant' ? 'success' : 'outline'}>
            {t(`collections.standards.validationStatus.${report.status}`)}
          </Badge>
          {hasCritical && (
            <Badge variant="destructive">
              {t('collections.standards.criticalCount', {
                count: report.summary.critical,
              })}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-2">
          {report.checklist.map((item) => (
            <div key={item.code} className="rounded-md border p-2 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{item.label}</span>
                <Badge variant={item.status === 'pass' ? 'success' : 'outline'}>
                  {t(`collections.standards.checklistStatus.${item.status}`)}
                </Badge>
              </div>
              {item.message && (
                <p className="mt-1 text-muted-foreground">{item.message}</p>
              )}
            </div>
          ))}
        </div>

        {report.issues.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold">
              {t('collections.standards.issues')}
            </h4>
            {report.issues.map((issue) => (
              <div
                key={`${issue.code}-${issue.path ?? issue.message}`}
                className="rounded-md border p-2 text-xs"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={issue.severity === 'critical' ? 'destructive' : 'outline'}>
                    {t(`collections.standards.severity.${issue.severity}`)}
                  </Badge>
                  <span className="font-medium">{issue.code}</span>
                  {issue.path && (
                    <span className="text-muted-foreground">{issue.path}</span>
                  )}
                </div>
                <p className="mt-1 text-muted-foreground">{issue.message}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
