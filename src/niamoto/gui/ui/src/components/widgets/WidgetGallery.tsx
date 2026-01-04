/**
 * WidgetGallery - Main gallery component with field grouping
 */
import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import {
  Grid3X3,
  Filter,
  CheckSquare,
  XSquare,
  Sparkles,
  Database,
  FileSpreadsheet,
  ChevronDown,
  ChevronRight,
  Combine,
  X,
  Flower2,
  Ruler,
  TrendingUp,
  BarChart3,
  ToggleLeft,
  GitCompareArrows,
  Leaf,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FieldGroup } from './FieldGroup'
import { CombinedWidgetModal } from './CombinedWidgetModal'
import type { TemplateSuggestion, WidgetCategory } from './types'
import { CATEGORY_INFO, groupSuggestionsByField } from './types'
import {
  useSemanticGroups,
  PATTERN_INFO,
  type SemanticGroup,
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

// Source filter type - 'all' or actual source_name
type SourceFilter = string

interface WidgetGalleryProps {
  suggestions: TemplateSuggestion[]
  selectedIds: Set<string>
  groupBy?: string  // Reference name for correct data filtering
  onSelect: (templateId: string) => void
  onPreview: (template: TemplateSuggestion) => void
  onSelectAll: () => void
  onDeselectAll: () => void
  className?: string
  // Callback when a combined widget configuration is generated
  onAddCombinedWidget?: (config: Record<string, unknown>) => void
}

export function WidgetGallery({
  suggestions,
  selectedIds,
  groupBy,
  onSelect,
  onPreview,
  onSelectAll,
  onDeselectAll,
  className,
  onAddCombinedWidget,
}: WidgetGalleryProps) {
  const [activeCategory, setActiveCategory] = useState<WidgetCategory | 'all'>('all')
  const [activeSource, setActiveSource] = useState<SourceFilter>('all')
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set())
  const [allExpanded, setAllExpanded] = useState(true)

  // Multi-field selection state
  const [fieldSelectionMode, setFieldSelectionMode] = useState(false)
  const [selectedFields, setSelectedFields] = useState<Set<string>>(new Set())
  const [showCombinedModal, setShowCombinedModal] = useState(false)
  const [showSemanticGroups, setShowSemanticGroups] = useState(true)

  // Fetch semantic groups for proactive suggestions
  const { groups: semanticGroups } = useSemanticGroups(groupBy || '', 'occurrences')

  // Get unique categories with counts
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: suggestions.length }
    suggestions.forEach((s) => {
      counts[s.category] = (counts[s.category] || 0) + 1
    })
    return counts
  }, [suggestions])

  // Get unique sources with counts (using source_name)
  const sourcesInfo = useMemo(() => {
    const sources = new Map<string, { count: number; isClassObject: boolean }>()
    suggestions.forEach((s) => {
      const name = s.source_name
      const existing = sources.get(name)
      if (existing) {
        existing.count++
      } else {
        sources.set(name, { count: 1, isClassObject: s.source === 'class_object' })
      }
    })
    return sources
  }, [suggestions])

  // Filter suggestions by category AND source_name
  const filteredSuggestions = useMemo(() => {
    return suggestions.filter((s) => {
      const matchesCategory = activeCategory === 'all' || s.category === activeCategory
      const matchesSource = activeSource === 'all' || s.source_name === activeSource
      return matchesCategory && matchesSource
    })
  }, [suggestions, activeCategory, activeSource])

  // Group by field
  const groupedSuggestions = useMemo(() => {
    return groupSuggestionsByField(filteredSuggestions, selectedIds)
  }, [filteredSuggestions, selectedIds])

  // Track if initial expansion has been done
  const initializedRef = useRef(false)

  // Initialize expanded state for all fields on first render only
  useEffect(() => {
    if (!initializedRef.current && groupedSuggestions.length > 0) {
      setExpandedFields(new Set(groupedSuggestions.map(g => g.field)))
      initializedRef.current = true
    }
  }, [groupedSuggestions])

  // Toggle field expansion
  const toggleFieldExpansion = useCallback((field: string) => {
    setExpandedFields(prev => {
      const next = new Set(prev)
      if (next.has(field)) {
        next.delete(field)
      } else {
        next.add(field)
      }
      return next
    })
  }, [])

  // Expand/collapse all
  const handleToggleAll = useCallback(() => {
    if (allExpanded) {
      setExpandedFields(new Set())
      setAllExpanded(false)
    } else {
      setExpandedFields(new Set(groupedSuggestions.map(g => g.field)))
      setAllExpanded(true)
    }
  }, [allExpanded, groupedSuggestions])

  // Toggle field selection for multi-field widget
  const handleFieldSelect = useCallback((field: string) => {
    setSelectedFields(prev => {
      const next = new Set(prev)
      if (next.has(field)) {
        next.delete(field)
      } else {
        next.add(field)
      }
      return next
    })
  }, [])

  // Toggle field selection mode
  const handleToggleFieldSelectionMode = useCallback(() => {
    if (fieldSelectionMode) {
      // Exiting selection mode - clear selections
      setSelectedFields(new Set())
    }
    setFieldSelectionMode(prev => !prev)
  }, [fieldSelectionMode])

  // Open combined widget modal
  const handleProposeCombinedWidget = useCallback(() => {
    if (selectedFields.size >= 2) {
      setShowCombinedModal(true)
    }
  }, [selectedFields])

  // Handle combined widget addition
  const handleAddCombinedWidget = useCallback((config: Record<string, unknown>) => {
    if (onAddCombinedWidget) {
      onAddCombinedWidget(config)
    }
    // Clear selection and close modal
    setSelectedFields(new Set())
    setFieldSelectionMode(false)
    setShowCombinedModal(false)
  }, [onAddCombinedWidget])

  // Handle semantic group selection (proactive suggestion)
  const handleSemanticGroupClick = useCallback((group: SemanticGroup) => {
    // Set selected fields from the semantic group
    setSelectedFields(new Set(group.fields))
    // Enter selection mode
    setFieldSelectionMode(true)
    // Open the modal directly
    setShowCombinedModal(true)
  }, [])

  const filteredSelectedCount = filteredSuggestions.filter(s => selectedIds.has(s.template_id)).length

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Filters header */}
      <div className="flex-shrink-0 p-4 border-b bg-muted/30">
        {/* Source filters - primary filter */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Source des donnees</span>
          </div>
        </div>

        {/* Source filter buttons */}
        <div className="flex flex-wrap gap-2 mb-4">
          {/* "All" button */}
          <button
            onClick={() => setActiveSource('all')}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
              activeSource === 'all'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-background hover:bg-muted border'
            )}
          >
            <Grid3X3 className="h-4 w-4" />
            Toutes
            <Badge
              variant={activeSource === 'all' ? 'outline' : 'secondary'}
              className={cn('ml-1 text-xs px-1.5', activeSource === 'all' && 'border-current')}
            >
              {suggestions.length}
            </Badge>
          </button>

          {/* Dynamic source buttons based on source_name */}
          {Array.from(sourcesInfo.entries()).map(([sourceName, info]) => {
            const isActive = activeSource === sourceName
            const Icon = info.isClassObject ? FileSpreadsheet : Database
            return (
              <button
                key={sourceName}
                onClick={() => setActiveSource(sourceName)}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                  isActive
                    ? info.isClassObject
                      ? 'bg-data-source-secondary/15 text-data-source-secondary dark:bg-data-source-secondary/20 shadow-sm'
                      : 'bg-data-source-primary/15 text-data-source-primary dark:bg-data-source-primary/20 shadow-sm'
                    : 'bg-background hover:bg-muted border'
                )}
              >
                <Icon className="h-4 w-4" />
                {sourceName}
                <Badge
                  variant={isActive ? 'outline' : 'secondary'}
                  className={cn('ml-1 text-xs px-1.5', isActive && 'border-current')}
                >
                  {info.count}
                </Badge>
              </button>
            )
          })}
        </div>

        {/* Category filters - secondary */}
        <div className="flex items-center gap-2 mb-2">
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground">Type de widget</span>
        </div>

        <div className="flex flex-wrap gap-2">
          {/* All category */}
          <button
            onClick={() => setActiveCategory('all')}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
              activeCategory === 'all'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-background hover:bg-muted border'
            )}
          >
            <Grid3X3 className="h-4 w-4" />
            Tous
            <Badge variant="secondary" className="ml-1 text-xs px-1.5">
              {categoryCounts.all}
            </Badge>
          </button>

          {/* Individual categories */}
          {(['navigation', 'info', 'map', 'chart', 'gauge', 'donut'] as WidgetCategory[]).map((category) => {
            const count = categoryCounts[category] || 0
            if (count === 0) return null

            const info = CATEGORY_INFO[category]
            const isActive = activeCategory === category

            return (
              <button
                key={category}
                onClick={() => setActiveCategory(category)}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                  isActive
                    ? cn('shadow-sm', info.bgColor, info.color)
                    : 'bg-background hover:bg-muted border'
                )}
              >
                {info.label}
                <Badge
                  variant={isActive ? 'outline' : 'secondary'}
                  className={cn('ml-1 text-xs px-1.5', isActive && 'border-current')}
                >
                  {count}
                </Badge>
              </button>
            )
          })}
        </div>
      </div>

      {/* Selection controls */}
      <div className="flex-shrink-0 px-4 py-2 border-b flex items-center justify-between bg-background">
        <div className="flex items-center gap-3">
          {fieldSelectionMode ? (
            // Multi-field selection mode info
            <>
              <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30">
                {selectedFields.size} champ{selectedFields.size > 1 ? 's' : ''} selectionne{selectedFields.size > 1 ? 's' : ''}
              </Badge>
              {selectedFields.size >= 2 && (
                <Button
                  size="sm"
                  onClick={handleProposeCombinedWidget}
                  className="h-7 text-xs bg-primary"
                >
                  <Combine className="h-3.5 w-3.5 mr-1.5" />
                  Proposer un widget combine
                </Button>
              )}
            </>
          ) : (
            // Normal mode info
            <>
              <span className="text-sm text-muted-foreground">
                {filteredSelectedCount} / {filteredSuggestions.length} selectionne{filteredSelectedCount > 1 ? 's' : ''}
              </span>
              <span className="text-xs text-muted-foreground">
                - {groupedSuggestions.length} champ{groupedSuggestions.length > 1 ? 's' : ''}
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Multi-field combine button */}
          <Button
            variant={fieldSelectionMode ? 'default' : 'outline'}
            size="sm"
            onClick={handleToggleFieldSelectionMode}
            className={cn(
              'h-8 text-xs',
              fieldSelectionMode && 'bg-primary'
            )}
          >
            {fieldSelectionMode ? (
              <>
                <X className="h-3.5 w-3.5 mr-1.5" />
                Annuler
              </>
            ) : (
              <>
                <Combine className="h-3.5 w-3.5 mr-1.5" />
                Combiner
              </>
            )}
          </Button>
          <div className="w-px h-4 bg-border mx-1" />
          {!fieldSelectionMode && (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={onSelectAll}
                className="h-8 text-xs"
              >
                <CheckSquare className="h-3.5 w-3.5 mr-1.5" />
                Tout
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={onDeselectAll}
                className="h-8 text-xs"
              >
                <XSquare className="h-3.5 w-3.5 mr-1.5" />
                Aucun
              </Button>
              <div className="w-px h-4 bg-border mx-1" />
            </>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleToggleAll}
            className="h-8 text-xs"
          >
            {allExpanded ? (
              <>
                <ChevronDown className="h-3.5 w-3.5 mr-1" />
                Replier
              </>
            ) : (
              <>
                <ChevronRight className="h-3.5 w-3.5 mr-1" />
                Deplier
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Semantic groups suggestions */}
      {semanticGroups.length > 0 && showSemanticGroups && !fieldSelectionMode && (
        <div className="flex-shrink-0 px-4 py-3 border-b bg-gradient-to-r from-primary/5 to-transparent">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">Widgets combines suggeres</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setShowSemanticGroups(false)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {semanticGroups.map((group) => {
              const patternInfo = PATTERN_INFO[group.pattern_type] || {
                label: group.display_name,
                icon: 'BarChart3',
                color: 'text-gray-600',
              }
              const IconComponent = PATTERN_ICONS[patternInfo.icon] || BarChart3
              return (
                <button
                  key={group.group_name}
                  onClick={() => handleSemanticGroupClick(group)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all bg-background hover:bg-primary/10 border hover:border-primary/30"
                >
                  <IconComponent className={cn('h-4 w-4', patternInfo.color)} />
                  <span className={patternInfo.color}>{group.display_name}</span>
                  <Badge variant="secondary" className="text-[10px] px-1.5">
                    {group.fields.length} champs
                  </Badge>
                </button>
              )
            })}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Cliquez pour creer un widget combinant plusieurs champs
          </p>
        </div>
      )}

      {/* Grouped gallery content */}
      <div className="flex-1 overflow-auto p-4">
        {groupedSuggestions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
              <Sparkles className="h-8 w-8 text-muted-foreground/50" />
            </div>
            <h3 className="text-lg font-medium text-muted-foreground">
              Aucun widget disponible
            </h3>
            <p className="text-sm text-muted-foreground/70 mt-2">
              {activeCategory === 'all' && activeSource === 'all'
                ? "Importez des donnees pour obtenir des suggestions"
                : "Aucun widget avec ces filtres"}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {groupedSuggestions.map((group) => (
              <FieldGroup
                key={group.field}
                group={group}
                selectedIds={selectedIds}
                groupBy={groupBy}
                onSelect={onSelect}
                onPreview={onPreview}
                isExpanded={expandedFields.has(group.field)}
                onToggleExpand={() => toggleFieldExpansion(group.field)}
                showFieldSelection={fieldSelectionMode}
                isFieldSelected={selectedFields.has(group.field)}
                onFieldSelect={handleFieldSelect}
              />
            ))}
          </div>
        )}
      </div>

      {/* Combined Widget Modal */}
      {showCombinedModal && groupBy && (
        <CombinedWidgetModal
          isOpen={showCombinedModal}
          onClose={() => setShowCombinedModal(false)}
          selectedFields={Array.from(selectedFields)}
          referenceName={groupBy}
          onAddWidget={handleAddCombinedWidget}
        />
      )}
    </div>
  )
}
