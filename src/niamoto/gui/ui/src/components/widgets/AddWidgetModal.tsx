/**
 * AddWidgetModal - Modal for adding new widgets
 *
 * Large modal (90vw × 85vh) with three tabs:
 * - Suggestions: Grid with iframe previews + right panel customization
 * - Combined: Semantic groups + manual field selection
 * - Custom: 4-step wizard with YAML preview
 */
import { useState, useCallback, useMemo, useEffect } from 'react'
import {
  Loader2,
  Sparkles,
  Combine,
  Wand2,
  Check,
  Info,
  Map,
  BarChart3,
  Activity,
  PieChart,
  Layers,
  FolderTree,
  Plus,
  Search,
  ChevronRight,
  ChevronDown,
  Settings2,
  Eye,
  Zap,
  Link2,
  RefreshCw,
  Database,
  ChevronsUpDown,
  MapPin,
  LayoutGrid,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Checkbox } from '@/components/ui/checkbox'
import { Separator } from '@/components/ui/separator'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { TemplateSuggestion } from './types'
import { useGenerateConfig, useSaveConfig } from './useTemplates'
import { RecipeEditor } from './recipe'
import {
  useCombinedWidgetSuggestions,
  useSemanticGroups,
  type SemanticGroup,
  type CombinedWidgetSuggestion,
} from '@/lib/api/widget-suggestions'
import type { ReferenceInfo } from '@/hooks/useReferences'

// Category icons
const CATEGORY_ICONS: Record<string, React.ElementType> = {
  navigation: FolderTree,
  info: Info,
  map: Map,
  chart: BarChart3,
  gauge: Activity,
  donut: PieChart,
  table: Layers,
}

// Default colors for customization
const COLOR_PALETTE = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336']

// Widget preview iframe component with scaling (like WidgetMiniature)
interface WidgetPreviewProps {
  templateId: string
  groupBy?: string
  className?: string
  width?: number
  height?: number
}

// Base iframe dimensions before scaling
const IFRAME_BASE_WIDTH = 400
const IFRAME_BASE_HEIGHT = 300

function WidgetPreview({ templateId, groupBy, className, width = 200, height = 96 }: WidgetPreviewProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [key, setKey] = useState(0)

  // Calculate scale to fit the container
  const scale = Math.min(width / IFRAME_BASE_WIDTH, height / IFRAME_BASE_HEIGHT)

  const previewUrl = groupBy
    ? `/api/templates/preview/${templateId}?group_by=${encodeURIComponent(groupBy)}`
    : `/api/templates/preview/${templateId}`

  useEffect(() => {
    setIsLoading(true)
    setHasError(false)
    setKey((k) => k + 1)
  }, [templateId, groupBy])

  return (
    <div
      className={cn('relative bg-muted/30 overflow-hidden', className)}
      style={{ width, height }}
    >
      {isLoading && !hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/50 z-10">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      )}
      {hasError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-muted/50 z-10">
          <span className="text-[10px] text-muted-foreground">Erreur</span>
        </div>
      )}
      <iframe
        key={key}
        src={previewUrl}
        className="pointer-events-none origin-top-left border-0"
        style={{
          width: IFRAME_BASE_WIDTH,
          height: IFRAME_BASE_HEIGHT,
          transform: `scale(${scale})`,
        }}
        onLoad={() => setIsLoading(false)}
        onError={() => setHasError(true)}
        title={`Preview ${templateId}`}
      />
    </div>
  )
}

// Large preview component for right panel (with scaling)
interface LargePreviewProps {
  templateId: string
  groupBy?: string
}

// Large preview dimensions
const LARGE_PREVIEW_WIDTH = 348  // Right panel width - padding
const LARGE_PREVIEW_HEIGHT = 192

