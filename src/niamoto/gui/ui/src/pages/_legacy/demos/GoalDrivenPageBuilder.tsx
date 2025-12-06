import { useState, useEffect } from 'react'
import { Responsive, WidthProvider, type Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import { DemoWrapper } from '@/components/demos/DemoWrapper'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  LayoutGrid,
  Map,
  BarChart3,
  PieChart,
  Gauge,
  Table2,
  Grid3x3,
  Activity,
  TrendingUp,
  Trash2,
  Eye,
  EyeOff,
  Download,
  Sparkles,
  Plus,
  Settings2,
  Layers,
  Database,
  CheckCircle2,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { useGoalDrivenStore, type WidgetType } from '@/stores/goalDrivenStore'
import { WidgetPreview } from '@/components/goal-driven/WidgetPreviews'
import { listEntities, getEntityDetail, type EntitySummary, type EntityDetail } from '@/lib/api/entities'

const ResponsiveGridLayout = WidthProvider(Responsive)

const widgetLibrary: {
  type: WidgetType
  name: string
  description: string
  icon: any
  color: string
  category: string
}[] = [
  {
    type: 'interactive_map',
    name: 'Carte Interactive',
    description: 'Carte avec points géolocalisés',
    icon: Map,
    color: 'text-emerald-500',
    category: 'Géospatial'
  },
  {
    type: 'info_cards',
    name: 'Cartes d\'Info',
    description: 'Cartes avec statistiques clés',
    icon: Grid3x3,
    color: 'text-blue-500',
    category: 'Info'
  },
  {
    type: 'horizontal_bar_chart',
    name: 'Barres Horizontales',
    description: 'Graphique à barres horizontales',
    icon: BarChart3,
    color: 'text-green-500',
    category: 'Graphiques'
  },
  {
    type: 'histogram',
    name: 'Histogramme',
    description: 'Distribution par classes',
    icon: Activity,
    color: 'text-amber-500',
    category: 'Graphiques'
  },
  {
    type: 'vertical_bar_chart',
    name: 'Barres Verticales',
    description: 'Graphique à barres verticales',
    icon: BarChart3,
    color: 'text-blue-500',
    category: 'Graphiques'
  },
  {
    type: 'pie_chart',
    name: 'Camembert',
    description: 'Graphique en secteurs',
    icon: PieChart,
    color: 'text-purple-500',
    category: 'Graphiques'
  },
  {
    type: 'donut_chart',
    name: 'Donut',
    description: 'Graphique en anneau',
    icon: PieChart,
    color: 'text-orange-500',
    category: 'Graphiques'
  },
  {
    type: 'stacked_bar_chart',
    name: 'Barres Empilées',
    description: 'Barres avec segments empilés',
    icon: Layers,
    color: 'text-teal-500',
    category: 'Graphiques'
  },
  {
    type: 'circular_gauge',
    name: 'Jauge Circulaire',
    description: 'Indicateur circulaire',
    icon: Gauge,
    color: 'text-teal-500',
    category: 'Jauges'
  },
  {
    type: 'linear_gauge',
    name: 'Jauge Linéaire',
    description: 'Barre de progression',
    icon: TrendingUp,
    color: 'text-cyan-500',
    category: 'Jauges'
  },
  {
    type: 'stat_card',
    name: 'Carte Stat',
    description: 'Carte avec une statistique',
    icon: Grid3x3,
    color: 'text-indigo-500',
    category: 'Info'
  },
  {
    type: 'table',
    name: 'Tableau',
    description: 'Tableau de données',
    icon: Table2,
    color: 'text-slate-500',
    category: 'Données'
  },
  {
    type: 'heatmap',
    name: 'Heatmap',
    description: 'Carte de chaleur',
    icon: LayoutGrid,
    color: 'text-pink-500',
    category: 'Graphiques'
  }
]

const categories = ['Tous', ...new Set(widgetLibrary.map(w => w.category))]

export default function GoalDrivenPageBuilder() {
  const {
    widgets,
    selectedWidgetId,
    previewMode,
    requiredTransforms,
    addWidget,
    removeWidget,
    selectWidget,
    updateWidgetConfig,
    updateWidgetLayout,
    setPreviewMode,
    generateRequirements,
    generateYAML,
    reset
  } = useGoalDrivenStore()

  const [yamlOutput, setYamlOutput] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState('Tous')
  const [activeTab, setActiveTab] = useState<'design' | 'preview'>('design')

  // Real data preview state
  const [previewGroupBy, setPreviewGroupBy] = useState<'taxon' | 'plot' | 'shape'>('taxon')
  const [entities, setEntities] = useState<EntitySummary[]>([])
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)
  const [entityDetail, setEntityDetail] = useState<EntityDetail | null>(null)
  const [loadingEntities, setLoadingEntities] = useState(false)
  const [loadingEntityDetail, setLoadingEntityDetail] = useState(false)

  const selectedWidget = widgets.find(w => w.id === selectedWidgetId)

  const filteredWidgets = selectedCategory === 'Tous'
    ? widgetLibrary
    : widgetLibrary.filter(w => w.category === selectedCategory)

  // Load entities when preview tab is activated or groupBy changes
  useEffect(() => {
    if (activeTab === 'preview') {
      loadEntityList()
    }
  }, [activeTab, previewGroupBy])

  // Load entity detail when entity is selected
  useEffect(() => {
    if (selectedEntityId !== null && activeTab === 'preview') {
      loadEntityDetail()
    }
  }, [selectedEntityId, activeTab])

  const loadEntityList = async () => {
    setLoadingEntities(true)
    try {
      const data = await listEntities(previewGroupBy, 20)
      setEntities(Array.isArray(data) ? data : [])
      if (data.length > 0) {
        setSelectedEntityId(data[0].id)
      }
    } catch (error) {
      console.error('Error loading entities:', error)
      setEntities([])
    } finally {
      setLoadingEntities(false)
    }
  }

  const loadEntityDetail = async () => {
    if (selectedEntityId === null) return
    setLoadingEntityDetail(true)
    try {
      const data = await getEntityDetail(previewGroupBy, selectedEntityId)
      setEntityDetail(data)
    } catch (error) {
      console.error('Error loading entity detail:', error)
      setEntityDetail(null)
    } finally {
      setLoadingEntityDetail(false)
    }
  }

  // Map widget types to transformation keys
  const getTransformationKeyForWidget = (widgetType: WidgetType): string | null => {
    // This mapping uses the actual transformation names from transform.yml
    const mapping: Record<WidgetType, string | null> = {
      hierarchical_nav: null,
      interactive_map: 'distribution_map',  // geospatial_extractor
      info_cards: 'general_info',  // field_aggregator with basic info
      horizontal_bar_chart: 'distribution_substrat',  // binary_counter or categorical distribution
      histogram: 'dbh_distribution',  // binned distribution for DBH
      vertical_bar_chart: 'strata_distribution',  // categorical distribution
      pie_chart: 'distribution_substrat',  // binary_counter
      donut_chart: 'holdridge_distribution',  // categorical distribution
      stacked_bar_chart: 'phenology',  // time series or stacked data
      circular_gauge: 'height_max',  // single value aggregation
      linear_gauge: 'dbh_max',  // single value aggregation
      stat_card: 'general_info',  // field_aggregator
      table: 'top_species',  // ranking or tabular data
      heatmap: 'elevation_distribution'  // 2D distribution
    }
    return mapping[widgetType]
  }

  // Check if widget has available transformation data
  const hasTransformationData = (widgetType: WidgetType): boolean => {
    if (!entityDetail?.widgets_data) return false
    const transformKey = getTransformationKeyForWidget(widgetType)
    if (!transformKey) return false
    return transformKey in entityDetail.widgets_data
  }

  // Get widget status for preview
  const getWidgetStatus = (widgetType: WidgetType) => {
    if (!entityDetail) {
      return { available: false, message: 'Sélectionnez une entité' }
    }
    const transformKey = getTransformationKeyForWidget(widgetType)
    if (!transformKey) {
      return { available: false, message: 'Type de widget non supporté' }
    }
    const hasData = hasTransformationData(widgetType)
    return {
      available: hasData,
      message: hasData ? 'Données disponibles' : 'Transformation manquante'
    }
  }

  const handleAddWidget = (type: WidgetType) => {
    addWidget(type)
  }

  const handleGenerateConfig = () => {
    generateRequirements()
    const yaml = generateYAML()
    setYamlOutput(yaml)
  }

  const handleLayoutChange = (layout: Layout[]) => {
    layout.forEach(item => {
      const widget = widgets.find(w => w.id === item.i)
      if (widget && (
        widget.x !== item.x ||
        widget.y !== item.y ||
        widget.w !== item.w ||
        widget.h !== item.h
      )) {
        updateWidgetLayout(item.i, {
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.h
        })
      }
    })
  }

  const layouts = {
    lg: widgets.map(w => ({
      i: w.id,
      x: w.x,
      y: w.y,
      w: w.w,
      h: w.h
    }))
  }

  return (
    <DemoWrapper currentDemo="goal-driven">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold flex items-center gap-2">
              <Sparkles className="w-8 h-8 text-teal-400" />
              Éditeur Goal-Driven
            </h2>
            <p className="text-muted-foreground mt-2">
              Concevez votre page visuellement, générez la configuration automatiquement
            </p>
          </div>
          <div className="flex gap-2">
            {activeTab === 'design' && (
              <Button
                variant={previewMode ? 'default' : 'outline'}
                onClick={() => setPreviewMode(!previewMode)}
              >
                {previewMode ? <Eye className="w-4 h-4 mr-2" /> : <EyeOff className="w-4 h-4 mr-2" />}
                {previewMode ? 'Mode Preview' : 'Mode Édition'}
              </Button>
            )}
            <Button
              variant="outline"
              onClick={reset}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Réinitialiser
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'design' | 'preview')}>
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="design" className="flex items-center gap-2">
              <LayoutGrid className="w-4 h-4" />
              Conception
            </TabsTrigger>
            <TabsTrigger value="preview" className="flex items-center gap-2">
              <Database className="w-4 h-4" />
              Aperçu avec Données
            </TabsTrigger>
          </TabsList>

          {/* Design Tab */}
          <TabsContent value="design" className="mt-6">

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Panel - Canvas (3/4 width on large screens) */}
          <div className="lg:col-span-3 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LayoutGrid className="w-5 h-5" />
                  Canvas de Page
                </CardTitle>
                <CardDescription>
                  Glissez-déposez et redimensionnez vos widgets pour construire votre page
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="min-h-[600px] border rounded-lg p-4 bg-muted/10">
                  {widgets.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                      <LayoutGrid className="w-16 h-16 text-muted-foreground/50 mb-4" />
                      <p className="text-muted-foreground">
                        Commencez par ajouter des widgets depuis la bibliothèque
                      </p>
                    </div>
                  ) : (
                    <ResponsiveGridLayout
                      className="layout"
                      layouts={layouts}
                      breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                      cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                      rowHeight={80}
                      onLayoutChange={handleLayoutChange}
                      isDraggable={!previewMode}
                      isResizable={!previewMode}
                      compactType="vertical"
                    >
                      {widgets.map((widget) => {
                        const widgetDef = widgetLibrary.find(w => w.type === widget.type)
                        const Icon = widgetDef?.icon || LayoutGrid

                        return (
                          <div
                            key={widget.id}
                            className={`relative ${
                              selectedWidgetId === widget.id
                                ? 'ring-2 ring-teal-400 shadow-lg'
                                : ''
                            }`}
                          >
                            <Card
                              className="h-full cursor-pointer"
                              onClick={() => selectWidget(widget.id)}
                            >
                              {!previewMode && (
                                <CardHeader className="pb-2">
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <Icon className={`w-4 h-4 ${widgetDef?.color}`} />
                                      <CardTitle className="text-sm">
                                        {widgetDef?.name}
                                      </CardTitle>
                                    </div>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        removeWidget(widget.id)
                                      }}
                                    >
                                      <Trash2 className="w-3 h-3" />
                                    </Button>
                                  </div>
                                </CardHeader>
                              )}
                              <CardContent className={previewMode ? "h-full p-0" : "h-full pt-0"}>
                                <div className="h-full">
                                  {previewMode && <WidgetPreview widget={widget} />}
                                  {!previewMode && (
                                    <div className="h-full flex items-center justify-center text-muted-foreground">
                                      <Icon className={`w-12 h-12 ${widgetDef?.color} opacity-30`} />
                                    </div>
                                  )}
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                        )
                      })}
                    </ResponsiveGridLayout>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Requirements Display */}
            {requiredTransforms.length > 0 && (
              <Card className="border-teal-300/30 bg-teal-50/30 dark:bg-teal-950/10">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Settings2 className="w-4 h-4 text-teal-400" />
                    Transformations Requises ({requiredTransforms.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-32">
                    <div className="space-y-2">
                      {requiredTransforms.map((transform, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <Badge variant="outline" className="text-teal-600">
                            {transform.plugin}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {transform.fields.join(', ')}
                          </span>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Panel - Widget Library & Config (1/4 width on large screens) */}
          <div className="space-y-4">
            {/* Widget Library */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Plus className="w-4 h-4" />
                  Bibliothèque ({filteredWidgets.length})
                </CardTitle>
                <div className="pt-2">
                  <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.map(cat => (
                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {filteredWidgets.map((widget) => {
                      const Icon = widget.icon
                      return (
                        <Button
                          key={widget.type}
                          variant="outline"
                          className="w-full justify-start h-auto py-2 text-left"
                          onClick={() => handleAddWidget(widget.type)}
                        >
                          <Icon className={`w-4 h-4 mr-2 shrink-0 ${widget.color}`} />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-xs truncate">{widget.name}</div>
                            <div className="text-xs text-muted-foreground truncate">
                              {widget.description}
                            </div>
                          </div>
                        </Button>
                      )
                    })}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Widget Configuration */}
            {selectedWidget && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Configuration</CardTitle>
                  <CardDescription className="text-xs">
                    {widgetLibrary.find(w => w.type === selectedWidget.type)?.name}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(selectedWidget.type === 'histogram' ||
                    selectedWidget.type === 'horizontal_bar_chart' ||
                    selectedWidget.type === 'vertical_bar_chart') && (
                    <div className="space-y-2">
                      <Label className="text-xs">Champ à visualiser</Label>
                      <Select
                        value={selectedWidget.config.field || 'dbh'}
                        onValueChange={(value) =>
                          updateWidgetConfig(selectedWidget.id, { ...selectedWidget.config, field: value })
                        }
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="dbh">DBH (Diamètre)</SelectItem>
                          <SelectItem value="height">Hauteur</SelectItem>
                          <SelectItem value="wood_density">Densité du bois</SelectItem>
                          <SelectItem value="elevation">Élévation</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {selectedWidget.type === 'histogram' && (
                    <div className="space-y-2">
                      <Label className="text-xs">Classes (bins)</Label>
                      <Input
                        className="h-8 text-xs"
                        placeholder="10,20,30,40,50,75,100,200"
                        value={selectedWidget.config.bins?.join(',') || ''}
                        onChange={(e) =>
                          updateWidgetConfig(selectedWidget.id, {
                            ...selectedWidget.config,
                            bins: e.target.value.split(',').map(Number)
                          })
                        }
                      />
                    </div>
                  )}

                  {(selectedWidget.type === 'circular_gauge' ||
                    selectedWidget.type === 'linear_gauge') && (
                    <>
                      <div className="space-y-2">
                        <Label className="text-xs">Champ</Label>
                        <Select
                          value={selectedWidget.config.field || 'height'}
                          onValueChange={(value) =>
                            updateWidgetConfig(selectedWidget.id, { ...selectedWidget.config, field: value })
                          }
                        >
                          <SelectTrigger className="h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="height">Hauteur</SelectItem>
                            <SelectItem value="dbh">DBH</SelectItem>
                            <SelectItem value="wood_density">Densité</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">Opération</Label>
                        <Select
                          value={selectedWidget.config.operation || 'max'}
                          onValueChange={(value) =>
                            updateWidgetConfig(selectedWidget.id, { ...selectedWidget.config, operation: value })
                          }
                        >
                          <SelectTrigger className="h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="max">Maximum</SelectItem>
                            <SelectItem value="min">Minimum</SelectItem>
                            <SelectItem value="mean">Moyenne</SelectItem>
                            <SelectItem value="median">Médiane</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Generate Config Button */}
            <Button
              className="w-full"
              onClick={handleGenerateConfig}
              disabled={widgets.length === 0}
            >
              <Download className="w-4 h-4 mr-2" />
              Générer Configuration
            </Button>

            {/* YAML Output */}
            {yamlOutput && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Configuration JSON</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[200px]">
                    <pre className="text-xs bg-muted p-3 rounded font-mono">
                      {yamlOutput}
                    </pre>
                  </ScrollArea>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
          </TabsContent>

          {/* Preview with Real Data Tab */}
          <TabsContent value="preview" className="mt-6">
            <div className="space-y-6">
              {/* Entity Selection Controls */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="w-5 h-5" />
                    Sélection des Données
                  </CardTitle>
                  <CardDescription>
                    Choisissez une entité pour tester les widgets avec des données réelles
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Type d'entité</Label>
                      <Select
                        value={previewGroupBy}
                        onValueChange={(value) => setPreviewGroupBy(value as 'taxon' | 'plot' | 'shape')}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="taxon">Taxons</SelectItem>
                          <SelectItem value="plot">Placettes</SelectItem>
                          <SelectItem value="shape">Formes</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Entité</Label>
                      <Select
                        value={selectedEntityId || ''}
                        onValueChange={(value) => setSelectedEntityId(value)}
                        disabled={loadingEntities || entities.length === 0}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Sélectionner..." />
                        </SelectTrigger>
                        <SelectContent>
                          {entities.map((entity) => (
                            <SelectItem key={entity.id} value={entity.id}>
                              {entity.display_name || entity.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {loadingEntityDetail && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                      Chargement des données...
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Widget Status Grid */}
              {entityDetail && widgets.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Settings2 className="w-5 h-5" />
                      État des Widgets ({widgets.length})
                    </CardTitle>
                    <CardDescription>
                      Correspondance entre vos widgets configurés et les données disponibles
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {widgets.map((widget) => {
                        const widgetDef = widgetLibrary.find(w => w.type === widget.type)
                        const status = getWidgetStatus(widget.type)
                        const Icon = widgetDef?.icon || LayoutGrid
                        const StatusIcon = status.available ? CheckCircle2 : XCircle

                        return (
                          <div
                            key={widget.id}
                            className={`flex items-center justify-between p-3 rounded-lg border ${
                              status.available
                                ? 'bg-green-50/50 border-green-200 dark:bg-green-950/20 dark:border-green-900/30'
                                : 'bg-amber-50/50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900/30'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <Icon className={`w-5 h-5 ${widgetDef?.color}`} />
                              <div>
                                <div className="font-medium text-sm">{widgetDef?.name}</div>
                                <div className="text-xs text-muted-foreground">
                                  Transform: {getTransformationKeyForWidget(widget.type) || 'N/A'}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge
                                variant={status.available ? 'default' : 'outline'}
                                className={
                                  status.available
                                    ? 'bg-green-500 text-white'
                                    : 'text-amber-600 border-amber-300'
                                }
                              >
                                {status.message}
                              </Badge>
                              <StatusIcon
                                className={`w-5 h-5 ${
                                  status.available ? 'text-green-500' : 'text-amber-500'
                                }`}
                              />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Available Transformations */}
              {entityDetail && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertCircle className="w-5 h-5 text-teal-400" />
                      Transformations Disponibles
                    </CardTitle>
                    <CardDescription>
                      Données de transformation disponibles pour cette entité
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-48">
                      <div className="space-y-2">
                        {Object.keys(entityDetail.widgets_data || {}).map((key) => (
                          <Badge key={key} variant="outline" className="mr-2">
                            {key}
                          </Badge>
                        ))}
                        {Object.keys(entityDetail.widgets_data || {}).length === 0 && (
                          <p className="text-sm text-muted-foreground">
                            Aucune transformation disponible pour cette entité
                          </p>
                        )}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              )}

              {/* Real Widget Preview Grid with Layout */}
              {entityDetail && widgets.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Aperçu des Widgets Réels</CardTitle>
                    <CardDescription>
                      Rendu des widgets avec les données de transformation réelles (layout respecté)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="min-h-[600px] border rounded-lg p-4 bg-muted/10">
                      <ResponsiveGridLayout
                        className="layout"
                        layouts={layouts}
                        breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                        cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                        rowHeight={80}
                        isDraggable={false}
                        isResizable={false}
                        compactType="vertical"
                      >
                        {widgets.map((widget) => {
                          const widgetDef = widgetLibrary.find(w => w.type === widget.type)
                          const transformKey = getTransformationKeyForWidget(widget.type)
                          const hasData = hasTransformationData(widget.type)
                          const Icon = widgetDef?.icon || LayoutGrid

                          return (
                            <div key={widget.id}>
                              <Card className={`h-full ${hasData ? 'border-2 border-teal-300/30' : 'border-amber-300/30'}`}>
                                <CardHeader className="pb-2">
                                  <div className="flex items-center gap-2">
                                    <Icon className={`w-4 h-4 ${widgetDef?.color}`} />
                                    <CardTitle className="text-sm">{widgetDef?.name}</CardTitle>
                                  </div>
                                </CardHeader>
                                <CardContent className="h-[calc(100%-60px)]">
                                  {hasData && transformKey ? (
                                    <div className="w-full h-full border rounded overflow-hidden bg-background">
                                      <iframe
                                        src={`/api/entities/render-widget/${previewGroupBy}/${selectedEntityId}/${transformKey}`}
                                        className="w-full h-full border-0"
                                        title={`Preview ${widgetDef?.name}`}
                                        sandbox="allow-scripts allow-same-origin"
                                      />
                                    </div>
                                  ) : (
                                    <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground border border-dashed rounded">
                                      <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
                                      <p className="text-xs text-center">Transformation manquante</p>
                                      <p className="text-xs text-center mt-1">{transformKey || 'N/A'}</p>
                                    </div>
                                  )}
                                </CardContent>
                              </Card>
                            </div>
                          )
                        })}
                      </ResponsiveGridLayout>
                    </div>
                  </CardContent>
                </Card>
              )}

              {widgets.length === 0 && (
                <Card>
                  <CardContent className="py-12">
                    <div className="text-center text-muted-foreground">
                      <LayoutGrid className="w-16 h-16 mx-auto mb-4 opacity-30" />
                      <p>Ajoutez des widgets dans l'onglet "Conception" pour voir l'aperçu avec données</p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </DemoWrapper>
  )
}
