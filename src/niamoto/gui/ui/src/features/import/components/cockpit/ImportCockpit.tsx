import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, Circle, Loader2, Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { ImportContextPanel } from './ImportContextPanel'
import { ImportInventoryList } from './ImportInventoryList'
import {
  summarizeInventory,
  type ImportInventoryItem,
} from './importInventory'

export type ImportCockpitPhase =
  | 'idle'
  | 'uploading'
  | 'configuring'
  | 'reviewing'
  | 'editing'
  | 'importing'
  | 'complete'
  | 'error'

interface ImportCockpitProps {
  phase: ImportCockpitPhase
  items: ImportInventoryItem[]
  selectedItemId?: string | null
  onSelectItem?: (item: ImportInventoryItem) => void
  stage?: string | null
  progress?: number | null
  introGuidance?: ReactNode
  sourceControls?: ReactNode
  detailPanel?: ReactNode
  footer?: ReactNode
  emptyInventory?: ReactNode
}

const workflowSteps: Array<{
  key: 'files' | 'analysis' | 'import'
  phases: ImportCockpitPhase[]
}> = [
  {
    key: 'files',
    phases: ['idle', 'uploading'],
  },
  {
    key: 'analysis',
    phases: ['configuring'],
  },
  {
    key: 'import',
    phases: ['reviewing', 'editing', 'importing', 'complete', 'error'],
  },
]

function stepState(index: number, activeIndex: number, total: number) {
  if (index === activeIndex) return 'active'
  if (total > 0 && index < activeIndex) return 'done'
  return 'idle'
}

function stepIcon(state: 'active' | 'done' | 'idle', running: boolean) {
  if (state === 'active' && running) return <Loader2 className="h-3.5 w-3.5 animate-spin" />
  if (state === 'active') return <Circle className="h-3.5 w-3.5" />
  if (state === 'done') return <CheckCircle2 className="h-3.5 w-3.5" />
  return <Circle className="h-3.5 w-3.5" />
}

export function ImportCockpit({
  phase,
  items,
  selectedItemId,
  onSelectItem,
  stage,
  progress: jobProgress,
  introGuidance,
  sourceControls,
  detailPanel,
  footer,
  emptyInventory,
}: ImportCockpitProps) {
  const { t } = useTranslation(['sources'])
  const summary = summarizeInventory(items)
  const selectedItem = items.find((item) => item.id === selectedItemId) ?? null
  const activeStepIndex = Math.max(
    0,
    workflowSteps.findIndex((step) => step.phases.includes(phase))
  )
  const progressInfo = (() => {
    if (summary.total === 0) return null

    if (phase === 'idle') {
      return {
        showBar: false,
        label: t('cockpit.inventory.readyToUpload', { count: summary.total }),
        progress: 0,
      }
    }

    if (phase === 'uploading') {
      return {
        showBar: false,
        label: t('cockpit.inventory.uploadingFiles', { count: summary.total }),
        progress: 0,
      }
    }

    if (phase === 'configuring') {
      const done = summary.analysed + summary.needs_attention + summary.not_configured + summary.failed
      const progress = Math.round((done / summary.total) * 100)
      return {
        showBar: true,
        label: t('cockpit.inventory.analysisProgress', { progress }),
        progress,
      }
    }

    if (phase === 'reviewing' || phase === 'editing') {
      return {
        showBar: true,
        label: t('cockpit.inventory.analysisComplete', { count: summary.total }),
        progress: 100,
      }
    }

    const progress = typeof jobProgress === 'number'
      ? Math.min(Math.max(Math.round(jobProgress), 0), 100)
      : Math.round(((summary.imported + summary.failed) / summary.total) * 100)
    return {
      showBar: true,
      label: t('cockpit.inventory.importProgress', { progress }),
      progress,
    }
  })()

  return (
    <div className="flex h-[calc(100vh-18rem)] min-h-[360px] min-w-0 flex-col overflow-hidden">
      <div className="grid min-h-0 min-w-0 flex-1 gap-4 overflow-hidden xl:grid-cols-[150px_minmax(0,1fr)_420px] 2xl:grid-cols-[160px_minmax(0,1fr)_460px]">
        <nav className="min-w-0 self-start rounded-lg border bg-muted/20 p-3">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <Sparkles className="h-4 w-4 text-primary" />
            {t('cockpit.workflow.title')}
          </div>
          <ol className="space-y-2">
            {workflowSteps.map((step, index) => {
              const count = summary.total > 0 && index <= activeStepIndex ? summary.total : 0
              const state = stepState(index, activeStepIndex, summary.total)
              const running =
                (phase === 'uploading' && step.key === 'files') ||
                (phase === 'configuring' && step.key === 'analysis') ||
                (phase === 'importing' && step.key === 'import')

              return (
                <li
                  key={step.key}
                  className={cn(
                    'rounded-md border px-2.5 py-2 text-xs transition-colors',
                    state === 'active' && 'border-primary/30 bg-primary/10 text-primary',
                    state === 'done' && 'border-border bg-background text-foreground',
                    state === 'idle' && 'bg-background text-muted-foreground'
                  )}
                >
                  <div className="flex items-center gap-2">
                    {stepIcon(state, running)}
                    <span className="font-medium">{t(`cockpit.workflow.${step.key}`)}</span>
                  </div>
                  <div className="mt-1 pl-5 text-[11px] opacity-80">
                    {t('cockpit.workflow.itemCount', { count })}
                  </div>
                </li>
              )
            })}
          </ol>
        </nav>

        <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border bg-background">
          <div className="shrink-0 p-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold">{t('cockpit.inventory.title')}</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {summary.total > 0
                    ? t('cockpit.inventory.descriptionWithFiles', { count: summary.total })
                    : t('cockpit.inventory.descriptionEmpty')}
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="outline">{t('cockpit.summary.total', { count: summary.total })}</Badge>
                {summary.attention > 0 && (
                  <Badge className="border-amber-200 bg-amber-50 text-amber-800">
                    {t('cockpit.summary.attention', { count: summary.attention })}
                  </Badge>
                )}
                {summary.imported > 0 && (
                  <Badge className="border-emerald-200 bg-emerald-50 text-emerald-800">
                    {t('cockpit.summary.imported', { count: summary.imported })}
                  </Badge>
                )}
              </div>
            </div>
            {progressInfo && (
              <div className="mt-3 space-y-1">
                {progressInfo.showBar && (
                  <Progress value={progressInfo.progress} className="h-1.5" />
                )}
                <div className="text-[11px] text-muted-foreground">
                  {progressInfo.label}
                </div>
              </div>
            )}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain border-t bg-muted/20 p-3">
            <ImportInventoryList
              items={items}
              selectedItemId={selectedItemId}
              onSelectItem={onSelectItem}
              emptyState={emptyInventory}
            />

            {sourceControls}
            {detailPanel && (
              <div className="mt-3">
                {detailPanel}
              </div>
            )}
          </div>

          {footer && (
            <div className="shrink-0 border-t p-3">
              {footer}
            </div>
          )}
        </section>

        <ImportContextPanel
          item={selectedItem}
          phase={phase}
          stage={stage}
          guidance={introGuidance}
        />
      </div>

    </div>
  )
}
