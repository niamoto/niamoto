import { useState } from 'react'
import {
  BarChart3,
  LineChart,
  PieChart,
  Trophy,
  ToggleLeft,
  Map,
  Clock,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { TransformerSuggestion, TransformerConfig } from '@/types/suggestions'
import { TRANSFORMER_LABELS } from '@/types/suggestions'

interface SuggestionCardProps {
  suggestion: TransformerSuggestion
  selected: boolean
  onToggle: () => void
}

const TRANSFORMER_ICON_COMPONENTS: Record<string, React.ElementType> = {
  binned_distribution: BarChart3,
  statistical_summary: LineChart,
  categorical_distribution: PieChart,
  top_ranking: Trophy,
  binary_counter: ToggleLeft,
  geospatial_extractor: Map,
  time_series_analysis: Clock,
}

function getConfidenceVariant(confidence: number): 'default' | 'secondary' | 'outline' {
  if (confidence >= 0.8) return 'default'
  if (confidence >= 0.6) return 'secondary'
  return 'outline'
}

function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}

function ConfigPreview({ config }: { config: TransformerConfig }) {
  const { plugin, params } = config

  const formatValue = (value: unknown): string => {
    if (Array.isArray(value)) {
      if (value.length > 5) {
        return `[${value.slice(0, 3).join(', ')}, ... +${value.length - 3}]`
      }
      return `[${value.join(', ')}]`
    }
    if (value === null || value === undefined) {
      return 'auto'
    }
    return String(value)
  }

  return (
    <div className="mt-3 rounded-md bg-muted/50 p-3 font-mono text-xs">
      <div className="text-muted-foreground">plugin: {plugin}</div>
      <div className="text-muted-foreground">params:</div>
      {Object.entries(params).map(([key, value]) => (
        <div key={key} className="ml-4 text-muted-foreground">
          {key}: <span className="text-foreground">{formatValue(value)}</span>
        </div>
      ))}
    </div>
  )
}

export function SuggestionCard({
  suggestion,
  selected,
  onToggle,
}: SuggestionCardProps) {
  const [expanded, setExpanded] = useState(false)
  const Icon = TRANSFORMER_ICON_COMPONENTS[suggestion.transformer] || Sparkles

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:shadow-md',
        selected && 'ring-2 ring-primary'
      )}
      onClick={onToggle}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Checkbox
            checked={selected}
            onClick={(e) => e.stopPropagation()}
            className="mt-1"
          />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Icon className="h-4 w-4 text-primary shrink-0" />
              <span className="font-medium truncate">
                {TRANSFORMER_LABELS[suggestion.transformer] || suggestion.transformer}
              </span>
              <Badge
                variant={getConfidenceVariant(suggestion.confidence)}
                className="ml-auto shrink-0"
              >
                {formatConfidence(suggestion.confidence)}
              </Badge>
            </div>

            <p className="text-sm text-muted-foreground">{suggestion.reason}</p>

            {expanded && <ConfigPreview config={suggestion.config} />}

            <Button
              variant="ghost"
              size="sm"
              className="mt-2 h-6 px-2 text-xs"
              onClick={(e) => {
                e.stopPropagation()
                setExpanded(!expanded)
              }}
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" />
                  Masquer la config
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" />
                  Voir la config
                </>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
