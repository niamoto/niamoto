import { useState, useCallback, useMemo, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import * as yaml from 'js-yaml'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import {
  Code2,
  Wand2,
  Save,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Database,
  FileSpreadsheet,
  Eye,
  Columns,
  Play,
  RefreshCw,
  Plus,
  Lock,
  Check,
} from 'lucide-react'

import { YamlEditor, type YamlTemplate } from './YamlEditor'
import { FieldAggregatorBuilder, type FieldConfig } from './FieldAggregatorBuilder'
import { ColorMapEditor } from './ColorMapEditor'
import { JsonKeyValueEditor } from './JsonKeyValueEditor'
import { NumberArrayInput } from './NumberArrayInput'
import { TransformParamsEditor } from './TransformParamsEditor'
import {
  useAvailableSources,
  useTransformers,
  useWidgets,
  useTransformerSchema,
  useWidgetSchema,
  useSaveRecipe,
  useRecipeValidation,
  useRecipePreview,
  type WidgetRecipe,
  type SaveRecipeRequest,
  type SourceInfo,
  type ParamSchema,
} from '@/lib/api/recipes'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'

interface RecipeEditorProps {
  groupBy: string
  onSave?: () => void
  initialRecipe?: WidgetRecipe
}

// Default templates for quick start
const DEFAULT_TEMPLATES: YamlTemplate[] = [
  {
    id: 'bar_chart',
    label: 'Bar Chart',
    description: 'Histogramme avec categories_extractor',
    content: `widget_id: my_bar_chart
transformer:
  plugin: class_object_categories_extractor
  params:
    source: stats_source
    class_object: my_class_object
widget:
  plugin: bar_plot
  title: My Bar Chart
  params:
    orientation: h
  layout:
    colspan: 1
    order: 0
`,
  },
  {
    id: 'donut',
    label: 'Donut',
    description: 'Graphique binaire',
    content: `widget_id: my_donut
transformer:
  plugin: class_object_binary_aggregator
  params:
    source: stats_source
    class_object: my_binary_field
    true_label: "Oui"
    false_label: "Non"
widget:
  plugin: donut_chart
  title: My Donut
  params:
    labels_field: labels
    values_field: counts
  layout:
    colspan: 1
    order: 0
`,
  },
  {
    id: 'top_ranking',
    label: 'Top 10',
    description: 'Classement occurrences',
    content: `widget_id: my_top_ranking
transformer:
  plugin: top_ranking
  params:
    source: occurrences
    field: category_field
    mode: direct
    count: 10
widget:
  plugin: bar_plot
  title: Top 10
  params:
    orientation: h
    x_axis: counts
    y_axis: tops
    sort_order: ascending
  layout:
    colspan: 1
    order: 0
`,
  },
  {
    id: 'stats',
    label: 'Statistiques',
    description: 'Min/Max/Moyenne',
    content: `widget_id: my_stats
transformer:
  plugin: statistical_summary
  params:
    source: occurrences
    field: numeric_field
    stats:
      - min
      - max
      - mean
    units: cm
widget:
  plugin: radial_gauge
  title: Statistiques
  params:
    stat_to_display: mean
    show_range: true
  layout:
    colspan: 1
    order: 0
`,
  },
]

// Transformer descriptions
const TRANSFORMER_INFO: Record<string, { label: string; description: string; icon: string }> = {
  field_aggregator: { label: 'Agregateur de champs', description: 'Regroupe plusieurs colonnes', icon: 'columns' },
  geospatial_extractor: { label: 'Extracteur geo', description: 'Coordonnees GeoJSON', icon: 'map' },
  top_ranking: { label: 'Top N', description: 'Classement des N premiers', icon: 'trophy' },
  binary_counter: { label: 'Compteur binaire', description: 'Compte oui/non', icon: 'toggle' },
  binned_distribution: { label: 'Distribution', description: 'Histogramme par classes', icon: 'bar-chart' },
  statistical_summary: { label: 'Statistiques', description: 'Min/Max/Moyenne/etc', icon: 'calculator' },
  categorical_distribution: { label: 'Categories', description: 'Distribution par categorie', icon: 'pie-chart' },
  time_series_analysis: { label: 'Series temporelles', description: 'Analyse dans le temps', icon: 'clock' },
  class_object_field_aggregator: { label: 'Agregateur scalaires', description: 'Regroupe des metriques', icon: 'columns' },
  class_object_binary_aggregator: { label: 'Agregateur binaire', description: 'Ratio 2 categories', icon: 'pie-chart' },
  class_object_series_extractor: { label: 'Extracteur series', description: 'Serie numerique', icon: 'line-chart' },
  class_object_categories_extractor: { label: 'Extracteur categories', description: 'Multi-categories', icon: 'bar-chart' },
  class_object_series_ratio_aggregator: { label: 'Ratios series', description: 'Compare distributions', icon: 'chart' },
  class_object_categories_mapper: { label: 'Mapper categories', description: 'Compare groupes', icon: 'git-compare' },
  class_object_series_matrix_extractor: { label: 'Matrice series', description: 'Grille de valeurs', icon: 'grid' },
  class_object_series_by_axis_extractor: { label: 'Series par axe', description: 'Plusieurs series', icon: 'chart' },
}

// Widget labels/descriptions are now fetched dynamically from the API via useWidgets()

// Group labels for widget params
const PARAM_GROUP_LABELS: Record<string, string> = {
  '1_transform': 'Transformation des donnees',
  '2_data': 'Mapping des donnees',
  '3_layout': 'Disposition',
  '4_colors': 'Couleurs',
  '5_display': 'Affichage',
  '6_general': 'General',
}

// Helper function to organize params by groups
function organizeParamsByGroups(
  params: Record<string, ParamSchema>
): Array<{ group: string; label: string; params: Array<[string, ParamSchema]> }> {
  // Group params
  const grouped: Record<string, Array<[string, ParamSchema]>> = {}
  const ungrouped: Array<[string, ParamSchema]> = []

  for (const [key, param] of Object.entries(params)) {
    if (param.ui_group) {
      if (!grouped[param.ui_group]) {
        grouped[param.ui_group] = []
      }
      grouped[param.ui_group].push([key, param])
    } else {
      ungrouped.push([key, param])
    }
  }

  // Sort params within each group by ui_order
  for (const group of Object.values(grouped)) {
    group.sort((a, b) => (a[1].ui_order ?? 999) - (b[1].ui_order ?? 999))
  }

  // Sort groups by key (e.g., "1_transform" before "2_data")
  const sortedGroups = Object.entries(grouped)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([group, params]) => ({
      group,
      label: PARAM_GROUP_LABELS[group] || group.replace(/^\d+_/, '').replace(/_/g, ' '),
      params,
    }))

  // Add ungrouped params at the end if any
  if (ungrouped.length > 0) {
    sortedGroups.push({
      group: 'other',
      label: 'Autres parametres',
      params: ungrouped,
    })
  }

  return sortedGroups
}