function LargePreview({ templateId, groupBy }: LargePreviewProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [key, setKey] = useState(0)

  // Calculate scale to fit the container
  const scale = Math.min(LARGE_PREVIEW_WIDTH / IFRAME_BASE_WIDTH, LARGE_PREVIEW_HEIGHT / IFRAME_BASE_HEIGHT)

  const previewUrl = groupBy
    ? `/api/templates/preview/${templateId}?group_by=${encodeURIComponent(groupBy)}`
    : `/api/templates/preview/${templateId}`

  useEffect(() => {
    setIsLoading(true)
    setHasError(false)
    setKey((k) => k + 1)
  }, [templateId, groupBy])

  const handleRefresh = () => {
    setIsLoading(true)
    setHasError(false)
    setKey((k) => k + 1)
  }

  return (
    <div className="relative">
      <div
        className="bg-background border rounded-lg overflow-hidden"
        style={{ width: LARGE_PREVIEW_WIDTH, height: LARGE_PREVIEW_HEIGHT }}
      >
        {isLoading && !hasError && (
          <div className="absolute inset-0 flex items-center justify-center bg-background z-10">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}
        {hasError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-background z-10">
            <Eye className="h-8 w-8 text-muted-foreground/30 mb-2" />
            <span className="text-sm text-muted-foreground">Preview indisponible</span>
            <Button variant="ghost" size="sm" className="mt-2" onClick={handleRefresh}>
              <RefreshCw className="h-3 w-3 mr-1" />
              Reessayer
            </Button>
          </div>
        )}
        <iframe
          key={key}
          src={previewUrl}
          className="pointer-events-none origin-top-left border-0"
          style={{
            width: IFRAME_BASE_WIDTH,
            height: IFRAME_BASE_HEIGHT,
            transform: `scale(${scale})`,
          }}
          onLoad={() => setIsLoading(false)}
          onError={() => setHasError(true)}
          title={`Preview ${templateId}`}
        />
      </div>
      {!hasError && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 right-2 h-7 w-7 bg-background/80 hover:bg-background z-20"
          onClick={handleRefresh}
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isLoading && 'animate-spin')} />
        </Button>
      )}
    </div>
  )
}

interface AddWidgetModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultTab?: 'suggestions' | 'combined' | 'custom'
  reference: ReferenceInfo
  suggestions: TemplateSuggestion[]
  suggestionsLoading: boolean
  onWidgetAdded: () => void
}

interface Customization {
  title: string
  bins?: number
  color: string
}

