import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Sparkles,
  RefreshCw,
  CheckSquare,
  XSquare,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Database,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { SuggestionCard } from './SuggestionCard'
import {
  useTransformerSuggestions,
  useEntitiesWithSuggestions,
} from '@/hooks/useTransformerSuggestions'
import { DATA_CATEGORY_LABELS } from '@/types/suggestions'
import type { ColumnProfile, TransformerSuggestion, TransformerConfig } from '@/types/suggestions'

interface TransformerSuggestionsProps {
  onApply?: (configs: TransformerConfig[]) => void
}

function ColumnSection({
  column,
  columnSuggestions,
  selections,
  onToggle,
  t,
}: {
  column: ColumnProfile
  columnSuggestions: TransformerSuggestion[]
  selections: { transformerName: string; selected: boolean }[]
  onToggle: (transformerName: string) => void
  t: (key: string, fallback: string) => string
}) {
  const [isOpen, setIsOpen] = useState(true)
  const selectedCount = selections.filter((s) => s.selected).length

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg bg-muted/50 px-4 py-3 hover:bg-muted transition-colors">
        <div className="flex items-center gap-3">
          {isOpen ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          <span className="font-medium">{column.name}</span>
          <Badge variant="outline" className="text-xs">
            {DATA_CATEGORY_LABELS[column.data_category] || column.data_category}
          </Badge>
          {column.cardinality > 0 && (
            <span className="text-xs text-muted-foreground">
              {column.cardinality} {t('suggestions.unique_values', 'valeurs uniques')}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {selectedCount > 0 && (
            <Badge variant="default" className="text-xs">
              {selectedCount} {t('suggestions.selected', 'sélectionné')}{selectedCount > 1 ? 's' : ''}
            </Badge>
          )}
          <span className="text-sm text-muted-foreground">
            {columnSuggestions.length} {t('suggestions.suggestion', 'suggestion')}{columnSuggestions.length > 1 ? 's' : ''}
          </span>
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid gap-3 pt-3 pl-7">
          {columnSuggestions.map((suggestion) => {
            const selection = selections.find(
              (s) => s.transformerName === suggestion.transformer
            )
            return (
              <SuggestionCard
                key={suggestion.transformer}
                suggestion={suggestion}
                selected={selection?.selected ?? false}
                onToggle={() => onToggle(suggestion.transformer)}
              />
            )
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export function TransformerSuggestions({ onApply }: TransformerSuggestionsProps) {
  const { t } = useTranslation()
  const {
    entities,
    loading: loadingEntities,
    error: entitiesError,
    refetch: refetchEntities,
  } = useEntitiesWithSuggestions()

  const [selectedEntity, setSelectedEntity] = useState<string | null>(null)

  const {
    suggestions,
    loading: loadingSuggestions,
    error: suggestionsError,
    selections,
    toggleSelection,
    selectAll,
    deselectAll,
    getSelectedConfigs,
    refetch: refetchSuggestions,
  } = useTransformerSuggestions(selectedEntity)

  const handleApply = () => {
    const configs = getSelectedConfigs()
    if (onApply && configs.length > 0) {
      onApply(configs)
    }
  }

  const selectedCount = selections.filter((s) => s.selected).length
  const totalCount = selections.length

  // Loading state for entities
  if (loadingEntities) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            {t('suggestions.title', 'Suggestions de transformers')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </CardContent>
      </Card>
    )
  }

  // Error state for entities
  if (entitiesError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            {t('suggestions.title', 'Suggestions de transformers')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{entitiesError}</AlertDescription>
          </Alert>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => refetchEntities()}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('common.retry', 'Réessayer')}
          </Button>
        </CardContent>
      </Card>
    )
  }

  // No entities with suggestions
  if (entities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            {t('suggestions.title', 'Suggestions de transformers')}
          </CardTitle>
          <CardDescription>
            {t('suggestions.description', 'Analysez vos données pour obtenir des suggestions automatiques')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Database className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              {t('suggestions.no_entities', 'Aucune entité avec profil sémantique disponible.')}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {t('suggestions.import_hint', 'Importez des données pour générer des suggestions automatiques.')}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              {t('suggestions.title', 'Suggestions de transformers')}
            </CardTitle>
            <CardDescription className="mt-1">
              {t('suggestions.select_entity', 'Sélectionnez une entité pour voir les transformers suggérés')}
            </CardDescription>
          </div>
          {selectedEntity && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchSuggestions()}
              disabled={loadingSuggestions}
            >
              <RefreshCw
                className={`h-4 w-4 mr-2 ${loadingSuggestions ? 'animate-spin' : ''}`}
              />
              {t('common.refresh', 'Actualiser')}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Entity selector */}
        <div className="flex items-center gap-4">
          <Select
            value={selectedEntity ?? ''}
            onValueChange={(value) => setSelectedEntity(value || null)}
          >
            <SelectTrigger className="w-[250px]">
              <SelectValue placeholder={t('suggestions.select_placeholder', 'Sélectionner une entité')} />
            </SelectTrigger>
            <SelectContent>
              {entities.map((entity) => (
                <SelectItem key={entity} value={entity}>
                  {entity}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {selectedEntity && suggestions && (
            <div className="flex items-center gap-2 ml-auto">
              <Button variant="ghost" size="sm" onClick={selectAll}>
                <CheckSquare className="h-4 w-4 mr-1" />
                {t('common.all', 'Tout')}
              </Button>
              <Button variant="ghost" size="sm" onClick={deselectAll}>
                <XSquare className="h-4 w-4 mr-1" />
                {t('common.none', 'Aucun')}
              </Button>
            </div>
          )}
        </div>

        {/* Loading state for suggestions */}
        {loadingSuggestions && (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}

        {/* Error state for suggestions */}
        {suggestionsError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{suggestionsError}</AlertDescription>
          </Alert>
        )}

        {/* Suggestions list */}
        {suggestions && !loadingSuggestions && (
          <>
            <div className="text-sm text-muted-foreground">
              {t('suggestions.analyzed_at', 'Analysé le')}{' '}
              {new Date(suggestions.analyzed_at).toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>

            <div className="space-y-4">
              {suggestions.columns
                .filter((col) => suggestions.suggestions[col.name]?.length > 0)
                .map((column) => (
                  <ColumnSection
                    key={column.name}
                    column={column}
                    columnSuggestions={suggestions.suggestions[column.name]}
                    selections={selections.filter(
                      (s) => s.columnName === column.name
                    )}
                    onToggle={(transformerName) =>
                      toggleSelection(column.name, transformerName)
                    }
                    t={t}
                  />
                ))}
            </div>

            {/* Apply button */}
            {onApply && (
              <div className="flex items-center justify-between pt-4 border-t">
                <span className="text-sm text-muted-foreground">
                  {selectedCount} / {totalCount} {t('suggestions.transformers_selected', 'transformer(s) sélectionné(s)')}
                </span>
                <Button onClick={handleApply} disabled={selectedCount === 0}>
                  {t('suggestions.apply', 'Appliquer les suggestions')}
                </Button>
              </div>
            )}
          </>
        )}

        {/* No entity selected */}
        {!selectedEntity && (
          <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
            <Database className="h-12 w-12 mb-4 opacity-50" />
            <p>{t('suggestions.select_entity_hint', 'Sélectionnez une entité pour voir les suggestions')}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
