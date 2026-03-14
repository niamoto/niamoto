/**
 * Mockup Option D: Hybrid (3 onglets + panneau contextuel)
 * Route: /labs/mockup-widgets-hybrid
 *
 * Combine les avantages de A et B:
 * - 3 onglets (Sources/Contenu/Index)
 * - Panneau droit contextuel:
 *   - Aucune sélection → Aperçu mise en page
 *   - Widget sélectionné → Détails du widget
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  Plus,
  GripVertical,
  BarChart3,
  Gauge,
  PieChart,
  MapPin,
  Search,
  ChevronDown,
  Trash2,
  Copy,
  RefreshCw,
  Sparkles,
  Link2,
  Settings2,
  Eye,
  FileCode,
  Palette,
  LayoutGrid,
  ArrowLeftCircle,
  Columns2,
  Square,
  Database,
  List,
  Target,
  Zap,
  TrendingUp,
  Clock,
  Filter,
  ChevronRight,
  Check,
  Info,
  Wand2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'

// Mock data for template suggestions with more details for preview
const mockSuggestions = [
  {
    id: 'dbh_distribution',
    name: 'Distribution du DBH',
    description: 'Histogramme montrant la répartition des diamètres à hauteur de poitrine',
    field: 'dbh',
    category: 'chart',
    plugin: 'bar_plot',
    transformer: 'binned_distribution',
    confidence: 95,
    icon: BarChart3,
    isRecommended: true,
    defaultParams: { bins: 10, color: '#4CAF50' },
  },
  {
    id: 'dbh_stats',
    name: 'Statistiques DBH',
    description: 'Jauge affichant la moyenne du DBH avec min/max',
    field: 'dbh',
    category: 'gauge',
    plugin: 'gauge',
    transformer: 'stats_aggregator',
    confidence: 90,
    icon: Gauge,
    isRecommended: false,
    defaultParams: { unit: 'cm', decimals: 1 },
  },
  {
    id: 'height_distribution',
    name: 'Distribution hauteur',
    description: 'Histogramme montrant la répartition des hauteurs',
    field: 'height',
    category: 'chart',
    plugin: 'bar_plot',
    transformer: 'binned_distribution',
    confidence: 95,
    icon: BarChart3,
    isRecommended: true,
    defaultParams: { bins: 10, color: '#2196F3' },
  },
  {
    id: 'height_stats',
    name: 'Statistiques hauteur',
    description: 'Jauge affichant la hauteur moyenne avec min/max',
    field: 'height',
    category: 'gauge',
    plugin: 'gauge',
    transformer: 'stats_aggregator',
    confidence: 90,
    icon: Gauge,
    isRecommended: false,
    defaultParams: { unit: 'm', decimals: 1 },
  },
  {
    id: 'endemic_donut',
    name: 'Répartition endémisme',
    description: 'Diagramme circulaire du statut d\'endémisme',
    field: 'endemic_status',
    category: 'donut',
    plugin: 'donut',
    transformer: 'categorical_distribution',
    confidence: 98,
    icon: PieChart,
    isRecommended: true,
    defaultParams: { colors: ['#4CAF50', '#FFC107', '#F44336'] },
  },
  {
    id: 'strate_donut',
    name: 'Répartition strates',
    description: 'Diagramme circulaire des strates de végétation',
    field: 'strate',
    category: 'donut',
    plugin: 'donut',
    transformer: 'categorical_distribution',
    confidence: 95,
    icon: PieChart,
    isRecommended: true,
    defaultParams: { colors: ['#8BC34A', '#CDDC39', '#FFEB3B', '#FF9800'] },
  },
]

// Mock data for semantic groups (combined patterns)
const mockSemanticGroups = [
  {
    id: 'phenology',
    name: 'Phénologie',
    description: 'Floraison, fructification, feuillaison',
    fields: ['flowering', 'fruiting', 'leafing'],
    icon: Clock,
    confidence: 92,
  },
  {
    id: 'allometry',
    name: 'Allométrie',
    description: 'Relations DBH/hauteur/houppier',
    fields: ['dbh', 'height', 'crown_diameter'],
    icon: TrendingUp,
    confidence: 88,
  },
]

// Mock data for widgets
const mockWidgets = [
  {
    id: 'dbh_distribution',
    title: 'Distribution du DBH',
    transformer: 'binned_distribution',
    widget: 'bar_plot',
    icon: BarChart3,
    colspan: 1,
  },
  {
    id: 'height_gauge',
    title: 'Hauteur moyenne',
    transformer: 'stats_aggregator',
    widget: 'gauge',
    icon: Gauge,
    colspan: 1,
  },
  {
    id: 'endemic_donut',
    title: 'Répartition endémisme',
    transformer: 'categorical_distribution',
    widget: 'donut',
    icon: PieChart,
    colspan: 1,
  },
  {
    id: 'distribution_map',
    title: 'Carte de distribution',
    transformer: 'geo_aggregator',
    widget: 'map',
    icon: MapPin,
    colspan: 2,
  },
]

export default function MockupWidgetsHybrid() {
  const [selectedWidget, setSelectedWidget] = useState<string | null>(null)
  const [mainTab, setMainTab] = useState('content')
  const [detailTab, setDetailTab] = useState('preview')
  const [searchQuery, setSearchQuery] = useState('')

  // Modal state
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addModalTab, setAddModalTab] = useState('suggestions')
  const [selectedSuggestions, setSelectedSuggestions] = useState<string[]>([])
  const [hoveredSuggestion, setHoveredSuggestion] = useState<string | null>(null)
  const [focusedSuggestion, setFocusedSuggestion] = useState<string | null>(null)
  const [wizardStep, setWizardStep] = useState(1)
  const [customizations, setCustomizations] = useState<Record<string, { title: string; bins?: number; color?: string }>>({})

  // Get the suggestion to preview (focused > hovered > first selected)
  const previewSuggestionId = focusedSuggestion || hoveredSuggestion || selectedSuggestions[0] || null
  const previewSuggestion = mockSuggestions.find(s => s.id === previewSuggestionId)

  // Get customization for a suggestion
  const getCustomization = (id: string) => {
    const suggestion = mockSuggestions.find(s => s.id === id)
    return customizations[id] || {
      title: suggestion?.name || '',
      bins: suggestion?.defaultParams?.bins,
      color: suggestion?.defaultParams?.color,
    }
  }

  // Update customization for a suggestion
  const updateCustomization = (id: string, updates: Partial<{ title: string; bins?: number; color?: string }>) => {
    setCustomizations(prev => ({
      ...prev,
      [id]: { ...getCustomization(id), ...updates }
    }))
  }

  const selectedWidgetData = mockWidgets.find((w) => w.id === selectedWidget)

  // Group suggestions by field
  const suggestionsByField = mockSuggestions.reduce((acc, s) => {
    if (!acc[s.field]) acc[s.field] = []
    acc[s.field].push(s)
    return acc
  }, {} as Record<string, typeof mockSuggestions>)

  const toggleSuggestion = (id: string) => {
    setSelectedSuggestions(prev => {
      const isSelected = prev.includes(id)
      if (!isSelected) {
        setFocusedSuggestion(id) // Focus the newly selected suggestion
      }
      return isSelected ? prev.filter(x => x !== id) : [...prev, id]
    })
  }

  // Switch to custom wizard with pre-filled values from a suggestion
  const editSuggestionAdvanced = (suggestionId: string) => {
    const suggestion = mockSuggestions.find(s => s.id === suggestionId)
    if (suggestion) {
      setAddModalTab('custom')
      setWizardStep(1)
      // In real implementation, we'd pre-fill the wizard with suggestion data
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b px-4 py-3 flex items-center justify-between bg-muted/30">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/labs">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Retour
            </Link>
          </Button>
          <Separator orientation="vertical" className="h-6" />
          <div>
            <h1 className="font-semibold">Option D: Hybride</h1>
            <p className="text-xs text-muted-foreground">
              3 onglets + panneau contextuel (layout ou détail)
            </p>
          </div>
        </div>
        <Badge className="bg-blue-600">Nouveau</Badge>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 3 tabs - Enhanced visibility */}
        <div className="border-b bg-muted/30">
          <Tabs value={mainTab} onValueChange={setMainTab}>
            <TabsList className="h-12 bg-transparent gap-1 px-4">
              <TabsTrigger
                value="sources"
                className="text-sm font-medium px-6 py-2.5 data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border rounded-lg"
              >
                <Database className="h-4 w-4 mr-2" />
                Sources
              </TabsTrigger>
              <TabsTrigger
                value="content"
                className="text-sm font-medium px-6 py-2.5 data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border rounded-lg"
              >
                <LayoutGrid className="h-4 w-4 mr-2" />
                Contenu
              </TabsTrigger>
              <TabsTrigger
                value="index"
                className="text-sm font-medium px-6 py-2.5 data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border rounded-lg"
              >
                <List className="h-4 w-4 mr-2" />
                Liste
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Content tab - Hybrid approach */}
        {mainTab === 'content' && (
          <ResizablePanelGroup direction="horizontal" className="flex-1">
            {/* Left panel - Widget list */}
            <ResizablePanel defaultSize={30} minSize={20} maxSize={40}>
              <div className="h-full flex flex-col border-r">
                {/* Header with add button */}
                <div className="p-3 border-b flex items-center gap-2">
                  <Button className="flex-1" onClick={() => setAddModalOpen(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Ajouter un widget
                  </Button>
                </div>

                {/* Search */}
                <div className="p-3 border-b">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Rechercher..."
                      className="pl-8 h-9"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>

                {/* Widget list */}
                <ScrollArea className="flex-1">
                  <div className="p-2 space-y-1">
                    {mockWidgets.map((widget) => {
                      const Icon = widget.icon
                      const isSelected = selectedWidget === widget.id

                      return (
                        <div
                          key={widget.id}
                          className={cn(
                            'flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors group',
                            isSelected
                              ? 'bg-primary/10 border border-primary/30'
                              : 'hover:bg-muted border border-transparent'
                          )}
                          onClick={() => setSelectedWidget(widget.id)}
                        >
                          <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                          <Icon className="h-4 w-4 text-muted-foreground" />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">{widget.title}</div>
                            <div className="text-xs text-muted-foreground">{widget.widget}</div>
                          </div>
                          {widget.colspan === 2 && (
                            <Badge variant="outline" className="text-[10px] px-1">
                              2 col
                            </Badge>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </ScrollArea>

                {/* Footer */}
                <div className="p-3 border-t text-xs text-muted-foreground text-center">
                  {mockWidgets.length} widgets • Glisser pour réordonner
                </div>
              </div>
            </ResizablePanel>

            <ResizableHandle withHandle />

            {/* Right panel - Contextual: Layout overview OR Widget details */}
            <ResizablePanel defaultSize={70}>
              {selectedWidget === null ? (
                /* No selection: Show layout overview */
                <div className="h-full flex flex-col">
                  <div className="p-4 border-b flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <LayoutGrid className="h-5 w-5 text-muted-foreground" />
                      <span className="font-medium">Aperçu de la mise en page</span>
                    </div>
                    <Button variant="outline" size="sm">
                      <Eye className="h-4 w-4 mr-2" />
                      Prévisualiser
                    </Button>
                  </div>

                  <ScrollArea className="flex-1 p-6">
                    <div className="max-w-3xl mx-auto">
                      {/* Grid layout preview */}
                      <div className="grid grid-cols-2 gap-4">
                        {mockWidgets.map((widget) => {
                          const Icon = widget.icon

                          return (
                            <div
                              key={widget.id}
                              className={cn(
                                'border-2 border-dashed rounded-lg p-4 cursor-pointer transition-all hover:border-primary/50 hover:bg-primary/5',
                                widget.colspan === 2 ? 'col-span-2' : 'col-span-1',
                                'border-muted-foreground/20'
                              )}
                              onClick={() => setSelectedWidget(widget.id)}
                            >
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                  <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                                  <Icon className="h-4 w-4 text-muted-foreground" />
                                  <span className="text-sm font-medium">{widget.title}</span>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 w-6 p-0"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  {widget.colspan === 2 ? (
                                    <Square className="h-3 w-3" />
                                  ) : (
                                    <Columns2 className="h-3 w-3" />
                                  )}
                                </Button>
                              </div>
                              <div
                                className={cn(
                                  'bg-muted rounded flex items-center justify-center',
                                  widget.colspan === 2 ? 'h-32' : 'h-24'
                                )}
                              >
                                <Icon className="h-8 w-8 text-muted-foreground/30" />
                              </div>
                            </div>
                          )
                        })}
                      </div>

                      <p className="text-center text-sm text-muted-foreground mt-6">
                        Cliquez sur un widget pour l'éditer • Glissez pour réordonner
                      </p>
                    </div>
                  </ScrollArea>
                </div>
              ) : (
                /* Widget selected: Show details */
                <div className="h-full flex flex-col">
                  {/* Header with back button */}
                  <div className="p-4 border-b flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedWidget(null)}
                        className="h-8 px-2"
                      >
                        <ArrowLeftCircle className="h-4 w-4 mr-1" />
                        Retour
                      </Button>
                      <Separator orientation="vertical" className="h-6" />
                      {selectedWidgetData && <selectedWidgetData.icon className="h-5 w-5 text-muted-foreground" />}
                      <div>
                        <div className="font-medium">{selectedWidgetData?.title}</div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1">
                          <Badge variant="outline" className="text-[10px]">
                            {selectedWidgetData?.transformer}
                          </Badge>
                          <span>→</span>
                          <Badge variant="outline" className="text-[10px]">
                            {selectedWidgetData?.widget}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Detail tabs */}
                  <Tabs
                    value={detailTab}
                    onValueChange={setDetailTab}
                    className="flex-1 flex flex-col"
                  >
                    <div className="px-4 border-b">
                      <TabsList className="h-9">
                        <TabsTrigger value="preview" className="text-xs">
                          <Eye className="h-3.5 w-3.5 mr-1.5" />
                          Preview
                        </TabsTrigger>
                        <TabsTrigger value="params" className="text-xs">
                          <Settings2 className="h-3.5 w-3.5 mr-1.5" />
                          Paramètres
                        </TabsTrigger>
                        <TabsTrigger value="yaml" className="text-xs">
                          <FileCode className="h-3.5 w-3.5 mr-1.5" />
                          YAML
                        </TabsTrigger>
                      </TabsList>
                    </div>

                    <TabsContent value="preview" className="flex-1 m-0 p-4 overflow-auto">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm text-muted-foreground">Aperçu du widget</span>
                        <Button variant="outline" size="sm">
                          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                          Actualiser
                        </Button>
                      </div>
                      <div className="h-64 border rounded-lg bg-muted/30 flex items-center justify-center">
                        <div className="text-center text-muted-foreground">
                          {selectedWidgetData && <selectedWidgetData.icon className="h-12 w-12 mx-auto mb-2 opacity-30" />}
                          <p className="text-sm">
                            Preview du widget {selectedWidgetData?.title}
                          </p>
                          <p className="text-xs">(iframe de preview)</p>
                        </div>
                      </div>
                    </TabsContent>

                    <TabsContent value="params" className="flex-1 m-0 p-4 overflow-auto">
                      <div className="grid grid-cols-2 gap-4 max-w-3xl">
                        {/* Transform params */}
                        <Card>
                          <CardHeader className="py-3 px-4">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <Settings2 className="h-4 w-4 text-amber-600" />
                              Transformation
                              <Badge variant="secondary" className="text-xs ml-auto">
                                {selectedWidgetData?.transformer}
                              </Badge>
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="p-4 pt-0 space-y-3">
                            <div>
                              <label className="text-xs text-muted-foreground">Source</label>
                              <Input defaultValue="occurrences" className="h-8 mt-1" />
                            </div>
                            <div>
                              <label className="text-xs text-muted-foreground">Field</label>
                              <Input defaultValue="height" className="h-8 mt-1" />
                            </div>
                          </CardContent>
                        </Card>

                        {/* Widget params */}
                        <Card>
                          <CardHeader className="py-3 px-4">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <Palette className="h-4 w-4 text-emerald-600" />
                              Visualisation
                              <Badge variant="secondary" className="text-xs ml-auto">
                                {selectedWidgetData?.widget}
                              </Badge>
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="p-4 pt-0 space-y-3">
                            <div>
                              <label className="text-xs text-muted-foreground">Titre</label>
                              <Input defaultValue={selectedWidgetData?.title} className="h-8 mt-1" />
                            </div>
                            <div>
                              <label className="text-xs text-muted-foreground">Color</label>
                              <Input defaultValue="#4CAF50" className="h-8 mt-1" />
                            </div>
                          </CardContent>
                        </Card>

                        {/* Layout params */}
                        <Card className="col-span-2">
                          <CardHeader className="py-3 px-4">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <LayoutGrid className="h-4 w-4 text-blue-600" />
                              Mise en page
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="p-4 pt-0">
                            <div className="flex items-center gap-4">
                              <label className="text-xs text-muted-foreground">Largeur:</label>
                              <div className="flex gap-2">
                                <Button
                                  variant={selectedWidgetData?.colspan === 1 ? 'default' : 'outline'}
                                  size="sm"
                                  className="h-8"
                                >
                                  1 colonne
                                </Button>
                                <Button
                                  variant={selectedWidgetData?.colspan === 2 ? 'default' : 'outline'}
                                  size="sm"
                                  className="h-8"
                                >
                                  2 colonnes
                                </Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>

                    <TabsContent value="yaml" className="flex-1 m-0 p-4 overflow-auto">
                      <div className="grid grid-cols-2 gap-4 max-w-3xl">
                        <Card>
                          <CardHeader className="py-2 px-3">
                            <CardTitle className="text-xs">transform.yml</CardTitle>
                          </CardHeader>
                          <CardContent className="p-3 pt-0">
                            <pre className="text-xs bg-muted rounded p-3 overflow-auto">
                              {`${selectedWidgetData?.id}:
  plugin: ${selectedWidgetData?.transformer}
  params:
    source: occurrences
    field: height`}
                            </pre>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader className="py-2 px-3">
                            <CardTitle className="text-xs">export.yml</CardTitle>
                          </CardHeader>
                          <CardContent className="p-3 pt-0">
                            <pre className="text-xs bg-muted rounded p-3 overflow-auto">
                              {`- plugin: ${selectedWidgetData?.widget}
  data: ${selectedWidgetData?.id}
  params:
    title: "${selectedWidgetData?.title}"`}
                            </pre>
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                  </Tabs>

                  {/* Footer with save */}
                  <div className="p-4 border-t flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setSelectedWidget(null)}>
                      Annuler
                    </Button>
                    <Button>Sauvegarder</Button>
                  </div>
                </div>
              )}
            </ResizablePanel>
          </ResizablePanelGroup>
        )}

        {/* Other tabs placeholder */}
        {mainTab !== 'content' && (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <p className="text-lg font-medium mb-1">
                Onglet {mainTab === 'sources' ? 'Sources' : 'Liste'}
              </p>
              <p className="text-sm">Contenu non implémenté dans ce mockup</p>
            </div>
          </div>
        )}
      </div>

      {/* Add Widget Modal - Wide with two columns */}
      <Dialog open={addModalOpen} onOpenChange={(open) => {
        setAddModalOpen(open)
        if (!open) {
          setHoveredSuggestion(null)
          setFocusedSuggestion(null)
        }
      }}>
        <DialogContent className="!max-w-[90vw] w-[1200px] h-[85vh] flex flex-col p-0">
          <DialogHeader className="px-6 py-4 border-b shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Ajouter un widget
            </DialogTitle>
          </DialogHeader>

          <Tabs value={addModalTab} onValueChange={setAddModalTab} className="flex-1 flex flex-col overflow-hidden">
            {/* Modal tabs */}
            <div className="px-6 border-b bg-muted/30 shrink-0">
              <TabsList className="h-11 bg-transparent gap-1">
                <TabsTrigger
                  value="suggestions"
                  className="text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-lg"
                >
                  <Target className="h-4 w-4 mr-2" />
                  Suggestions
                  <Badge variant="secondary" className="ml-2 text-xs">
                    {mockSuggestions.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger
                  value="combined"
                  className="text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-lg"
                >
                  <Link2 className="h-4 w-4 mr-2" />
                  Combinés
                  {mockSemanticGroups.length > 0 && (
                    <Badge className="ml-2 text-xs bg-amber-500">
                      {mockSemanticGroups.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger
                  value="custom"
                  className="text-sm px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-lg"
                >
                  <Wand2 className="h-4 w-4 mr-2" />
                  Personnalisé
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Tab: Suggestions - Two columns layout */}
            <TabsContent value="suggestions" className="flex-1 m-0 overflow-hidden">
              <div className="flex h-full">
                {/* Left column - List of suggestions */}
                <div className="flex-1 flex flex-col border-r min-w-0">
                  {/* Filters */}
                  <div className="px-4 py-3 border-b flex items-center gap-3 shrink-0">
                    <div className="relative flex-1">
                      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input placeholder="Rechercher..." className="pl-8 h-9" />
                    </div>
                    <Button variant="outline" size="sm">
                      <Filter className="h-4 w-4 mr-1.5" />
                      Source
                      <ChevronDown className="h-3 w-3 ml-1" />
                    </Button>
                    <Button variant="outline" size="sm">
                      Type
                      <ChevronDown className="h-3 w-3 ml-1" />
                    </Button>
                  </div>

                  {/* Suggestions list with mini-previews */}
                  <ScrollArea className="flex-1 p-4">
                    <div className="space-y-6">
                      {Object.entries(suggestionsByField).map(([field, suggestions]) => (
                        <div key={field}>
                          <div className="flex items-center gap-2 mb-3">
                            <h3 className="font-medium text-sm capitalize">{field}</h3>
                            <Badge variant="outline" className="text-xs">
                              {suggestions.length}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            {suggestions.map((suggestion) => {
                              const Icon = suggestion.icon
                              const isSelected = selectedSuggestions.includes(suggestion.id)
                              const isFocused = focusedSuggestion === suggestion.id
                              return (
                                <div
                                  key={suggestion.id}
                                  className={cn(
                                    'border rounded-lg overflow-hidden cursor-pointer transition-all hover:shadow-md group',
                                    isSelected && isFocused
                                      ? 'border-primary ring-2 ring-primary/30'
                                      : isSelected
                                        ? 'border-primary/50 bg-primary/5'
                                        : 'hover:border-muted-foreground/40'
                                  )}
                                  onClick={() => {
                                    toggleSuggestion(suggestion.id)
                                  }}
                                  onMouseEnter={() => setHoveredSuggestion(suggestion.id)}
                                  onMouseLeave={() => setHoveredSuggestion(null)}
                                >
                                  {/* Mini preview area */}
                                  <div className="h-20 bg-muted/50 flex items-center justify-center relative">
                                    {suggestion.category === 'chart' && (
                                      <div className="flex items-end gap-0.5 h-12">
                                        {[4, 7, 5, 8, 6, 9, 7, 5, 3, 2].map((h, i) => (
                                          <div
                                            key={i}
                                            className="w-2 bg-primary/60 rounded-t"
                                            style={{ height: `${h * 4}px` }}
                                          />
                                        ))}
                                      </div>
                                    )}
                                    {suggestion.category === 'gauge' && (
                                      <div className="relative">
                                        <div className="w-14 h-7 border-t-4 border-l-4 border-r-4 border-primary/60 rounded-t-full" />
                                        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-xs font-bold text-primary">
                                          42.5
                                        </div>
                                      </div>
                                    )}
                                    {suggestion.category === 'donut' && (
                                      <div className="w-12 h-12 rounded-full border-4 border-primary/60 relative">
                                        <div className="absolute inset-2 rounded-full bg-background" />
                                        <div
                                          className="absolute top-0 right-0 w-6 h-6 bg-amber-500/60 rounded-tr-full"
                                          style={{ clipPath: 'polygon(50% 50%, 100% 0, 100% 100%)' }}
                                        />
                                      </div>
                                    )}
                                    {/* Checkbox overlay */}
                                    <div className="absolute top-2 right-2">
                                      <Checkbox
                                        checked={isSelected}
                                        className="bg-background"
                                        onClick={(e) => e.stopPropagation()}
                                      />
                                    </div>
                                    {/* Confidence badge */}
                                    {suggestion.isRecommended && (
                                      <Badge className="absolute top-2 left-2 text-[10px] bg-green-600">
                                        <Sparkles className="h-3 w-3 mr-1" />
                                        {suggestion.confidence}%
                                      </Badge>
                                    )}
                                  </div>
                                  {/* Info */}
                                  <div className="p-2.5">
                                    <div className="flex items-center gap-1.5 mb-1">
                                      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                                      <span className="font-medium text-sm truncate">{suggestion.name}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      <Badge variant="outline" className="text-[10px] h-5">
                                        {suggestion.plugin}
                                      </Badge>
                                      {!suggestion.isRecommended && (
                                        <span className="text-[10px] text-muted-foreground">
                                          {suggestion.confidence}%
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>

                {/* Right column - Preview & Customization */}
                <div className="w-[380px] flex flex-col bg-muted/20 shrink-0">
                  {previewSuggestion ? (
                    <>
                      {/* Preview header */}
                      <div className="px-4 py-3 border-b bg-background flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <previewSuggestion.icon className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium text-sm">{previewSuggestion.name}</span>
                        </div>
                        {selectedSuggestions.includes(previewSuggestion.id) && (
                          <Badge variant="outline" className="text-xs">
                            <Check className="h-3 w-3 mr-1" />
                            Sélectionné
                          </Badge>
                        )}
                      </div>

                      {/* Large preview */}
                      <div className="p-4">
                        <div className="h-40 bg-background border rounded-lg flex items-center justify-center">
                          {previewSuggestion.category === 'chart' && (
                            <div className="flex items-end gap-1 h-28">
                              {[4, 7, 5, 8, 6, 9, 7, 5, 3, 2, 4, 6].map((h, i) => (
                                <div
                                  key={i}
                                  className="w-4 rounded-t transition-all"
                                  style={{
                                    height: `${h * 10}px`,
                                    backgroundColor: getCustomization(previewSuggestion.id).color || '#4CAF50'
                                  }}
                                />
                              ))}
                            </div>
                          )}
                          {previewSuggestion.category === 'gauge' && (
                            <div className="text-center">
                              <div className="w-24 h-12 border-t-8 border-l-8 border-r-8 rounded-t-full mx-auto"
                                style={{ borderColor: getCustomization(previewSuggestion.id).color || '#4CAF50' }}
                              />
                              <div className="text-2xl font-bold mt-2">42.5</div>
                              <div className="text-xs text-muted-foreground">min: 12 | max: 89</div>
                            </div>
                          )}
                          {previewSuggestion.category === 'donut' && (
                            <div className="relative">
                              <div className="w-24 h-24 rounded-full border-8 relative"
                                style={{ borderColor: getCustomization(previewSuggestion.id).color || '#4CAF50' }}
                              >
                                <div className="absolute inset-2 rounded-full bg-background flex items-center justify-center">
                                  <span className="text-lg font-bold">67%</span>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Info */}
                        <div className="mt-3 space-y-1">
                          <p className="text-sm text-muted-foreground">{previewSuggestion.description}</p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Badge variant="secondary" className="text-[10px]">
                              {previewSuggestion.transformer}
                            </Badge>
                            <span>→</span>
                            <Badge variant="secondary" className="text-[10px]">
                              {previewSuggestion.plugin}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      <Separator />

                      {/* Quick customization (only when selected) */}
                      {selectedSuggestions.includes(previewSuggestion.id) && (
                        <div className="p-4 flex-1">
                          <div className="flex items-center gap-2 mb-3">
                            <Settings2 className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium text-sm">Personnalisation rapide</span>
                          </div>

                          <div className="space-y-3">
                            <div>
                              <label className="text-xs text-muted-foreground">Titre</label>
                              <Input
                                value={getCustomization(previewSuggestion.id).title}
                                onChange={(e) => updateCustomization(previewSuggestion.id, { title: e.target.value })}
                                className="h-8 mt-1"
                              />
                            </div>

                            {previewSuggestion.category === 'chart' && (
                              <div>
                                <label className="text-xs text-muted-foreground">Nombre de bins</label>
                                <Input
                                  type="number"
                                  value={getCustomization(previewSuggestion.id).bins || 10}
                                  onChange={(e) => updateCustomization(previewSuggestion.id, { bins: parseInt(e.target.value) })}
                                  className="h-8 mt-1"
                                />
                              </div>
                            )}

                            <div>
                              <label className="text-xs text-muted-foreground">Couleur</label>
                              <div className="flex gap-2 mt-1">
                                {['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336'].map((color) => (
                                  <button
                                    key={color}
                                    className={cn(
                                      'w-7 h-7 rounded border-2 transition-all',
                                      getCustomization(previewSuggestion.id).color === color
                                        ? 'border-foreground scale-110'
                                        : 'border-transparent hover:scale-105'
                                    )}
                                    style={{ backgroundColor: color }}
                                    onClick={() => updateCustomization(previewSuggestion.id, { color })}
                                  />
                                ))}
                              </div>
                            </div>
                          </div>

                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full mt-4"
                            onClick={() => editSuggestionAdvanced(previewSuggestion.id)}
                          >
                            <Wand2 className="h-4 w-4 mr-2" />
                            Édition avancée (YAML)
                            <ChevronRight className="h-4 w-4 ml-auto" />
                          </Button>
                        </div>
                      )}

                      {/* Hover state - just info */}
                      {!selectedSuggestions.includes(previewSuggestion.id) && (
                        <div className="p-4 flex-1 flex flex-col items-center justify-center text-center">
                          <Info className="h-8 w-8 text-muted-foreground/50 mb-2" />
                          <p className="text-sm text-muted-foreground">
                            Cliquez sur ce widget pour le sélectionner et personnaliser
                          </p>
                        </div>
                      )}
                    </>
                  ) : (
                    /* No selection/hover */
                    <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
                      <Eye className="h-12 w-12 text-muted-foreground/30 mb-3" />
                      <p className="font-medium text-muted-foreground">Aperçu du widget</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Survolez ou sélectionnez un widget pour voir l'aperçu
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Tab: Combined - Two columns layout */}
            <TabsContent value="combined" className="flex-1 m-0 overflow-hidden">
              <div className="flex h-full">
                {/* Left column */}
                <div className="flex-1 overflow-auto p-6 border-r">
                  {/* Semantic groups detected */}
                  <div className="mb-8">
                    <div className="flex items-center gap-2 mb-4">
                      <Zap className="h-5 w-5 text-amber-500" />
                      <h3 className="font-medium">Patterns détectés automatiquement</h3>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      {mockSemanticGroups.map((group) => {
                        const Icon = group.icon
                        return (
                          <Card
                            key={group.id}
                            className="cursor-pointer hover:shadow-md transition-all hover:border-primary/50"
                          >
                            <CardHeader className="pb-2">
                              <CardTitle className="text-base flex items-center gap-2">
                                <Icon className="h-5 w-5 text-amber-600" />
                                {group.name}
                                <Badge className="ml-auto text-xs bg-amber-100 text-amber-800">
                                  {group.confidence}%
                                </Badge>
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <p className="text-sm text-muted-foreground mb-3">
                                {group.description}
                              </p>
                              <div className="flex flex-wrap gap-1 mb-3">
                                {group.fields.map((f) => (
                                  <Badge key={f} variant="outline" className="text-xs">
                                    {f}
                                  </Badge>
                                ))}
                              </div>
                              <Button className="w-full" variant="outline" size="sm">
                                <Plus className="h-4 w-4 mr-2" />
                                Créer ce widget
                              </Button>
                            </CardContent>
                          </Card>
                        )
                      })}
                    </div>
                  </div>

                  {/* Manual field selection */}
                  <div>
                    <div className="flex items-center gap-2 mb-4">
                      <Link2 className="h-5 w-5 text-blue-500" />
                      <h3 className="font-medium">Combiner manuellement</h3>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      Sélectionnez 2 à 5 champs pour créer un widget combiné personnalisé.
                    </p>
                    <div className="grid grid-cols-4 gap-2 p-4 border rounded-lg bg-muted/30">
                      {['dbh', 'height', 'crown_diameter', 'wood_density', 'flowering', 'fruiting', 'leafing', 'bark_type'].map((field) => (
                        <div
                          key={field}
                          className="flex items-center gap-2 p-2 rounded-md border bg-background cursor-pointer hover:border-primary/50"
                        >
                          <Checkbox />
                          <span className="text-sm">{field}</span>
                        </div>
                      ))}
                    </div>
                    <Button className="mt-4" disabled>
                      <Link2 className="h-4 w-4 mr-2" />
                      Proposer un widget combiné
                    </Button>
                  </div>
                </div>

                {/* Right column - Preview */}
                <div className="w-[380px] bg-muted/20 flex flex-col items-center justify-center text-center p-6">
                  <Eye className="h-12 w-12 text-muted-foreground/30 mb-3" />
                  <p className="font-medium text-muted-foreground">Aperçu du widget combiné</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Sélectionnez un pattern ou des champs pour voir l'aperçu
                  </p>
                </div>
              </div>
            </TabsContent>

            {/* Tab: Custom - Wizard with preview */}
            <TabsContent value="custom" className="flex-1 m-0 overflow-hidden flex flex-col">
              <div className="flex-1 flex">
                {/* Wizard steps */}
                <div className="w-56 border-r p-4 bg-muted/20 shrink-0">
                  <h3 className="font-medium mb-4 text-sm">Étapes de création</h3>
                  <div className="space-y-2">
                    {[
                      { step: 1, label: 'Identifiant', desc: 'Nom unique' },
                      { step: 2, label: 'Source', desc: 'Données' },
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

                {/* Wizard content */}
                <div className="flex-1 p-6 overflow-auto">
                  {wizardStep === 1 && (
                    <div className="max-w-md">
                      <h3 className="font-medium mb-4">Identifiant du widget</h3>
                      <Input placeholder="ex: dbh_distribution" />
                      <p className="text-xs text-muted-foreground mt-2">
                        Un identifiant unique en minuscules, sans espaces.
                      </p>
                    </div>
                  )}
                  {wizardStep === 2 && (
                    <div>
                      <h3 className="font-medium mb-4">Source de données</h3>
                      <div className="grid grid-cols-2 gap-3 max-w-lg">
                        {['occurrences', 'taxons', 'plots', 'shapes'].map((source) => (
                          <div
                            key={source}
                            className="border rounded-lg p-3 cursor-pointer hover:border-primary/50 hover:bg-primary/5"
                          >
                            <div className="font-medium text-sm">{source}</div>
                            <div className="text-xs text-muted-foreground">15 colonnes</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {wizardStep === 3 && (
                    <div className="max-w-md">
                      <h3 className="font-medium mb-4">Transformation</h3>
                      <div className="space-y-3">
                        <div>
                          <label className="text-sm text-muted-foreground">Plugin</label>
                          <Input placeholder="binned_distribution" className="mt-1" />
                        </div>
                        <div>
                          <label className="text-sm text-muted-foreground">Champ source</label>
                          <Input placeholder="dbh" className="mt-1" />
                        </div>
                      </div>
                    </div>
                  )}
                  {wizardStep === 4 && (
                    <div className="max-w-md">
                      <h3 className="font-medium mb-4">Affichage</h3>
                      <div className="space-y-3">
                        <div>
                          <label className="text-sm text-muted-foreground">Type de widget</label>
                          <Input placeholder="bar_plot" className="mt-1" />
                        </div>
                        <div>
                          <label className="text-sm text-muted-foreground">Titre</label>
                          <Input placeholder="Distribution du DBH" className="mt-1" />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Navigation buttons */}
                  <div className="flex gap-2 mt-6">
                    {wizardStep > 1 && (
                      <Button variant="outline" onClick={() => setWizardStep(wizardStep - 1)}>
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Précédent
                      </Button>
                    )}
                    {wizardStep < 4 && (
                      <Button onClick={() => setWizardStep(wizardStep + 1)}>
                        Suivant
                        <ChevronRight className="h-4 w-4 ml-2" />
                      </Button>
                    )}
                  </div>
                </div>

                {/* Preview panel */}
                <div className="w-[380px] border-l bg-muted/20 flex flex-col shrink-0">
                  <div className="p-4 border-b bg-background">
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium text-sm">Aperçu</h3>
                      <Tabs defaultValue="yaml">
                        <TabsList className="h-7">
                          <TabsTrigger value="yaml" className="text-xs h-6 px-2">
                            YAML
                          </TabsTrigger>
                          <TabsTrigger value="widget" className="text-xs h-6 px-2">
                            Widget
                          </TabsTrigger>
                        </TabsList>
                      </Tabs>
                    </div>
                  </div>
                  <div className="p-4 flex-1">
                    <pre className="text-xs bg-background border rounded p-3 overflow-auto h-full">
                      {`# transform.yml
my_widget:
  plugin: binned_distribution
  params:
    source: occurrences
    field: dbh
    bins: 10

# export.yml
- plugin: bar_plot
  data: my_widget
  params:
    title: "Distribution du DBH"
    color: "#4CAF50"`}
                    </pre>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          {/* Modal footer */}
          <div className="px-6 py-4 border-t flex items-center justify-between shrink-0">
            <div className="text-sm text-muted-foreground">
              {addModalTab === 'suggestions' && selectedSuggestions.length > 0 && (
                <span className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary" />
                  {selectedSuggestions.length} widget(s) sélectionné(s)
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setAddModalOpen(false)}>
                Annuler
              </Button>
              <Button
                onClick={() => setAddModalOpen(false)}
                disabled={addModalTab === 'suggestions' && selectedSuggestions.length === 0}
              >
                {addModalTab === 'suggestions'
                  ? `Ajouter ${selectedSuggestions.length} widget(s)`
                  : 'Créer le widget'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
