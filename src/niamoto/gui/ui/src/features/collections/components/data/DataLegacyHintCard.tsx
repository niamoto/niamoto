import { useTranslation } from 'react-i18next'
import { History } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import type { CollectionDataConfiguredOutput } from '@/features/collections/hooks/useCollectionDataOptions'
import { configuredOutputSummary, standardOutputLabel } from './dataOutputLabels'

interface DataLegacyHintCardProps {
  output: CollectionDataConfiguredOutput
  selected: boolean
  onSelect: () => void
}

export function DataLegacyHintCard({
  output,
  selected,
  onSelect,
}: DataLegacyHintCardProps) {
  const { t } = useTranslation(['sources'])

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
        <History className="mt-0.5 h-4 w-4 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="truncate text-sm font-medium">{output.label}</span>
            <Badge variant="outline">
              {t('collectionPanel.data.legacyBadge')}
            </Badge>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {configuredOutputSummary(output, t)}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            {standardOutputLabel(output, t)}
          </p>
        </div>
      </div>
    </button>
  )
}