export function AddWidgetModal({
  open,
  onOpenChange,
  defaultTab = 'suggestions',
  reference,
  suggestions,
  suggestionsLoading,
  onWidgetAdded,
}: AddWidgetModalProps) {
  const [activeTab, setActiveTab] = useState(defaultTab)

  // Suggestions tab state
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set())
  const [hoveredSuggestion, setHoveredSuggestion] = useState<string | null>(null)
  const [focusedSuggestion, setFocusedSuggestion] = useState<string | null>(null)
  const [customizations, setCustomizations] = useState<Record<string, Customization>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set())
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)

  // Combined tab state
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [selectedCombined, setSelectedCombined] = useState<CombinedWidgetSuggestion | null>(null)

  // Custom tab state
  const [wizardStep, setWizardStep] = useState(1)

  // Hooks for generating and saving config
  const { generate: generateConfig, loading: generating } = useGenerateConfig()
  const { save: saveConfig, loading: saving } = useSaveConfig()

  // Semantic groups for combined widgets
  const { groups: semanticGroups } = useSemanticGroups(reference.name, 'occurrences')

  // Combined widget suggestions based on selected fields
  const {
    suggestions: combinedSuggestions,
    loading: combinedLoading,
    fetchSuggestions: fetchCombinedSuggestions,
  } = useCombinedWidgetSuggestions(reference.name, selectedFields, 'occurrences')

  // Get available fields from suggestions
  const availableFields = useMemo(() => {
    const fields = new Set<string>()
    suggestions.forEach((s) => {
      if (s.matched_column) fields.add(s.matched_column)
    })
    return Array.from(fields).sort()
  }, [suggestions])

  // Reset state when modal opens/closes
  useEffect(() => {
    if (open) {
      setActiveTab(defaultTab)
      setSelectedSuggestions(new Set())
      setHoveredSuggestion(null)
      setFocusedSuggestion(null)
      setCustomizations({})
      setSearchQuery('')
      setCollapsedSections(new Set())
      setCategoryFilter(null)
      setSelectedFields([])
      setSelectedCombined(null)
      setWizardStep(1)
    }
  }, [open, defaultTab])

  // Fetch combined suggestions when fields change
  useEffect(() => {
    if (selectedFields.length >= 2) {
      fetchCombinedSuggestions()
    }
  }, [selectedFields, fetchCombinedSuggestions])

  // Auto-select first combined suggestion
  useEffect(() => {
    if (combinedSuggestions.length > 0 && !selectedCombined) {
      const recommended = combinedSuggestions.find((s) => s.is_recommended)
      setSelectedCombined(recommended || combinedSuggestions[0])
    }
  }, [combinedSuggestions, selectedCombined])

  // Get the suggestion to preview (focused > hovered > first selected)
  const previewSuggestionId =
    focusedSuggestion || hoveredSuggestion || Array.from(selectedSuggestions)[0] || null
  const previewSuggestion = suggestions.find((s) => s.template_id === previewSuggestionId)

  // Group suggestions with smart ordering:
  // 1. Group widgets (navigation, info) - with group name
  // 2. Map widgets (cartography)
  // 3. Data visualizations grouped by field
  const groupedSuggestions = useMemo(() => {
    // Apply search filter
    let filtered = searchQuery
      ? suggestions.filter(
          (s) =>
            s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.matched_column?.toLowerCase().includes(searchQuery.toLowerCase())
        )
      : suggestions

    // Apply category filter
    if (categoryFilter) {
      filtered = filtered.filter((s) => s.category === categoryFilter)
    }

    // Separate into categories
    const groupWidgets = filtered.filter(
      (s) => s.category === 'navigation' || s.category === 'info'
    )
    const mapWidgets = filtered.filter((s) => s.category === 'map')
    const dataWidgets = filtered.filter(
      (s) => !['navigation', 'info', 'map'].includes(s.category)
    )

    // Group data widgets by field
    const fieldGroups: Record<string, TemplateSuggestion[]> = {}
    dataWidgets.forEach((s) => {
      const field = s.matched_column || 'other'
      if (!fieldGroups[field]) fieldGroups[field] = []
      fieldGroups[field].push(s)
    })

    // Sort field groups by confidence of best suggestion
    const sortedFieldGroups = Object.entries(fieldGroups).sort((a, b) => {
      const maxConfA = Math.max(...a[1].map((s) => s.confidence))
      const maxConfB = Math.max(...b[1].map((s) => s.confidence))
      return maxConfB - maxConfA
    })

    // Build final ordered list
    const result: Array<{ key: string; label: string; icon: 'group' | 'map' | 'field'; suggestions: TemplateSuggestion[] }> = []

    // 1. Group widgets (navigation + info) with group name
    if (groupWidgets.length > 0) {
      result.push({
        key: '_group',
        label: reference.name, // Use actual group name
        icon: 'group',
        suggestions: groupWidgets.sort((a, b) => b.confidence - a.confidence),
      })
    }

    // 2. Map widgets
    if (mapWidgets.length > 0) {
      result.push({
        key: '_map',
        label: 'Cartographie',
        icon: 'map',
        suggestions: mapWidgets.sort((a, b) => b.confidence - a.confidence),
      })
    }

    // 3. Data widgets by field
    sortedFieldGroups.forEach(([field, fieldSuggestions]) => {
      result.push({
        key: field,
        label: field,
        icon: 'field',
        suggestions: fieldSuggestions.sort((a, b) => b.confidence - a.confidence),
      })
    })

    return result
  }, [suggestions, searchQuery, categoryFilter, reference.name])

  // Get all unique categories for filter chips
  const availableCategories = useMemo(() => {
    const cats = new Set<string>()
    suggestions.forEach((s) => cats.add(s.category))
    return Array.from(cats)
  }, [suggestions])

  // Toggle section collapse
  const toggleSection = useCallback((key: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }, [])

  // Collapse/expand all sections
  const collapseAll = useCallback(() => {
    setCollapsedSections(new Set(groupedSuggestions.map((g) => g.key)))
  }, [groupedSuggestions])

  const expandAll = useCallback(() => {
    setCollapsedSections(new Set())
  }, [])

  // Get customization for a suggestion
  const getCustomization = useCallback(
    (id: string): Customization => {
      if (customizations[id]) return customizations[id]
      const suggestion = suggestions.find((s) => s.template_id === id)
      return {
        title: suggestion?.name || '',
        bins: 10,
        color: COLOR_PALETTE[0],
      }
    },
    [customizations, suggestions]
  )

  // Update customization
  const updateCustomization = useCallback((id: string, updates: Partial<Customization>) => {
    setCustomizations((prev) => ({
      ...prev,
      [id]: { ...prev[id], ...updates } as Customization,
    }))
  }, [])

  // Toggle suggestion selection
  const toggleSuggestion = useCallback((id: string) => {
    setSelectedSuggestions((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
        setFocusedSuggestion(id)
      }
      return next
    })
  }, [])

  // Toggle field selection for combined
  const toggleField = useCallback((field: string) => {
    setSelectedFields((prev) => {
      if (prev.includes(field)) {
        return prev.filter((f) => f !== field)
      }
      if (prev.length >= 5) return prev // Max 5 fields
      return [...prev, field]
    })
    setSelectedCombined(null)
  }, [])

  // Handle semantic group click
  const handleSemanticGroupClick = useCallback((group: SemanticGroup) => {
    setSelectedFields(group.fields)
    setSelectedCombined(null)
  }, [])

  // Handle adding suggestion widgets
  const handleAddSuggestions = useCallback(async () => {
    if (selectedSuggestions.size === 0) return

    const templates = Array.from(selectedSuggestions)
      .map((id) => {
        const suggestion = suggestions.find((s) => s.template_id === id)
        if (!suggestion) return null
        const customization = getCustomization(id)
        return {
          template_id: suggestion.template_id,
          plugin: suggestion.plugin,
          config: {
            ...suggestion.config,
            title: customization.title || suggestion.name,
          },
        }
      })
      .filter(Boolean) as Array<{
      template_id: string
      plugin: string
      config: Record<string, unknown>
    }>

    const result = await generateConfig(templates, reference.name, reference.kind)
    if (result) {
      await saveConfig(result)
      onWidgetAdded()
    }
  }, [selectedSuggestions, suggestions, getCustomization, generateConfig, saveConfig, reference, onWidgetAdded])

  // Handle adding a combined widget
  const handleAddCombined = useCallback(async () => {
    if (!selectedCombined) return

    const widgetId = `combined_${selectedCombined.pattern_type}_${Date.now()}`

    const response = await fetch('/api/config/widgets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        widget_id: widgetId,
        group_by: reference.name,
        transform: {
          plugin: selectedCombined.transformer_config.plugin,
          params: selectedCombined.transformer_config.params,
        },
        export: {
          plugin: selectedCombined.widget_config.plugin,
          title: selectedCombined.name,
          params: selectedCombined.widget_config.params,
        },
      }),
    })

    if (response.ok) {
      onWidgetAdded()
    }
  }, [selectedCombined, reference, onWidgetAdded])

  // Handle recipe editor save
  const handleRecipeSave = useCallback(() => {
    onWidgetAdded()
  }, [onWidgetAdded])

  const isBusy = generating || saving

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        onOpenChange(isOpen)
        if (!isOpen) {
          setHoveredSuggestion(null)
          setFocusedSuggestion(null)
        }
      }}
    >
      <DialogContent className="!max-w-[90vw] w-[1200px] h-[85vh] flex flex-col p-0">
        <DialogHeader className="px-6 py-4 border-b shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Ajouter un widget
          </DialogTitle>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as typeof activeTab)}
          className="flex-1 flex flex-col min-h-0"
        >
          {/* Modal tabs */}
          <div className="px-6 border-b bg-muted/30 shrink-0">
            <TabsList className="h-11 bg-transparent gap-1">
              <TabsTrigger
                value="suggestions"
                className="text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-lg"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Suggestions
                <Badge variant="secondary" className="ml-2 text-xs">
                  {suggestions.length}
                </Badge>
              </TabsTrigger>
              <TabsTrigger
                value="combined"
                className="text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-lg"
              >
                <Combine className="h-4 w-4 mr-2" />
                Combines
                {semanticGroups.length > 0 && (
                  <Badge className="ml-2 text-xs bg-amber-500">{semanticGroups.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="custom"
                className="text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-lg"
              >
                <Wand2 className="h-4 w-4 mr-2" />
                Personnalise
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Tab: Suggestions - Two columns layout */}
          <TabsContent value="suggestions" className="flex-1 m-0 min-h-0 overflow-hidden">
            {suggestionsLoading ? (
              <div className="flex flex-col items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <p className="mt-3 text-sm text-muted-foreground">Analyse des donnees...</p>
              </div>
            ) : suggestions.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full">
                <Sparkles className="h-12 w-12 text-muted-foreground/50" />
                <h3 className="mt-4 font-medium">Aucune suggestion</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Importez des donnees pour obtenir des suggestions de widgets.
                </p>
              </div>
            ) : (
              <div className="flex h-full min-h-0">
                {/* Left column - Grid of suggestions */}
                <div className="flex-1 flex flex-col border-r min-w-0 min-h-0">
                  {/* Search and filters */}
                  <div className="px-4 py-3 border-b shrink-0 space-y-3">
                    {/* Search + collapse buttons */}
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                          placeholder="Rechercher..."
                          className="pl-8 h-9"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                        />
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-9 px-2"
                        onClick={collapsedSections.size === groupedSuggestions.length ? expandAll : collapseAll}
                        title={collapsedSections.size === groupedSuggestions.length ? 'Tout déplier' : 'Tout replier'}
                      >
                        <ChevronsUpDown className="h-4 w-4" />
                      </Button>
                    </div>

                    {/* Category filter chips */}
                    <div className="flex flex-wrap gap-1.5">
                      <Button
                        variant={categoryFilter === null ? 'default' : 'outline'}
                        size="sm"
                        className="h-7 text-xs px-2.5"
                        onClick={() => setCategoryFilter(null)}
                      >
                        Tous
                      </Button>
                      {availableCategories.map((cat) => {
                        const catIcons: Record<string, React.ElementType> = {
                          navigation: FolderTree,
                          info: LayoutGrid,
                          map: MapPin,
                          chart: BarChart3,
                          gauge: Activity,
                          donut: PieChart,
                          table: Layers,
                        }
                        const CatIcon = catIcons[cat] || BarChart3
                        const catLabels: Record<string, string> = {
                          navigation: 'Navigation',
                          info: 'Info',
                          map: 'Carte',
                          chart: 'Graphique',
                          gauge: 'Jauge',
                          donut: 'Donut',
                          table: 'Tableau',
                        }
                        return (
                          <Button
                            key={cat}
                            variant={categoryFilter === cat ? 'default' : 'outline'}
                            size="sm"
                            className="h-7 text-xs px-2.5"
                            onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
                          >
                            <CatIcon className="h-3 w-3 mr-1" />
                            {catLabels[cat] || cat}
                          </Button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Suggestions grid with scroll */}
                  <div className="flex-1 min-h-0 overflow-hidden">
                    <ScrollArea className="h-full">
                      <div className="p-4 space-y-2">
                        {groupedSuggestions.map((group) => {
                          const isCollapsed = collapsedSections.has(group.key)
                          const SectionIcon =
                            group.icon === 'group'
                              ? FolderTree
                              : group.icon === 'map'
                                ? MapPin
                                : Database

                          return (
                            <div key={group.key} className="border rounded-lg overflow-hidden">
                              {/* Collapsible section header */}
                              <button
                                className={cn(
                                  'w-full flex items-center gap-2 px-3 py-2.5 text-left transition-colors',
                                  'hover:bg-muted/50',
                                  group.icon === 'group' && 'bg-primary/5',
                                  group.icon === 'map' && 'bg-emerald-50 dark:bg-emerald-950/20'
                                )}
                                onClick={() => toggleSection(group.key)}
                              >
                                {isCollapsed ? (
                                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                                ) : (
                                  <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                                )}
                                <SectionIcon
                                  className={cn(
                                    'h-4 w-4 shrink-0',
                                    group.icon === 'group' && 'text-primary',
                                    group.icon === 'map' && 'text-emerald-600',
                                    group.icon === 'field' && 'text-amber-600'
                                  )}
                                />
                                <span
                                  className={cn(
                                    'font-medium text-sm',
                                    group.icon === 'field' && 'font-mono'
                                  )}
                                >
                                  {group.label}
                                </span>
                                <Badge variant="secondary" className="text-xs ml-auto">
                                  {group.suggestions.length}
                                </Badge>
                              </button>

                              {/* Section content */}
                              {!isCollapsed && (
                                <div className="p-3 pt-2 border-t bg-background">
                                  <div className="grid grid-cols-2 gap-3">
                                    {group.suggestions.map((suggestion) => {
                                      const Icon = CATEGORY_ICONS[suggestion.category] || BarChart3
                                      const isSelected = selectedSuggestions.has(suggestion.template_id)
                                      const isFocused = focusedSuggestion === suggestion.template_id

                                      return (
                                        <div
                                          key={suggestion.template_id}
                                          className={cn(
                                            'border rounded-lg overflow-hidden cursor-pointer transition-all hover:shadow-md group',
                                            isSelected && isFocused
                                              ? 'border-primary ring-2 ring-primary/30'
                                              : isSelected
                                                ? 'border-primary/50 bg-primary/5'
                                                : 'hover:border-muted-foreground/40'
                                          )}
                                          onClick={() => toggleSuggestion(suggestion.template_id)}
                                          onMouseEnter={() => setHoveredSuggestion(suggestion.template_id)}
                                          onMouseLeave={() => setHoveredSuggestion(null)}
                                        >
                                          {/* Preview area with scaled iframe */}
                                          <div className="relative bg-muted/30">
                                            <WidgetPreview
                                              templateId={suggestion.template_id}
                                              groupBy={reference.name}
                                              width={380}
                                              height={100}
                                            />
                                            {/* Checkbox overlay */}
                                            <div className="absolute top-2 right-2 z-20">
                                              <Checkbox
                                                checked={isSelected}
                                                className="bg-background shadow-sm"
                                                onClick={(e) => e.stopPropagation()}
                                              />
                                            </div>
                                          </div>
                                          {/* Info */}
                                          <div className="p-2.5">
                                            <div className="flex items-center gap-1.5 mb-1">
                                              <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                                              <span className="font-medium text-sm truncate">
                                                {suggestion.name}
                                              </span>
                                            </div>
                                            <Badge variant="outline" className="text-[10px] h-5">
                                              {suggestion.plugin}
                                            </Badge>
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </ScrollArea>
                  </div>
                </div>

                {/* Right column - Preview & Customization */}
                <div className="w-[380px] flex flex-col bg-muted/20 shrink-0 min-h-0">
                  {previewSuggestion ? (
                    <ScrollArea className="flex-1">
                      <div className="p-4">
                        {/* Preview header */}
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            {(() => {
                              const Icon = CATEGORY_ICONS[previewSuggestion.category] || BarChart3
                              return <Icon className="h-4 w-4 text-muted-foreground" />
                            })()}
                            <span className="font-medium text-sm">{previewSuggestion.name}</span>
                          </div>
                          {selectedSuggestions.has(previewSuggestion.template_id) && (
                            <Badge variant="outline" className="text-xs">
                              <Check className="h-3 w-3 mr-1" />
                              Selectionne
                            </Badge>
                          )}
                        </div>

                        {/* Large preview with iframe */}
                        <LargePreview
                          templateId={previewSuggestion.template_id}
                          groupBy={reference.name}
                        />

                        {/* Info */}
                        <div className="mt-3 space-y-2">
                          <p className="text-sm text-muted-foreground">
                            {previewSuggestion.description}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Badge variant="secondary" className="text-[10px]">
                              {previewSuggestion.plugin}
                            </Badge>
                            {previewSuggestion.matched_column && (
                              <>
                                <span>•</span>
                                <code className="text-[10px] bg-muted px-1 py-0.5 rounded">
                                  {previewSuggestion.matched_column}
                                </code>
                              </>
                            )}
                          </div>
                        </div>

                        <Separator className="my-4" />

                        {/* Quick customization (only when selected) */}
                        {selectedSuggestions.has(previewSuggestion.template_id) ? (
                          <div>
                            <div className="flex items-center gap-2 mb-3">
                              <Settings2 className="h-4 w-4 text-muted-foreground" />
                              <span className="font-medium text-sm">Personnalisation rapide</span>
                            </div>

                            <div className="space-y-3">
                              <div>
                                <label className="text-xs text-muted-foreground">Titre</label>
                                <Input
                                  value={getCustomization(previewSuggestion.template_id).title}
                                  onChange={(e) =>
                                    updateCustomization(previewSuggestion.template_id, {
                                      title: e.target.value,
                                    })
                                  }
                                  className="h-8 mt-1"
                                />
                              </div>

                              {previewSuggestion.category === 'chart' && (
                                <div>
                                  <label className="text-xs text-muted-foreground">
                                    Nombre de bins
                                  </label>
                                  <Input
                                    type="number"
                                    value={getCustomization(previewSuggestion.template_id).bins || 10}
                                    onChange={(e) =>
                                      updateCustomization(previewSuggestion.template_id, {
                                        bins: parseInt(e.target.value),
                                      })
                                    }
                                    className="h-8 mt-1"
                                  />
                                </div>
                              )}

                              <div>
                                <label className="text-xs text-muted-foreground">Couleur</label>
                                <div className="flex gap-2 mt-1">
                                  {COLOR_PALETTE.map((color) => (
                                    <button
                                      key={color}
                                      className={cn(
                                        'w-7 h-7 rounded border-2 transition-all',
                                        getCustomization(previewSuggestion.template_id).color === color
                                          ? 'border-foreground scale-110'
                                          : 'border-transparent hover:scale-105'
                                      )}
                                      style={{ backgroundColor: color }}
                                      onClick={() =>
                                        updateCustomization(previewSuggestion.template_id, { color })
                                      }
                                    />
                                  ))}
                                </div>
                              </div>
                            </div>

                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full mt-4"
                              onClick={() => {
                                setActiveTab('custom')
                                setWizardStep(1)
                              }}
                            >
                              <Wand2 className="h-4 w-4 mr-2" />
                              Edition avancee (YAML)
                              <ChevronRight className="h-4 w-4 ml-auto" />
                            </Button>
                          </div>
                        ) : (
                          <div className="text-center py-4">
                            <Info className="h-8 w-8 text-muted-foreground/50 mx-auto mb-2" />
                            <p className="text-sm text-muted-foreground">
                              Cliquez sur ce widget pour le selectionner et personnaliser
                            </p>
                          </div>
                        )}
                      </div>
                    </ScrollArea>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
                      <Eye className="h-12 w-12 text-muted-foreground/30 mb-3" />
                      <p className="font-medium text-muted-foreground">Apercu du widget</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Survolez ou selectionnez un widget pour voir l'apercu
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </TabsContent>

          {/* Tab: Combined - Two columns layout */}
          <TabsContent value="combined" className="flex-1 m-0 min-h-0">
            <div className="flex h-full min-h-0">
              {/* Left column */}
              <ScrollArea className="flex-1 border-r">
                <div className="p-6">
                  {/* Semantic groups detected */}
                  {semanticGroups.length > 0 && (
                    <div className="mb-8">
                      <div className="flex items-center gap-2 mb-4">
                        <Zap className="h-5 w-5 text-amber-500" />
                        <h3 className="font-medium">Patterns detectes automatiquement</h3>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        {semanticGroups.map((group) => (
                          <Card
                            key={group.group_name}
                            className={cn(
                              'cursor-pointer hover:shadow-md transition-all',
                              selectedFields.join(',') === group.fields.join(',')
                                ? 'border-primary ring-1 ring-primary'
                                : 'hover:border-primary/50'
                            )}
                            onClick={() => handleSemanticGroupClick(group)}
                          >
                            <CardHeader className="pb-2">
                              <CardTitle className="text-base flex items-center gap-2">
                                <Zap className="h-5 w-5 text-amber-600" />
                                {group.display_name}
                                <Badge className="ml-auto text-xs bg-amber-100 text-amber-800">
                                  {group.fields.length} champs
                                </Badge>
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <p className="text-sm text-muted-foreground mb-3">{group.description}</p>
                              <div className="flex flex-wrap gap-1">
                                {group.fields.map((f) => (
                                  <Badge key={f} variant="outline" className="text-xs font-mono">
                                    {f}
                                  </Badge>
                                ))}
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Manual field selection */}
                  <div>
                    <div className="flex items-center gap-2 mb-4">
                      <Link2 className="h-5 w-5 text-blue-500" />
                      <h3 className="font-medium">Combiner manuellement</h3>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      Selectionnez 2 a 5 champs pour creer un widget combine personnalise.
                    </p>
                    <div className="grid grid-cols-3 gap-2 p-4 border rounded-lg bg-muted/30">
                      {availableFields.map((field) => (
                        <div
                          key={field}
                          className={cn(
                            'flex items-center gap-2 p-2 rounded-md border bg-background cursor-pointer transition-colors',
                            selectedFields.includes(field)
                              ? 'border-primary bg-primary/5'
                              : 'hover:border-primary/50'
                          )}
                          onClick={() => toggleField(field)}
                        >
                          <Checkbox
                            checked={selectedFields.includes(field)}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <code className="text-xs font-mono truncate">{field}</code>
                        </div>
                      ))}
                    </div>

                    {/* Combined suggestions */}
                    {selectedFields.length >= 2 && (
                      <div className="mt-6">
                        {combinedLoading ? (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                          </div>
                        ) : combinedSuggestions.length > 0 ? (
                          <div className="space-y-2">
                            <h4 className="text-sm font-medium mb-3">Widgets proposes</h4>
                            {combinedSuggestions.map((suggestion, idx) => {
                              const isSelected = selectedCombined === suggestion
                              return (
                                <button
                                  key={idx}
                                  onClick={() => setSelectedCombined(suggestion)}
                                  className={cn(
                                    'w-full text-left rounded-lg border p-3 transition-all',
                                    isSelected
                                      ? 'border-primary bg-primary/5 ring-1 ring-primary'
                                      : 'hover:border-primary/50 hover:bg-muted/50'
                                  )}
                                >
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="font-medium">{suggestion.name}</span>
                                    {suggestion.is_recommended && (
                                      <Badge className="bg-primary/10 text-primary text-[10px]">
                                        Recommande
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="text-sm text-muted-foreground">{suggestion.description}</p>
                                </button>
                              )
                            })}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground text-center py-4">
                            Aucune combinaison detectee pour ces champs.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </ScrollArea>

              {/* Right column - Preview */}
              <div className="w-[380px] bg-muted/20 flex flex-col items-center justify-center text-center p-6 shrink-0">
                {selectedCombined ? (
                  <div className="w-full">
                    <h4 className="font-medium mb-2">{selectedCombined.name}</h4>
                    <p className="text-sm text-muted-foreground mb-4">{selectedCombined.description}</p>
                    <div className="h-40 bg-background border rounded-lg flex items-center justify-center mb-4">
                      <BarChart3 className="h-12 w-12 text-muted-foreground/30" />
                    </div>
                    <div className="flex flex-wrap gap-1 justify-center">
                      {selectedCombined.fields.map((field) => (
                        <Badge key={field} variant="outline" className="text-xs font-mono">
                          {field}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    <Eye className="h-12 w-12 text-muted-foreground/30 mb-3" />
                    <p className="font-medium text-muted-foreground">Apercu du widget combine</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Selectionnez un pattern ou des champs pour voir l'apercu
                    </p>
                  </>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Tab: Custom - Wizard with preview */}
          <TabsContent value="custom" className="flex-1 m-0 min-h-0">
            <div className="flex h-full min-h-0">
              {/* Wizard steps sidebar */}
              <div className="w-56 border-r p-4 bg-muted/20 shrink-0">
                <h3 className="font-medium mb-4 text-sm">Etapes de creation</h3>
                <div className="space-y-2">
                  {[
                    { step: 1, label: 'Identifiant', desc: 'Nom unique' },
                    { step: 2, label: 'Source', desc: 'Donnees' },
                    { step: 3, label: 'Transformation', desc: 'Traitement' },
                    { step: 4, label: 'Affichage', desc: 'Visualisation' },
                  ].map(({ step, label, desc }) => (
                    <div
                      key={step}
                      className={cn(
                        'flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors',
                        wizardStep === step
                          ? 'bg-primary/10 border border-primary/30'
                          : wizardStep > step
                            ? 'text-muted-foreground'
                            : 'hover:bg-muted'
                      )}
                      onClick={() => setWizardStep(step)}
                    >
                      <div
                        className={cn(
                          'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0',
                          wizardStep === step
                            ? 'bg-primary text-primary-foreground'
                            : wizardStep > step
                              ? 'bg-green-600 text-white'
                              : 'bg-muted text-muted-foreground'
                        )}
                      >
                        {wizardStep > step ? <Check className="h-3 w-3" /> : step}
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{label}</div>
                        <div className="text-xs text-muted-foreground truncate">{desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* RecipeEditor (handles wizard internally) */}
              <div className="flex-1 overflow-auto">
                <RecipeEditor groupBy={reference.name} onSave={handleRecipeSave} />
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Modal footer */}
        <div className="px-6 py-4 border-t flex items-center justify-between shrink-0">
          <div className="text-sm text-muted-foreground">
            {activeTab === 'suggestions' && selectedSuggestions.size > 0 && (
              <span className="flex items-center gap-2">
                <Check className="h-4 w-4 text-primary" />
                {selectedSuggestions.size} widget(s) selectionne(s)
              </span>
            )}
            {activeTab === 'combined' && selectedFields.length > 0 && (
              <span className="flex items-center gap-2">
                <Link2 className="h-4 w-4 text-primary" />
                {selectedFields.length} champ(s) selectionne(s)
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            {activeTab === 'suggestions' && (
              <Button
                onClick={handleAddSuggestions}
                disabled={selectedSuggestions.size === 0 || isBusy}
              >
                {isBusy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                Ajouter {selectedSuggestions.size} widget(s)
              </Button>
            )}
            {activeTab === 'combined' && (
              <Button onClick={handleAddCombined} disabled={!selectedCombined || isBusy}>
                {isBusy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                Creer le widget combine
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
