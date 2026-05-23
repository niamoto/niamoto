import { Badge } from '@/components/ui/badge'
import type { WidgetProposal } from '@/features/collections/api/widget-proposals'

interface WidgetProposalDetailProps {
  proposal: WidgetProposal | null
}

export function WidgetProposalDetail({ proposal }: WidgetProposalDetailProps) {
  if (!proposal) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Select a proposal
      </div>
    )
  }

  const scoreEntries = Object.entries(proposal.score.dimensions)

  return (
    <article className="min-h-0 overflow-auto p-4">
      <header className="mb-4 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold">{proposal.title}</h2>
          <Badge variant="outline">{proposal.status.replace('_', ' ')}</Badge>
          <Badge variant="secondary">{proposal.applyability.replace('_', ' ')}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          {proposal.candidate.intent}
        </p>
      </header>

      <section className="mb-4 grid gap-3 md:grid-cols-3">
        <DetailTile label="Shape" value={proposal.shape.kind} />
        <DetailTile
          label="Transformer"
          value={proposal.candidate.transformer_plugin ?? 'none'}
        />
        <DetailTile
          label="Widget"
          value={proposal.primary_fit?.widget ?? 'missing'}
        />
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

      {(proposal.warnings.length > 0 || proposal.skip_reasons.length > 0) && (
        <section className="mb-4 space-y-2">
          <h3 className="text-sm font-medium">Review notes</h3>
          {[...proposal.warnings, ...proposal.skip_reasons].map((item) => (
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

      {proposal.missing_chart && (
        <section className="mb-4 rounded-md border border-sky-300 bg-sky-50 p-3 text-sm text-sky-950">
          <p className="font-medium">Missing chart</p>
          <p className="mt-1">{proposal.missing_chart.reason}</p>
        </section>
      )}

      {scoreEntries.length > 0 && (
        <section className="mb-4">
          <h3 className="mb-2 text-sm font-medium">Score</h3>
          <div className="grid gap-2 sm:grid-cols-2">
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

      <section>
        <h3 className="mb-2 text-sm font-medium">Recipe</h3>
        <pre className="max-h-72 overflow-auto rounded-md border bg-muted/40 p-3 text-xs">
          {JSON.stringify(proposal.recipe, null, 2)}
        </pre>
      </section>
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
