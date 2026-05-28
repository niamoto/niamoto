import { Badge } from '@/components/ui/badge'
import type { WidgetProposal } from '@/features/collections/api/widget-proposals'

interface WidgetProposalDetailProps {
  proposal: WidgetProposal | null
}

export function WidgetProposalDetail({ proposal }: WidgetProposalDetailProps) {
  if (!proposal) {
    return (
      <div className="hidden h-full items-center justify-center border-l text-sm text-muted-foreground min-[2200px]:flex">
        Select a proposal to inspect it.
      </div>
    )
  }

  const scoreEntries = Object.entries(proposal.score.dimensions)
  const widgetName = proposal.primary_fit?.widget ?? 'missing'
  const chartFit = proposal.primary_fit?.score
  const reviewNotes = [...proposal.warnings, ...proposal.skip_reasons]

  return (
    <article className="hidden min-h-0 overflow-auto border-l bg-background p-4 min-[2200px]:block">
      <header className="mb-4 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold">Selected widget</h2>
          <Badge variant="outline">{proposal.status.replace('_', ' ')}</Badge>
          <Badge variant="secondary">{proposal.applyability.replace('_', ' ')}</Badge>
        </div>
        <div>
          <p className="text-sm font-medium">{proposal.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {proposal.candidate.intent}
          </p>
        </div>
      </header>

      <section className="mb-4 space-y-3">
        <DetailTile label="Display" value={widgetName} />
        <DetailTile
          label="Transformation"
          value={proposal.candidate.transformer_plugin ?? 'none'}
        />
        <DetailTile label="Data shape" value={proposal.shape.kind} />
      </section>

      {proposal.candidate.field_names.length > 0 && (
        <section className="mb-4">
          <h3 className="mb-2 text-sm font-medium">Source fields</h3>
          <div className="flex flex-wrap gap-1.5">
            {proposal.candidate.field_names.map((field) => (
              <Badge key={field} variant="outline">{field}</Badge>
            ))}
          </div>
        </section>
      )}

      <section className="mb-4 rounded-md border bg-muted/20 p-3 text-sm">
        <h3 className="font-medium">Why suggested</h3>
        <p className="mt-1 text-muted-foreground">
          {proposal.primary_fit?.reason ?? proposal.candidate.intent}
        </p>
        {typeof chartFit === 'number' && (
          <p className="mt-2 text-xs text-muted-foreground">
            Chart fit: {Math.round(chartFit * 100)}%
          </p>
        )}
      </section>

      {reviewNotes.length > 0 && (
        <section className="mb-4 space-y-2">
          <h3 className="text-sm font-medium">Review notes</h3>
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
          <p className="font-medium">Missing chart</p>
          <p className="mt-1">{proposal.missing_chart.reason}</p>
        </section>
      ) : null}

      <details className="rounded-md border bg-muted/10 p-3">
        <summary className="cursor-pointer text-sm font-medium">
          Technical details
        </summary>

        {scoreEntries.length > 0 && (
          <section className="mt-3">
            <h3 className="mb-2 text-sm font-medium">Internal score</h3>
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
          <h3 className="mb-2 text-sm font-medium">Recipe</h3>
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
