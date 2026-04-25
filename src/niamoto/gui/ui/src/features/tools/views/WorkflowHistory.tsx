import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { format, formatDistanceToNow } from 'date-fns'
import { enUS, fr } from 'date-fns/locale'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  FileClock,
  Eye,
  Layers,
  Loader2,
  RefreshCw,
  Send,
  Terminal,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { usePipelineHistory, type JobHistoryEntry } from '@/hooks/usePipelineHistory'
import { usePipelineStatus, type RunningJob } from '@/hooks/usePipelineStatus'
import { cn } from '@/lib/utils'

type HistoryStatus = 'completed' | 'failed' | 'cancelled' | 'interrupted' | 'running' | string

interface HistoryStats {
  total: number
  completed: number
  failed: number
  interrupted: number
}

const HISTORY_LIMIT = 50
const RAW_RESULT_MAX_LENGTH = 12_000

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function parseDate(value?: string | null): Date | null {
  if (!value) {
    return null
  }

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function formatDateTime(value: string | null | undefined): string {
  const date = parseDate(value)
  return date ? format(date, 'PP p') : '-'
}

function formatRelativeDate(
  value: string | null | undefined,
  locale: typeof fr | typeof enUS,
): string {
  const date = parseDate(value)

  if (!date) {
    return '-'
  }

  return formatDistanceToNow(date, { addSuffix: true, locale })
}

function durationSeconds(startedAt?: string | null, completedAt?: string | null): number | null {
  const started = parseDate(startedAt)
  const completed = parseDate(completedAt)

  if (!started || !completed) {
    return null
  }

  return Math.max(0, Math.round((completed.getTime() - started.getTime()) / 1000))
}

function runningDurationSeconds(startedAt?: string | null): number | null {
  const started = parseDate(startedAt)

  if (!started) {
    return null
  }

  return Math.max(0, Math.round((Date.now() - started.getTime()) / 1000))
}

function formatDuration(seconds: number | null, t: TFunction): string {
  if (seconds == null) {
    return '-'
  }

  if (seconds < 60) {
    return t('workflowHistory.durationSeconds', '{{count}}s', { count: seconds })
  }

  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60

  if (minutes < 60) {
    return remainder > 0
      ? t('workflowHistory.durationMinutesSeconds', '{{minutes}}m {{seconds}}s', {
        minutes,
        seconds: remainder,
      })
      : t('workflowHistory.durationMinutes', '{{count}}m', { count: minutes })
  }

  const hours = Math.floor(minutes / 60)
  const minuteRemainder = minutes % 60
  return minuteRemainder > 0
    ? t('workflowHistory.durationHoursMinutes', '{{hours}}h {{minutes}}m', {
      hours,
      minutes: minuteRemainder,
    })
    : t('workflowHistory.durationHours', '{{count}}h', { count: hours })
}

function jobTarget(
  groupBy: string | null | undefined,
  groupBys: string[] | null | undefined,
  t: TFunction,
): string {
  if (groupBys && groupBys.length > 1) {
    return t('workflowHistory.targets.collections', '{{count}} collections', {
      count: groupBys.length,
    })
  }

  if (groupBys && groupBys.length === 1) {
    return groupBys[0]
  }

  if (groupBy) {
    return groupBy
  }

  return t('workflowHistory.targets.project', 'Project')
}

function typeMeta(type: string, t: TFunction) {
  switch (type) {
    case 'import':
      return {
        icon: Database,
        label: t('workflowHistory.types.import', 'Import'),
        className: 'bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400',
      }
    case 'transform':
      return {
        icon: Layers,
        label: t('workflowHistory.types.transform', 'Transform'),
        className: 'bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400',
      }
    case 'export':
      return {
        icon: Send,
        label: t('workflowHistory.types.export', 'Export'),
        className: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400',
      }
    case 'export-cli':
      return {
        icon: Terminal,
        label: t('workflowHistory.types.exportCli', 'Export CLI'),
        className: 'bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300',
      }
    default:
      return {
        icon: Activity,
        label: type,
        className: 'bg-muted text-muted-foreground',
      }
  }
}

function statusMeta(status: HistoryStatus, t: TFunction) {
  switch (status) {
    case 'completed':
      return {
        label: t('workflowHistory.status.completed', 'Completed'),
        icon: CheckCircle2,
        badge: 'success' as const,
      }
    case 'failed':
      return {
        label: t('workflowHistory.status.failed', 'Failed'),
        icon: AlertTriangle,
        badge: 'destructive' as const,
      }
    case 'running':
      return {
        label: t('workflowHistory.status.running', 'Running'),
        icon: Loader2,
        badge: 'default' as const,
      }
    case 'cancelled':
      return {
        label: t('workflowHistory.status.cancelled', 'Cancelled'),
        icon: AlertTriangle,
        badge: 'outline' as const,
      }
    case 'interrupted':
      return {
        label: t('workflowHistory.status.interrupted', 'Interrupted'),
        icon: AlertTriangle,
        badge: 'outline' as const,
      }
    default:
      return {
        label: status || t('workflowHistory.status.unknown', 'Unknown'),
        icon: Clock3,
        badge: 'secondary' as const,
      }
  }
}

function metricNumber(metrics: Record<string, unknown>, key: string): number | null {
  const value = metrics[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function resultMetrics(entry: JobHistoryEntry): Record<string, unknown> | null {
  if (!isRecord(entry.result)) {
    return null
  }

  const metrics = entry.result.metrics
  return isRecord(metrics) ? metrics : null
}

function safeJsonStringify(value: unknown): string | null {
  if (value == null) {
    return null
  }

  try {
    const json = JSON.stringify(value, null, 2)
    return json.length > RAW_RESULT_MAX_LENGTH
      ? `${json.slice(0, RAW_RESULT_MAX_LENGTH)}\n…`
      : json
  } catch {
    return null
  }
}

function formatMetricValue(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2)
  }

  if (typeof value === 'string') {
    return value
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }

  if (Array.isArray(value)) {
    return value.length.toLocaleString()
  }

  return '-'
}

function humanizeMetricKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function metricEntries(entry: JobHistoryEntry): Array<[string, unknown]> {
  const metrics = resultMetrics(entry)

  if (!metrics) {
    return []
  }

  return Object.entries(metrics).filter(([, value]) => {
    if (value == null) {
      return false
    }

    if (Array.isArray(value)) {
      return value.length > 0
    }

    return typeof value !== 'object'
  })
}

function generatedPaths(entry: JobHistoryEntry): string[] {
  const paths = new Set<string>()
  const metrics = resultMetrics(entry)

  if (metrics) {
    const generatedFiles = metrics.generated_files
    if (Array.isArray(generatedFiles)) {
      generatedFiles.forEach((path) => {
        if (typeof path === 'string' && path) {
          paths.add(path)
        }
      })
    }

    const staticSitePath = metrics.static_site_path
    if (typeof staticSitePath === 'string' && staticSitePath) {
      paths.add(staticSitePath)
    }
  }

  if (isRecord(entry.result)) {
    const resultPaths = entry.result.generated_paths
    if (Array.isArray(resultPaths)) {
      resultPaths.forEach((path) => {
        if (typeof path === 'string' && path) {
          paths.add(path)
        }
      })
    }
  }

  return Array.from(paths)
}

function resultSummary(entry: JobHistoryEntry, t: TFunction): string | null {
  if (entry.error) {
    return entry.error
  }

  const metrics = resultMetrics(entry)

  if (metrics && entry.type === 'transform') {
    const completed = metricNumber(metrics, 'completed_transformations')
    const failed = metricNumber(metrics, 'failed_transformations')
    const total = metricNumber(metrics, 'total_transformations')

    if (total != null) {
      return t(
        'workflowHistory.result.transform',
        '{{completed}}/{{total}} widgets calculated, {{failed}} failed',
        {
          completed: completed ?? 0,
          total,
          failed: failed ?? 0,
        },
      )
    }
  }

  if (metrics && entry.type === 'export') {
    const completed = metricNumber(metrics, 'completed_exports')
    const total = metricNumber(metrics, 'total_exports')
    const pages = metricNumber(metrics, 'generated_pages')

    if (total != null) {
      return t(
        'workflowHistory.result.export',
        '{{completed}}/{{total}} exports, {{pages}} pages',
        {
          completed: completed ?? 0,
          total,
          pages: pages ?? 0,
        },
      )
    }
  }

  return entry.message ?? null
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-background/70 p-3">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium">{value}</dd>
    </div>
  )
}

