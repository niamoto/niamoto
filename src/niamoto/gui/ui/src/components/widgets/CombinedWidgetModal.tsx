/**
 * CombinedWidgetModal - Modal for selecting and configuring multi-field combined widgets
 *
 * Shows combined widget suggestions based on selected fields and allows
 * the user to select one to add to their configuration.
 */

import { useState, useEffect } from 'react'
import {
  Loader2,
  Combine,
  Check,
  AlertCircle,
  Sparkles,
  Flower2,
  Ruler,
  TrendingUp,
  BarChart3,
  ToggleLeft,
  GitCompareArrows,
  Leaf,
  type LucideIcon,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import {
  useCombinedWidgetSuggestions,
  PATTERN_INFO,
  type CombinedWidgetSuggestion,
  type MultiFieldPatternType,
} from '@/lib/api/widget-suggestions'

// Mapping from icon name to Lucide component
const PATTERN_ICONS: Record<string, LucideIcon> = {
  Flower2,
  Ruler,
  TrendingUp,
  BarChart3,
  ToggleLeft,
  GitCompareArrows,
  Leaf,
}

interface CombinedWidgetModalProps {
  isOpen: boolean
  onClose: () => void
  selectedFields: string[]
  referenceName: string
  sourceName?: string
  onAddWidget: (config: Record<string, unknown>) => void
}

export function CombinedWidgetModal({
  isOpen,
  onClose,
  selectedFields,
  referenceName,
  sourceName = 'occurrences',
  onAddWidget,
}: CombinedWidgetModalProps) {
  const [selectedSuggestion, setSelectedSuggestion] = useState<CombinedWidgetSuggestion | null>(null)

  // React Query auto-fetch quand selectedFields >= 2
  const {
    suggestions,
    loading,
    error,
  } = useCombinedWidgetSuggestions(referenceName, selectedFields, sourceName)

  // Auto-select the recommended suggestion
  useEffect(() => {
    if (suggestions.length > 0 && !selectedSuggestion) {
      const recommended = suggestions.find(s => s.is_recommended)
      setSelectedSuggestion(recommended || suggestions[0])
    }
  }, [suggestions, selectedSuggestion])

  // Reset selection when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedSuggestion(null)
    }
  }, [isOpen])

  const handleAddWidget = useCallback(() => {
    if (selectedSuggestion) {
      // Build the configuration for the widget
      const config = {
        pattern_type: selectedSuggestion.pattern_type,
        name: selectedSuggestion.name,
        fields: selectedSuggestion.fields,
        field_roles: selectedSuggestion.field_roles,
        transformer: selectedSuggestion.transformer_config,
        widget: selectedSuggestion.widget_config,
      }
      onAddWidget(config)
      onClose() // Close modal after adding
    }
  }, [selectedSuggestion, onAddWidget, onClose])

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Combine className="h-5 w-5 text-primary" />
            Widget combine
          </DialogTitle>
          <DialogDescription asChild>
            <div>
              <span>Selectionnez un type de widget combine pour les champs suivants:</span>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {selectedFields.map((field) => (
                  <Badge key={field} variant="secondary" className="font-mono text-xs">
                    {field}
                  </Badge>
                ))}
              </div>
            </div>
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 min-h-[200px]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">
                Analyse des combinaisons possibles...
              </p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                <span>Erreur lors de l'analyse</span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{error}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={fetchSuggestions}
              >
                Reessayer
              </Button>
            </div>
          ) : suggestions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
                <Sparkles className="h-8 w-8 text-muted-foreground/50" />
              </div>
              <h3 className="text-lg font-medium text-muted-foreground">
                Aucune combinaison detectee
              </h3>
              <p className="text-sm text-muted-foreground/70 mt-2 text-center max-w-sm">
                Ces champs ne forment pas un pattern reconnu.
                Essayez de selectionner des champs differents.
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[300px] pr-4">
              <div className="space-y-3">
                {suggestions.map((suggestion, index) => (
                  <SuggestionCard
                    key={`${suggestion.pattern_type}-${index}`}
                    suggestion={suggestion}
                    isSelected={selectedSuggestion === suggestion}
                    onSelect={() => setSelectedSuggestion(suggestion)}
                  />
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button
            onClick={handleAddWidget}
            disabled={!selectedSuggestion || loading}
          >
            <Check className="mr-2 h-4 w-4" />
            Ajouter le widget
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Sub-components
// =============================================================================

interface SuggestionCardProps {
  suggestion: CombinedWidgetSuggestion
  isSelected: boolean
  onSelect: () => void
}

function SuggestionCard({ suggestion, isSelected, onSelect }: SuggestionCardProps) {
  const patternInfo = PATTERN_INFO[suggestion.pattern_type as MultiFieldPatternType] || {
    label: suggestion.pattern_type,
    description: '',
    icon: 'BarChart3',
    color: 'text-gray-600',
  }

  const IconComponent = PATTERN_ICONS[patternInfo.icon] || BarChart3

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left rounded-lg border p-4 transition-all',
        isSelected
          ? 'border-primary bg-primary/5 ring-1 ring-primary'
          : 'border-border hover:border-primary/50 hover:bg-muted/50'
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn('p-2 rounded-lg bg-muted/50', patternInfo.color)}>
          <IconComponent className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className={cn('font-medium', patternInfo.color)}>
              {suggestion.name}
            </h4>
            {suggestion.is_recommended && (
              <Badge className="bg-primary/10 text-primary text-[10px] px-1.5">
                Recommande
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            {suggestion.description}
          </p>

          {/* Field roles */}
          <div className="flex flex-wrap gap-1.5 mt-2">
            {Object.entries(suggestion.field_roles).map(([field, role]) => (
              <Badge
                key={field}
                variant="outline"
                className="text-[10px] font-normal"
              >
                <span className="font-mono">{field}</span>
                <span className="text-muted-foreground mx-1">→</span>
                <span>{role}</span>
              </Badge>
            ))}
          </div>

          {/* Confidence */}
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs text-muted-foreground">
              Confiance: {Math.round(suggestion.confidence * 100)}%
            </span>
            <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full"
                style={{ width: `${suggestion.confidence * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Selection indicator */}
        {isSelected && (
          <div className="flex-shrink-0">
            <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
              <Check className="h-3 w-3 text-primary-foreground" />
            </div>
          </div>
        )}
      </div>
    </button>
  )
}
