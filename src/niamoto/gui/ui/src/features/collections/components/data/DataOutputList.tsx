import { useTranslation } from 'react-i18next'
import { FileBadge2, FileJson } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import type {
  CollectionDataConfiguredOutput,
  CollectionDataOption,
} from '@/features/collections/hooks/useCollectionDataOptions'
import {
  configuredOutputSummary,
  outputStatusLabel,
  suitabilityBadgeVariant,
} from './dataOutputLabels'
import { DataLegacyHintCard } from './DataLegacyHintCard'

interface DataOutputListProps {
  outputs: CollectionDataConfiguredOutput[]
  options: CollectionDataOption[]
  selectedId: string | null
  onSelectOutput: (outputId: string) => void
  onSelectOption: (optionId: string) => void
}

export function DataOutputList({
  outputs,
  options,
  selectedId,
  onSelectOutput,
  onSelectOption,
}: DataOutputListProps) {
  const { t } = useTranslation(['sources'])
  const activeOutputs = outputs.filter(
    (output) => output.kind !== 'legacy_standard_hint',
  )
  const legacyOutputs = outputs.filter(
    (output) => output.kind === 'legacy_standard_hint',
  )

  return (
    <aside className="min-h-0 overflow-auto border-b bg-muted/20 lg:border-b-0 lg:border-r">
      <div className="border-b p-3">
        <h2 className="text-sm font-semibold">
          {t('collectionPanel.data.outputListTitle')}
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">
          {t('collectionPanel.data.outputListDescription')}
        </p>
      </div>

      <div className="space-y-4 p-3">
        {activeOutputs.length > 0 && (
          <section className="space-y-2">
            <p className="px-1 text-xs font-medium text-muted-foreground">
              {t('collectionPanel.data.configuredTitle')}
            </p>
            {activeOutputs.map((output) => (
              <OutputListButton
                key={output.id}
                output={output}
                selected={selectedId === output.id}
                onSelect={() => onSelectOutput(output.id)}
              />
            ))}
          </section>
        )}

        {legacyOutputs.length > 0 && (
          <section className="space-y-2">
            <p className="px-1 text-xs font-medium text-muted-foreground">
              {t('collectionPanel.data.legacyTitle')}
            </p>
            {legacyOutputs.map((output) => (
              <DataLegacyHintCard
                key={output.id}
                output={output}
                selected={selectedId === output.id}
                onSelect={() => onSelectOutput(output.id)}
              />
            ))}
          </section>
        )}

        <section className="space-y-2">
          <p className="px-1 text-xs font-medium text-muted-foreground">
            {t('collectionPanel.data.availableTitle')}
          </p>
          {options.map((option) => (
            <button
              key={option.id}
              type="button"
              className={[
                'w-full rounded-md border bg-background p-3 text-left transition-colors',
                selectedId === `option:${option.id}`
                  ? 'border-primary bg-primary/5 shadow-sm'
                  : 'hover:border-primary/40 hover:bg-muted/40',
              ].join(' ')}
              onClick={() => onSelectOption(option.id)}
            >
              <div className="flex items-start gap-3">
                {option.family === 'standard' ? (
                  <FileBadge2 className="mt-0.5 h-4 w-4 text-muted-foreground" />
                ) : (
                  <FileJson className="mt-0.5 h-4 w-4 text-muted-foreground" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-medium">
                      {option.label}
                    </span>
                    <Badge variant={suitabilityBadgeVariant(option.suitability)}>
                      {t(`collectionPanel.data.suitability.${option.suitability}`)}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {t('collectionPanel.data.confidence', {
                      confidence: Math.round(option.confidence * 100),
                    })}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </section>
      </div>
    </aside>
  )
}

function OutputListButton({
  output,
  selected,
  onSelect,
}: {
  output: CollectionDataConfiguredOutput
  selected: boolean
  onSelect: () => void
}) {
  const { t } = useTranslation(['sources'])
  const Icon = output.family === 'standard' ? FileBadge2 : FileJson

  return (
    <button
      type="button"
      className={[
        'w-full rounded-md border bg-background p-3 text-left transition-colors',
        selected
          ? 'border-primary bg-primary/5 shadow-sm'
          : 'hover:border-primary/40 hover:bg-muted/40',
      ].join(' ')}
      onClick={onSelect}
    >
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-4 w-4 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="truncate text-sm font-medium">{output.label}</span>
            <Badge variant={output.enabled ? 'success' : 'secondary'}>
              {output.enabled
                ? t('collectionPanel.data.enabled')
                : t('collectionPanel.data.disabled')}
            </Badge>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {configuredOutputSummary(output, t)}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            {outputStatusLabel(output, t)}
          </p>
        </div>
      </div>
    </button>
  )
}
