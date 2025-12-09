/**
 * FieldGroup - Collapsible group of widget suggestions for a data field
 */
import { memo } from 'react'
import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { WidgetOptionCard } from './WidgetOptionCard'
import type { FieldGroup as FieldGroupType, TemplateSuggestion } from './types'

interface FieldGroupProps {
  group: FieldGroupType
  selectedIds: Set<string>
  onSelect: (templateId: string) => void
  onPreview: (template: TemplateSuggestion) => void
  onSelectBest: () => void
  isExpanded: boolean
  onToggleExpand: () => void
}

export const FieldGroup = memo(function FieldGroup({
  group,
  selectedIds,
  onSelect,
  onPreview,
  onSelectBest,
  isExpanded,
  onToggleExpand,
}: FieldGroupProps) {
  const selectedCount = group.suggestions.filter((s) =>
    selectedIds.has(s.template_id)
  ).length

  return (
    <Collapsible open={isExpanded} onOpenChange={onToggleExpand}>
      <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg bg-muted/50 px-4 py-3 hover:bg-muted transition-colors">
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}

          {/* Field name */}
          <span className="font-medium text-foreground">
            {group.displayName}
          </span>

          {/* Source badge */}
          <Badge
            variant="outline"
            className={cn(
              'text-xs',
              group.source === 'class_object'
                ? 'border-data-source-secondary/50 bg-data-source-secondary/10 text-data-source-secondary'
                : 'border-data-source-primary/50 bg-data-source-primary/10 text-data-source-primary'
            )}
          >
            {group.source === 'class_object' ? 'CSV' : 'Occurrences'}
          </Badge>

          {/* Recommended indicator */}
          {group.hasRecommended && (
            <Sparkles className="h-3.5 w-3.5 text-warning" />
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Selected count */}
          {selectedCount > 0 && (
            <Badge variant="default" className="text-xs bg-emerald-500">
              {selectedCount} / {group.suggestions.length}
            </Badge>
          )}

          {/* Widget count */}
          <span className="text-sm text-muted-foreground">
            {group.suggestions.length} option{group.suggestions.length > 1 ? 's' : ''}
          </span>
        </div>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="pt-3 pl-7 pr-2 pb-2">
          {/* Quick action - Select best */}
          {selectedCount === 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="mb-3 text-xs h-7"
              onClick={(e) => {
                e.stopPropagation()
                onSelectBest()
              }}
            >
              <Sparkles className="h-3 w-3 mr-1" />
              Selectionner le meilleur
            </Button>
          )}

          {/* Widget options grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {group.suggestions.map((suggestion, idx) => (
              <WidgetOptionCard
                key={suggestion.template_id}
                suggestion={suggestion}
                selected={selectedIds.has(suggestion.template_id)}
                isPrimary={idx === 0}
                onSelect={() => onSelect(suggestion.template_id)}
                onPreview={() => onPreview(suggestion)}
              />
            ))}
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
})
