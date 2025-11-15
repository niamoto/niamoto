import { useState } from 'react'
import { DemoWrapper } from '@/components/demos/DemoWrapper'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Plus,
  Trash2,
  Save,
  Download,
  ChevronRight,
  Database,
  Settings,
  BarChart,
  Copy,
  Check,
  AlertCircle,
  Layers,
  Code,
  Eye
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface Entity {
  id: string
  name: string
  type: 'taxon' | 'plot' | 'shape' | 'custom'
  color: string
  transformations: Transformation[]
  widgets: Widget[]
}

interface Transformation {
  id: string
  name: string
  plugin: string
  config: Record<string, any>
  outputs: string[]
}

interface Widget {
  id: string
  name: string
  type: string
  requiredData: string[]
  config: Record<string, any>
}

const availableTransformations = [
  { id: 'stats', name: 'Statistical Summary', outputs: ['statistics'] },
  { id: 'distribution', name: 'Distribution Analysis', outputs: ['distribution'] },
  { id: 'temporal', name: 'Temporal Trends', outputs: ['temporal_data'] },
  { id: 'spatial', name: 'Spatial Analysis', outputs: ['spatial_stats'] },
  { id: 'aggregation', name: 'Data Aggregation', outputs: ['aggregated_data'] }
]

const availableWidgets = [
  { id: 'sunburst', name: 'Sunburst Chart', requiredData: ['statistics'] },
  { id: 'map', name: 'Interactive Map', requiredData: ['spatial_stats'] },
  { id: 'timeline', name: 'Timeline', requiredData: ['temporal_data'] },
  { id: 'barchart', name: 'Bar Chart', requiredData: ['distribution'] },
  { id: 'table', name: 'Data Table', requiredData: ['aggregated_data'] }
]

const entityColors = {
  taxon: 'bg-green-500',
  plot: 'bg-blue-500',
  shape: 'bg-purple-500',
  custom: 'bg-orange-500'
}

