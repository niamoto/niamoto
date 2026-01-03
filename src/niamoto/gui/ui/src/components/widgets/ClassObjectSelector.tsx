/**
 * ClassObjectSelector - Select class_objects by category with auto-configs
 *
 * Displays class_objects grouped by category (scalar, binary, numeric_bins, etc.)
 * with auto-generated configs ready to use.
 */
import { useState, useMemo } from 'react'
import {
  Hash,
  Binary,
  BarChart3,
  List,
  ChevronDown,
  ChevronRight,
  Check,
  Sparkles,
  Link2,
  FileSpreadsheet,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type {
  ClassObjectSuggestion,
  ClassObjectCategory,
} from '@/lib/api/widget-suggestions'
import { CATEGORY_INFO, PLUGIN_INFO } from '@/lib/api/widget-suggestions'

// Icons for each category
const CATEGORY_ICONS: Record<ClassObjectCategory, React.ComponentType<{ className?: string }>> = {
  scalar: Hash,
  binary: Binary,
  ternary: List,
  multi_category: List,
  numeric_bins: BarChart3,
  large_category: List,
}

interface ClassObjectSelectorProps {
  classObjects: ClassObjectSuggestion[]
  selectedNames: Set<string>
  onSelect: (name: string, config: Record<string, unknown>) => void
  onDeselect: (name: string) => void
  className?: string
}

export function ClassObjectSelector({
  classObjects,
  selectedNames,
  onSelect,
  onDeselect,
  className,
}: ClassObjectSelectorProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['scalar', 'binary', 'numeric_bins'])
  )
  const [activeCategory, setActiveCategory] = useState<ClassObjectCategory | 'all'>('all')

  // Group by category
  const groupedByCategory = useMemo(() => {
    const groups: Record<ClassObjectCategory, ClassObjectSuggestion[]> = {
      scalar: [],
      binary: [],
      ternary: [],
      multi_category: [],
      numeric_bins: [],
      large_category: [],
    }
    classObjects.forEach((co) => {
      groups[co.category].push(co)
    })
    return groups
  }, [classObjects])

  // Filter by active category
  const filteredClassObjects = useMemo(() => {
    if (activeCategory === 'all') return classObjects
    return classObjects.filter((co) => co.category === activeCategory)
  }, [classObjects, activeCategory])

  // Group filtered results by category for display
  const displayGroups = useMemo(() => {
    const groups: Record<ClassObjectCategory, ClassObjectSuggestion[]> = {
      scalar: [],
      binary: [],
      ternary: [],
      multi_category: [],
      numeric_bins: [],
      large_category: [],
    }
    filteredClassObjects.forEach((co) => {
      groups[co.category].push(co)
    })
    return groups
  }, [filteredClassObjects])

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  const handleToggle = (co: ClassObjectSuggestion) => {
    if (selectedNames.has(co.name)) {
      onDeselect(co.name)
    } else {
      onSelect(co.name, co.auto_config)
    }
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Category filter tabs */}
      <div className="flex-shrink-0 p-3 border-b bg-muted/30">
        <div className="flex items-center gap-2 mb-2">
          <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Class objects disponibles</span>
          <Badge variant="secondary" className="ml-auto">
            {classObjects.length}
          </Badge>
        </div>

        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setActiveCategory('all')}
            className={cn(
              'px-2.5 py-1 rounded-md text-xs font-medium transition-all',
              activeCategory === 'all'
                ? 'bg-primary text-primary-foreground'
                : 'bg-background hover:bg-muted border'
            )}
          >
            Tous ({classObjects.length})
          </button>
          {(Object.keys(CATEGORY_INFO) as ClassObjectCategory[]).map((cat) => {
            const count = groupedByCategory[cat].length
            if (count === 0) return null
            const info = CATEGORY_INFO[cat]
            const isActive = activeCategory === cat

            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={cn(
                  'px-2.5 py-1 rounded-md text-xs font-medium transition-all',
                  isActive
                    ? cn(info.bgColor, info.color)
                    : 'bg-background hover:bg-muted border'
                )}
              >
                {info.label} ({count})
              </button>
            )
          })}
        </div>
      </div>

      {/* Selection summary */}
      <div className="flex-shrink-0 px-3 py-2 border-b bg-background">
        <span className="text-sm text-muted-foreground">
          {selectedNames.size} selectionne{selectedNames.size > 1 ? 's' : ''}
        </span>
      </div>

      {/* Class objects list */}
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {(Object.keys(displayGroups) as ClassObjectCategory[]).map((category) => {
          const items = displayGroups[category]
          if (items.length === 0) return null

          const info = CATEGORY_INFO[category]
          const Icon = CATEGORY_ICONS[category]
          const isExpanded = expandedCategories.has(category)
          const selectedInCategory = items.filter((co) => selectedNames.has(co.name)).length

          return (
            <Collapsible
              key={category}
              open={isExpanded}
              onOpenChange={() => toggleCategory(category)}
            >
              <CollapsibleTrigger asChild>
                <button
                  className={cn(
                    'w-full flex items-center gap-2 p-2 rounded-lg transition-colors',
                    'hover:bg-muted/50',
                    isExpanded && 'bg-muted/30'
                  )}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  <div className={cn('p-1 rounded', info.bgColor)}>
                    <Icon className={cn('h-3.5 w-3.5', info.color)} />
                  </div>
                  <span className="text-sm font-medium">{info.label}</span>
                  <span className="text-xs text-muted-foreground ml-1">
                    ({items.length})
                  </span>
                  {selectedInCategory > 0 && (
                    <Badge variant="default" className="ml-auto text-xs">
                      {selectedInCategory}
                    </Badge>
                  )}
                </button>
              </CollapsibleTrigger>

              <CollapsibleContent className="pl-8 pr-2 py-1 space-y-1">
                {items.map((co) => (
                  <ClassObjectItem
                    key={co.name}
                    classObject={co}
                    isSelected={selectedNames.has(co.name)}
                    onToggle={() => handleToggle(co)}
                  />
                ))}
              </CollapsibleContent>
            </Collapsible>
          )
        })}

        {filteredClassObjects.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Sparkles className="h-8 w-8 text-muted-foreground/50 mb-2" />
            <p className="text-sm text-muted-foreground">
              Aucun class_object dans cette categorie
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

interface ClassObjectItemProps {
  classObject: ClassObjectSuggestion
  isSelected: boolean
  onToggle: () => void
}

function ClassObjectItem({ classObject, isSelected, onToggle }: ClassObjectItemProps) {
  const pluginInfo = PLUGIN_INFO[classObject.suggested_plugin]
  const hasRelated = classObject.related_class_objects.length > 0
  const hasMappingHints = Object.keys(classObject.mapping_hints).length > 0

  return (
    <button
      onClick={onToggle}
      className={cn(
        'w-full flex items-start gap-2 p-2 rounded-md text-left transition-colors',
        isSelected
          ? 'bg-primary/10 border border-primary/30'
          : 'hover:bg-muted/50 border border-transparent'
      )}
    >
      <div
        className={cn(
          'flex-shrink-0 w-4 h-4 mt-0.5 rounded border transition-colors',
          isSelected
            ? 'bg-primary border-primary text-primary-foreground'
            : 'border-muted-foreground/30'
        )}
      >
        {isSelected && <Check className="h-3 w-3 m-0.5" />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{classObject.name}</span>
          {hasRelated && (
            <Tooltip>
              <TooltipTrigger>
                <Link2 className="h-3 w-3 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                <p className="text-xs font-medium mb-1">Class objects lies:</p>
                <p className="text-xs text-muted-foreground">
                  {classObject.related_class_objects.slice(0, 5).join(', ')}
                  {classObject.related_class_objects.length > 5 && '...'}
                </p>
              </TooltipContent>
            </Tooltip>
          )}
          {hasMappingHints && (
            <Tooltip>
              <TooltipTrigger>
                <Sparkles className="h-3 w-3 text-amber-500" />
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="text-xs">Mapping auto-detecte</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-muted-foreground">
            {pluginInfo?.label || classObject.suggested_plugin}
          </span>
          <span className="text-xs text-muted-foreground/50">|</span>
          <span className="text-xs text-muted-foreground">
            {classObject.cardinality === 0
              ? 'valeur unique'
              : `${classObject.cardinality} valeurs`}
          </span>
        </div>

        {classObject.class_names.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {classObject.class_names.slice(0, 3).map((name) => (
              <Badge key={name} variant="outline" className="text-[10px] px-1 py-0">
                {name}
              </Badge>
            ))}
            {classObject.class_names.length > 3 && (
              <Badge variant="outline" className="text-[10px] px-1 py-0">
                +{classObject.class_names.length - 3}
              </Badge>
            )}
          </div>
        )}
      </div>

      <Badge
        variant="secondary"
        className={cn(
          'text-[10px] px-1.5',
          classObject.confidence >= 0.9 && 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400'
        )}
      >
        {Math.round(classObject.confidence * 100)}%
      </Badge>
    </button>
  )
}

export default ClassObjectSelector
