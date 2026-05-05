import { useTranslation } from 'react-i18next'
import { AlertTriangle, ArrowRight, FileBadge2, FileJson } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type {
  CollectionDataAction,
  CollectionDataOption,
  DataOptionsState,
} from '@/features/collections/hooks/useCollectionDataOptions'
import {
  dataActionLabel,
  suitabilityBadgeVariant,
} from './dataOutputLabels'

interface DataRecommendationPanelProps {
  state: DataOptionsState
  options: CollectionDataOption[]
  selectedOptionId: string | null
  primaryAction?: CollectionDataAction | null
  missingEvidence: string[]
  onAction: (action: CollectionDataAction) => void
}

export function DataRecommendationPanel({
  state,
  options,
  selectedOptionId,
  primaryAction,
  missingEvidence,
  onAction,
}: DataRecommendationPanelProps) {
  const { t } = useTranslation(['sources'])
  const selectedOption =
    options.find((option) => `option:${option.id}` === selectedOptionId)
    ?? options.find((option) => optionMatchesAction(option, primaryAction))
    ?? options[0]

  return (
    <section className="space-y-4">
      <div className="rounded-md border bg-background p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-600" />
            <div>
              <h3 className="text-sm font-semibold">
                {state === 'recommended'
                  ? t('collectionPanel.data.recommendationTitle')
                  : t('collectionPanel.data.needsIntentTitle')}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {state === 'recommended'
                  ? t('collectionPanel.data.recommendationDescription')
                  : t('collectionPanel.data.needsIntentDescription')}
              </p>
            </div>
          </div>
          {primaryAction && (
            <Button size="sm" onClick={() => onAction(primaryAction)}>
              <ArrowRight className="h-4 w-4" />
              {dataActionLabel(primaryAction, t)}
            </Button>
          )}
        </div>
      </div>

      {selectedOption && (
        <OptionDetail option={selectedOption} onAction={onAction} />
      )}

      {missingEvidence.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <h3 className="font-medium">
            {t('collectionPanel.data.missingEvidenceTitle')}
          </h3>
          <ul className="mt-2 space-y-1">
            {missingEvidence.map((message) => (
              <li key={message}>- {message}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function optionMatchesAction(
  option: CollectionDataOption,
  action: CollectionDataAction | null | undefined,
) {
  if (!action || option.action?.type !== action.type) {
    return false
  }
  const target = action.target ?? {}
  if (typeof target.standard === 'string' && option.standard !== target.standard) {
    return false
  }
  if (
    typeof target.target_grain === 'string' &&
    option.target_grain !== target.target_grain
  ) {
    return false
  }
  return true
}

function OptionDetail({
  option,
  onAction,
}: {
  option: CollectionDataOption
  onAction: (action: CollectionDataAction) => void
}) {
  const { t } = useTranslation(['sources'])
  const Icon = option.family === 'standard' ? FileBadge2 : FileJson
  const canAct = option.action && option.suitability !== 'not_recommended'

  return (
    <article className="rounded-md border bg-background p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <Icon className="mt-1 h-4 w-4 text-muted-foreground" />
          <div className="min-w-0">
            <h3 className="text-base font-semibold">{option.label}</h3>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge variant={suitabilityBadgeVariant(option.suitability)}>
                {t(`collectionPanel.data.suitability.${option.suitability}`)}
              </Badge>
              <Badge variant="outline">
                {t('collectionPanel.data.confidence', {
                  confidence: Math.round(option.confidence * 100),
                })}
              </Badge>
            </div>
          </div>
        </div>
        {canAct && (
          <Button
            type="button"
            variant={option.suitability === 'recommended' ? 'default' : 'outline'}
            size="sm"
            onClick={() => onAction(option.action as CollectionDataAction)}
          >
            {dataActionLabel(option.action, t)}
          </Button>
        )}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <section className="rounded-md border bg-muted/20 p-3">
          <h4 className="text-sm font-medium">
            {t('collectionPanel.data.reasonTitle')}
          </h4>
          <div className="mt-2 space-y-2 text-sm text-muted-foreground">
            {(option.reasons.length > 0
              ? option.reasons
              : [t('collectionPanel.data.noRecommendationReason')]
            ).map((reason) => (
              <p key={reason}>{reason}</p>
            ))}
          </div>
        </section>

        <section className="rounded-md border bg-muted/20 p-3">
          <h4 className="text-sm font-medium">
            {t('collectionPanel.data.evidenceTitle')}
          </h4>
          <div className="mt-2 space-y-2 text-sm text-muted-foreground">
            {(option.evidence.length > 0
              ? option.evidence.map((evidence) => evidence.message)
              : [t('collectionPanel.data.noEvidence')])
              .map((message) => (
                <p key={message}>{message}</p>
              ))}
          </div>
        </section>
      </div>

      {option.missing_evidence.length > 0 && (
        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {option.missing_evidence.map((message) => (
            <p key={message}>{message}</p>
          ))}
        </div>
      )}
    </article>
  )
}