function EntityCentricDemo() {
  const [entities, setEntities] = useState<Entity[]>([
    {
      id: '1',
      name: 'taxon',
      type: 'taxon',
      color: 'green',
      transformations: [
        { id: 't1', name: 'Statistical Summary', plugin: 'stats', config: {}, outputs: ['statistics'] }
      ],
      widgets: [
        { id: 'w1', name: 'Sunburst Chart', type: 'sunburst', requiredData: ['statistics'], config: {} }
      ]
    }
  ])
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(entities[0])
  const [showAddEntity, setShowAddEntity] = useState(false)
  const [newEntityName, setNewEntityName] = useState('')
  const [newEntityType, setNewEntityType] = useState<'taxon' | 'plot' | 'shape' | 'custom'>('taxon')
  const [yamlPreview, setYamlPreview] = useState<'transform' | 'export'>('transform')
  const [copied, setCopied] = useState(false)

  const addEntity = () => {
    if (newEntityName) {
      const newEntity: Entity = {
        id: Date.now().toString(),
        name: newEntityName,
        type: newEntityType,
        color: newEntityType === 'taxon' ? 'green' : newEntityType === 'plot' ? 'blue' : newEntityType === 'shape' ? 'purple' : 'orange',
        transformations: [],
        widgets: []
      }
      setEntities([...entities, newEntity])
      setSelectedEntity(newEntity)
      setNewEntityName('')
      setShowAddEntity(false)
    }
  }

  const deleteEntity = (id: string) => {
    setEntities(entities.filter(e => e.id !== id))
    if (selectedEntity?.id === id) {
      setSelectedEntity(entities[0] || null)
    }
  }

  const addTransformation = (entityId: string, transformation: any) => {
    setEntities(entities.map(e => {
      if (e.id === entityId) {
        return {
          ...e,
          transformations: [...e.transformations, {
            id: Date.now().toString(),
            name: transformation.name,
            plugin: transformation.id,
            config: {},
            outputs: transformation.outputs
          }]
        }
      }
      return e
    }))
  }

  const addWidget = (entityId: string, widget: any) => {
    setEntities(entities.map(e => {
      if (e.id === entityId) {
        return {
          ...e,
          widgets: [...e.widgets, {
            id: Date.now().toString(),
            name: widget.name,
            type: widget.id,
            requiredData: widget.requiredData,
            config: {}
          }]
        }
      }
      return e
    }))
  }

  const removeTransformation = (entityId: string, transformId: string) => {
    setEntities(entities.map(e => {
      if (e.id === entityId) {
        return {
          ...e,
          transformations: e.transformations.filter(t => t.id !== transformId)
        }
      }
      return e
    }))
  }

  const removeWidget = (entityId: string, widgetId: string) => {
    setEntities(entities.map(e => {
      if (e.id === entityId) {
        return {
          ...e,
          widgets: e.widgets.filter(w => w.id !== widgetId)
        }
      }
      return e
    }))
  }

  const generateTransformYaml = () => {
    const yaml: any = {}
    entities.forEach(entity => {
      if (entity.transformations.length > 0) {
        yaml[entity.name] = {
          widget_data: entity.transformations.map(t => ({
            name: t.name.toLowerCase().replace(/\s+/g, '_'),
            transformer: t.plugin,
            config: t.config
          }))
        }
      }
    })
    return `# Generated transform.yml\n${JSON.stringify(yaml, null, 2).replace(/["{},]/g, '').replace(/^\s{2}/gm, '')}`
  }

  const generateExportYaml = () => {
    const pages: any[] = []
    entities.forEach(entity => {
      if (entity.widgets.length > 0) {
        pages.push({
          name: entity.name,
          path: `/${entity.name}`,
          widgets: entity.widgets.map(w => ({
            type: w.type,
            data_source: `${entity.name}.widget_data`,
            config: w.config
          }))
        })
      }
    })
    const yaml = {
      site: {
        title: "Niamoto Dashboard",
        output_dir: "./dist"
      },
      pages
    }
    return `# Generated export.yml\n${JSON.stringify(yaml, null, 2).replace(/["{},]/g, '').replace(/^\s{2}/gm, '')}`
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const checkCompatibility = (entity: Entity, widget: any) => {
    const availableOutputs = entity.transformations.flatMap(t => t.outputs)
    return widget.requiredData.every((req: string) => availableOutputs.includes(req))
  }

  return (
    <DemoWrapper currentDemo="entity-centric">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Interface Entity-Centric</h1>
          <p className="text-muted-foreground mt-2">
            Gérez vos entités et leurs pipelines de transformation de manière dynamique
          </p>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* Entity List */}
          <div className="col-span-3">
            <Card className="h-[800px]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Entités
                </CardTitle>
                <CardDescription>
                  Gérez vos sources de données
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[450px]">
                  <div className="space-y-2">
                    {entities.map(entity => (
                      <div
                        key={entity.id}
                        onClick={() => setSelectedEntity(entity)}
                        className={cn(
                          "p-3 rounded-lg border cursor-pointer transition-all",
                          selectedEntity?.id === entity.id ? "border-primary bg-primary/5" : "hover:bg-muted/50"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className={cn("w-2 h-2 rounded-full", entityColors[entity.type])} />
                            <span className="font-medium">{entity.name}</span>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={(e) => {
                              e.stopPropagation()
                              deleteEntity(entity.id)
                            }}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                        <div className="flex gap-2 mt-2">
                          <Badge variant="secondary" className="text-xs">
                            {entity.transformations.length} transforms
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            {entity.widgets.length} widgets
                          </Badge>
                        </div>
                      </div>
                    ))}

                    {showAddEntity ? (
                      <div className="p-3 border rounded-lg space-y-3">
                        <Input
                          placeholder="Nom de l'entité"
                          value={newEntityName}
                          onChange={(e) => setNewEntityName(e.target.value)}
                        />
                        <select
                          className="w-full p-2 border rounded"
                          value={newEntityType}
                          onChange={(e) => setNewEntityType(e.target.value as any)}
                        >
                          <option value="taxon">Taxon</option>
                          <option value="plot">Plot</option>
                          <option value="shape">Shape</option>
                          <option value="custom">Custom</option>
                        </select>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={addEntity}>Ajouter</Button>
                          <Button size="sm" variant="outline" onClick={() => setShowAddEntity(false)}>
                            Annuler
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => setShowAddEntity(true)}
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Nouvelle entité
                      </Button>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Pipeline Builder */}
          <div className="col-span-6">
            {selectedEntity ? (
              <Card className="h-[800px]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Layers className="h-4 w-4" />
                    Pipeline: {selectedEntity.name}
                  </CardTitle>
                  <CardDescription>
                    Configurez les transformations et widgets
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {/* Transformations */}
                    <div>
                      <Label className="flex items-center gap-2 mb-3">
                        <Settings className="h-4 w-4" />
                        Transformations
                      </Label>
                      <div className="space-y-2">
                        {selectedEntity.transformations.map(trans => (
                          <div key={trans.id} className="flex items-center gap-2 p-2 border rounded">
                            <Badge>{trans.plugin}</Badge>
                            <span className="flex-1 text-sm">{trans.name}</span>
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            {trans.outputs.map(output => (
                              <Badge key={output} variant="outline" className="text-xs">
                                {output}
                              </Badge>
                            ))}
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => removeTransformation(selectedEntity.id, trans.id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        ))}
                        <div className="border-2 border-dashed rounded-lg p-3">
                          <Label className="text-xs text-muted-foreground">Ajouter une transformation:</Label>
                          <div className="grid grid-cols-2 gap-2 mt-2">
                            {availableTransformations.map(t => (
                              <Button
                                key={t.id}
                                variant="outline"
                                size="sm"
                                onClick={() => addTransformation(selectedEntity.id, t)}
                              >
                                <Plus className="h-3 w-3 mr-1" />
                                {t.name}
                              </Button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Widgets */}
                    <div>
                      <Label className="flex items-center gap-2 mb-3">
                        <BarChart className="h-4 w-4" />
                        Widgets
                      </Label>
                      <div className="space-y-2">
                        {selectedEntity.widgets.map(widget => (
                          <div key={widget.id} className="flex items-center gap-2 p-2 border rounded">
                            <Badge variant="secondary">{widget.type}</Badge>
                            <span className="flex-1 text-sm">{widget.name}</span>
                            {widget.requiredData.map(data => (
                              <Badge key={data} variant="outline" className="text-xs">
                                ← {data}
                              </Badge>
                            ))}
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => removeWidget(selectedEntity.id, widget.id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        ))}
                        <div className="border-2 border-dashed rounded-lg p-3">
                          <Label className="text-xs text-muted-foreground">Ajouter un widget:</Label>
                          <div className="grid grid-cols-2 gap-2 mt-2">
                            {availableWidgets.map(w => {
                              const isCompatible = checkCompatibility(selectedEntity, w)
                              return (
                                <Button
                                  key={w.id}
                                  variant="outline"
                                  size="sm"
                                  disabled={!isCompatible}
                                  onClick={() => addWidget(selectedEntity.id, w)}
                                  className={cn(!isCompatible && "opacity-50")}
                                >
                                  <Plus className="h-3 w-3 mr-1" />
                                  {w.name}
                                  {!isCompatible && (
                                    <AlertCircle className="h-3 w-3 ml-1 text-orange-500" />
                                  )}
                                </Button>
                              )
                            })}
                          </div>
                          <p className="text-xs text-muted-foreground mt-2">
                            <AlertCircle className="h-3 w-3 inline mr-1" />
                            Les widgets grisés nécessitent des transformations manquantes
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="h-[800px] flex items-center justify-center">
                <CardContent>
                  <p className="text-muted-foreground">
                    Sélectionnez ou créez une entité pour commencer
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* YAML Preview */}
          <div className="col-span-3">
            <Card className="h-[800px]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-4 w-4" />
                  Configuration YAML
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs value={yamlPreview} onValueChange={(v) => setYamlPreview(v as any)}>
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="transform">transform.yml</TabsTrigger>
                    <TabsTrigger value="export">export.yml</TabsTrigger>
                  </TabsList>
                  <TabsContent value="transform" className="mt-4">
                    <div className="relative">
                      <ScrollArea className="h-[420px] border rounded-lg p-3">
                        <pre className="text-xs font-mono">
                          {generateTransformYaml()}
                        </pre>
                      </ScrollArea>
                      <Button
                        size="sm"
                        variant="outline"
                        className="absolute top-2 right-2"
                        onClick={() => copyToClipboard(generateTransformYaml())}
                      >
                        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      </Button>
                    </div>
                  </TabsContent>
                  <TabsContent value="export" className="mt-4">
                    <div className="relative">
                      <ScrollArea className="h-[420px] border rounded-lg p-3">
                        <pre className="text-xs font-mono">
                          {generateExportYaml()}
                        </pre>
                      </ScrollArea>
                      <Button
                        size="sm"
                        variant="outline"
                        className="absolute top-2 right-2"
                        onClick={() => copyToClipboard(generateExportYaml())}
                      >
                        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      </Button>
                    </div>
                  </TabsContent>
                </Tabs>

                <div className="mt-4 space-y-2">
                  <Button className="w-full" variant="default">
                    <Save className="h-4 w-4 mr-2" />
                    Sauvegarder la configuration
                  </Button>
                  <Button className="w-full" variant="outline">
                    <Download className="h-4 w-4 mr-2" />
                    Exporter les fichiers YAML
                  </Button>
                  <Button className="w-full" variant="outline">
                    <Eye className="h-4 w-4 mr-2" />
                    Prévisualiser le site
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Gestion Dynamique</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                Ajoutez, modifiez et supprimez des entités selon vos besoins.
                Chaque entité peut avoir ses propres transformations et widgets.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Compatibilité Automatique</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                Les widgets incompatibles sont automatiquement désactivés.
                Le système vérifie les données requises vs disponibles.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Génération YAML</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                Visualisez en temps réel les fichiers de configuration générés.
                Exportez-les directement vers votre projet.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </DemoWrapper>
  )
}

export { EntityCentricDemo }
