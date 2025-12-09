/**
 * WidgetOptionCard - Compact widget card for grouped gallery view
 */
import { memo } from 'react'
import { Check, Star } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { WidgetMiniature } from '@/components/widgets'
import type { TemplateSuggestion } from './types'
import { CATEGORY_INFO } from './types'

interface WidgetOptionCardProps {
  suggestion: TemplateSuggestion
  selected: boolean
  isPrimary: boolean
  onSelect: () => void
  onPreview: () => void
}

export const WidgetOptionCard = memo(function WidgetOptionCard({
  suggestion,
  selected,
  isPrimary,
  onSelect,
  onPreview,
}: WidgetOptionCardProps) {
  const categoryInfo = CATEGORY_INFO[suggestion.category]

  // Extract widget type from template_id (e.g., "height_binned_distribution_bar_plot" -> "bar_plot")
  const parts = suggestion.template_id.split('_')
  const widgetType = parts.slice(-2).join('_') // Get last two parts for widget name

  // Humanize widget type for display
  const widgetLabel = widgetType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <div
      className={cn(
        'group relative rounded-lg border transition-all duration-200 overflow-hidden cursor-pointer',
        'hover:shadow-md hover:shadow-black/5 dark:hover:shadow-black/20',
        selected
          ? 'border-success bg-success/10 dark:bg-success/15 ring-1 ring-success/50'
          : 'border-border/60 bg-card hover:border-border',
        isPrimary && !selected && 'border-primary/30 bg-primary/5'
      )}
      onClick={onPreview}
    >
      {/* Primary indicator */}
      {isPrimary && (
        <div className="absolute top-1.5 left-1.5 z-10">
          <div className="flex items-center gap-1 bg-warning/20 text-warning px-1.5 py-0.5 rounded text-[10px] font-medium">
            <Star className="h-2.5 w-2.5 fill-current" />
            Top
          </div>
        </div>
      )}

      {/* Selection checkbox */}
      <button
        onClick={(e) => {
          e.stopPropagation()
          onSelect()
        }}
        className={cn(
          'absolute top-1.5 right-1.5 z-10 h-5 w-5 rounded-full transition-all duration-200',
          'flex items-center justify-center',
          selected
            ? 'bg-emerald-500 text-white scale-100'
            : 'bg-white/90 dark:bg-gray-800/90 border border-border/80 opacity-0 group-hover:opacity-100'
        )}
      >
        <Check className={cn('h-3 w-3', !selected && 'opacity-40')} />
      </button>

      {/* Miniature preview */}
      <div className="p-2">
        <WidgetMiniature
          templateId={suggestion.template_id}
          size="sm"
          className="w-full transition-transform duration-200 group-hover:scale-[1.02]"
          onClick={onPreview}
        />
      </div>

      {/* Widget info */}
      <div className="px-2 pb-2 pt-0">
        <div className="flex items-center justify-between gap-1">
          <span className="text-xs font-medium text-foreground truncate">
            {widgetLabel}
          </span>
          <Badge
            variant="secondary"
            className={cn(
              'text-[10px] px-1.5 py-0 h-4 flex-shrink-0',
              categoryInfo.bgColor,
              categoryInfo.color
            )}
          >
            {categoryInfo.label}
          </Badge>
        </div>
      </div>
    </div>
  )
})
