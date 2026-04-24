/**
 * AddWidgetModal - Modal for adding new widgets
 *
 * Large modal (90vw × 85vh) with three tabs:
 * - Suggestions: Grid with iframe previews + right panel customization
 * - Combined: Semantic groups + manual field selection
 * - Custom: 4-step wizard with YAML preview
 */
import { useState, useCallback, useMemo, useEffect, useReducer, memo, startTransition, useDeferredValue } from 'react'
import { useTranslation } from 'react-i18next'
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
  FileSpreadsheet,
  GitBranch,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import type { WidgetRecipe } from '@/lib/api/recipes'
import {
  useCombinedWidgetSuggestions,
  useSemanticGroups,
  type SemanticGroup,
  type CombinedWidgetSuggestion,
} from '@/lib/api/widget-suggestions'
import type { ReferenceInfo } from '@/hooks/useReferences'
import { useDebouncedValue } from '@/shared/hooks/useDebouncedValue'
import { useQueryClient } from '@tanstack/react-query'
import { PreviewTile } from '@/components/preview'
import { PreviewPane } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { invalidateAllPreviews } from '@/lib/preview/usePreviewFrame'

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

// Type for dynamic quick edit fields from plugin schema
interface QuickEditField {
  name: string
  type: string
  title: string
  description?: string
  default?: unknown
  component?: string
  examples?: unknown[]
  help?: string
  minimum?: number
  maximum?: number
}

// Widget preview iframe component with scaling (like WidgetMiniature)
interface WidgetPreviewProps {
  templateId: string
  groupBy?: string
  source?: string
  disablePreview?: boolean
  className?: string
  width?: number
  height?: number
  // When provided, uses inline POST preview (same pipeline as configured widgets)
  transformerPlugin?: string
  transformerConfig?: Record<string, unknown>
  widgetPlugin?: string
  widgetParams?: Record<string, unknown> | null
  widgetTitle?: string
}


/**
 * Build a PreviewDescriptor from inline plugin config or template_id fallback.
 * Shared by WidgetPreview, LargePreview, and CombinedPreview.
 */
function buildInlineDescriptor(opts: {
  mode: PreviewDescriptor['mode']
  groupBy?: string
  templateId?: string
  source?: string
  transformerPlugin?: string
  transformerConfig?: Record<string, unknown>
  widgetPlugin?: string
  widgetParams?: Record<string, unknown> | null
  widgetTitle?: string
}): PreviewDescriptor {
  const { mode, groupBy, templateId, source, transformerPlugin, transformerConfig, widgetPlugin, widgetParams, widgetTitle } = opts
  // Use inline POST when we have the full config (avoids config reconstruction on server)
  if (transformerPlugin && transformerConfig && widgetPlugin) {
    return {
      groupBy,
      mode,
      inline: {
        transformer_plugin: transformerPlugin,
        transformer_params: transformerConfig,
        widget_plugin: widgetPlugin,
        widget_params: widgetParams ?? null,
        widget_title: widgetTitle || templateId || '',
      },
    }
  }
  // Fallback to GET by template_id (navigation, general_info, entity_map, etc.)
  return {
    templateId,
    groupBy,
    source: source && source !== 'occurrences' ? source : undefined,
    mode,
  }
}

const WidgetPreview = memo(function WidgetPreview({
  templateId,
  groupBy,
  source,
  disablePreview = false,
  className,
  width = 200,
  height = 96,
  transformerPlugin,
  transformerConfig,
  widgetPlugin,
  widgetParams,
  widgetTitle,
}: WidgetPreviewProps) {
  const descriptor: PreviewDescriptor = useMemo(() =>
    buildInlineDescriptor({ mode: 'thumbnail', groupBy, templateId, source, transformerPlugin, transformerConfig, widgetPlugin, widgetParams, widgetTitle }),
  [templateId, groupBy, source, transformerPlugin, transformerConfig, widgetPlugin, widgetParams, widgetTitle])

  return (
    <div
      className={cn('relative bg-muted/30 overflow-hidden', className)}
      style={{ width, height }}
    >
      {disablePreview ? (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/30">
          <Map className="h-4 w-4 text-muted-foreground/60" />
        </div>
      ) : (
        <PreviewTile descriptor={descriptor} width={width} height={height} />
      )}
    </div>
  )
})

// Large preview component for right panel (with scaling)
interface LargePreviewProps {
  templateId: string
  groupBy?: string
  source?: string
  disablePreview?: boolean
  transformerPlugin?: string
  transformerConfig?: Record<string, unknown>
  widgetPlugin?: string
  widgetParams?: Record<string, unknown> | null
  widgetTitle?: string
}

// Large preview dimensions
const LARGE_PREVIEW_WIDTH = 388  // Right panel width (420px) - padding
const LARGE_PREVIEW_HEIGHT = 291  // 4:3 ratio (388 * 3/4)

function getCombinedSuggestionKey(suggestion: CombinedWidgetSuggestion): string {
  return `${suggestion.pattern_type}:${suggestion.name}:${suggestion.fields.join('|')}`
}

