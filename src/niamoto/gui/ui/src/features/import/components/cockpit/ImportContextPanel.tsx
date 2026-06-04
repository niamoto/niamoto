import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CheckCircle2, FileQuestion, HelpCircle, Info, Loader2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { importInventoryStatuses, type ImportInventoryItem, type ImportInventoryStatus } from './importInventory'

interface ImportContextPanelProps {
  item?: ImportInventoryItem | null
  phase: string
  stage?: string | null
  guidance?: ReactNode
  action?: ReactNode
}

function statusIcon(status: ImportInventoryStatus) {
  switch (status) {
    case 'ready':
    case 'analysed':
    case 'imported':
      return <CheckCircle2 className="h-4 w-4 text-emerald-600" />
    case 'needs_attention':
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-amber-600" />
    case 'checking':
    case 'uploading':
    case 'importing':
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />
    default:
      return <Info className="h-4 w-4 text-muted-foreground" />
  }
}

function displayMessage(
  message: string | undefined,
  t: (key: string, options?: Record<string, unknown>) => string
) {
  if (message && importInventoryStatuses.includes(message as ImportInventoryStatus)) {
    return t(`cockpit.status.${message}`)
  }
  if (message === 'not_configured') {
    return t('cockpit.messages.not_configured')
  }
  return message
}

function displayDetailValue(
  detail: ImportInventoryItem['details'][number],
  t: (key: string, options?: { defaultValue?: string }) => string
) {
  if (detail.label === 'decision') {
    return t(`cockpit.detailValues.decision.${detail.value}`, {
      defaultValue: detail.value,
    })
  }

  return detail.value
}

export function ImportContextPanel({
  item,
  phase,
  stage,
  guidance,
  action,
}: ImportContextPanelProps) {
  const { t } = useTranslation(['sources'])
  const [panelView, setPanelView] = useState<'details' | 'help'>('details')

  if (!item) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-muted/20 p-3">
        <div className="flex shrink-0 items-start gap-2">
          <FileQuestion className="mt-0.5 h-4 w-4 text-primary" />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold">{t('cockpit.context.emptyTitle')}</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              {stage || t(`cockpit.context.phase.${phase}`)}
            </p>
          </div>
        </div>
        {guidance && <div className="mt-3 min-h-0 min-w-0 flex-1 overflow-y-auto pr-1">{guidance}</div>}
        {action && <div className="mt-3 shrink-0">{action}</div>}
      </aside>
    )
  }

  const hasDetails = item.details.length > 0
  const hasChecks = item.badges.length > 0 || item.tips.length > 0
  const showHelp = panelView === 'help' && guidance

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-muted/20 p-3">
      {guidance && (
        <div className="grid shrink-0 grid-cols-2 rounded-full border bg-background/70 p-0.5 text-xs">
          <button
            type="button"
            className={cn(
              'rounded-full px-2 py-1.5 font-medium text-muted-foreground transition-colors hover:text-foreground',
              panelView === 'details' && 'bg-foreground text-background shadow-sm hover:text-background'
            )}
            onClick={() => setPanelView('details')}
          >
            {t('cockpit.context.details')}
          </button>
          <button
            type="button"
            className={cn(
              'flex items-center justify-center gap-1.5 rounded-full px-2 py-1.5 font-medium text-muted-foreground transition-colors hover:text-foreground',
              panelView === 'help' && 'bg-foreground text-background shadow-sm hover:text-background'
            )}
            onClick={() => setPanelView('help')}
          >
            <HelpCircle className="h-3.5 w-3.5" />
            {t('cockpit.context.helpTitle')}
          </button>
        </div>
      )}

      {showHelp ? (
        <div className="mt-3 min-h-0 min-w-0 flex-1 overflow-y-auto rounded-md border bg-background/60 p-2">
          {guidance}
        </div>
      ) : (
        <div className="mt-3 min-h-0 min-w-0 flex-1 space-y-3 overflow-y-auto pr-1">
          <div className="flex items-start gap-2">
            {statusIcon(item.status)}
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">{item.name}</div>
              <p className="mt-1 text-xs text-muted-foreground">
                {displayMessage(item.primaryMessage, t) || t(`cockpit.context.phase.${phase}`)}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5">
            <Badge variant="outline" className="text-[10px]">
              {t(`cockpit.roles.${item.role}`)}
            </Badge>
            <Badge variant="outline" className="text-[10px]">
              {t(`cockpit.status.${item.status}`)}
            </Badge>
          </div>

          {hasDetails && (
            <>
              <Separator />
              <div className="space-y-2">
                <div className="text-xs font-medium uppercase text-muted-foreground">
                  {t('cockpit.context.details')}
                </div>
                <div className="space-y-1.5">
                  {item.details.slice(0, 8).map((detail, detailIndex) => (
                    <div key={`${detail.label}:${detail.value}:${detailIndex}`} className="rounded-md bg-background/70 px-2 py-1.5">
                      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                        {t(`cockpit.detailLabels.${detail.label}`, { defaultValue: detail.label })}
                      </div>
                      <div
                        className={cn(
                          'mt-0.5 break-words text-xs',
                          detail.tone === 'review' && 'text-amber-700 dark:text-amber-300',
                          detail.tone === 'error' && 'text-red-700 dark:text-red-300'
                        )}
                      >
                        {displayDetailValue(detail, t)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {hasChecks && (
            <>
              <Separator />
              <div className="space-y-2">
                <div className="text-xs font-medium uppercase text-muted-foreground">
                  {t('cockpit.context.checks')}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {item.badges.map((badge) => (
                    <Badge key={badge} variant="secondary" className="text-[10px]">
                      {t(`upload.preflight.badges.${badge}`, { defaultValue: badge })}
                    </Badge>
                  ))}
                  {item.tips.map((tip) => (
                    <Badge key={tip} className="border-amber-200 bg-amber-50 text-[10px] text-amber-800" variant="outline">
                      {t(`upload.preflight.tips.${tip}`, { defaultValue: tip })}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}

          {action && (
            <>
              <Separator />
              <div>{action}</div>
            </>
          )}
        </div>
      )}
    </aside>
  )
}
