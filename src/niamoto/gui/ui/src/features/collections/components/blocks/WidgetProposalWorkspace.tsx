import { useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation(['sources'])
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
  const isRefreshing = query.isFetching && !query.isLoading

  const groups = useMemo(() => {
    const data = query.data
    if (!data) return []
    return [
      { id: 'recommended', label: t('collectionPanel.widgetProposals.groups.recommended'), proposals: data.recommended },
      { id: 'warnings', label: t('collectionPanel.widgetProposals.groups.warnings'), proposals: data.warnings },
      { id: 'review_only', label: t('collectionPanel.widgetProposals.groups.reviewOnly'), proposals: data.review_only },
      { id: 'missing_chart', label: t('collectionPanel.widgetProposals.groups.missingChart'), proposals: data.missing_chart },
      { id: 'skipped', label: t('collectionPanel.widgetProposals.groups.skipped'), proposals: data.skipped },
      { id: 'configured', label: t('collectionPanel.widgetProposals.groups.configured'), proposals: data.already_configured },
    ].filter((group) => group.proposals.length > 0)
  }, [query.data, t])

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
  const selectedProposalIsApplicable = selectedProposal?.applyability === 'applicable'
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

  const refreshProposals = async () => {
    setApplyResult(null)
    setPreview(null)
    setPreviewSelections([])
    await query.refetch()
  }

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
        {t('collectionPanel.widgetProposals.loading')}
      </div>
    )
  }

  if (query.error || !query.data) {
    return (
      <div className="m-4 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        {query.error instanceof Error ? query.error.message : t('collectionPanel.widgetProposals.analysisFailed')}
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
            <h1 className="text-base font-semibold">{t('collectionPanel.widgetProposals.reviewTitle')}</h1>
            <p className="text-sm text-muted-foreground">
              {t('collectionPanel.widgetProposals.selectedWidgets', { count: selectedApplicableCount })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={isRefreshing}
              onClick={() => void refreshProposals()}
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              {isRefreshing
                ? t('collectionPanel.widgetProposals.refreshing')
                : t('collectionPanel.widgetProposals.refresh')}
            </Button>
            <Button
              size="sm"
              disabled={selectedApplicableCount === 0 || query.previewState.isPending}
              onClick={openPreview}
            >
              {t('collectionPanel.widgetProposals.reviewAndAdd')}
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose} aria-label={t('collectionPanel.widgetProposals.close')}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </header>
        <div
          className={`grid min-h-0 flex-1 grid-cols-1 overflow-hidden ${
            selectedProposalIsApplicable
              ? 'grid-rows-[minmax(180px,35%)_minmax(0,1fr)] xl:grid-cols-[minmax(0,1fr)_380px] xl:grid-rows-1'
              : 'grid-rows-1'
          }`}
        >
          {selectedProposalIsApplicable ? (
            <>
              <div className="order-2 min-h-0 overflow-hidden xl:order-1">
                <WidgetProposalPagePreview
                  proposals={allProposals}
                  selectedId={selectedId}
                  selectedProposalIds={selectedProposalIds}
                  onSelectProposal={setSelectedIdOverride}
                  onToggleProposal={toggleProposal}
                />
              </div>
              <div className="order-1 min-h-0 overflow-hidden border-b xl:order-2 xl:border-b-0 xl:border-l">
                <WidgetProposalDetail
                  proposal={selectedProposal as WidgetProposal | null}
                  variant="main"
                />
              </div>
            </>
          ) : (
            <WidgetProposalDetail
              proposal={selectedProposal as WidgetProposal | null}
              variant="main"
            />
          )}
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
