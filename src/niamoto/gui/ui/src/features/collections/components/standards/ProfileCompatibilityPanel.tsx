import { AlertTriangle, CheckCircle, CircleSlash, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import type { StandardCompatibilityReport } from '@/features/collections/hooks/useStandardProfiles'

interface ProfileCompatibilityPanelProps {
  report?: StandardCompatibilityReport
  isLoading?: boolean
  error?: unknown
}

const statusIcon = {
  compatible: CheckCircle,
  plausible: AlertTriangle,
  blocked: CircleSlash,
} as const

export function ProfileCompatibilityPanel({
  report,
  isLoading = false,
  error,
}: ProfileCompatibilityPanelProps) {
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
            : t('collections.standards.compatibilityLoadFailed')}
        </CardContent>
      </Card>
    )
  }

  if (!report) {
    return null
  }

  const Icon = statusIcon[report.status]
  const confidence = Math.round(report.confidence * 100)

  return (
    <Card>
      <CardHeader className="space-y-2 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">
            {t('collections.standards.compatibility')}
          </h3>
          <Badge variant={report.status === 'compatible' ? 'success' : 'outline'}>
            {t(`collections.standards.compatibilityStatus.${report.status}`)}
          </Badge>
          <Badge variant="secondary">{confidence}%</Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          {t('collections.standards.grainSummary', {
            source: report.source_grain,
            target: report.target_grain,
          })}
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {report.warnings.length > 0 && (
          <ul className="space-y-1 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
            {report.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        )}
        {report.blockers.length > 0 && (
          <ul className="space-y-1 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
            {report.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        )}
        {report.evidence.length > 0 && (
          <div className="space-y-2">
            {report.evidence.map((evidence) => (
              <div
                key={`${evidence.kind}-${evidence.message}`}
                className="rounded-md border p-2 text-xs"
              >
                <div className="font-medium">
                  {t(`collections.standards.evidence.${evidence.kind}`, evidence.kind)}
                </div>
                <div className="mt-0.5 text-muted-foreground">
                  {evidence.message}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
