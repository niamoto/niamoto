import React, { useState, useMemo } from 'react'
import { DemoWrapper } from '@/components/demos/DemoWrapper'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  AlertCircle,
  Info,
  Database,
  Settings,
  Package,
  FileOutput,
  Sparkles,
  FileCode,
  Download,
  Upload,
  Save
} from 'lucide-react'
import * as yaml from 'js-yaml'

interface StepData {
  imports: {
    taxonomy: boolean
    occurrences: boolean
    plots: boolean
    shapes: string[]
    layers: string[]
  }
  transforms: {
    entity: 'taxon' | 'plot' | 'shape'
    plugins: string[]
    customParams: Record<string, any>
  }
  widgets: {
    selected: string[]
    config: Record<string, any>
  }
  exports: {
    webEnabled: boolean
    apiEnabled: boolean
    staticPages: string[]
    settings: Record<string, any>
  }
}

const steps = [
  { id: 'imports', title: 'Sources de données', icon: Database },
  { id: 'transforms', title: 'Transformations', icon: Settings },
  { id: 'widgets', title: 'Widgets', icon: Package },
  { id: 'exports', title: 'Exports', icon: FileOutput },
  { id: 'review', title: 'Révision', icon: FileCode },
]

const availableShapes = [
  'Provinces', 'Communes', 'Aires protegées', 'Substrats',
  'Zone de vie', 'Captage', 'Emprises Minières'
]

const availableLayers = [
  'forest_cover', 'elevation', 'rainfall', 'holdridge'
]

const transformPlugins = {
  taxon: [
    { id: 'field_aggregator', name: 'Field Aggregator', description: 'Agrège les champs de différentes sources' },
    { id: 'geospatial_extractor', name: 'Geospatial Extractor', description: 'Extrait les données géospatiales' },
    { id: 'top_ranking', name: 'Top Ranking', description: 'Calcule le classement des éléments' },
    { id: 'time_series_analysis', name: 'Time Series', description: 'Analyse temporelle des données' },
    { id: 'binned_distribution', name: 'Binned Distribution', description: 'Distribution par classes' },
    { id: 'statistical_summary', name: 'Statistical Summary', description: 'Résumés statistiques' },
  ],
  plot: [
    { id: 'field_aggregator', name: 'Field Aggregator', description: 'Agrège les champs' },
    { id: 'stats_loader', name: 'Stats Loader', description: 'Charge les statistiques' },
    { id: 'class_object_series_extractor', name: 'Series Extractor', description: 'Extrait les séries' },
  ],
  shape: [
    { id: 'spatial_analysis', name: 'Spatial Analysis', description: 'Analyse spatiale' },
    { id: 'overlay_analysis', name: 'Overlay Analysis', description: 'Analyse de superposition' },
  ]
}

const widgetTypes = [
  { id: 'interactive_map', name: 'Carte interactive', category: 'visualization' },
  { id: 'bar_plot', name: 'Graphique en barres', category: 'chart' },
  { id: 'donut_chart', name: 'Graphique en anneau', category: 'chart' },
  { id: 'radial_gauge', name: 'Jauge radiale', category: 'gauge' },
  { id: 'info_grid', name: 'Grille d\'informations', category: 'info' },
  { id: 'hierarchical_nav_widget', name: 'Navigation hiérarchique', category: 'navigation' },
]

