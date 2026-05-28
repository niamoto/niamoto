import { AlertCircle, CheckCircle2, EyeOff, Lightbulb, Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import type { WidgetProposal } from '@/features/collections/api/widget-proposals'

interface ProposalGroup {
  id: string
  label: string
  proposals: WidgetProposal[]
}

interface WidgetProposalListProps {
  groups: ProposalGroup[]
  selectedId: string | null
  selectedProposalIds: Set<string>
  onSelectProposal: (proposalId: string) => void
  onToggleProposal: (proposalId: string) => void
}

export function WidgetProposalList({
  groups,
  selectedId,
  selectedProposalIds,
  onSelectProposal,
  onToggleProposal,
}: WidgetProposalListProps) {
  return (
    <aside className="min-h-0 overflow-auto border-r bg-muted/20">
      <div className="space-y-4 p-3">
        {groups.map((group) => (
          <section key={group.id}>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h3 className="text-xs font-medium uppercase text-muted-foreground">
                {group.label}
              </h3>
              <Badge variant="outline">{group.proposals.length}</Badge>
            </div>
            <div className="space-y-1.5">
              {group.proposals.map((proposal) => {
                const selectable = proposal.applyability === 'applicable'
                const active = selectedId === proposal.id
                return (
                  <div
                    key={proposal.id}
                    role="button"
                    tabIndex={0}
                    className={`grid w-full grid-cols-[auto_minmax(0,1fr)] gap-2 rounded-md border p-2 text-left transition-colors ${
                      active ? 'border-primary bg-background' : 'bg-background/70 hover:bg-background'
                    }`}
                    onClick={() => onSelectProposal(proposal.id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        onSelectProposal(proposal.id)
                      }
                    }}
                  >
                    <span
                      className="pt-0.5"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <Checkbox
                        checked={selectedProposalIds.has(proposal.id)}
                        disabled={!selectable}
                        aria-label={proposal.title}
                        onCheckedChange={() => onToggleProposal(proposal.id)}
                      />
                    </span>
                    <span className="min-w-0">
                      <span className="flex items-center gap-1.5">
                        <StatusIcon status={proposal.status} />
                        <span className="truncate text-sm font-medium">
                          {proposal.title}
                        </span>
                      </span>
                      <span className="mt-1 block truncate text-xs text-muted-foreground">
                        {proposal.primary_fit?.widget ?? proposal.shape.kind}
                      </span>
                    </span>
                  </div>
                )
              })}
            </div>
          </section>
        ))}
      </div>
    </aside>
  )
}

function StatusIcon({ status }: { status: WidgetProposal['status'] }) {
  if (status === 'recommended') {
    return <Sparkles className="h-3.5 w-3.5 text-primary" />
  }
  if (status === 'warning' || status === 'review_only') {
    return <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
  }
  if (status === 'missing_chart') {
    return <Lightbulb className="h-3.5 w-3.5 text-sky-600" />
  }
  if (status === 'skipped') {
    return <EyeOff className="h-3.5 w-3.5 text-muted-foreground" />
  }
  return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
}
