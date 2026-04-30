import { Info } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { CollectionEvidence } from '@/features/collections/hooks/useCollectionsCatalog'

interface CollectionEvidenceBadgeProps {
  evidence: CollectionEvidence
}

export function CollectionEvidenceBadge({ evidence }: CollectionEvidenceBadgeProps) {
  const { t } = useTranslation(['sources'])
  const confidence = Math.round(evidence.confidence * 100)

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className="gap-1 border-muted-foreground/20 bg-muted/30 text-[10px]"
        >
          <Info className="h-3 w-3" />
          {t(`collections.review.evidence.${evidence.kind}`, evidence.kind)}
          <span className="tabular-nums">{confidence}%</span>
        </Badge>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        {evidence.message}
      </TooltipContent>
    </Tooltip>
  )
}