function DetailSection({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
      {children}
    </section>
  )
}

function WorkflowHistoryDetailsSheet({
  entry,
  onClose,
}: {
  entry: JobHistoryEntry | null
  onClose: () => void
}) {
  const { t } = useTranslation('tools')

  if (!entry) {
    return null
  }

  const meta = typeMeta(entry.type, t)
  const Icon = meta.icon
  const status = statusMeta(entry.status, t)
  const StatusIcon = status.icon
  const completedAt = entry.completed_at ?? entry.updated_at
  const duration = formatDuration(durationSeconds(entry.started_at, completedAt), t)
  const summary = resultSummary(entry, t)
  const metrics = metricEntries(entry)
  const paths = generatedPaths(entry)
  const rawResult = safeJsonStringify(entry.result)

  return (
    <Sheet open={entry !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-[min(760px,92vw)] sm:max-w-[760px]">
        <SheetHeader className="border-b px-6 py-5">
          <div className="flex items-start gap-3 pr-8">
            <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-lg', meta.className)}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <SheetTitle className="truncate">
                {t('workflowHistory.details.title', 'Workflow action details')}
              </SheetTitle>
              <SheetDescription>
                {meta.label} · {jobTarget(entry.group_by, entry.group_bys, t)}
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-96px)] px-6 pb-6">
          <div className="space-y-5 pt-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={status.badge} className="gap-1.5">
                <StatusIcon className="h-3 w-3" />
                {status.label}
              </Badge>
              <Badge variant="outline" className="font-mono text-[11px]">
                {entry.id}
              </Badge>
            </div>

            <dl className="grid gap-3 sm:grid-cols-2">
              <DetailField
                label={t('workflowHistory.details.target', 'Target')}
                value={jobTarget(entry.group_by, entry.group_bys, t)}
              />
              <DetailField
                label={t('workflowHistory.details.duration', 'Duration')}
                value={duration}
              />
              <DetailField
                label={t('workflowHistory.details.startedAt', 'Started')}
                value={formatDateTime(entry.started_at)}
              />
              <DetailField
                label={t('workflowHistory.details.completedAt', 'Completed')}
                value={formatDateTime(completedAt)}
              />
            </dl>

            {summary && (
              <DetailSection title={t('workflowHistory.details.summary', 'Summary')}>
                <p
                  className={cn(
                    'rounded-lg border p-3 text-sm',
                    entry.status === 'failed'
                      ? 'border-destructive/20 bg-destructive/5 text-destructive'
                      : 'bg-muted/40 text-muted-foreground',
                  )}
                >
                  {summary}
                </p>
              </DetailSection>
            )}

            {entry.message && entry.message !== summary && (
              <DetailSection title={t('workflowHistory.details.message', 'Message')}>
                <p className="rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
                  {entry.message}
                </p>
              </DetailSection>
            )}

            {metrics.length > 0 && (
              <DetailSection title={t('workflowHistory.details.metrics', 'Metrics')}>
                <dl className="grid gap-2 sm:grid-cols-2">
                  {metrics.map(([key, value]) => (
                    <DetailField
                      key={key}
                      label={humanizeMetricKey(key)}
                      value={formatMetricValue(value)}
                    />
                  ))}
                </dl>
              </DetailSection>
            )}

            {paths.length > 0 && (
              <DetailSection title={t('workflowHistory.details.files', 'Generated files')}>
                <div className="space-y-2">
                  {paths.map((path) => (
                    <div
                      key={path}
                      className="rounded-md border bg-muted/30 px-3 py-2 font-mono text-xs text-muted-foreground"
                    >
                      {path}
                    </div>
                  ))}
                </div>
              </DetailSection>
            )}

            {rawResult && (
              <DetailSection title={t('workflowHistory.details.rawResult', 'Raw result')}>
                <pre className="max-h-[360px] overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-xs text-slate-50">
                  {rawResult}
                </pre>
              </DetailSection>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}

function buildStats(history: JobHistoryEntry[] | undefined): HistoryStats {
  const entries = history ?? []

  return {
    total: entries.length,
    completed: entries.filter((entry) => entry.status === 'completed').length,
    failed: entries.filter((entry) => entry.status === 'failed').length,
    interrupted: entries.filter(
      (entry) => entry.status === 'interrupted' || entry.status === 'cancelled',
    ).length,
  }
}

function RunningJobCard({ job }: { job: RunningJob }) {
  const { t, i18n } = useTranslation('tools')
  const locale = i18n.language === 'fr' ? fr : enUS
  const meta = typeMeta(job.type, t)
  const Icon = meta.icon
  const elapsed = runningDurationSeconds(job.started_at)

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className={cn('flex h-9 w-9 items-center justify-center rounded-lg', meta.className)}>
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-base">
                {t('workflowHistory.runningTitle', 'Action running')}
              </CardTitle>
              <CardDescription>
                {meta.label} · {jobTarget(job.group_by, job.group_bys, t)} ·{' '}
                {formatRelativeDate(job.started_at, locale)}
              </CardDescription>
            </div>
          </div>
          <Badge>
            <Loader2 className="h-3 w-3 animate-spin" />
            {t('workflowHistory.status.running', 'Running')}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Progress value={job.progress} />
        <div className="flex flex-col gap-1 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>{job.message || t('workflowHistory.noMessage', 'No message')}</span>
          <span>
            {job.progress}% · {formatDuration(elapsed, t)}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

export function WorkflowHistory() {
  const { t, i18n } = useTranslation('tools')
  const [selectedEntry, setSelectedEntry] = useState<JobHistoryEntry | null>(null)
  const locale = i18n.language === 'fr' ? fr : enUS
  const {
    data: history,
    error,
    isFetching,
    isLoading,
    refetch,
  } = usePipelineHistory(HISTORY_LIMIT)
  const { data: pipelineStatus } = usePipelineStatus()
  const stats = useMemo(() => buildStats(history), [history])
  const runningJob = pipelineStatus?.running_job ?? null
  const entries = history ?? []
  const latestEntry = entries[0]
  const latestLabel = latestEntry
    ? formatRelativeDate(latestEntry.completed_at ?? latestEntry.updated_at, locale)
    : t('workflowHistory.never', 'Never')

  return (
    <div className="h-full overflow-auto">
      <div className="space-y-4 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              {t('workflowHistory.title', 'Workflow history')}
            </h1>
            <p className="text-muted-foreground">
              {t(
                'workflowHistory.description',
                'Inspect recent import, transform and export actions for this project.',
              )}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={cn('mr-2 h-4 w-4', isFetching && 'animate-spin')} />
            {t('workflowHistory.refresh', 'Refresh')}
          </Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t('workflowHistory.stats.total', 'Recent actions')}</CardDescription>
              <CardTitle className="text-2xl">{stats.total}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t('workflowHistory.stats.completed', 'Completed')}</CardDescription>
              <CardTitle className="text-2xl">{stats.completed}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t('workflowHistory.stats.failed', 'Failed')}</CardDescription>
              <CardTitle className="text-2xl">{stats.failed}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t('workflowHistory.stats.latest', 'Latest action')}</CardDescription>
              <CardTitle className="truncate text-base">{latestLabel}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        {runningJob && <RunningJobCard job={runningJob} />}

        <Card>
          <CardHeader>
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <FileClock className="h-4 w-4" />
              </div>
              <div>
                <CardTitle>{t('workflowHistory.tableTitle', 'Recent workflow actions')}</CardTitle>
                <CardDescription>
                  {t(
                    'workflowHistory.tableDescription',
                    'The last {{count}} completed actions stored by the local project.',
                    { count: HISTORY_LIMIT },
                  )}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
                {t('workflowHistory.loadError', 'Failed to load workflow history')}
                {error instanceof Error ? `: ${error.message}` : null}
              </div>
            ) : entries.length === 0 ? (
              <div className="rounded-lg border border-dashed p-8 text-center">
                <Clock3 className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
                <p className="font-medium">{t('workflowHistory.emptyTitle', 'No workflow action yet')}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {t(
                    'workflowHistory.emptyDescription',
                    'Run a transform or export job to populate this local history.',
                  )}
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('workflowHistory.columns.date', 'Date')}</TableHead>
                    <TableHead>{t('workflowHistory.columns.action', 'Action')}</TableHead>
                    <TableHead>{t('workflowHistory.columns.status', 'Status')}</TableHead>
                    <TableHead>{t('workflowHistory.columns.duration', 'Duration')}</TableHead>
                    <TableHead>{t('workflowHistory.columns.result', 'Result')}</TableHead>
                    <TableHead className="w-[92px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((entry) => {
                    const meta = typeMeta(entry.type, t)
                    const Icon = meta.icon
                    const status = statusMeta(entry.status, t)
                    const StatusIcon = status.icon
                    const completedAt = entry.completed_at ?? entry.updated_at
                    const summary = resultSummary(entry, t)

                    return (
                      <TableRow
                        key={entry.id}
                        role="button"
                        tabIndex={0}
                        className="cursor-pointer"
                        onClick={() => setSelectedEntry(entry)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            setSelectedEntry(entry)
                          }
                        }}
                      >
                        <TableCell className="min-w-[160px]">
                          <div className="flex flex-col">
                            <span>{formatRelativeDate(completedAt, locale)}</span>
                            <span className="text-xs text-muted-foreground">
                              {formatDateTime(completedAt)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="min-w-[210px]">
                          <div className="flex items-center gap-2">
                            <div className={cn('flex h-7 w-7 shrink-0 items-center justify-center rounded-md', meta.className)}>
                              <Icon className="h-3.5 w-3.5" />
                            </div>
                            <div className="min-w-0">
                              <p className="truncate font-medium">{meta.label}</p>
                              <p className="truncate text-xs text-muted-foreground">
                                {jobTarget(entry.group_by, entry.group_bys, t)}
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={status.badge} className="gap-1.5">
                            <StatusIcon
                              className={cn(
                                'h-3 w-3',
                                entry.status === 'running' && 'animate-spin',
                              )}
                            />
                            {status.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {formatDuration(
                            durationSeconds(entry.started_at, completedAt),
                            t,
                          )}
                        </TableCell>
                        <TableCell className="max-w-[360px]">
                          {summary ? (
                            <span
                              className={cn(
                                'block truncate text-sm',
                                entry.status === 'failed'
                                  ? 'text-destructive'
                                  : 'text-muted-foreground',
                              )}
                              title={summary}
                            >
                              {summary}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 gap-1.5 px-2 text-xs"
                            onClick={(event) => {
                              event.stopPropagation()
                              setSelectedEntry(entry)
                            }}
                          >
                            <Eye className="h-3.5 w-3.5" />
                            {t('workflowHistory.details.open', 'Details')}
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
        <WorkflowHistoryDetailsSheet
          entry={selectedEntry}
          onClose={() => setSelectedEntry(null)}
        />
      </div>
    </div>
  )
}
