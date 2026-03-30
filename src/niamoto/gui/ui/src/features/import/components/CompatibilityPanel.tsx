/**
 * CompatibilityPanel - Shows pre-import impact check results
 *
 * Displays impact items grouped by severity:
 * - Red: blocks_import (missing columns in import.yml)
 * - Orange: breaks_transform (missing columns in transform.yml)
 * - Yellow: warning (type changes)
 * - Blue: opportunity (new columns)
 */

import { AlertTriangle, AlertCircle, Info, Sparkles, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ImpactCheckResult, ImpactItem } from '../api/compatibility'

interface CompatibilityPanelProps {
  reports: ImpactCheckResult[]
  unmatchedFiles: string[]
  onContinue: () => void
  onFixData: () => void
}

const LEVEL_CONFIG = {
  blocks_import: {
    icon: AlertCircle,
    label: 'Blocks Import',
    className: 'text-red-600 dark:text-red-400',
    bgClassName: 'bg-red-50 dark:bg-red-950/30',
    borderClassName: 'border-red-200 dark:border-red-900',
  },
  breaks_transform: {
    icon: AlertTriangle,
    label: 'Breaks Transform',
    className: 'text-orange-600 dark:text-orange-400',
    bgClassName: 'bg-orange-50 dark:bg-orange-950/30',
    borderClassName: 'border-orange-200 dark:border-orange-900',
  },
  warning: {
    icon: Info,
    label: 'Warning',
    className: 'text-yellow-600 dark:text-yellow-400',
    bgClassName: 'bg-yellow-50 dark:bg-yellow-950/30',
    borderClassName: 'border-yellow-200 dark:border-yellow-900',
  },
  opportunity: {
    icon: Sparkles,
    label: 'New Column',
    className: 'text-blue-600 dark:text-blue-400',
    bgClassName: 'bg-blue-50 dark:bg-blue-950/30',
    borderClassName: 'border-blue-200 dark:border-blue-900',
  },
} as const

function ImpactItemRow({ item }: { item: ImpactItem }) {
  const config = LEVEL_CONFIG[item.level]
  const Icon = config.icon

  return (
    <div className={`flex items-start gap-2 rounded-md border px-3 py-2 ${config.bgClassName} ${config.borderClassName}`}>
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${config.className}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className={`text-xs font-medium uppercase ${config.className}`}>{config.label}</span>
          <code className="text-sm font-semibold">{item.column}</code>
        </div>
        <p className="text-sm text-muted-foreground">{item.detail}</p>
        {item.referenced_in.length > 0 && (
          <div className="mt-1 space-y-0.5">
            {item.referenced_in.map((ref, i) => (
              <p key={i} className="text-xs text-muted-foreground/70">&rarr; {ref}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function CompatibilityPanel({ reports, unmatchedFiles, onContinue, onFixData }: CompatibilityPanelProps) {
  const totalMatched = reports.reduce((sum, r) => sum + r.matched_columns.length, 0)
  const hasBlockers = reports.some((r) => r.has_blockers)
  const hasWarnings = reports.some((r) => r.has_warnings)

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className="h-5 w-5 text-yellow-500" />
          Compatibility Check
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Matched columns summary */}
        {totalMatched > 0 && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <span>{totalMatched} columns OK</span>
          </div>
        )}

        {/* Impact items per report */}
        {reports.map((report) => (
          <div key={report.entity_name} className="space-y-2">
            {reports.length > 1 && (
              <h4 className="text-sm font-medium">{report.entity_name}</h4>
            )}
            {report.skipped_reason && (
              <div className="flex items-start gap-2 rounded-md border border-muted bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{report.skipped_reason}</span>
              </div>
            )}
            {report.info_message && (
              <div className="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300">
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{report.info_message}</span>
              </div>
            )}
            {report.error && (
              <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
                {report.error}
              </div>
            )}
            {report.impacts.map((item, i) => (
              <ImpactItemRow key={`${report.entity_name}-${i}`} item={item} />
            ))}
          </div>
        ))}

        {/* Unmatched files info */}
        {unmatchedFiles.length > 0 && (
          <div className="flex items-start gap-2 text-sm text-muted-foreground">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {unmatchedFiles.length} new file{unmatchedFiles.length > 1 ? 's' : ''} — will be auto-configured
            </span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <Button
            onClick={onContinue}
            variant={hasBlockers ? 'outline' : 'default'}
            size="sm"
          >
            {hasBlockers || hasWarnings ? 'Continue anyway' : 'Continue'}
          </Button>
          <Button onClick={onFixData} variant="ghost" size="sm">
            Fix data
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
