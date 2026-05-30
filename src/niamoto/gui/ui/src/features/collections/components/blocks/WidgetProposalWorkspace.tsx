import { useMemo, useRef, useState } from 'react'
import { Loader2, RefreshCw, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type {
  WidgetProposal,
  WidgetProposalApplyResponse,
  WidgetProposalPreviewResponse,
  WidgetProposalSelection,
} from '@/features/collections/api/widget-proposals'
import { useWidgetProposals } from '@/features/collections/hooks/useWidgetProposals'
import { WidgetProposalApplyDialog } from './WidgetProposalApplyDialog'
import { WidgetProposalDetail } from './WidgetProposalDetail'
import { WidgetProposalList } from './WidgetProposalList'
import { WidgetProposalPagePreview } from './WidgetProposalPagePreview'

interface WidgetProposalWorkspaceProps {
  collectionName: string
  onClose: () => void
  onApplied: () => void | Promise<void>
}

export function WidgetProposalWorkspace({
  collectionName,
  onClose,
  onApplied,
}: WidgetProposalWorkspaceProps) {
  const query = useWidgetProposals(collectionName)
  const [selectedIdOverride, setSelectedIdOverride] = useState<string | null>(null)
  const [selectedProposalIdsState, setSelectedProposalIdsState] = useState<{
    key: string
    ids: Set<string>
  } | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [preview, setPreview] = useState<WidgetProposalPreviewResponse | null>(null)
  const [previewSelections, setPreviewSelections] = useState<WidgetProposalSelection[]>([])
  const [applyResult, setApplyResult] = useState<WidgetProposalApplyResponse | null>(null)
  const [applyInFlight, setApplyInFlight] = useState(false)
  const previewRequestId = useRef(0)

  const groups = useMemo(() => {
    const data = query.data
    if (!data) return []
    return [
      { id: 'recommended', label: 'Recommended', proposals: data.recommended },
      { id: 'warnings', label: 'Needs review', proposals: data.warnings },
      { id: 'review_only', label: 'Review only', proposals: data.review_only },
      { id: 'missing_chart', label: 'Missing chart', proposals: data.missing_chart },
      { id: 'skipped', label: 'Skipped', proposals: data.skipped },
      { id: 'configured', label: 'Already configured', proposals: data.already_configured },
    ].filter((group) => group.proposals.length > 0)
  }, [query.data])

  const allProposals = useMemo(
    () => groups.flatMap((group) => group.proposals),
    [groups],
  )

  const proposalKey = useMemo(
    () => allProposals.map((proposal) => proposal.id).join('|'),
    [allProposals],
  )

  const defaultSelectedProposalIds = useMemo(() => {
    if (!query.data) return new Set<string>()
    return new Set(
      query.data.recommended
        .filter((proposal) => proposal.applyability === 'applicable')
        .map((proposal) => proposal.id),
    )
  }, [query.data])

  const selectedProposalIds =
    selectedProposalIdsState?.key === proposalKey
      ? selectedProposalIdsState.ids
      : defaultSelectedProposalIds

  const selectedId =
    selectedIdOverride &&
    allProposals.some((proposal) => proposal.id === selectedIdOverride)
      ? selectedIdOverride
      : allProposals[0]?.id ?? null

  const selectedProposal = allProposals.find((proposal) => proposal.id === selectedId) ?? null
  const selectedApplicableCount = allProposals.filter(
    (proposal) =>
      selectedProposalIds.has(proposal.id) && proposal.applyability === 'applicable',
  ).length

  const toggleProposal = (proposalId: string) => {
    const proposal = allProposals.find((item) => item.id === proposalId)
    if (!proposal || proposal.applyability !== 'applicable') {
      return
    }
    const next = new Set(selectedProposalIds)
    if (next.has(proposalId)) {
      next.delete(proposalId)
    } else {
      next.add(proposalId)
    }
    setSelectedProposalIdsState({ key: proposalKey, ids: next })
  }

  const selections = (): WidgetProposalSelection[] =>
    [...selectedProposalIds].map((proposalId) => ({ proposal_id: proposalId }))

  const openPreview = async () => {
    const nextSelections = selections()
    const requestId = previewRequestId.current + 1
    previewRequestId.current = requestId
    setApplyResult(null)
    setApplyInFlight(false)
    setPreview(null)
    setPreviewSelections(nextSelections)
    setDialogOpen(true)
    const response = await query.preview(nextSelections)
    if (previewRequestId.current === requestId) {
      setPreview(response)
    }
  }

  const applySelected = async () => {
    if (!preview || applyInFlight) return
    setApplyResult(null)
    setApplyInFlight(true)
    try {
      const response = await query.apply({
        selections: previewSelections,
        previewToken: preview.preview_token,
      })
      setApplyResult(response)
      if (response.success) {
        await onApplied()
        setDialogOpen(false)
        setPreview(null)
        setPreviewSelections([])
      }
    } finally {
      setApplyInFlight(false)
    }
  }

  if (query.isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Loading proposals
      </div>
    )
  }

  if (query.error || !query.data) {
    return (
      <div className="m-4 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        {query.error instanceof Error ? query.error.message : 'Proposal analysis failed'}
      </div>
    )
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-1 overflow-hidden lg:grid-cols-[320px_minmax(0,1fr)]">
      <WidgetProposalList
        groups={groups}
        selectedId={selectedId}
        selectedProposalIds={selectedProposalIds}
        onSelectProposal={setSelectedIdOverride}
        onToggleProposal={toggleProposal}
      />
      <main className="flex min-h-0 flex-col">
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b px-4 py-2">
          <div>
            <h1 className="text-base font-semibold">Review proposed page</h1>
            <p className="text-sm text-muted-foreground">
              {selectedApplicableCount} selected widget{selectedApplicableCount === 1 ? '' : 's'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => query.refetch()}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
            <Button
              size="sm"
              disabled={selectedApplicableCount === 0 || query.previewState.isPending}
              onClick={openPreview}
            >
              Review and add
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </header>
        <div className="grid min-h-0 flex-1 grid-cols-1 min-[2200px]:grid-cols-[minmax(0,1fr)_360px]">
          <WidgetProposalPagePreview
            proposals={allProposals}
            selectedId={selectedId}
            selectedProposalIds={selectedProposalIds}
            onSelectProposal={setSelectedIdOverride}
            onToggleProposal={toggleProposal}
          />
          <WidgetProposalDetail proposal={selectedProposal as WidgetProposal | null} />
        </div>
      </main>
      <WidgetProposalApplyDialog
        open={dialogOpen}
        preview={preview}
        loading={query.previewState.isPending}
        applying={applyInFlight || query.applyState.isPending}
        result={applyResult}
        error={
          (query.previewState.error as Error | null) ??
          (query.applyState.error as Error | null)
        }
        onOpenChange={(open) => {
          if (applyInFlight && !open) return
          setDialogOpen(open)
        }}
        onApply={applySelected}
      />
    </div>
  )
}