function LargePreview({
  templateId,
  groupBy,
  source,
  disablePreview = false,
  transformerPlugin,
  transformerConfig,
  widgetPlugin,
  widgetParams,
  widgetTitle,
}: LargePreviewProps) {
  const queryClient = useQueryClient()

  const descriptor: PreviewDescriptor = useMemo(() =>
    buildInlineDescriptor({ mode: 'full', groupBy, templateId, source, transformerPlugin, transformerConfig, widgetPlugin, widgetParams, widgetTitle }),
  [templateId, groupBy, source, transformerPlugin, transformerConfig, widgetPlugin, widgetParams, widgetTitle])

  const handleRefresh = useCallback(() => {
    invalidateAllPreviews(queryClient)
  }, [queryClient])

  return (
    <div className="relative">
      <div
        className="bg-background border rounded-md overflow-hidden"
        style={{ width: LARGE_PREVIEW_WIDTH, height: LARGE_PREVIEW_HEIGHT }}
      >
        {disablePreview ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-background z-10">
            <Map className="h-8 w-8 text-muted-foreground/40 mb-2" />
            <span className="text-sm text-muted-foreground text-center px-4">
              Preview carte complète désactivée dans la modale
            </span>
          </div>
        ) : (
          <PreviewPane descriptor={descriptor} className="w-full h-full" />
        )}
      </div>
      {!disablePreview && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 right-2 h-7 w-7 bg-background/80 hover:bg-background z-20"
          onClick={handleRefresh}
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  )
}

// Combined widget preview via POST /api/templates/preview
interface CombinedPreviewProps {
  suggestion: CombinedWidgetSuggestion
  groupBy: string
}

// Combined preview dimensions (fits in 340px panel with p-4 padding)
const COMBINED_PREVIEW_WIDTH = 308
const COMBINED_PREVIEW_HEIGHT = 231  // 4:3 ratio

