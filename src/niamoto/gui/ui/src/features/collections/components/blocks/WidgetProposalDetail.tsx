import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import type { WidgetProposal } from '@/features/collections/api/widget-proposals'

interface WidgetProposalDetailProps {
  proposal: WidgetProposal | null
  variant?: 'sidebar' | 'main'
}

export function WidgetProposalDetail({
  proposal,
  variant = 'sidebar',
}: WidgetProposalDetailProps) {
  const { t } = useTranslation(['sources'])
  const className =
    variant === 'main'
      ? 'h-full min-h-0 overflow-auto bg-background p-4'
      : 'hidden min-h-0 overflow-auto border-l bg-background p-4 min-[2200px]:block'

  if (!proposal) {
    const emptyClassName =
      variant === 'main'
        ? 'flex h-full items-center justify-center text-sm text-muted-foreground'
        : 'hidden h-full items-center justify-center border-l text-sm text-muted-foreground min-[2200px]:flex'

    return (
      <div className={emptyClassName}>
        {t('collectionPanel.widgetProposals.detail.empty')}
      </div>
    )
  }

  const scoreEntries = Object.entries(proposal.score.dimensions)
  const widgetName = proposal.primary_fit?.widget ?? t('collectionPanel.widgetProposals.detail.missing')
  const chartFit = proposal.primary_fit?.score
  const reviewNotes = [...proposal.warnings, ...proposal.skip_reasons]

  return (
    <article className={className}>
      <header className="mb-4 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold">{t('collectionPanel.widgetProposals.detail.title')}</h2>
          <Badge variant="outline">{t(`collectionPanel.widgetProposals.status.${proposal.status}`)}</Badge>
          <Badge variant="secondary">{t(`collectionPanel.widgetProposals.applyability.${proposal.applyability}`)}</Badge>
        </div>
        <div>
          <p className="text-sm font-medium">{proposal.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {proposal.candidate.intent}
          </p>
        </div>
      </header>

      <section className="mb-4 space-y-3">
        <DetailTile label={t('collectionPanel.widgetProposals.detail.display')} value={widgetName} />
        <DetailTile
          label={t('collectionPanel.widgetProposals.detail.transformation')}
          value={proposal.candidate.transformer_plugin ?? t('collectionPanel.widgetProposals.detail.none')}
        />
        <DetailTile label={t('collectionPanel.widgetProposals.detail.dataShape')} value={proposal.shape.kind} />
      </section>

      {proposal.candidate.field_names.length > 0 && (
        <section className="mb-4">
          <h3 className="mb-2 text-sm font-medium">{t('collectionPanel.widgetProposals.detail.sourceFields')}</h3>
          <div className="flex flex-wrap gap-1.5">
            {proposal.candidate.field_names.map((field) => (
              <Badge key={field} variant="outline">{field}</Badge>
            ))}
          </div>
        </section>
      )}

      <section className="mb-4 rounded-md border bg-muted/20 p-3 text-sm">
        <h3 className="font-medium">{t('collectionPanel.widgetProposals.detail.whySuggested')}</h3>
        <p className="mt-1 text-muted-foreground">
          {proposal.primary_fit?.reason ?? proposal.candidate.intent}
        </p>
        {typeof chartFit === 'number' && (
          <p className="mt-2 text-xs text-muted-foreground">
            {t('collectionPanel.widgetProposals.detail.chartFit', { score: Math.round(chartFit * 100) })}
          </p>
        )}
      </section>

      {reviewNotes.length > 0 && (
        <section className="mb-4 space-y-2">
          <h3 className="text-sm font-medium">{t('collectionPanel.widgetProposals.detail.reviewNotes')}</h3>
          {reviewNotes.map((item) => (
            <div
              key={`${item.code}:${item.message}`}
              className="rounded-md border bg-muted/30 p-3 text-sm"
            >
              <p className="font-medium">{item.code.replace('_', ' ')}</p>
              <p className="mt-1 text-muted-foreground">{item.message}</p>
            </div>
          ))}
        </section>
      )}

      {proposal.missing_chart ? (
        <section className="mb-4 rounded-md border border-sky-300 bg-sky-50 p-3 text-sm text-sky-950">
          <p className="font-medium">{t('collectionPanel.widgetProposals.detail.missingChart')}</p>
          <p className="mt-1">{proposal.missing_chart.reason}</p>
        </section>
      ) : null}

      <details className="rounded-md border bg-muted/10 p-3">
        <summary className="cursor-pointer text-sm font-medium">
          {t('collectionPanel.widgetProposals.detail.technicalDetails')}
        </summary>

        {scoreEntries.length > 0 && (
          <section className="mt-3">
            <h3 className="mb-2 text-sm font-medium">{t('collectionPanel.widgetProposals.detail.internalScore')}</h3>
            <div className="grid gap-2">
              {scoreEntries.map(([name, value]) => (
                <div key={name} className="rounded-md border bg-background p-2">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="truncate text-muted-foreground">{name}</span>
                    <span className="font-medium">{Math.round(value * 100)}%</span>
                  </div>
                  <div className="mt-2 h-1.5 rounded-full bg-muted">
                    <div
                      className="h-1.5 rounded-full bg-primary"
                      style={{ width: `${Math.round(value * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="mt-3">
          <h3 className="mb-2 text-sm font-medium">{t('collectionPanel.widgetProposals.detail.recipe')}</h3>
          <pre className="max-h-72 overflow-auto rounded-md border bg-muted/40 p-3 text-xs">
            {JSON.stringify(proposal.recipe, null, 2)}
          </pre>
        </section>
      </details>
    </article>
  )
}

function DetailTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-medium" title={value}>
        {value}
      </p>
    </div>
  )
}