// Wizard steps definition
const WIZARD_STEPS = [
  { id: 'identity', label: 'Identifiant', icon: Database },
  { id: 'source', label: 'Source', icon: FileSpreadsheet },
  { id: 'transform', label: 'Transformation', icon: Columns },
  { id: 'display', label: 'Affichage', icon: Eye },
] as const

// Simple Stepper component
function WizardStepper({
  completedSteps,
  currentStep,
  onStepClick
}: {
  completedSteps: boolean[]
  currentStep: number
  onStepClick: (index: number) => void
}) {
  return (
    <div className="flex items-center gap-1 px-4 py-3 bg-muted/30 border-b">
      {WIZARD_STEPS.map((step, index) => {
        const isCompleted = completedSteps[index]
        const isCurrent = index === currentStep
        const isAccessible = index === 0 || completedSteps[index - 1]

        return (
          <div key={step.id} className="flex items-center flex-1">
            <button
              onClick={() => isAccessible && onStepClick(index)}
              disabled={!isAccessible}
              className={`
                flex items-center gap-2 px-3 py-2 rounded-lg transition-all text-sm
                ${isCurrent ? 'bg-primary text-primary-foreground' : ''}
                ${isCompleted && !isCurrent ? 'text-primary' : ''}
                ${!isAccessible ? 'opacity-40 cursor-not-allowed' : 'hover:bg-muted cursor-pointer'}
              `}
            >
              <div className={`
                w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium
                ${isCurrent ? 'bg-primary-foreground text-primary' : ''}
                ${isCompleted && !isCurrent ? 'bg-primary/20' : 'bg-muted'}
              `}>
                {isCompleted ? (
                  <Check className="h-3 w-3" />
                ) : !isAccessible ? (
                  <Lock className="h-3 w-3" />
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>
              <span className="hidden sm:inline">{step.label}</span>
            </button>
            {index < WIZARD_STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 ${completedSteps[index] ? 'bg-primary' : 'bg-border'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

export function RecipeEditor({ groupBy, onSave, initialRecipe }: RecipeEditorProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const [activeTab, setActiveTab] = useState<'expert' | 'wizard'>('wizard')
  const [yamlContent, setYamlContent] = useState(() => {
    if (initialRecipe) {
      return yaml.dump(initialRecipe, { indent: 2 })
    }
    return DEFAULT_TEMPLATES[0].content
  })
  const [isValidYaml, setIsValidYaml] = useState(true)
  const [parsedRecipe, setParsedRecipe] = useState<WidgetRecipe | null>(null)

  // Wizard state
  const [widgetId, setWidgetId] = useState('')
  const [selectedSource, setSelectedSource] = useState<SourceInfo | null>(null)
  const [selectedTransformer, setSelectedTransformer] = useState('')
  const [transformerParams, setTransformerParams] = useState<Record<string, unknown>>({})
  const [selectedWidget, setSelectedWidget] = useState('')
  const [widgetParams, setWidgetParams] = useState<Record<string, unknown>>({})
  const [widgetTitle, setWidgetTitle] = useState('')
  const [colspan, setColspan] = useState(1)
  const [order, setOrder] = useState(0)

  // Stepper state
  const [currentStep, setCurrentStep] = useState(0)

  // API hooks
  const { sources, loading: sourcesLoading } = useAvailableSources(groupBy)
  const { transformers } = useTransformers()
  const { widgets } = useWidgets()
  const { schema: transformerSchema, loading: schemaLoading } = useTransformerSchema(selectedTransformer || null)
  const { schema: widgetSchema, loading: widgetSchemaLoading } = useWidgetSchema(selectedWidget || null)
  const { save, saving } = useSaveRecipe()
  const { validate, validation, validating } = useRecipeValidation()
  const { preview, previewUrl, loading: previewLoading, error: previewError } = useRecipePreview()

  // Check if transformer required params are filled
  const transformerParamsComplete = useMemo(() => {
    if (!selectedTransformer || !transformerSchema) return false

    // Check all required params (except 'source' which is auto-filled)
    for (const [key, param] of Object.entries(transformerSchema.params)) {
      if (key === 'source') continue
      if (param.required) {
        const value = transformerParams[key]
        if (value === undefined || value === null || value === '') {
          return false
        }
        // For objects (like fields), check if not empty
        if (param.type === 'object' && typeof value === 'object') {
          if (Object.keys(value as object).length === 0) return false
        }
        // For arrays, check if not empty
        if (param.type === 'array' && Array.isArray(value)) {
          if (value.length === 0) return false
        }
      }
    }
    return true
  }, [selectedTransformer, transformerSchema, transformerParams])

  // Calculate completed steps (cumulative - each step requires previous to be complete)
  const completedSteps = useMemo(() => {
    const step1 = !!widgetId.trim()
    const step2 = step1 && !!selectedSource
    const step3 = step2 && !!selectedTransformer && transformerParamsComplete
    const step4 = step3 && !!selectedWidget
    return [step1, step2, step3, step4]
  }, [widgetId, selectedSource, selectedTransformer, transformerParamsComplete, selectedWidget])

  // Auto-advance to next incomplete step
  useEffect(() => {
    if (completedSteps[currentStep] && currentStep < WIZARD_STEPS.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStep(prev => Math.min(prev + 1, WIZARD_STEPS.length - 1))
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [completedSteps, currentStep])

  // Load initial recipe into wizard state (most fields)
  useEffect(() => {
    if (initialRecipe) {
      setWidgetId(initialRecipe.widget_id || '')
      setSelectedTransformer(initialRecipe.transformer?.plugin || '')
      setTransformerParams(initialRecipe.transformer?.params || {})
      setSelectedWidget(initialRecipe.widget?.plugin || '')
      setWidgetParams(initialRecipe.widget?.params || {})
      setWidgetTitle(initialRecipe.widget?.title || '')
      setColspan(initialRecipe.widget?.layout?.colspan ?? 1)
      setOrder(initialRecipe.widget?.layout?.order ?? 0)
    }
  }, [initialRecipe])

  // Set source when sources become available
  useEffect(() => {
    if (initialRecipe && sources && sources.length > 0) {
      const sourceName = initialRecipe.transformer?.params?.source as string
      if (sourceName) {
        const source = sources.find(s => s.name === sourceName)
        if (source) {
          setSelectedSource(source)
        }
      }
    }
  }, [initialRecipe, sources])

  // Preview panel state
  const [previewTab, setPreviewTab] = useState<'yaml' | 'widget'>('yaml')

  // Build recipe from wizard
  const wizardRecipe = useMemo((): WidgetRecipe => {
    // Determine if transformer needs a source param from its schema
    // Only add source if the transformer declares it in its params
    const needsSourceParam = transformerSchema?.params?.source !== undefined

    return {
      widget_id: widgetId || 'new_widget',
      transformer: {
        plugin: selectedTransformer,
        params: {
          ...(needsSourceParam && { source: selectedSource?.name || '' }),
          ...transformerParams,
        },
      },
      widget: {
        plugin: selectedWidget,
        title: widgetTitle || widgetId.replace(/_/g, ' '),
        params: widgetParams,
        layout: { colspan, order },
      },
    }
  }, [widgetId, selectedSource, selectedTransformer, transformerSchema, transformerParams, selectedWidget, widgetParams, widgetTitle, colspan, order])

  // Live YAML from wizard
  const wizardYaml = useMemo(() => {
    if (!selectedTransformer) return ''
    return yaml.dump(wizardRecipe, { indent: 2 })
  }, [wizardRecipe, selectedTransformer])

  // Handle YAML validation
  const handleYamlValidChange = useCallback((parsed: unknown, valid: boolean) => {
    setIsValidYaml(valid)
    if (valid && parsed && typeof parsed === 'object') {
      setParsedRecipe(parsed as WidgetRecipe)
    } else {
      setParsedRecipe(null)
    }
  }, [])

  // Load recipe into wizard state
  const loadRecipeIntoWizard = useCallback((recipe: WidgetRecipe) => {
    setWidgetId(recipe.widget_id || '')
    setSelectedTransformer(recipe.transformer?.plugin || '')
    setTransformerParams(recipe.transformer?.params || {})
    setSelectedWidget(recipe.widget?.plugin || '')
    setWidgetParams(recipe.widget?.params || {})
    setWidgetTitle(recipe.widget?.title || '')
    setColspan(recipe.widget?.layout?.colspan ?? 1)
    setOrder(recipe.widget?.layout?.order ?? 0)

    // Try to find and select source from transformer params
    const sourceName = recipe.transformer?.params?.source as string
    if (sourceName && sources) {
      const source = sources.find(s => s.name === sourceName)
      if (source) {
        setSelectedSource(source)
      }
    }
  }, [sources])

  // Handle tab change with synchronization
  const handleTabChange = useCallback((newTab: string) => {
    const tab = newTab as 'expert' | 'wizard'

    if (activeTab === 'wizard' && tab === 'expert') {
      // Sync wizard -> expert: copy wizardYaml to yamlContent
      if (wizardYaml) {
        setYamlContent(wizardYaml)
      }
    } else if (activeTab === 'expert' && tab === 'wizard') {
      // Sync expert -> wizard: parse yamlContent and load into wizard
      try {
        const parsed = yaml.load(yamlContent) as WidgetRecipe
        if (parsed && typeof parsed === 'object') {
          loadRecipeIntoWizard(parsed)
        }
      } catch {
        // Invalid YAML, keep current wizard state
      }
    }

    setActiveTab(tab)
  }, [activeTab, wizardYaml, yamlContent, loadRecipeIntoWizard])

  // Get transformers for selected source type
  const availableTransformers = useMemo(() => {
    if (!selectedSource) return transformers
    return selectedSource.transformers.filter(t => transformers.includes(t))
  }, [selectedSource, transformers])

  // Auto-select suggested widget when transformer changes
  useEffect(() => {
    if (selectedTransformer) {
      const suggestions: Record<string, string> = {
        top_ranking: 'bar_plot',
        binned_distribution: 'bar_plot',
        statistical_summary: 'radial_gauge',
        field_aggregator: 'info_grid',
        geospatial_extractor: 'interactive_map',
        binary_counter: 'donut_chart',
        class_object_binary_aggregator: 'donut_chart',
        class_object_categories_extractor: 'bar_plot',
        class_object_series_extractor: 'bar_plot',
        class_object_field_aggregator: 'info_grid',
      }
      const suggested = suggestions[selectedTransformer]
      if (suggested && widgets.some(w => w.name === suggested)) {
        setSelectedWidget(suggested)
      }
    }
  }, [selectedTransformer, widgets])

  // Handle save
  const handleSave = useCallback(async () => {
    let recipe: WidgetRecipe | null = null

    if (activeTab === 'expert') {
      if (!isValidYaml || !parsedRecipe) {
        toast.error('Le YAML contient des erreurs')
        return
      }
      recipe = parsedRecipe
    } else {
      if (!widgetId || !selectedTransformer || !selectedWidget) {
        toast.error('Veuillez remplir tous les champs obligatoires')
        return
      }
      recipe = wizardRecipe
    }

    const request: SaveRecipeRequest = { group_by: groupBy, recipe }
    const validationResult = await validate(request)

    if (!validationResult?.valid) {
      const errors = validationResult?.errors.map((e) => e.message).join(', ')
      toast.error(`Validation echouee: ${errors}`)
      return
    }

    const result = await save(request)
    if (result?.success) {
      toast.success(`Widget "${recipe.widget_id}" ajoute`)
      onSave?.()
    } else {
      toast.error(t('widgets:form.saveError'))
    }
  }, [activeTab, isValidYaml, parsedRecipe, widgetId, selectedTransformer, selectedWidget, wizardRecipe, groupBy, validate, save, onSave])

  // Update transformer param
  const updateTransformerParam = useCallback((key: string, value: unknown) => {
    setTransformerParams(prev => ({ ...prev, [key]: value }))
  }, [])

  // Update widget param
  const updateWidgetParam = useCallback((key: string, value: unknown) => {
    setWidgetParams(prev => ({ ...prev, [key]: value }))
  }, [])

  // Handle preview
  const handlePreview = useCallback(async () => {
    if (!selectedTransformer || !selectedWidget) {
      toast.error('Selectionnez un transformer et un widget')
      return
    }

    const request: SaveRecipeRequest = { group_by: groupBy, recipe: wizardRecipe }
    await preview(request)
    setPreviewTab('widget')
  }, [groupBy, wizardRecipe, selectedTransformer, selectedWidget, preview])

  // Check if all steps are complete
  const allStepsComplete = completedSteps.every(Boolean)
  const canPreview = !!(widgetId && selectedSource && selectedTransformer && selectedWidget)

  return (
    <div className="flex h-full flex-col min-h-0 overflow-hidden">
      <Tabs value={activeTab} onValueChange={handleTabChange} className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30 shrink-0">
          <TabsList className="bg-background">
            <TabsTrigger value="wizard" className="gap-2">
              <Wand2 className="h-4 w-4" />
              Assistant
            </TabsTrigger>
            <TabsTrigger value="expert" className="gap-2">
              <Code2 className="h-4 w-4" />
              YAML
            </TabsTrigger>
          </TabsList>

          <Button
            onClick={handleSave}
            disabled={saving || validating || (activeTab === 'wizard' && !allStepsComplete)}
            size="sm"
            className="gap-2"
          >
            {saving || validating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : activeTab === 'wizard' ? (
              <Plus className="h-4 w-4" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {activeTab === 'wizard' ? t('widgets:actions.addWidget') : t('common:actions.save')}
          </Button>
        </div>

        {/* Expert Mode */}
        <TabsContent value="expert" className="flex-1 p-4 m-0 overflow-auto">
          <div className="max-w-4xl mx-auto space-y-4">
            <div className="text-sm text-muted-foreground">
              Editez directement la configuration YAML. Les templates permettent de demarrer rapidement.
            </div>

            <YamlEditor
              value={yamlContent}
              onChange={setYamlContent}
              onValidChange={handleYamlValidChange}
              height="500px"
              templates={DEFAULT_TEMPLATES}
            />

            {validation && !validation.valid && (
              <div className="bg-red-50 dark:bg-red-950/30 p-3 rounded-md">
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-medium mb-2">
                  <AlertTriangle className="h-4 w-4" />
                  Erreurs de validation
                </div>
                <ul className="text-sm list-disc list-inside">
                  {validation.errors.map((e, i) => (
                    <li key={i}>{e.field}: {e.message}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Wizard Mode */}
        <TabsContent value="wizard" className="flex-1 m-0 min-h-0 overflow-hidden">
          <div className="h-full flex flex-col min-h-0">
            {/* Stepper */}
            <WizardStepper
              completedSteps={completedSteps}
              currentStep={currentStep}
              onStepClick={setCurrentStep}
            />

            <div className="flex-1 flex min-h-0">
              {/* Left: Configuration */}
              <div className="flex-1 flex flex-col min-h-0 border-r overflow-hidden">
                <ScrollArea className="flex-1 min-h-0">
                  <div className="p-4 space-y-6">
                    {/* Step 1: Widget ID */}
                    <div
                      className={`space-y-2 p-4 rounded-lg border-2 transition-all cursor-pointer ${
                        currentStep === 0 ? 'border-primary bg-primary/5' : 'border-transparent hover:bg-muted/50'
                      }`}
                      onClick={() => setCurrentStep(0)}
                    >
                      <Label className="text-sm font-medium flex items-center gap-2">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          completedSteps[0] ? 'bg-primary text-primary-foreground' : 'bg-primary/10 text-primary'
                        }`}>
                          {completedSteps[0] ? <Check className="h-3 w-3" /> : '1'}
                        </span>
                        Identifiant du widget *
                      </Label>
                      <Input
                        value={widgetId}
                        onChange={(e) => setWidgetId(e.target.value.replace(/\s+/g, '_').toLowerCase())}
                        placeholder="mon_widget"
                        className="font-mono"
                      />
                      {!widgetId && (
                        <p className="text-xs text-muted-foreground">
                          Donnez un identifiant unique (ex: distribution_altitude)
                        </p>
                      )}
                    </div>

                    <Separator />

                    {/* Step 2: Source Selection */}
                    <div
                      className={`space-y-3 p-4 rounded-lg border-2 transition-all ${
                        currentStep === 1 ? 'border-primary bg-primary/5' : 'border-transparent'
                      } ${!completedSteps[0] ? 'opacity-50 pointer-events-none' : 'cursor-pointer hover:bg-muted/50'}`}
                      onClick={() => completedSteps[0] && setCurrentStep(1)}
                    >
                      <Label className="text-sm font-medium flex items-center gap-2">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          completedSteps[1] ? 'bg-primary text-primary-foreground' : 'bg-primary/10 text-primary'
                        }`}>
                          {completedSteps[1] ? <Check className="h-3 w-3" /> : '2'}
                        </span>
                        <Database className="h-4 w-4" />
                        Source de donnees *
                        {!completedSteps[0] && <Lock className="h-3 w-3 ml-auto text-muted-foreground" />}
                      </Label>

                      {sourcesLoading ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {t('recipe.loadingSources')}
                        </div>
                      ) : sources.length === 0 ? (
                        <div className="text-sm text-muted-foreground p-3 bg-muted rounded-md">
                          {t('recipe.noSourcesConfigured')}
                        </div>
                      ) : (
                        <div className="grid gap-2">
                          {sources.map((source) => (
                            <button
                              key={source.name || source.type}
                              onClick={(e) => {
                                e.stopPropagation()
                                setSelectedSource(source)
                              }}
                              className={`flex items-center gap-3 p-3 rounded-lg border text-left transition-colors ${
                                selectedSource?.name === source.name
                                  ? 'border-primary bg-primary/5'
                                  : 'hover:bg-muted'
                              }`}
                            >
                              {source.type === 'reference' ? (
                                <Database className="h-5 w-5 text-blue-500" />
                              ) : source.type === 'dataset' ? (
                                <Database className="h-5 w-5 text-green-500" />
                              ) : (
                                <FileSpreadsheet className="h-5 w-5 text-orange-500" />
                              )}
                              <div className="flex-1 min-w-0">
                                <div className="font-medium">{source.name}</div>
                                <div className="text-xs text-muted-foreground truncate">
                                  {source.type} - {source.columns.length} {t('recipe.columns')}
                                </div>
                              </div>
                              {selectedSource?.name === source.name && (
                                <CheckCircle2 className="h-5 w-5 text-primary" />
                              )}
                            </button>
                          ))}
                        </div>
                      )}

                      {selectedSource && (
                        <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
                          <span className="font-medium">Colonnes:</span>{' '}
                          {selectedSource.columns.slice(0, 8).join(', ')}
                          {selectedSource.columns.length > 8 && ` +${selectedSource.columns.length - 8} autres`}
                        </div>
                      )}
                    </div>

                    <Separator />

                    {/* Step 3: Transformer Selection */}
                    <div
                      className={`space-y-3 p-4 rounded-lg border-2 transition-all ${
                        currentStep === 2 ? 'border-primary bg-primary/5' : 'border-transparent'
                      } ${!completedSteps[1] ? 'opacity-50 pointer-events-none' : 'cursor-pointer hover:bg-muted/50'}`}
                      onClick={() => completedSteps[1] && setCurrentStep(2)}
                    >
                      <Label className="text-sm font-medium flex items-center gap-2">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          completedSteps[2] ? 'bg-primary text-primary-foreground' : 'bg-primary/10 text-primary'
                        }`}>
                          {completedSteps[2] ? <Check className="h-3 w-3" /> : '3'}
                        </span>
                        <Columns className="h-4 w-4" />
                        Transformation *
                        {!completedSteps[1] && <Lock className="h-3 w-3 ml-auto text-muted-foreground" />}
                      </Label>

                      <Select value={selectedTransformer} onValueChange={setSelectedTransformer}>
                        <SelectTrigger onClick={(e) => e.stopPropagation()}>
                          <SelectValue placeholder={t('recipe.selectTransformer')} />
                        </SelectTrigger>
                        <SelectContent>
                          {availableTransformers.map((t) => {
                            const info = TRANSFORMER_INFO[t]
                            return (
                              <SelectItem key={t} value={t}>
                                <div className="flex flex-col">
                                  <span>{info?.label || t}</span>
                                  {info?.description && (
                                    <span className="text-xs text-muted-foreground">{info.description}</span>
                                  )}
                                </div>
                              </SelectItem>
                            )
                          })}
                        </SelectContent>
                      </Select>

                      {/* Transformer params */}
                      {selectedTransformer && transformerSchema && (
                        <Card className="bg-muted/30" onClick={(e) => e.stopPropagation()}>
                          <CardHeader className="py-3 px-4">
                            <CardTitle className="text-sm">Parametres du transformer</CardTitle>
                          </CardHeader>
                          <CardContent className="py-3 px-4 space-y-3">
                            {Object.entries(transformerSchema.params).map(([key, param]) => {
                              if (key === 'source') return null

                              if (param.ui_condition) {
                                if (param.ui_condition.includes('!fields') && transformerParams.fields && Object.keys(transformerParams.fields as object).length > 0) {
                                  return null
                                }
                                if (param.ui_condition.includes('!field') && transformerParams.field) {
                                  return null
                                }
                              }

                              const isFieldSelector = param.ui_widget === 'field-select' ||
                                key === 'field' ||
                                key.endsWith('_field') ||
                                key === 'time_field'

                              // Special case: field_aggregator's fields param
                              if (selectedTransformer === 'field_aggregator' && key === 'fields') {
                                return (
                                  <div key={key} className="space-y-1">
                                    <Label className="text-xs">
                                      {key} {param.required && <span className="text-red-500">*</span>}
                                    </Label>
                                    <FieldAggregatorBuilder
                                      groupBy={groupBy}
                                      sources={sources}
                                      value={(transformerParams.fields as FieldConfig[]) || []}
                                      onChange={(fields) => updateTransformerParam('fields', fields)}
                                    />
                                  </div>
                                )
                              }

                              return (
                                <div key={key} className="space-y-1">
                                  <Label className="text-xs">
                                    {key} {param.required && <span className="text-red-500">*</span>}
                                  </Label>

                                  {param.enum ? (
                                    <Select
                                      value={String(transformerParams[key] || param.default || '')}
                                      onValueChange={(v) => updateTransformerParam(key, v)}
                                    >
                                      <SelectTrigger className="h-8">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {param.enum.map((opt) => (
                                          <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  ) : isFieldSelector && selectedSource ? (
                                    <Select
                                      value={String(transformerParams[key] || '')}
                                      onValueChange={(v) => updateTransformerParam(key, v)}
                                    >
                                      <SelectTrigger className="h-8">
                                        <SelectValue placeholder={t('recipe.selectColumn')} />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {selectedSource.columns.map((col) => (
                                          <SelectItem key={col} value={col}>{col}</SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  ) : param.type === 'integer' || param.type === 'number' ? (
                                    <Input
                                      type="number"
                                      className="h-8"
                                      value={String(transformerParams[key] ?? param.default ?? '')}
                                      onChange={(e) => updateTransformerParam(key, parseInt(e.target.value) || 0)}
                                    />
                                  ) : param.type === 'boolean' ? (
                                    <div className="flex items-center gap-2">
                                      <input
                                        type="checkbox"
                                        className="h-4 w-4"
                                        checked={Boolean(transformerParams[key] ?? param.default)}
                                        onChange={(e) => updateTransformerParam(key, e.target.checked)}
                                      />
                                      <span className="text-xs text-muted-foreground">{param.description}</span>
                                    </div>
                                  ) : param.type === 'array' && param.items_type === 'string' ? (
                                    <Input
                                      className="h-8"
                                      value={Array.isArray(transformerParams[key])
                                        ? (transformerParams[key] as string[]).join(', ')
                                        : Array.isArray(param.default)
                                          ? (param.default as string[]).join(', ')
                                          : ''}
                                      onChange={(e) => {
                                        const values = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                                        updateTransformerParam(key, values)
                                      }}
                                      placeholder={t('recipe.commaSeparatedValues')}
                                    />
                                  ) : param.type === 'array' && param.items_type === 'number' ? (
                                    <Input
                                      className="h-8"
                                      value={Array.isArray(transformerParams[key])
                                        ? (transformerParams[key] as number[]).join(', ')
                                        : Array.isArray(param.default)
                                          ? (param.default as number[]).join(', ')
                                          : ''}
                                      onChange={(e) => {
                                        const values = e.target.value.split(',')
                                          .map(s => s.trim())
                                          .filter(Boolean)
                                          .map(s => parseFloat(s))
                                          .filter(n => !isNaN(n))
                                        updateTransformerParam(key, values)
                                      }}
                                      placeholder="ex: 0, 100, 500, 1000"
                                    />
                                  ) : param.type === 'object' && param.additional_properties_type === 'string' ? (
                                    <div className="space-y-2 p-2 bg-background rounded border">
                                      {Object.entries((transformerParams[key] as Record<string, string>) || {}).map(([k, v], idx) => (
                                        <div key={idx} className="flex gap-2 items-center">
                                          <Input
                                            className="h-7 flex-1"
                                            placeholder={t('recipe.label')}
                                            value={k}
                                            onChange={(e) => {
                                              const current = (transformerParams[key] as Record<string, string>) || {}
                                              const entries = Object.entries(current)
                                              entries[idx] = [e.target.value, v]
                                              updateTransformerParam(key, Object.fromEntries(entries))
                                            }}
                                          />
                                          <span className="text-xs text-muted-foreground">→</span>
                                          {selectedSource ? (
                                            <Select
                                              value={v}
                                              onValueChange={(newVal) => {
                                                const current = (transformerParams[key] as Record<string, string>) || {}
                                                updateTransformerParam(key, { ...current, [k]: newVal })
                                              }}
                                            >
                                              <SelectTrigger className="h-7 flex-1">
                                                <SelectValue placeholder="Colonne" />
                                              </SelectTrigger>
                                              <SelectContent>
                                                {selectedSource.columns.map((col) => (
                                                  <SelectItem key={col} value={col}>{col}</SelectItem>
                                                ))}
                                              </SelectContent>
                                            </Select>
                                          ) : (
                                            <Input
                                              className="h-7 flex-1"
                                              placeholder="Colonne"
                                              value={v}
                                              onChange={(e) => {
                                                const current = (transformerParams[key] as Record<string, string>) || {}
                                                updateTransformerParam(key, { ...current, [k]: e.target.value })
                                              }}
                                            />
                                          )}
                                          <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-7 w-7 p-0"
                                            onClick={() => {
                                              const current = (transformerParams[key] as Record<string, string>) || {}
                                              const { [k]: _, ...rest } = current
                                              updateTransformerParam(key, rest)
                                            }}
                                          >
                                            ×
                                          </Button>
                                        </div>
                                      ))}
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-7 text-xs w-full"
                                        onClick={() => {
                                          const current = (transformerParams[key] as Record<string, string>) || {}
                                          const newKey = `champ${Object.keys(current).length + 1}`
                                          updateTransformerParam(key, { ...current, [newKey]: '' })
                                        }}
                                      >
                                        + Ajouter un champ
                                      </Button>
                                    </div>
                                  ) : (
                                    <Input
                                      className="h-8"
                                      value={String(transformerParams[key] ?? param.default ?? '')}
                                      onChange={(e) => updateTransformerParam(key, e.target.value)}
                                      placeholder={param.description}
                                    />
                                  )}

                                  {param.description && param.type !== 'boolean' && (
                                    <p className="text-[10px] text-muted-foreground">{param.description}</p>
                                  )}
                                </div>
                              )
                            })}
                            {schemaLoading && (
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Loader2 className="h-3 w-3 animate-spin" />
                                Chargement du schema...
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      )}
                    </div>

                    <Separator />

                    {/* Step 4: Widget Selection */}
                    <div
                      className={`space-y-3 p-4 rounded-lg border-2 transition-all ${
                        currentStep === 3 ? 'border-primary bg-primary/5' : 'border-transparent'
                      } ${!completedSteps[2] ? 'opacity-50 pointer-events-none' : 'cursor-pointer hover:bg-muted/50'}`}
                      onClick={() => completedSteps[2] && setCurrentStep(3)}
                    >
                      <Label className="text-sm font-medium flex items-center gap-2">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          completedSteps[3] ? 'bg-primary text-primary-foreground' : 'bg-primary/10 text-primary'
                        }`}>
                          {completedSteps[3] ? <Check className="h-3 w-3" /> : '4'}
                        </span>
                        <Eye className="h-4 w-4" />
                        Affichage *
                        {!completedSteps[2] && <Lock className="h-3 w-3 ml-auto text-muted-foreground" />}
                      </Label>

                      <Select value={selectedWidget} onValueChange={setSelectedWidget}>
                        <SelectTrigger onClick={(e) => e.stopPropagation()}>
                          <SelectValue placeholder={t('recipe.selectWidget')} />
                        </SelectTrigger>
                        <SelectContent>
                          {widgets.map((w) => (
                            <SelectItem key={w.name} value={w.name}>
                              <div className="flex flex-col">
                                <span>{w.label}</span>
                                <span className="text-xs text-muted-foreground">{w.description}</span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                        <Label className="text-xs">Titre du widget</Label>
                        <Input
                          value={widgetTitle}
                          onChange={(e) => setWidgetTitle(e.target.value)}
                          placeholder={widgetId.replace(/_/g, ' ') || t('widgets:form.autoTitle')}
                          className="h-8"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-3" onClick={(e) => e.stopPropagation()}>
                        <div className="space-y-1">
                          <Label className="text-xs">Largeur</Label>
                          <Select value={String(colspan)} onValueChange={(v) => setColspan(parseInt(v))}>
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="1">1 colonne</SelectItem>
                              <SelectItem value="2">2 colonnes</SelectItem>
                              <SelectItem value="3">3 colonnes</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Ordre</Label>
                          <Input
                            type="number"
                            className="h-8"
                            value={order}
                            onChange={(e) => setOrder(parseInt(e.target.value) || 0)}
                          />
                        </div>
                      </div>

                      {/* Widget Parameters - Grouped */}
                      {selectedWidget && widgetSchema && Object.keys(widgetSchema.params).length > 0 && (
                        <div className="space-y-3" onClick={(e) => e.stopPropagation()}>
                          {organizeParamsByGroups(widgetSchema.params).map((group) => (
                            <Card key={group.group} className="bg-muted/30">
                              <CardHeader className="py-2 px-4">
                                <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                                  {group.label}
                                  {widgetSchemaLoading && group.group === '1_transform' && (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  )}
                                </CardTitle>
                              </CardHeader>
                              <CardContent className="py-2 px-4 space-y-3">
                                {group.params.map(([key, param]) => (
                              <div key={key} className="space-y-1">
                                <Label className="text-xs">
                                  {key.replace(/_/g, ' ')}
                                  {param.required && <span className="text-red-500">*</span>}
                                </Label>

                                {param.ui_widget === 'select' && param.ui_options ? (
                                  <Select
                                    value={String(widgetParams[key] ?? param.default ?? '')}
                                    onValueChange={(v) => updateWidgetParam(key, v)}
                                  >
                                    <SelectTrigger className="h-8">
                                      <SelectValue placeholder={t('recipe.select')} />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {param.ui_options.map((opt) => {
                                        const value = typeof opt === 'string' ? opt : opt.value
                                        const label = typeof opt === 'string' ? opt : opt.label
                                        return (
                                          <SelectItem key={value} value={value}>{label}</SelectItem>
                                        )
                                      })}
                                    </SelectContent>
                                  </Select>
                                ) : param.enum ? (
                                  <Select
                                    value={String(widgetParams[key] ?? param.default ?? '')}
                                    onValueChange={(v) => updateWidgetParam(key, v)}
                                  >
                                    <SelectTrigger className="h-8">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {param.enum.map((opt) => (
                                        <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                ) : param.ui_widget === 'checkbox' || param.type === 'boolean' ? (
                                  <div className="flex items-center gap-2">
                                    <Switch
                                      checked={Boolean(widgetParams[key] ?? param.default)}
                                      onCheckedChange={(checked) => updateWidgetParam(key, checked)}
                                    />
                                    <span className="text-xs text-muted-foreground">{param.description}</span>
                                  </div>
                                ) : param.ui_widget === 'color' ? (
                                  <div className="flex gap-2">
                                    <Input
                                      type="color"
                                      className="h-8 w-12 p-1"
                                      value={String(widgetParams[key] ?? param.default ?? '#1fb99d')}
                                      onChange={(e) => updateWidgetParam(key, e.target.value)}
                                    />
                                    <Input
                                      className="h-8 flex-1"
                                      value={String(widgetParams[key] ?? param.default ?? '')}
                                      onChange={(e) => updateWidgetParam(key, e.target.value)}
                                      placeholder="#RRGGBB"
                                    />
                                  </div>
                                ) : param.ui_widget === 'number' && param.ui_min !== undefined && param.ui_max !== undefined ? (
                                  <div className="flex gap-3 items-center">
                                    <Slider
                                      className="flex-1"
                                      value={[Number(widgetParams[key] ?? param.default ?? param.ui_min)]}
                                      min={param.ui_min}
                                      max={param.ui_max}
                                      step={param.ui_step ?? 0.1}
                                      onValueChange={([v]) => updateWidgetParam(key, v)}
                                    />
                                    <span className="text-xs w-10 text-right">
                                      {Number(widgetParams[key] ?? param.default ?? param.ui_min).toFixed(1)}
                                    </span>
                                  </div>
                                ) : param.type === 'integer' || param.type === 'number' ? (
                                  <Input
                                    type="number"
                                    className="h-8"
                                    value={String(widgetParams[key] ?? param.default ?? '')}
                                    onChange={(e) => updateWidgetParam(key, e.target.value ? Number(e.target.value) : undefined)}
                                    step={param.ui_step}
                                    min={param.ui_min}
                                    max={param.ui_max}
                                  />
                                ) : param.type === 'array' && (param.ui_item_widget === 'number' || param.items_type === 'number') ? (
                                  <NumberArrayInput
                                    value={widgetParams[key] as number[] | undefined}
                                    onChange={(v) => updateWidgetParam(key, v)}
                                    placeholder="ex: 0, 100"
                                  />
                                ) : key === 'color_discrete_map' ? (
                                  <ColorMapEditor
                                    value={widgetParams[key] as Record<string, string> | undefined}
                                    onChange={(v) => updateWidgetParam(key, v)}
                                    placeholder={t('recipe.addColorsForSeries')}
                                  />
                                ) : key === 'labels' ? (
                                  <JsonKeyValueEditor
                                    value={widgetParams[key] as Record<string, string> | undefined}
                                    onChange={(v) => updateWidgetParam(key, v)}
                                    keyPlaceholder={t('recipe.field')}
                                    valuePlaceholder={t('recipe.labelDisplayed')}
                                    suggestedKeys={['x_axis', 'y_axis', 'color_field']}
                                    placeholder={t('recipe.labelsForAxesLegends')}
                                  />
                                ) : key === 'transform_params' && param.ui_transform_schemas ? (
                                  <TransformParamsEditor
                                    selectedTransform={widgetParams['transform'] as string | undefined}
                                    transformSchemas={param.ui_transform_schemas}
                                    value={widgetParams[key] as Record<string, unknown> | undefined}
                                    onChange={(v) => updateWidgetParam(key, v)}
                                  />
                                ) : param.ui_widget === 'json' ? (
                                  <JsonKeyValueEditor
                                    value={widgetParams[key] as Record<string, string> | undefined}
                                    onChange={(v) => updateWidgetParam(key, v)}
                                    placeholder={param.description}
                                  />
                                ) : (
                                  <Input
                                    className="h-8"
                                    value={String(widgetParams[key] ?? param.default ?? '')}
                                    onChange={(e) => updateWidgetParam(key, e.target.value || undefined)}
                                    placeholder={param.description}
                                  />
                                )}

                                {param.description && param.type !== 'boolean' && param.ui_widget !== 'checkbox' && (
                                  <p className="text-[10px] text-muted-foreground">{param.description}</p>
                                )}
                              </div>
                                ))}
                              </CardContent>
                            </Card>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </ScrollArea>
              </div>

              {/* Right: Live Preview */}
              <div className="w-96 flex flex-col min-h-0 bg-muted/20 overflow-hidden">
                {/* Preview header with tabs */}
                <div className="p-2 border-b bg-background shrink-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex gap-1">
                      <Button
                        variant={previewTab === 'yaml' ? 'default' : 'ghost'}
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => setPreviewTab('yaml')}
                      >
                        <Code2 className="h-3 w-3 mr-1" />
                        YAML
                      </Button>
                      <Button
                        variant={previewTab === 'widget' ? 'default' : 'ghost'}
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => setPreviewTab('widget')}
                      >
                        <Eye className="h-3 w-3 mr-1" />
                        Widget
                      </Button>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={handlePreview}
                      disabled={!canPreview || previewLoading}
                    >
                      {previewLoading ? (
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      ) : previewUrl ? (
                        <RefreshCw className="h-3 w-3 mr-1" />
                      ) : (
                        <Play className="h-3 w-3 mr-1" />
                      )}
                      {previewUrl ? 'Actualiser' : 'Apercu'}
                    </Button>
                  </div>
                </div>

                {/* Preview content */}
                <div className="flex-1 min-h-0 overflow-hidden">
                  {previewTab === 'yaml' ? (
                    <ScrollArea className="h-full">
                      <div className="p-3">
                        {selectedTransformer ? (
                          <pre className="text-xs font-mono bg-background p-3 rounded border overflow-x-auto whitespace-pre-wrap">
                            {wizardYaml}
                          </pre>
                        ) : (
                          <div className="text-sm text-muted-foreground text-center py-8">
                            Selectionnez une source et un transformer pour voir la configuration generee.
                          </div>
                        )}
                      </div>
                    </ScrollArea>
                  ) : (
                    <div className="h-full p-3">
                      {previewLoading ? (
                        <div className="h-full flex flex-col items-center justify-center">
                          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                          <span className="text-sm text-muted-foreground mt-2">Chargement...</span>
                        </div>
                      ) : previewError ? (
                        <div className="h-full flex flex-col items-center justify-center text-center p-4">
                          <AlertTriangle className="h-8 w-8 text-amber-500 mb-2" />
                          <span className="text-sm text-muted-foreground">{previewError}</span>
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-3"
                            onClick={handlePreview}
                          >
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Reessayer
                          </Button>
                        </div>
                      ) : previewUrl ? (
                        <div className="h-full rounded-lg border bg-background overflow-hidden">
                          <iframe
                            src={previewUrl}
                            className="w-full h-full border-0"
                            title="Widget Preview"
                          />
                        </div>
                      ) : (
                        <div className="h-full flex flex-col items-center justify-center text-center p-4">
                          <Eye className="h-10 w-10 text-muted-foreground/50 mb-3" />
                          <span className="text-sm text-muted-foreground">
                            {canPreview
                              ? 'Cliquez sur "Apercu" pour voir le widget'
                              : 'Completez la configuration pour activer l\'apercu'}
                          </span>
                          {canPreview && (
                            <Button
                              variant="default"
                              size="sm"
                              className="mt-3"
                              onClick={handlePreview}
                            >
                              <Play className="h-4 w-4 mr-2" />
                              Generer l'apercu
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Validation status */}
                {selectedTransformer && (
                  <div className="p-3 border-t bg-background shrink-0">
                    <div className="flex items-center gap-2 text-xs">
                      {allStepsComplete ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          <span className="text-green-600">Pret a ajouter</span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="h-4 w-4 text-amber-500" />
                          <span className="text-amber-600">Champs obligatoires manquants</span>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