function CombinedPreview({ suggestion, groupBy }: CombinedPreviewProps) {
  const queryClient = useQueryClient()

  const descriptor: PreviewDescriptor = useMemo(() => {
    const tConfig = suggestion.transformer_config as Record<string, unknown>
    const wConfig = suggestion.widget_config as Record<string, unknown>
    return buildInlineDescriptor({
      mode: 'full',
      groupBy,
      transformerPlugin: tConfig.plugin as string,
      transformerConfig: (tConfig.params ?? {}) as Record<string, unknown>,
      widgetPlugin: wConfig.plugin as string,
      widgetParams: (wConfig.params ?? null) as Record<string, unknown> | null,
      widgetTitle: suggestion.name,
    })
  }, [suggestion, groupBy])

  const handleRefresh = useCallback(() => {
    invalidateAllPreviews(queryClient)
  }, [queryClient])

  return (
    <div className="relative">
      <div
        className="bg-background border rounded-md overflow-hidden"
        style={{ width: COMBINED_PREVIEW_WIDTH, height: COMBINED_PREVIEW_HEIGHT }}
      >
        <PreviewPane descriptor={descriptor} className="w-full h-full" />
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 h-7 w-7 bg-background/80 hover:bg-background z-20"
        onClick={handleRefresh}
      >
        <RefreshCw className="h-3.5 w-3.5" />
      </Button>
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
  [key: string]: unknown // Dynamic fields from plugin schema
}

// Cache for plugin schemas to avoid repeated fetches
const pluginSchemaCache: Record<string, QuickEditField[]> = {}

// Extract quick_edit fields from plugin JSON schema
function extractQuickEditFields(schema: Record<string, unknown>): QuickEditField[] {
  const fields: QuickEditField[] = []
  const defs = schema['$defs'] as Record<string, Record<string, unknown>> | undefined

  // Helper to extract fields from a properties object
  const extractFromProperties = (properties: Record<string, Record<string, unknown>>) => {
    for (const [name, prop] of Object.entries(properties)) {
      // Check for ui:quick_edit in the property
      if (prop['ui:quick_edit'] === true) {
        // Determine type - handle anyOf types (Optional fields)
        let type = 'string'
        const propType = prop.type
        const anyOf = prop.anyOf as Array<Record<string, unknown>> | undefined

        if (propType === 'number' || propType === 'integer') {
          type = 'number'
        } else if (propType === 'boolean') {
          type = 'boolean'
        } else if (propType === 'array') {
          type = 'array'
        } else if (anyOf) {
          // Handle Optional types like anyOf: [{type: 'string'}, {type: 'null'}]
          const nonNullType = anyOf.find(t => t.type !== 'null')
          if (nonNullType) {
            if (nonNullType.type === 'number' || nonNullType.type === 'integer') type = 'number'
            else if (nonNullType.type === 'boolean') type = 'boolean'
            else if (nonNullType.type === 'array') type = 'array'
          }
        }

        fields.push({
          name,
          type,
          title: (prop.title as string) || name,
          description: prop.description as string | undefined,
          default: prop.default,
          component: prop.ui_component as string | undefined,
          examples: prop.examples as unknown[] | undefined,
          help: (prop.ui_help || prop['ui:help']) as string | undefined,
          minimum: prop.minimum as number | undefined,
          maximum: prop.maximum as number | undefined,
        })
      }
    }
  }

  // First, check top-level properties
  const properties = schema.properties as Record<string, Record<string, unknown>> | undefined
  if (properties) {
    extractFromProperties(properties)
  }

  // Then, check $defs for nested schemas (like params.$ref -> ClassObjectSeriesParams)
  if (defs) {
    for (const defSchema of Object.values(defs)) {
      const defProperties = defSchema.properties as Record<string, Record<string, unknown>> | undefined
      if (defProperties) {
        extractFromProperties(defProperties)
      }
    }
  }

  return fields
}

// Convert a template suggestion to a widget recipe
function suggestionToRecipe(suggestion: TemplateSuggestion, customization?: Customization): WidgetRecipe {
  const config = suggestion.config as Record<string, unknown>
  const transformer = config.transformer as Record<string, unknown> || {}
  const widget = config.widget as Record<string, unknown> || {}
  const layout = widget.layout as Record<string, unknown> || {}

  // Extract transformer params from nested structure or directly from config
  const nestedParams = transformer.params as Record<string, unknown> || {}

  // Common transformer param fields that might be at top-level of config
  const knownTransformerParams = ['source', 'field', 'bins', 'labels', 'include_percentages',
    'stats', 'units', 'max_value', 'count', 'mode', 'fields', 'true_label', 'false_label',
    'categories', 'time_field', 'aggregation']

  // Extract params from config top-level (for suggestion templates)
  const configParams: Record<string, unknown> = {}
  for (const key of knownTransformerParams) {
    if (config[key] !== undefined) {
      configParams[key] = config[key]
    }
  }

  // Also include matched_column as 'field' if present
  if (suggestion.matched_column && !configParams.field) {
    configParams.field = suggestion.matched_column
  }

  // Process customization values (convert comma-separated strings to arrays for bins/labels)
  const customParams: Record<string, unknown> = {}
  if (customization) {
    for (const [key, value] of Object.entries(customization)) {
      if (key === 'title') continue // title is for widget, not transformer
      if (key === 'bins' && typeof value === 'string') {
        // Convert "0, 200, 400" string to number array
        customParams[key] = value.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))
      } else if (key === 'labels' && typeof value === 'string') {
        // Convert "Low, Medium, High" string to string array
        customParams[key] = value.split(',').map(s => s.trim()).filter(Boolean)
      } else {
        customParams[key] = value
      }
    }
  }

  // Merge params: nested > config > customization (later values override)
  const mergedTransformerParams = {
    ...configParams,
    ...nestedParams,
    ...customParams,
  }

  return {
    widget_id: suggestion.template_id,
    transformer: {
      plugin: transformer.plugin as string || suggestion.plugin,
      params: mergedTransformerParams,
    },
    widget: {
      plugin: widget.plugin as string || 'bar_plot',
      title: customization?.title || suggestion.name,
      params: widget.params as Record<string, unknown> || {},
      layout: {
        colspan: (layout.colspan as number) || 2,
        order: (layout.order as number) || 0,
      },
    },
  }
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
  const { t } = useTranslation(['widgets', 'common'])
  const [activeTab, setActiveTab] = useState(defaultTab)

  // Suggestions tab state
  const [selectedSuggestions, setSelectedSuggestions] = useState<string[]>([])
  const [focusedSuggestion, setFocusedSuggestion] = useState<string | null>(null)
  const [customizations, setCustomizations] = useState<Record<string, Customization>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set())
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [sourceFilter, setSourceFilter] = useState<string | null>(null)
  const [, refreshPluginSchemaCache] = useReducer((count: number) => count + 1, 0)

  // Combined tab state
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [selectedCombinedKey, setSelectedCombinedKey] = useState<string | null>(null)

  // Custom tab state
  const [wizardStep, setWizardStep] = useState(1)
  const [initialRecipe, setInitialRecipe] = useState<WidgetRecipe | undefined>(undefined)
  const queryClient = useQueryClient()

  // Hooks for generating and saving config
  const { generate: generateConfig, loading: generating } = useGenerateConfig()
  const { save: saveConfig, loading: saving } = useSaveConfig()

  // Semantic groups for combined widgets
  const { groups: semanticGroups } = useSemanticGroups(
    reference.name,
    'occurrences',
    activeTab === 'combined'
  )

  // Debounce des champs sélectionnés pour throttle les appels combined (300ms)
  const debouncedFields = useDebouncedValue(selectedFields, 300)

  // Combined widget suggestions — React Query auto-fetch quand debouncedFields >= 2
  const {
    suggestions: combinedSuggestions,
    loading: combinedLoading,
  } = useCombinedWidgetSuggestions(reference.name, debouncedFields, 'occurrences')

  // Get available fields from suggestions
  const visibleSuggestions = useMemo(
    () => suggestions,
    [suggestions]
  )

  const selectedSuggestionIds = useMemo(
    () => new Set(selectedSuggestions),
    [selectedSuggestions]
  )

  const selectedSuggestionOrder = useMemo(() => {
    const order = new globalThis.Map<string, number>()
    selectedSuggestions.forEach((id, index) => {
      order.set(id, index + 1)
    })
    return order
  }, [selectedSuggestions])

  // Get available fields from suggestions
  const availableFields = useMemo(() => {
    const fields = new Set<string>()
    visibleSuggestions.forEach((s) => {
      if (s.matched_column) fields.add(s.matched_column)
    })
    return Array.from(fields).sort()
  }, [visibleSuggestions])

  const selectedCombined = useMemo(() => {
    if (combinedSuggestions.length === 0) return null
    if (selectedCombinedKey) {
      const selected = combinedSuggestions.find(
        (suggestion) => getCombinedSuggestionKey(suggestion) === selectedCombinedKey,
      )
      if (selected) return selected
    }
    return combinedSuggestions.find((suggestion) => suggestion.is_recommended) ?? combinedSuggestions[0]
  }, [combinedSuggestions, selectedCombinedKey])

  const resetModalState = useCallback(() => {
    setActiveTab(defaultTab)
    setSelectedSuggestions([])
    setFocusedSuggestion(null)
    setCustomizations({})
    setSearchQuery('')
    setCollapsedSections(new Set())
    setExpandedGroups(new Set())
    setCategoryFilter(null)
    setSourceFilter(null)
    setInitialRecipe(undefined)
    setSelectedFields([])
    setSelectedCombinedKey(null)
    setWizardStep(1)
  }, [defaultTab])

  // Reset state when modal opens/closes
  useEffect(() => {
    if (open) {
      const frameId = window.requestAnimationFrame(resetModalState)
      return () => window.cancelAnimationFrame(frameId)
    } else {
      // Annuler les previews en attente quand la modale se ferme
      void queryClient.cancelQueries({ queryKey: ['preview'] })
    }
  }, [open, queryClient, resetModalState])

  // Defer right-panel preview updates so card selection feels instant.
  const deferredFocusedSuggestion = useDeferredValue(focusedSuggestion)
  const previewSuggestionId = deferredFocusedSuggestion || null
  const previewSuggestion = visibleSuggestions.find((s) => s.template_id === previewSuggestionId)
  const previewQuickEditFields = useMemo(() => {
    if (!previewSuggestion || !selectedSuggestionIds.has(previewSuggestion.template_id)) {
      return []
    }
    return pluginSchemaCache[previewSuggestion.plugin] || []
  }, [previewSuggestion, selectedSuggestionIds])
  // Fetch plugin schema when a suggestion is focused for quick edit
  useEffect(() => {
    if (!previewSuggestion || !selectedSuggestionIds.has(previewSuggestion.template_id)) {
      return
    }

    const pluginId = previewSuggestion.plugin

    // Check cache first
    if (pluginId in pluginSchemaCache) {
      return
    }

    const controller = new AbortController()
    let cancelled = false

    fetch(`/api/plugins/${pluginId}/schema`, { signal: controller.signal })
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return
        if (data.has_params && data.schema) {
          const fields = extractQuickEditFields(data.schema)
          pluginSchemaCache[pluginId] = fields
        } else {
          pluginSchemaCache[pluginId] = []
        }
        refreshPluginSchemaCache()
      })
      .catch((error: unknown) => {
        if (cancelled || (error instanceof DOMException && error.name === 'AbortError')) {
          return
        }
        pluginSchemaCache[pluginId] = []
        refreshPluginSchemaCache()
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [previewSuggestion, selectedSuggestionIds])

  // Group suggestions with smart ordering:
  // 1. Group widgets (navigation, info) - with group name
  // 2. Map widgets (cartography)
  // 3. Data visualizations grouped by field
  const groupedSuggestions = useMemo(() => {
    // Apply search filter
    let filtered = searchQuery
      ? visibleSuggestions.filter(
          (s) =>
            s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.matched_column?.toLowerCase().includes(searchQuery.toLowerCase())
        )
      : visibleSuggestions

    // Apply category filter
    if (categoryFilter) {
      filtered = filtered.filter((s) => s.category === categoryFilter)
    }

    // Apply source filter
    if (sourceFilter) {
      filtered = filtered.filter((s) => s.source_name === sourceFilter)
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
        label: t('modal.cartography'),
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
  }, [visibleSuggestions, searchQuery, categoryFilter, sourceFilter, reference.name, t])

  // Get all unique categories for filter chips
  const availableCategories = useMemo(() => {
    const cats = new Set<string>()
    visibleSuggestions.forEach((s) => cats.add(s.category))
    return Array.from(cats)
  }, [visibleSuggestions])

  // Get all unique sources for filter chips
  const availableSources = useMemo(() => {
    const sourcesMap: Record<string, { name: string; type: string }> = {}
    visibleSuggestions.forEach((s) => {
      if (s.source_name && !sourcesMap[s.source_name]) {
        sourcesMap[s.source_name] = { name: s.source_name, type: s.source || 'auto' }
      }
    })
    return Object.values(sourcesMap)
  }, [visibleSuggestions])

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
      const suggestion = visibleSuggestions.find((s) => s.template_id === id)
      return {
        title: suggestion?.name || '',
      }
    },
    [customizations, visibleSuggestions]
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
    startTransition(() => {
      setFocusedSuggestion((current) => current === id ? current : id)
    })
    setSelectedSuggestions((prev) => {
      if (prev.includes(id)) {
        return prev.filter((s) => s !== id)
      }
      return [...prev, id]
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
    setSelectedCombinedKey(null)
  }, [])

  // Handle semantic group click
  const handleSemanticGroupClick = useCallback((group: SemanticGroup) => {
    setSelectedFields(group.fields)
    setSelectedCombinedKey(null)
  }, [])

  // Handle adding suggestion widgets
  const handleAddSuggestions = useCallback(async () => {
    if (selectedSuggestions.length === 0) return

    const templates = selectedSuggestions
      .map((id) => {
        const suggestion = visibleSuggestions.find((s) => s.template_id === id)
        if (!suggestion) return null
        const customization = getCustomization(id)

        // Extract dynamic customization fields (all except title)
        const { title, ...dynamicFields } = customization

        // Process array fields (convert comma-separated strings to arrays)
        const processedFields: Record<string, unknown> = {}
        for (const [key, value] of Object.entries(dynamicFields)) {
          if (typeof value === 'string' && value.includes(',')) {
            // Try to parse as array of numbers
            const parts = value.split(',').map((s) => s.trim())
            const numbers = parts.map((p) => parseFloat(p))
            if (numbers.every((n) => !isNaN(n))) {
              processedFields[key] = numbers
            } else {
              processedFields[key] = parts
            }
          } else if (value !== undefined) {
            processedFields[key] = value
          }
        }

        return {
          template_id: suggestion.template_id,
          plugin: suggestion.plugin,
          config: {
            ...suggestion.config,
            ...processedFields,
            title: title || suggestion.name,
          },
          widget_plugin: suggestion.widget_plugin,
          widget_params: suggestion.widget_params,
        }
      })
      .filter(Boolean) as Array<{
      template_id: string
      plugin: string
      config: Record<string, unknown>
      widget_plugin?: string
      widget_params?: Record<string, unknown>
    }>

    const result = await generateConfig(templates, reference.name, reference.kind)
    if (result) {
      // Use 'merge' mode to add widgets to existing config instead of replacing
      await saveConfig(result, 'merge')
      onWidgetAdded()
    }
  }, [selectedSuggestions, visibleSuggestions, getCustomization, generateConfig, saveConfig, reference, onWidgetAdded])

  // Handle adding a combined widget (via generateConfig + saveConfig like suggestions)
  const handleAddCombined = useCallback(async () => {
    if (!selectedCombined) return

    const widgetId = `combined_${selectedCombined.pattern_type}_${Date.now()}`

    const templates = [{
      template_id: widgetId,
      plugin: selectedCombined.transformer_config.plugin as string,
      config: {
        ...(selectedCombined.transformer_config.params as Record<string, unknown>),
        title: selectedCombined.name,
      },
    }]

    const result = await generateConfig(templates, reference.name, reference.kind)
    if (result) {
      // Inject export override so save-config uses the correct widget plugin & params
      const widgetConfig = selectedCombined.widget_config as Record<string, unknown>
      const widgetData = result.widgets_data[widgetId] as Record<string, unknown> | undefined
      if (widgetData) {
        widgetData.export_override = {
          plugin: widgetConfig.plugin,
          title: selectedCombined.name,
          params: widgetConfig.params,
        }
      }
      await saveConfig(result, 'merge')
      onWidgetAdded()
    }
  }, [selectedCombined, reference, generateConfig, saveConfig, onWidgetAdded])

  // Handle recipe editor save
  const handleRecipeSave = useCallback(() => {
    onWidgetAdded()
  }, [onWidgetAdded])

  const isBusy = generating || saving
  const showSchemaLoader =
    !!previewSuggestion &&
    !(previewSuggestion.plugin in pluginSchemaCache) &&
    selectedSuggestionIds.has(previewSuggestion.template_id)

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        onOpenChange(isOpen)
        if (!isOpen) {
          setFocusedSuggestion((current) => current === null ? current : null)
        }
      }}
    >
      <DialogContent className="!max-w-[90vw] w-[1200px] h-[85vh] flex flex-col p-0">
        <DialogHeader className="px-6 py-4 border-b shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            {t('actions.addWidget')}
          </DialogTitle>
          <DialogDescription className="sr-only">
            Ajouter un ou plusieurs widgets a partir des suggestions, des combinaisons
            ou d&apos;une configuration personnalisee.
          </DialogDescription>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) =>
            setActiveTab((current) => current === v ? current : v as typeof activeTab)
          }
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
                  {visibleSuggestions.length}
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
                <p className="mt-3 text-sm text-muted-foreground">{t('analysis.analyzing')}</p>
              </div>
            ) : visibleSuggestions.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full">
                <Sparkles className="h-12 w-12 text-muted-foreground/50" />
                <h3 className="mt-4 font-medium">{t('gallery.noWidgets')}</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {t('analysis.importForSuggestions')}
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
                          placeholder={t('common:placeholders.search')}
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
                        title={collapsedSections.size === groupedSuggestions.length ? t('common:aria.expandAll') : t('common:aria.collapseAll')}
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
                        {t('gallery.selectAll')}
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
                          navigation: t('categories.navigation'),
                          info: t('categories.info'),
                          map: t('categories.map'),
                          chart: t('categories.chart'),
                          gauge: t('categories.gauge'),
                          donut: t('categories.donut'),
                          table: t('categories.table'),
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

                    {/* Source filter chips */}
                    {availableSources.length > 1 && (
                      <div className="flex flex-wrap gap-1.5 items-center">
                        <span className="text-xs text-muted-foreground mr-1">{t('modal.filterBySource')}:</span>
                        <Button
                          variant={sourceFilter === null ? 'secondary' : 'ghost'}
                          size="sm"
                          className="h-6 text-[11px] px-2"
                          onClick={() => setSourceFilter(null)}
                        >
                          {t('gallery.allSources')}
                        </Button>
                        {availableSources.map((source) => {
                          const SourceIcon = source.type === 'class_object'
                            ? FileSpreadsheet
                            : source.name === reference.name
                              ? GitBranch
                              : Database
                          return (
                            <Button
                              key={source.name}
                              variant={sourceFilter === source.name ? 'secondary' : 'ghost'}
                              size="sm"
                              className="h-6 text-[11px] px-2"
                              onClick={() => setSourceFilter(sourceFilter === source.name ? null : source.name)}
                            >
                              <SourceIcon className="h-3 w-3 mr-1" />
                              {source.name}
                            </Button>
                          )
                        })}
                      </div>
                    )}

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
                            <div key={group.key} className="border rounded-md overflow-hidden">
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
                              {!isCollapsed && (() => {
                                const VISIBLE_LIMIT = 6
                                const isExpanded = expandedGroups.has(group.key)
                                const visible = isExpanded
                                  ? group.suggestions
                                  : group.suggestions.slice(0, VISIBLE_LIMIT)
                                const hiddenCount = group.suggestions.length - VISIBLE_LIMIT

                                return (
                                <div className="p-2 border-t bg-background">
                                  <div className="grid grid-cols-2 gap-2">
                                    {visible.map((suggestion, suggestionIdx) => {
                                      const Icon = CATEGORY_ICONS[suggestion.category] || BarChart3
                                      const isSelected = selectedSuggestionIds.has(suggestion.template_id)
                                      const isFocused = focusedSuggestion === suggestion.template_id

                                      return (
                                        <div
                                          key={`${suggestion.template_id}-${suggestionIdx}`}
                                          className={cn(
                                            'flex border rounded-md overflow-hidden cursor-pointer transition-all hover:shadow-sm group',
                                            isSelected && isFocused
                                              ? 'border-primary ring-2 ring-primary/20'
                                              : isSelected
                                                ? 'border-primary/50 bg-primary/5'
                                                : 'hover:border-muted-foreground/30'
                                          )}
                                          onClick={() => toggleSuggestion(suggestion.template_id)}
                                        >
                                          {/* Preview area - left side (4:3 ratio) */}
                                          <div className="relative shrink-0">
                                            {isSelected && (
                                              <div className="absolute top-1 left-1 z-10 bg-primary text-primary-foreground rounded-full w-5 h-5 flex items-center justify-center text-[10px] font-bold">
                                                {selectedSuggestionOrder.get(suggestion.template_id)}
                                              </div>
                                            )}
                                            <WidgetPreview
                                              templateId={suggestion.template_id}
                                              groupBy={reference.name}
                                              source={suggestion.source_name}
                                              transformerPlugin={suggestion.widget_plugin ? suggestion.plugin : undefined}
                                              transformerConfig={suggestion.widget_plugin ? suggestion.config as Record<string, unknown> : undefined}
                                              widgetPlugin={suggestion.widget_plugin}
                                              widgetParams={suggestion.widget_params}
                                              widgetTitle={suggestion.name}
                                              width={100}
                                              height={75}
                                            />
                                          </div>
                                          {/* Info - right side */}
                                          <div className="flex-1 min-w-0 px-2.5 py-1.5 flex flex-col justify-center">
                                            <div className="flex items-center gap-1.5 mb-1">
                                              <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                                              <span className="font-medium text-xs truncate">
                                                {suggestion.name}
                                              </span>
                                            </div>
                                            <div className="flex items-center gap-1 flex-wrap">
                                              <Badge variant="outline" className="text-[9px] h-4 px-1.5">
                                                {suggestion.plugin}
                                              </Badge>
                                              {suggestion.source_name && (
                                                <Badge variant="secondary" className="text-[9px] h-4 px-1.5">
                                                  {suggestion.source === 'class_object' ? (
                                                    <FileSpreadsheet className="h-2.5 w-2.5 mr-0.5" />
                                                  ) : suggestion.source_name === reference.name ? (
                                                    <GitBranch className="h-2.5 w-2.5 mr-0.5" />
                                                  ) : (
                                                    <Database className="h-2.5 w-2.5 mr-0.5" />
                                                  )}
                                                  {suggestion.source_name}
                                                </Badge>
                                              )}
                                            </div>
                                          </div>
                                          {/* Checkbox - right edge */}
                                          <div className="shrink-0 flex items-center pr-2">
                                            <Checkbox
                                              checked={isSelected}
                                              className="h-4 w-4"
                                              onClick={(e) => e.stopPropagation()}
                                              onPointerDown={(e) => e.stopPropagation()}
                                              onCheckedChange={() => toggleSuggestion(suggestion.template_id)}
                                            />
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                  {hiddenCount > 0 && !isExpanded && (
                                    <button
                                      className="w-full mt-2 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                                      onClick={() => setExpandedGroups(prev => {
                                        const next = new Set(prev)
                                        next.add(group.key)
                                        return next
                                      })}
                                    >
                                      +{hiddenCount} more...
                                    </button>
                                  )}
                                </div>
                                )
                              })()}
                            </div>
                          )
                        })}
                      </div>
                    </ScrollArea>
                  </div>
                </div>

                {/* Right column - Preview & Customization */}
                <div className="w-[420px] flex flex-col bg-muted/20 shrink-0 min-h-0 overflow-hidden">
                  {previewSuggestion ? (
                    <ScrollArea className="flex-1 h-full">
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
                          {selectedSuggestionIds.has(previewSuggestion.template_id) && (
                            <Badge variant="outline" className="text-xs">
                              <Check className="h-3 w-3 mr-1" />
                              {t('common:status.selected')}
                            </Badge>
                          )}
                        </div>

                        {/* Large preview with iframe */}
                        <LargePreview
                          templateId={previewSuggestion.template_id}
                          groupBy={reference.name}
                          source={previewSuggestion.source_name}
                          transformerPlugin={previewSuggestion.widget_plugin ? previewSuggestion.plugin : undefined}
                          transformerConfig={previewSuggestion.widget_plugin ? previewSuggestion.config as Record<string, unknown> : undefined}
                          widgetPlugin={previewSuggestion.widget_plugin}
                          widgetParams={previewSuggestion.widget_params}
                          widgetTitle={previewSuggestion.name}
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
                        {selectedSuggestionIds.has(previewSuggestion.template_id) ? (
                          <div>
                            <div className="flex items-center gap-2 mb-3">
                              <Settings2 className="h-4 w-4 text-muted-foreground" />
                              <span className="font-medium text-sm">{t('modal.quickCustomization')}</span>
                              {showSchemaLoader && (
                                <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                              )}
                            </div>

                            <div className="space-y-3">
                              {/* Title - always shown */}
                              <div>
                                <label className="text-xs text-muted-foreground">{t('modal.title')}</label>
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

                              {/* Dynamic fields from plugin schema */}
                              {previewQuickEditFields.map((field) => (
                                <div key={field.name}>
                                  <label className="text-xs text-muted-foreground flex items-center gap-1">
                                    {field.title}
                                    {field.help && (
                                      <span
                                        className="text-[10px] text-muted-foreground/70 cursor-help"
                                        title={field.help}
                                      >
                                        (?)
                                      </span>
                                    )}
                                  </label>
                                  {field.type === 'number' ? (
                                    <Input
                                      type="number"
                                      value={
                                        (getCustomization(previewSuggestion.template_id)[
                                          field.name
                                        ] as number) ??
                                        (previewSuggestion.config as Record<string, unknown>)?.[
                                          field.name
                                        ] ??
                                        field.default ??
                                        ''
                                      }
                                      min={field.minimum}
                                      max={field.maximum}
                                      onChange={(e) =>
                                        updateCustomization(previewSuggestion.template_id, {
                                          [field.name]: e.target.value
                                            ? parseFloat(e.target.value)
                                            : undefined,
                                        })
                                      }
                                      className="h-8 mt-1"
                                      placeholder={
                                        field.examples
                                          ? `ex: ${field.examples.slice(0, 2).join(', ')}`
                                          : undefined
                                      }
                                    />
                                  ) : field.type === 'array' && field.component === 'array_number' ? (
                                    <Input
                                      value={
                                        (getCustomization(previewSuggestion.template_id)[
                                          field.name
                                        ] as string) ??
                                        (
                                          (previewSuggestion.config as Record<string, unknown>)?.[
                                            field.name
                                          ] as number[]
                                        )?.join(', ') ??
                                        (field.default as number[])?.join(', ') ??
                                        ''
                                      }
                                      onChange={(e) =>
                                        updateCustomization(previewSuggestion.template_id, {
                                          [field.name]: e.target.value,
                                        })
                                      }
                                      className="h-8 mt-1 font-mono text-xs"
                                      placeholder={
                                        field.examples && Array.isArray(field.examples[0])
                                          ? `ex: ${(field.examples[0] as number[]).join(', ')}`
                                          : 'ex: 0, 100, 200, 500'
                                      }
                                    />
                                  ) : (
                                    <Input
                                      value={
                                        (getCustomization(previewSuggestion.template_id)[
                                          field.name
                                        ] as string) ??
                                        ((previewSuggestion.config as Record<string, unknown>)?.[
                                          field.name
                                        ] as string) ??
                                        (field.default as string) ??
                                        ''
                                      }
                                      onChange={(e) =>
                                        updateCustomization(previewSuggestion.template_id, {
                                          [field.name]: e.target.value,
                                        })
                                      }
                                      className="h-8 mt-1"
                                      placeholder={
                                        field.examples
                                          ? `ex: ${field.examples.slice(0, 2).join(', ')}`
                                          : undefined
                                      }
                                    />
                                  )}
                                  {field.description && (
                                    <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                                      {field.description}
                                    </p>
                                  )}
                                </div>
                              ))}

                              {/* Message when no quick edit fields */}
                              {!showSchemaLoader && previewQuickEditFields.length === 0 && (
                                <p className="text-xs text-muted-foreground/70 italic">
                                  {t('modal.advancedEditHint')}
                                </p>
                              )}
                            </div>

                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full mt-4"
                              onClick={() => {
                                // Pre-fill the recipe editor with current suggestion
                                const customization = customizations[previewSuggestion.template_id]
                                const recipe = suggestionToRecipe(previewSuggestion, customization)
                                setInitialRecipe(recipe)
                                setActiveTab('custom')
                                setWizardStep(1)
                              }}
                            >
                              <Wand2 className="h-4 w-4 mr-2" />
                              {t('modal.advancedEdit')}
                              <ChevronRight className="h-4 w-4 ml-auto" />
                            </Button>
                          </div>
                        ) : (
                          <div className="text-center py-4">
                            <Info className="h-8 w-8 text-muted-foreground/50 mx-auto mb-2" />
                            <p className="text-sm text-muted-foreground">
                              {t('modal.clickToSelectAndCustomize')}
                            </p>
                          </div>
                        )}
                      </div>
                    </ScrollArea>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
                      <Eye className="h-12 w-12 text-muted-foreground/30 mb-3" />
                      <p className="font-medium text-muted-foreground">{t('preview.widgetPreview')}</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {t('preview.selectToPreview')}
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
                        <h3 className="font-medium">{t('modal.autoDetectedPatterns')}</h3>
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
                                  {t('gallery.fieldsCount', { count: group.fields.length })}
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
                      <h3 className="font-medium">{t('modal.manualCombine')}</h3>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      {t('selection.selectFields')}
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
                            <h4 className="text-sm font-medium mb-3">{t('modal.proposedWidgets')}</h4>
                            {combinedSuggestions.map((suggestion, idx) => {
                              const isSelected = selectedCombined === suggestion
                              return (
                                <button
                                  key={idx}
                                  onClick={() => setSelectedCombinedKey(getCombinedSuggestionKey(suggestion))}
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
                                        {t('modal.recommended')}
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
                            {t('selection.noCombination')}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </ScrollArea>

              {/* Right column - Preview */}
              <div className="w-[340px] bg-muted/20 flex flex-col items-center justify-center text-center p-4 shrink-0 overflow-hidden">
                {selectedCombined ? (
                  <div className="w-full">
                    <h4 className="font-medium mb-1 text-sm">{selectedCombined.name}</h4>
                    <p className="text-xs text-muted-foreground mb-3">{selectedCombined.description}</p>
                    <CombinedPreview suggestion={selectedCombined} groupBy={reference.name} />
                    <div className="flex flex-wrap gap-1 justify-center mt-4">
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
                    <p className="font-medium text-muted-foreground">{t('preview.combinedPreview')}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {t('config.selectPreview')}
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
                <h3 className="font-medium mb-4 text-sm">{t('modal.creationSteps')}</h3>
                <div className="space-y-2">
                  {[
                    { step: 1, label: t('modal.stepIdentifier'), desc: t('modal.stepIdentifierDesc') },
                    { step: 2, label: t('modal.stepSource'), desc: t('modal.stepSourceDesc') },
                    { step: 3, label: t('modal.stepTransform'), desc: t('modal.stepTransformDesc') },
                    { step: 4, label: t('modal.stepDisplay'), desc: t('modal.stepDisplayDesc') },
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
                <RecipeEditor groupBy={reference.name} onSave={handleRecipeSave} initialRecipe={initialRecipe} />
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Modal footer */}
        <div className="px-6 py-4 border-t flex items-center justify-between shrink-0">
          <div className="text-sm text-muted-foreground">
            {activeTab === 'suggestions' && selectedSuggestions.length > 0 && (
              <span className="flex items-center gap-2">
                <Check className="h-4 w-4 text-primary" />
                {t('selection.fieldsSelected', { count: selectedSuggestions.length })}
              </span>
            )}
            {activeTab === 'combined' && selectedFields.length > 0 && (
              <span className="flex items-center gap-2">
                <Link2 className="h-4 w-4 text-primary" />
                {t('selection.fieldsSelected', { count: selectedFields.length })}
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {t('common:actions.cancel')}
            </Button>
            {activeTab === 'suggestions' && (
              <Button
                onClick={handleAddSuggestions}
                disabled={selectedSuggestions.length === 0 || isBusy}
              >
                {isBusy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                {t('selection.addWidgets', { count: selectedSuggestions.length })}
              </Button>
            )}
            {activeTab === 'combined' && (
              <Button onClick={handleAddCombined} disabled={!selectedCombined || isBusy}>
                {isBusy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                {t('combined.createWidget')}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