export function WizardFormDemo() {
  const [currentStep, setCurrentStep] = useState(0)
  const [data, setData] = useState<StepData>({
    imports: {
      taxonomy: true,
      occurrences: true,
      plots: false,
      shapes: [],
      layers: []
    },
    transforms: {
      entity: 'taxon',
      plugins: [],
      customParams: {}
    },
    widgets: {
      selected: [],
      config: {}
    },
    exports: {
      webEnabled: true,
      apiEnabled: false,
      staticPages: ['home', 'methodology'],
      settings: {
        title: 'Niamoto',
        lang: 'fr',
        primary_color: '#228b22'
      }
    }
  })

  const [validation, setValidation] = useState<Record<string, string>>({})

  const progress = ((currentStep + 1) / steps.length) * 100

  const validateStep = () => {
    const errors: Record<string, string> = {}

    switch (currentStep) {
      case 0: // Imports
        if (!data.imports.taxonomy && !data.imports.occurrences && !data.imports.plots) {
          errors.general = 'Sélectionnez au moins une source de données principale'
        }
        break
      case 1: // Transforms
        if (data.transforms.plugins.length === 0) {
          errors.plugins = 'Sélectionnez au moins un plugin de transformation'
        }
        break
      case 2: // Widgets
        if (data.widgets.selected.length === 0) {
          errors.widgets = 'Sélectionnez au moins un widget'
        }
        break
      case 3: // Exports
        if (!data.exports.webEnabled && !data.exports.apiEnabled) {
          errors.exports = 'Activez au moins un type d\'export'
        }
        break
    }

    setValidation(errors)
    return Object.keys(errors).length === 0
  }

  const handleNext = () => {
    if (validateStep()) {
      setCurrentStep(Math.min(currentStep + 1, steps.length - 1))
    }
  }

  const handlePrevious = () => {
    setCurrentStep(Math.max(currentStep - 1, 0))
  }

  const generateConfig = useMemo(() => {
    const importConfig: any = {}
    if (data.imports.taxonomy) {
      importConfig.taxonomy = {
        path: 'imports/occurrences.csv',
        hierarchy: {
          levels: [
            { name: 'family', column: 'family' },
            { name: 'genus', column: 'genus' },
            { name: 'species', column: 'species' }
          ]
        }
      }
    }
    if (data.imports.occurrences) {
      importConfig.occurrences = {
        type: 'csv',
        path: 'imports/occurrences.csv',
        identifier: 'id_taxonref',
        location_field: 'geo_pt'
      }
    }
    if (data.imports.plots) {
      importConfig.plots = {
        type: 'csv',
        path: 'imports/plots.csv',
        identifier: 'id_plot'
      }
    }
    if (data.imports.shapes.length > 0) {
      importConfig.shapes = data.imports.shapes.map(shape => ({
        type: shape,
        path: `imports/shapes/${shape.toLowerCase()}.gpkg`
      }))
    }
    if (data.imports.layers.length > 0) {
      importConfig.layers = data.imports.layers.map(layer => ({
        name: layer,
        type: layer.includes('cover') ? 'vector' : 'raster',
        path: `imports/layers/${layer}.tif`
      }))
    }

    const transformConfig = [{
      group_by: data.transforms.entity,
      widgets_data: Object.fromEntries(
        data.transforms.plugins.map(plugin => [
          plugin,
          {
            plugin: plugin,
            params: data.transforms.customParams[plugin] || {}
          }
        ])
      )
    }]

    const exportConfig = {
      exports: []
    } as any

    if (data.exports.webEnabled) {
      exportConfig.exports.push({
        name: 'web_pages',
        enabled: true,
        exporter: 'html_page_exporter',
        params: {
          output_dir: 'exports/web',
          site: data.exports.settings,
          static_pages: data.exports.staticPages.map(page => ({
            name: page,
            template: `${page}.html`,
            output_file: `${page}.html`
          }))
        },
        groups: [{
          group_by: data.transforms.entity,
          widgets: data.widgets.selected.map(widgetId => {
            const widget = widgetTypes.find(w => w.id === widgetId)
            return {
              plugin: widgetId,
              title: widget?.name || widgetId,
              params: data.widgets.config[widgetId] || {}
            }
          })
        }]
      })
    }

    if (data.exports.apiEnabled) {
      exportConfig.exports.push({
        name: 'api',
        enabled: true,
        exporter: 'api_exporter',
        params: {
          output_dir: 'exports/api'
        }
      })
    }

    return {
      import: yaml.dump(importConfig, { indent: 2 }),
      transform: yaml.dump(transformConfig, { indent: 2 }),
      export: yaml.dump(exportConfig, { indent: 2 })
    }
  }, [data])

  return (
    <DemoWrapper currentDemo="wizard-form">
      <div className="max-w-6xl mx-auto">
        {/* Progress Bar */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              {steps.map((step, index) => (
                <div
                  key={step.id}
                  className={`flex items-center ${
                    index < steps.length - 1 ? 'flex-1' : ''
                  }`}
                >
                  <div
                    className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                      index <= currentStep
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'bg-background border-muted-foreground'
                    }`}
                  >
                    {index < currentStep ? (
                      <Check className="h-5 w-5" />
                    ) : (
                      <step.icon className="h-5 w-5" />
                    )}
                  </div>
                  <div className="ml-2">
                    <p className={`text-sm font-medium ${
                      index <= currentStep ? 'text-foreground' : 'text-muted-foreground'
                    }`}>
                      {step.title}
                    </p>
                  </div>
                  {index < steps.length - 1 && (
                    <div className={`flex-1 h-0.5 mx-4 ${
                      index < currentStep ? 'bg-primary' : 'bg-muted'
                    }`} />
                  )}
                </div>
              ))}
            </div>
            <Progress value={progress} className="h-2" />
          </CardContent>
        </Card>

        {/* Step Content */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {React.createElement(steps[currentStep].icon, { className: "h-5 w-5" })}
              {steps[currentStep].title}
            </CardTitle>
            <CardDescription>
              Étape {currentStep + 1} sur {steps.length}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Step 0: Imports */}
            {currentStep === 0 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium mb-4">Sources principales</h3>
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3">
                      <Checkbox
                        id="taxonomy"
                        checked={data.imports.taxonomy}
                        onCheckedChange={(checked) =>
                          setData({...data, imports: {...data.imports, taxonomy: !!checked}})
                        }
                      />
                      <Label htmlFor="taxonomy" className="flex-1">
                        <div>Taxonomie</div>
                        <div className="text-sm text-muted-foreground">
                          Hiérarchie taxonomique extraite des occurrences
                        </div>
                      </Label>
                    </div>
                    <div className="flex items-center space-x-3">
                      <Checkbox
                        id="occurrences"
                        checked={data.imports.occurrences}
                        onCheckedChange={(checked) =>
                          setData({...data, imports: {...data.imports, occurrences: !!checked}})
                        }
                      />
                      <Label htmlFor="occurrences" className="flex-1">
                        <div>Occurrences</div>
                        <div className="text-sm text-muted-foreground">
                          Données d'observations des espèces
                        </div>
                      </Label>
                    </div>
                    <div className="flex items-center space-x-3">
                      <Checkbox
                        id="plots"
                        checked={data.imports.plots}
                        onCheckedChange={(checked) =>
                          setData({...data, imports: {...data.imports, plots: !!checked}})
                        }
                      />
                      <Label htmlFor="plots" className="flex-1">
                        <div>Parcelles</div>
                        <div className="text-sm text-muted-foreground">
                          Données de parcelles d'inventaire
                        </div>
                      </Label>
                    </div>
                  </div>
                </div>

                <Separator />

                <div>
                  <h3 className="text-lg font-medium mb-4">Formes géographiques</h3>
                  <div className="grid grid-cols-2 gap-3">
                    {availableShapes.map(shape => (
                      <div key={shape} className="flex items-center space-x-3">
                        <Checkbox
                          id={shape}
                          checked={data.imports.shapes.includes(shape)}
                          onCheckedChange={(checked) => {
                            const newShapes = checked
                              ? [...data.imports.shapes, shape]
                              : data.imports.shapes.filter(s => s !== shape)
                            setData({...data, imports: {...data.imports, shapes: newShapes}})
                          }}
                        />
                        <Label htmlFor={shape}>{shape}</Label>
                      </div>
                    ))}
                  </div>
                </div>

                <Separator />

                <div>
                  <h3 className="text-lg font-medium mb-4">Couches de données</h3>
                  <div className="grid grid-cols-2 gap-3">
                    {availableLayers.map(layer => (
                      <div key={layer} className="flex items-center space-x-3">
                        <Checkbox
                          id={layer}
                          checked={data.imports.layers.includes(layer)}
                          onCheckedChange={(checked) => {
                            const newLayers = checked
                              ? [...data.imports.layers, layer]
                              : data.imports.layers.filter(l => l !== layer)
                            setData({...data, imports: {...data.imports, layers: newLayers}})
                          }}
                        />
                        <Label htmlFor={layer}>
                          {layer.replace('_', ' ').charAt(0).toUpperCase() + layer.slice(1).replace('_', ' ')}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                {validation.general && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{validation.general}</AlertDescription>
                  </Alert>
                )}
              </div>
            )}

            {/* Step 1: Transforms */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium mb-4">Entité principale</h3>
                  <RadioGroup
                    value={data.transforms.entity}
                    onValueChange={(value: 'taxon' | 'plot' | 'shape') =>
                      setData({...data, transforms: {...data.transforms, entity: value, plugins: []}})
                    }
                  >
                    <div className="space-y-3">
                      <div className="flex items-center space-x-3">
                        <RadioGroupItem value="taxon" id="entity-taxon" />
                        <Label htmlFor="entity-taxon" className="flex-1">
                          <div>Taxon</div>
                          <div className="text-sm text-muted-foreground">
                            Transformations centrées sur les espèces
                          </div>
                        </Label>
                      </div>
                      <div className="flex items-center space-x-3">
                        <RadioGroupItem value="plot" id="entity-plot" />
                        <Label htmlFor="entity-plot" className="flex-1">
                          <div>Parcelle</div>
                          <div className="text-sm text-muted-foreground">
                            Transformations centrées sur les parcelles
                          </div>
                        </Label>
                      </div>
                      <div className="flex items-center space-x-3">
                        <RadioGroupItem value="shape" id="entity-shape" />
                        <Label htmlFor="entity-shape" className="flex-1">
                          <div>Forme géographique</div>
                          <div className="text-sm text-muted-foreground">
                            Transformations centrées sur les zones
                          </div>
                        </Label>
                      </div>
                    </div>
                  </RadioGroup>
                </div>

                <Separator />

                <div>
                  <h3 className="text-lg font-medium mb-4">Plugins de transformation</h3>
                  <div className="space-y-3">
                    {transformPlugins[data.transforms.entity].map(plugin => (
                      <div key={plugin.id} className="flex items-start space-x-3">
                        <Checkbox
                          id={plugin.id}
                          checked={data.transforms.plugins.includes(plugin.id)}
                          onCheckedChange={(checked) => {
                            const newPlugins = checked
                              ? [...data.transforms.plugins, plugin.id]
                              : data.transforms.plugins.filter(p => p !== plugin.id)
                            setData({...data, transforms: {...data.transforms, plugins: newPlugins}})
                          }}
                        />
                        <Label htmlFor={plugin.id} className="flex-1">
                          <div>{plugin.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {plugin.description}
                          </div>
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                {data.transforms.plugins.length > 0 && (
                  <>
                    <Separator />
                    <div>
                      <h3 className="text-lg font-medium mb-4">Configuration des plugins</h3>
                      <Accordion type="single" collapsible>
                        {data.transforms.plugins.map(pluginId => {
                          const plugin = transformPlugins[data.transforms.entity].find(p => p.id === pluginId)
                          return (
                            <AccordionItem key={pluginId} value={pluginId}>
                              <AccordionTrigger>{plugin?.name}</AccordionTrigger>
                              <AccordionContent>
                                <Alert>
                                  <Info className="h-4 w-4" />
                                  <AlertDescription>
                                    Configuration avancée disponible dans l'éditeur complet
                                  </AlertDescription>
                                </Alert>
                              </AccordionContent>
                            </AccordionItem>
                          )
                        })}
                      </Accordion>
                    </div>
                  </>
                )}

                {validation.plugins && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{validation.plugins}</AlertDescription>
                  </Alert>
                )}
              </div>
            )}

            {/* Step 2: Widgets */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <Alert>
                  <Sparkles className="h-4 w-4" />
                  <AlertTitle>Widgets recommandés</AlertTitle>
                  <AlertDescription>
                    Basé sur vos transformations, nous recommandons les widgets suivants
                  </AlertDescription>
                </Alert>

                <div>
                  <h3 className="text-lg font-medium mb-4">Sélection des widgets</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {widgetTypes.map(widget => (
                      <Card
                        key={widget.id}
                        className={`cursor-pointer transition-colors ${
                          data.widgets.selected.includes(widget.id)
                            ? 'border-primary bg-primary/5'
                            : 'hover:bg-accent'
                        }`}
                        onClick={() => {
                          const newSelected = data.widgets.selected.includes(widget.id)
                            ? data.widgets.selected.filter(w => w !== widget.id)
                            : [...data.widgets.selected, widget.id]
                          setData({...data, widgets: {...data.widgets, selected: newSelected}})
                        }}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-medium">{widget.name}</p>
                              <Badge variant="outline" className="mt-1 text-xs">
                                {widget.category}
                              </Badge>
                            </div>
                            <Checkbox
                              checked={data.widgets.selected.includes(widget.id)}
                              className="pointer-events-none"
                            />
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>

                {validation.widgets && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{validation.widgets}</AlertDescription>
                  </Alert>
                )}
              </div>
            )}

            {/* Step 3: Exports */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium mb-4">Types d'export</h3>
                  <div className="space-y-4">
                    <Card className={`p-4 cursor-pointer ${
                      data.exports.webEnabled ? 'border-primary bg-primary/5' : ''
                    }`}
                      onClick={() => setData({...data, exports: {...data.exports, webEnabled: !data.exports.webEnabled}})}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium">Site Web Statique</p>
                          <p className="text-sm text-muted-foreground mt-1">
                            Génère un site web complet avec visualisations
                          </p>
                        </div>
                        <Checkbox checked={data.exports.webEnabled} className="pointer-events-none" />
                      </div>
                    </Card>

                    <Card className={`p-4 cursor-pointer ${
                      data.exports.apiEnabled ? 'border-primary bg-primary/5' : ''
                    }`}
                      onClick={() => setData({...data, exports: {...data.exports, apiEnabled: !data.exports.apiEnabled}})}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium">API REST</p>
                          <p className="text-sm text-muted-foreground mt-1">
                            Expose les données via une API REST
                          </p>
                        </div>
                        <Checkbox checked={data.exports.apiEnabled} className="pointer-events-none" />
                      </div>
                    </Card>
                  </div>
                </div>

                {data.exports.webEnabled && (
                  <>
                    <Separator />
                    <div>
                      <h3 className="text-lg font-medium mb-4">Configuration du site</h3>
                      <div className="space-y-4">
                        <div>
                          <Label>Titre du site</Label>
                          <Input
                            value={data.exports.settings.title}
                            onChange={(e) => setData({
                              ...data,
                              exports: {
                                ...data.exports,
                                settings: {...data.exports.settings, title: e.target.value}
                              }
                            })}
                          />
                        </div>
                        <div>
                          <Label>Langue</Label>
                          <Select
                            value={data.exports.settings.lang}
                            onValueChange={(value) => setData({
                              ...data,
                              exports: {
                                ...data.exports,
                                settings: {...data.exports.settings, lang: value}
                              }
                            })}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="fr">Français</SelectItem>
                              <SelectItem value="en">English</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label>Couleur principale</Label>
                          <div className="flex gap-2">
                            <Input
                              type="color"
                              value={data.exports.settings.primary_color}
                              onChange={(e) => setData({
                                ...data,
                                exports: {
                                  ...data.exports,
                                  settings: {...data.exports.settings, primary_color: e.target.value}
                                }
                              })}
                              className="w-20 h-10"
                            />
                            <Input
                              value={data.exports.settings.primary_color}
                              onChange={(e) => setData({
                                ...data,
                                exports: {
                                  ...data.exports,
                                  settings: {...data.exports.settings, primary_color: e.target.value}
                                }
                              })}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {validation.exports && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{validation.exports}</AlertDescription>
                  </Alert>
                )}
              </div>
            )}

            {/* Step 4: Review */}
            {currentStep === 4 && (
              <div className="space-y-6">
                <Alert>
                  <Check className="h-4 w-4" />
                  <AlertTitle>Configuration prête</AlertTitle>
                  <AlertDescription>
                    Vérifiez votre configuration avant de générer les fichiers YAML
                  </AlertDescription>
                </Alert>

                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <h3 className="font-medium mb-2">Sources de données</h3>
                    <div className="space-y-1 text-sm">
                      {data.imports.taxonomy && <Badge variant="outline">Taxonomie</Badge>}
                      {data.imports.occurrences && <Badge variant="outline">Occurrences</Badge>}
                      {data.imports.plots && <Badge variant="outline">Parcelles</Badge>}
                      {data.imports.shapes.map(shape => (
                        <Badge key={shape} variant="outline">{shape}</Badge>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-medium mb-2">Transformations</h3>
                    <div className="space-y-1 text-sm">
                      <Badge>Entité: {data.transforms.entity}</Badge>
                      {data.transforms.plugins.map(plugin => (
                        <Badge key={plugin} variant="secondary">{plugin}</Badge>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-medium mb-2">Widgets</h3>
                    <div className="space-y-1 text-sm">
                      {data.widgets.selected.map(widget => {
                        const w = widgetTypes.find(wt => wt.id === widget)
                        return <Badge key={widget} variant="outline">{w?.name}</Badge>
                      })}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-medium mb-2">Exports</h3>
                    <div className="space-y-1 text-sm">
                      {data.exports.webEnabled && <Badge variant="outline">Site Web</Badge>}
                      {data.exports.apiEnabled && <Badge variant="outline">API REST</Badge>}
                    </div>
                  </div>
                </div>

                <Separator />

                <div>
                  <h3 className="font-medium mb-4">Fichiers YAML générés</h3>
                  <Accordion type="single" collapsible defaultValue="import">
                    <AccordionItem value="import">
                      <AccordionTrigger>import.yml</AccordionTrigger>
                      <AccordionContent>
                        <ScrollArea className="h-[200px] w-full rounded-md border p-4">
                          <pre className="text-xs font-mono">
                            <code>{generateConfig.import}</code>
                          </pre>
                        </ScrollArea>
                      </AccordionContent>
                    </AccordionItem>
                    <AccordionItem value="transform">
                      <AccordionTrigger>transform.yml</AccordionTrigger>
                      <AccordionContent>
                        <ScrollArea className="h-[200px] w-full rounded-md border p-4">
                          <pre className="text-xs font-mono">
                            <code>{generateConfig.transform}</code>
                          </pre>
                        </ScrollArea>
                      </AccordionContent>
                    </AccordionItem>
                    <AccordionItem value="export">
                      <AccordionTrigger>export.yml</AccordionTrigger>
                      <AccordionContent>
                        <ScrollArea className="h-[200px] w-full rounded-md border p-4">
                          <pre className="text-xs font-mono">
                            <code>{generateConfig.export}</code>
                          </pre>
                        </ScrollArea>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </div>

                <div className="flex justify-center gap-2">
                  <Button variant="outline">
                    <Upload className="h-4 w-4 mr-2" />
                    Importer config
                  </Button>
                  <Button>
                    <Download className="h-4 w-4 mr-2" />
                    Télécharger YAML
                  </Button>
                  <Button variant="default">
                    <Save className="h-4 w-4 mr-2" />
                    Appliquer config
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Navigation Buttons */}
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentStep === 0}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Précédent
          </Button>

          {currentStep < steps.length - 1 ? (
            <Button onClick={handleNext}>
              Suivant
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          ) : (
            <Button variant="default">
              <Check className="h-4 w-4 mr-2" />
              Terminer
            </Button>
          )}
        </div>
      </div>
    </DemoWrapper>
  )
}
