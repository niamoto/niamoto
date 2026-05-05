import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Loader2, Settings2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  type CollectionDataAction,
  type CollectionDataOption,
  useCollectionDataOptions,
} from '@/features/collections/hooks/useCollectionDataOptions'
import { buildCollectionTabPath } from '@/features/collections/routing'
import { DataOutputDetail } from './DataOutputDetail'
import { DataOutputList } from './DataOutputList'
import { DataRecommendationPanel } from './DataRecommendationPanel'
import { dataActionLabel, tabForDataAction } from './dataOutputLabels'

interface DataWorkspaceProps {
  collectionName: string
}

export function DataWorkspace({ collectionName }: DataWorkspaceProps) {
  const { t } = useTranslation(['sources', 'common'])
  const navigate = useNavigate()
  const { data, isLoading, error } = useCollectionDataOptions(collectionName)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const defaultSelectedId = useMemo(() => {
    if (!data) {
      return null
    }
    const recommendedOption =
      optionForAction(data.available_options, data.primary_action)
      ?? data.available_options.find(
        (option) =>
          option.suitability === 'recommended' &&
          option.missing_evidence.length === 0,
      )
      ?? data.available_options[0]

    return data.configured_outputs[0]?.id
      ?? (recommendedOption ? `option:${recommendedOption.id}` : null)
  }, [data])

  useEffect(() => {
    if (!data) {
      setSelectedId(null)
      return
    }
    const knownIds = new Set([
      ...data.configured_outputs.map((output) => output.id),
      ...data.available_options.map((option) => `option:${option.id}`),
    ])
    setSelectedId((current) =>
      current && knownIds.has(current) ? current : defaultSelectedId,
    )
  }, [data, defaultSelectedId])

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        {t('common:status.loading')}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="m-4 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        {error instanceof Error ? error.message : t('collectionPanel.data.loadFailed')}
      </div>
    )
  }

  const selectedOutput = data.configured_outputs.find(
    (output) => output.id === selectedId,
  )

  const openAction = (action: CollectionDataAction | null | undefined) => {
    if (!action) {
      return
    }
    const tab = tabForDataAction(action)
    if (!tab) {
      return
    }
    navigate(
      buildCollectionTabPath(
        { type: 'collection', name: collectionName },
        tab,
        searchFromDataAction(action),
      ),
    )
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-1 overflow-hidden lg:grid-cols-[300px_minmax(0,1fr)]">
      <DataOutputList
        outputs={data.configured_outputs}
        options={data.available_options}
        selectedId={selectedId}
        onSelectOutput={setSelectedId}
        onSelectOption={(optionId) => setSelectedId(`option:${optionId}`)}
      />

      <main className="min-h-0 overflow-auto p-4">
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-base font-semibold">
              {t('collectionPanel.data.title')}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('collectionPanel.data.description', {
                collection: data.collection.label || data.collection.name,
              })}
            </p>
          </div>
          {data.primary_action && (
            <Button size="sm" onClick={() => openAction(data.primary_action)}>
              {dataActionLabel(data.primary_action, t)}
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={() => navigate('/groups/api-settings')}
          >
            <Settings2 className="h-4 w-4" />
            {t('collectionPanel.data.advancedDefaults')}
          </Button>
        </header>

        <section className="mb-4 grid gap-3 md:grid-cols-4">
          <SummaryTile
            label={t('collectionPanel.data.collection')}
            value={data.collection.label || data.collection.name}
          />
          <SummaryTile
            label={t('collectionPanel.data.grain')}
            value={data.collection.grain}
          />
          <SummaryTile
            label={t('collectionPanel.data.source')}
            value={`${data.collection.source.type} · ${data.collection.source.name}`}
          />
          <SummaryTile
            label={t('collectionPanel.data.reviewStatus')}
            value={t(
              `collections.review.status.${data.collection.review_status}`,
              data.collection.review_status,
            )}
          />
        </section>

        {selectedOutput ? (
          <DataOutputDetail
            collectionName={collectionName}
            output={selectedOutput}
          />
        ) : (
          <DataRecommendationPanel
            state={data.state}
            options={data.available_options}
            selectedOptionId={selectedId}
            primaryAction={data.primary_action}
            missingEvidence={data.missing_evidence}
            onAction={openAction}
          />
        )}

        {typeof data.sensitivity.message === 'string' && (
          <section className="mt-4 rounded-md border bg-background p-4 text-sm text-muted-foreground">
            {data.sensitivity.message}
          </section>
        )}
      </main>
    </div>
  )
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-medium" title={value}>
        {value}
      </p>
    </div>
  )
}

function optionForAction(
  options: CollectionDataOption[],
  action: CollectionDataAction | null | undefined,
) {
  if (!action) {
    return undefined
  }

  const target = action.target ?? {}
  const standard = typeof target.standard === 'string' ? target.standard : undefined
  const targetGrain =
    typeof target.target_grain === 'string' ? target.target_grain : undefined
  const template = typeof target.template === 'string' ? target.template : undefined

  return options.find((option) => {
    if (option.action?.type !== action.type) {
      return false
    }
    if (standard && option.standard !== standard) {
      return false
    }
    if (targetGrain && option.target_grain !== targetGrain) {
      return false
    }
    if (template && !option.id.includes(template)) {
      return false
    }
    return true
  })
}

function searchFromDataAction(action: CollectionDataAction) {
  const searchParams = new URLSearchParams()
  searchParams.set('data_action', action.type)
  Object.entries(action.target ?? {}).forEach(([key, value]) => {
    if (
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      searchParams.set(key, String(value))
    }
  })
  return searchParams.toString()
}
