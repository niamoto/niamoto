import { useTranslation } from 'react-i18next'
import { AlertCircle, CheckCircle2, Plus, Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { PreviewTile } from '@/components/preview'
import type { WidgetProposal } from '@/features/collections/api/widget-proposals'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { cn } from '@/lib/utils'
import { hasDesktopBridge } from '@/shared/desktop/bridge'

interface WidgetProposalPagePreviewProps {
  proposals: WidgetProposal[]
  selectedId: string | null
  selectedProposalIds: Set<string>
  onSelectProposal: (proposalId: string) => void
  onToggleProposal: (proposalId: string) => void
}

export function WidgetProposalPagePreview({
  proposals,
  selectedId,
  selectedProposalIds,
  onSelectProposal,
  onToggleProposal,
}: WidgetProposalPagePreviewProps) {
  const { t } = useTranslation(['sources'])
  const applicableProposals = proposals.filter(
    (proposal) => proposal.applyability === 'applicable',
  )
  const selectedProposals = applicableProposals.filter((proposal) =>
    selectedProposalIds.has(proposal.id),
  )
  const unselectedProposals = applicableProposals.filter(
    (proposal) => !selectedProposalIds.has(proposal.id),
  )

  return (
    <section className="h-full min-h-0 overflow-auto overflow-x-hidden bg-muted/10 p-4">
      <div className="mx-auto max-w-6xl min-w-0 space-y-4">
        <div>
          <h2 className="text-base font-semibold">{t('collectionPanel.widgetProposals.preview.title')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('collectionPanel.widgetProposals.preview.description')}
          </p>
        </div>

        {selectedProposals.length === 0 ? (
          <div className="flex min-h-60 items-center justify-center rounded-md border border-dashed bg-background/80 p-8 text-center text-sm text-muted-foreground">
            {t('collectionPanel.widgetProposals.preview.empty')}
          </div>
        ) : (
          <div className="grid min-w-0 grid-cols-1 gap-3 min-[1800px]:grid-cols-2">
            {selectedProposals.map((proposal) => (
              <ProposalPreviewCard
                key={proposal.id}
                proposal={proposal}
                active={selectedId === proposal.id}
                selected
                onSelectProposal={onSelectProposal}
                onToggleProposal={onToggleProposal}
              />
            ))}
          </div>
        )}

        {unselectedProposals.length > 0 && (
          <section className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-medium">{t('collectionPanel.widgetProposals.preview.available')}</h3>
              <Badge variant="outline">{unselectedProposals.length}</Badge>
            </div>
            <div className="grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 min-[1800px]:grid-cols-3">
              {unselectedProposals.map((proposal) => (
                <ProposalPreviewCard
                  key={proposal.id}
                  proposal={proposal}
                  active={selectedId === proposal.id}
                  selected={false}
                  compact
                  onSelectProposal={onSelectProposal}
                  onToggleProposal={onToggleProposal}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </section>
  )
}

interface ProposalPreviewCardProps {
  proposal: WidgetProposal
  active: boolean
  selected: boolean
  compact?: boolean
  onSelectProposal: (proposalId: string) => void
  onToggleProposal: (proposalId: string) => void
}

function ProposalPreviewCard({
  proposal,
  active,
  selected,
  compact = false,
  onSelectProposal,
  onToggleProposal,
}: ProposalPreviewCardProps) {
  const { t } = useTranslation(['sources'])
  const descriptor = buildPreviewDescriptor(proposal)
  const widgetName = proposal.primary_fit?.widget ?? proposal.shape.kind
  const action = selected
    ? t('collectionPanel.widgetProposals.preview.remove')
    : t('collectionPanel.widgetProposals.preview.add')

  return (
    <button
      type="button"
      aria-label={t(
        selected
          ? 'collectionPanel.widgetProposals.preview.removeAria'
          : 'collectionPanel.widgetProposals.preview.addAria',
        { title: proposal.title },
      )}
      className={cn(
        'group grid w-full min-w-0 gap-3 rounded-md border bg-background p-3 text-left shadow-sm transition',
        compact
          ? 'grid-cols-[auto_minmax(0,1fr)]'
          : 'grid-cols-1 lg:grid-cols-[minmax(180px,280px)_minmax(0,1fr)]',
        active && 'border-primary ring-1 ring-primary/30',
        selected ? 'hover:border-primary/70' : 'opacity-75 hover:opacity-100',
      )}
      onClick={() => {
        onSelectProposal(proposal.id)
        onToggleProposal(proposal.id)
      }}
    >
      {compact ? (
        <span
          className={cn(
            'mt-0.5 flex h-6 w-6 items-center justify-center rounded-md border',
            selected
              ? 'border-primary bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground',
          )}
        >
          {selected ? <CheckCircle2 className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
        </span>
      ) : (
        <span className="relative block min-w-0 overflow-hidden rounded-md border bg-muted/30">
          {descriptor ? (
            <PreviewTile
              descriptor={descriptor}
              width={280}
              height={158}
              className="max-w-full"
            />
          ) : (
            <span className="flex h-[158px] items-center justify-center text-xs text-muted-foreground">
              {t('collectionPanel.widgetProposals.preview.unavailable')}
            </span>
          )}
          <span
            className={cn(
              'absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-md border shadow-sm',
              selected
                ? 'border-primary bg-primary text-primary-foreground'
                : 'bg-background text-muted-foreground',
            )}
          >
            {selected ? <CheckCircle2 className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          </span>
        </span>
      )}

      <span className="min-w-0 space-y-2 overflow-hidden">
        <span className="flex min-w-0 items-start justify-between gap-2">
          <span className="min-w-0">
            <span className="flex items-center gap-1.5">
              <StatusIcon proposal={proposal} />
              <span className="truncate text-sm font-medium">{proposal.title}</span>
            </span>
            <span className="mt-1 block text-xs text-muted-foreground">
              {proposal.candidate.intent}
            </span>
          </span>
          <Badge variant={selected ? 'default' : 'outline'} className="shrink-0">
            {selected
              ? t('collectionPanel.widgetProposals.preview.selected')
              : action}
          </Badge>
        </span>

        <span className="flex flex-wrap gap-1.5">
          <Badge variant="secondary">{widgetName}</Badge>
          {proposal.candidate.source_name && (
            <Badge variant="outline">{proposal.candidate.source_name}</Badge>
          )}
        </span>
      </span>
    </button>
  )
}

function buildPreviewDescriptor(proposal: WidgetProposal): PreviewDescriptor | null {
  const recipe = toRecord(proposal.recipe)
  const transformer = toRecord(recipe.transformer)
  const widget = toRecord(recipe.widget)
  const transformerPlugin = toStringValue(transformer.plugin)
  const widgetPlugin = toStringValue(widget.plugin ?? proposal.primary_fit?.widget)

  if (!widgetPlugin) {
    return null
  }

  const base = {
    groupBy: proposal.collection,
    mode: 'thumbnail' as const,
  }

  const templateId = buildTemplateId(proposal, transformerPlugin, widgetPlugin)
  if (templateId) {
    return {
      ...base,
      templateId,
      source: proposal.candidate.source_name && proposal.candidate.source_name !== 'occurrences'
        ? proposal.candidate.source_name
        : undefined,
    }
  }

  if (transformerPlugin && hasDesktopBridge()) {
    return {
      ...base,
      inline: {
        transformer_plugin: transformerPlugin,
        transformer_params: toRecord(transformer.params),
        widget_plugin: widgetPlugin,
        widget_params: toNullableRecord(widget.params),
        widget_title: proposal.title,
      },
    }
  }

  return {
    ...base,
    templateId: proposal.id,
    source: proposal.candidate.source_name && proposal.candidate.source_name !== 'occurrences'
      ? proposal.candidate.source_name
      : undefined,
  }
}

function buildTemplateId(
  proposal: WidgetProposal,
  transformerPlugin: string | undefined,
  widgetPlugin: string,
): string | null {
  if (
    proposal.id.endsWith('_hierarchical_nav_widget') ||
    (proposal.id.startsWith('general_info_') &&
      proposal.id.endsWith('_field_aggregator_info_grid'))
  ) {
    return proposal.id
  }

  if (!transformerPlugin || proposal.candidate.field_names.length !== 1) {
    return null
  }

  return `${proposal.candidate.field_names[0]}_${transformerPlugin}_${widgetPlugin}`
}

function toRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function toNullableRecord(value: unknown): Record<string, unknown> | null {
  if (value == null) return null
  return toRecord(value)
}

function toStringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined
}

function StatusIcon({ proposal }: { proposal: WidgetProposal }) {
  if (proposal.status === 'recommended') {
    return <Sparkles className="h-3.5 w-3.5 text-primary" />
  }
  if (proposal.status === 'warning' || proposal.status === 'review_only') {
    return <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
  }
  return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
}
