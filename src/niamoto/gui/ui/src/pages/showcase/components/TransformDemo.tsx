import { useState, useMemo, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useShowcaseStore } from '@/stores/showcaseStore'
import { useProgressiveCounter } from '@/hooks/useProgressiveCounter'
import { listEntities, getEntityDetail, type EntitySummary, type EntityDetail } from '@/lib/api/entities'
import {
  Settings,
  BarChart3,
  MapPin,
  TrendingUp,
  Clock,
  Package,
  ChevronRight,
  Play,
  CheckCircle,
  Database,
  ArrowRight,
  GitBranch,
  Sparkles
} from 'lucide-react'
import * as yaml from 'js-yaml'
import { executeTransformAndWait } from '@/lib/api/transform'
import { toast } from 'sonner'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface TransformDemoProps {}

export function TransformDemo({}: TransformDemoProps) {
  const { transformConfig, exportConfig, setDemoProgress } = useShowcaseStore()
  const [activeGroup, setActiveGroup] = useState(0)
  const [transforming, setTransforming] = useState(false)
  const [transformProgress, setTransformProgress] = useState(0)
  const [transformStarted, setTransformStarted] = useState(false)
  const [selectedWidget, setSelectedWidget] = useState<string | null>(null)
  const [targetMetrics, setTargetMetrics] = useState<{
    widgets: number
    items: number
    duration: number
  }>({ widgets: 0, items: 0, duration: 0 })
  const [groupMetrics, setGroupMetrics] = useState<{
    [group: string]: { count: number; total: number }
  }>({})

  // Dynamic preview state
  const [previewGroupBy, setPreviewGroupBy] = useState<string>('taxon')
  const [entities, setEntities] = useState<EntitySummary[]>([])
  const [selectedEntityId, setSelectedEntityId] = useState<number | null>(null)
  const [entityDetail, setEntityDetail] = useState<EntityDetail | null>(null)
  const [selectedTransformKey, setSelectedTransformKey] = useState<string | null>(null)
  const [loadingEntities, setLoadingEntities] = useState(false)
  const [loadingEntityDetail, setLoadingEntityDetail] = useState(false)

  const widgetsCounter = useProgressiveCounter(
    transformStarted ? targetMetrics.widgets : 0,
    2500,
    transformStarted
  )

  const itemsCounter = useProgressiveCounter(
    transformStarted ? targetMetrics.items : 0,
    2000,
    transformStarted
  )

  // Parse dependencies from transform and export configs
  const dependencies = useMemo(() => {
    if (!transformConfig || !exportConfig) return []

    const deps: Array<{
      transformer: string
      widget: string
      plugin: string
      groupBy: string
    }> = []

    // Parse export config to find data_source references
    const exports = exportConfig.exports || []
    exports.forEach((exp: any) => {
      const groups = exp.groups || []
      groups.forEach((group: any) => {
        const groupBy = group.group_by
        const widgets = group.widgets || []

        widgets.forEach((widget: any) => {
          const dataSource = widget.data_source
          const pluginName = widget.plugin

          if (dataSource && pluginName) {
            deps.push({
              transformer: dataSource,
              widget: pluginName,
              plugin: pluginName,
              groupBy: groupBy
            })
          }
        })
      })
    })

    return deps
  }, [transformConfig, exportConfig])

  // Group dependencies by groupBy for visualization
  const dependenciesByGroup = useMemo(() => {
    const grouped: Record<string, typeof dependencies> = {}

    dependencies.forEach(dep => {
      if (!grouped[dep.groupBy]) {
        grouped[dep.groupBy] = []
      }
      grouped[dep.groupBy].push(dep)
    })

    return grouped
  }, [dependencies])

  // Load entities when group_by changes
  useEffect(() => {
    const loadEntityList = async () => {
      setLoadingEntities(true)
      try {
        // Pas de limite - récupérer toutes les entités
        const data = await listEntities(previewGroupBy)
        // Ensure data is an array
        const entitiesList = Array.isArray(data) ? data : []
        setEntities(entitiesList)
        // Auto-select first entity if available
        if (entitiesList.length > 0) {
          setSelectedEntityId(entitiesList[0].id)
        } else {
          setSelectedEntityId(null)
        }
      } catch (error) {
        console.error('Failed to load entities:', error)
        setEntities([])
        setSelectedEntityId(null)
      } finally {
        setLoadingEntities(false)
      }
    }
    loadEntityList()
  }, [previewGroupBy])

  // Load entity detail when entity is selected
  useEffect(() => {
    if (!selectedEntityId) {
      setEntityDetail(null)
      setSelectedTransformKey(null)
      return
    }

    const loadEntity = async () => {
      setLoadingEntityDetail(true)
      try {
        const data = await getEntityDetail(previewGroupBy, selectedEntityId)
        setEntityDetail(data)
        // Auto-select first transformation if available
        const transformKeys = Object.keys(data.widgets_data || {})
        if (transformKeys.length > 0) {
          setSelectedTransformKey(transformKeys[0])
        } else {
          setSelectedTransformKey(null)
        }
      } catch (error) {
        console.error('Failed to load entity detail:', error)
        setEntityDetail(null)
        setSelectedTransformKey(null)
      } finally {
        setLoadingEntityDetail(false)
      }
    }
    loadEntity()
  }, [selectedEntityId, previewGroupBy])

  // Get current transformation data
  const currentTransformationData = useMemo(() => {
    if (!entityDetail || !selectedTransformKey) return null

    const transformData = entityDetail.widgets_data[selectedTransformKey]
    if (!transformData) return null

    return {
      entity: {
        id: entityDetail.id,
        name: entityDetail.name,
        group_by: entityDetail.group_by
      },
      transformation: selectedTransformKey,
      jsonData: transformData
    }
  }, [entityDetail, selectedTransformKey])

  const runTransformation = async () => {
    setTransforming(true)
    setTransformStarted(false)
    setTransformProgress(0)

    const startTime = Date.now()

    try {
      const result = await executeTransformAndWait(
        { config_path: 'config/transform.yml' },
        (progress) => {
          setTransformProgress(progress)
        }
      )

      // Extract real metrics from result
      if (result.result) {
        const transformations = result.result.transformations || {}
        const metrics = result.result.metrics || {}

        let totalWidgets = 0
        const groups: { [group: string]: { count: number; total: number } } = {}

        // Count total widgets generated and group by group name
        Object.values(transformations).forEach((trans: any) => {
          if (trans && trans.generated !== undefined) {
            totalWidgets += trans.generated

            const groupName = trans.group || 'default'
            if (!groups[groupName]) {
              groups[groupName] = { count: 0, total: 0 }
            }
            groups[groupName].count += 1
            groups[groupName].total += trans.generated
          }
        })

        const totalItems = metrics.total_transformations || Object.keys(transformations).length
        const duration = metrics.execution_time
          ? metrics.execution_time.toFixed(1)
          : ((Date.now() - startTime) / 1000).toFixed(1)

        const newMetrics = {
          widgets: totalWidgets,
          items: totalItems,
          duration: parseFloat(duration)
        }

        setTargetMetrics(newMetrics)
        setGroupMetrics(groups)

        // Start counters after metrics are updated
        setTimeout(() => {
          setTransformStarted(true)
        }, 100)
      }

      setTransformProgress(100)
      setDemoProgress('transform', 100)
      toast.success('Transformations terminées avec succès!')
    } catch (error) {
      console.error('Transform error:', error)
      toast.error('Erreur lors des transformations')
    } finally {
      setTransforming(false)
    }
  }

  const groups = Array.isArray(transformConfig) ? transformConfig : []
  const currentGroup = groups[activeGroup] || {}

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Transformation des données</h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Calculs statistiques et préparation des données pour les visualisations
        </p>
      </div>

      {/* Group Selector */}
      {groups.length > 0 && (
        <div className="flex justify-center gap-4">
          {groups.map((group: any, idx: number) => (
            <Button
              key={idx}
              variant={activeGroup === idx ? 'default' : 'outline'}
              onClick={() => setActiveGroup(idx)}
              className="capitalize"
            >
              {group.group_by}
              {group.widgets_data && (
                <Badge variant="secondary" className="ml-2">
                  {Object.keys(group.widgets_data).length} transformations
                </Badge>
              )}
            </Button>
          ))}
        </div>
      )}

      {/* Transformation Details */}
      <Tabs defaultValue="widgets" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="widgets">Transformations</TabsTrigger>
          <TabsTrigger value="architecture">Architecture</TabsTrigger>
          <TabsTrigger value="graph">Graphe</TabsTrigger>
          <TabsTrigger value="preview">Aperçu live</TabsTrigger>
          <TabsTrigger value="yaml">YAML</TabsTrigger>
        </TabsList>

        <TabsContent value="widgets">
          <div className="grid grid-cols-1 gap-4">
            {/* Widget List */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentGroup.widgets_data && Object.entries(currentGroup.widgets_data).map(([key, widget]: [string, any]) => (
                <Card
                  key={key}
                  className={`cursor-pointer transition-all hover:ring-2 hover:ring-primary/50 ${
                    selectedWidget === key ? 'ring-2 ring-primary' : ''
                  }`}
                  onClick={() => setSelectedWidget(selectedWidget === key ? null : key)}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">{key}</CardTitle>
                      <Badge variant="outline">
                        <Package className="w-3 h-3 mr-1" />
                        {widget.plugin}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="text-xs text-muted-foreground">
                        Plugin de transformation
                      </div>
                      <div className="flex items-center gap-2">
                        {widget.plugin === 'field_aggregator' && <Settings className="w-4 h-4 text-blue-500" />}
                        {widget.plugin === 'geospatial_extractor' && <MapPin className="w-4 h-4 text-green-500" />}
                        {widget.plugin === 'top_ranking' && <TrendingUp className="w-4 h-4 text-purple-500" />}
                        {widget.plugin === 'time_series_analysis' && <Clock className="w-4 h-4 text-orange-500" />}
                        {widget.plugin === 'statistical_summary' && <BarChart3 className="w-4 h-4 text-red-500" />}
                        <span className="text-sm">{widget.plugin.replace(/_/g, ' ')}</span>
                      </div>
                      {widget.params && Object.keys(widget.params).length > 0 && (
                        <div className="pt-2 border-t">
                          <p className="text-xs text-muted-foreground mb-1">Paramètres:</p>
                          <div className="flex flex-wrap gap-1">
                            {Object.keys(widget.params).slice(0, 3).map(param => (
                              <Badge key={param} variant="secondary" className="text-xs">
                                {param}
                              </Badge>
                            ))}
                            {Object.keys(widget.params).length > 3 && (
                              <Badge variant="secondary" className="text-xs">
                                +{Object.keys(widget.params).length - 3}
                              </Badge>
                            )}
                          </div>
                        </div>
                      )}
                      {selectedWidget === key && (
                        <div className="pt-2">
                          <Badge variant="default" className="text-xs">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Sélectionné
                          </Badge>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Widget Detail View */}
            {selectedWidget && currentGroup.widgets_data?.[selectedWidget] && (
              <Card className="animate-fadeIn">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    Configuration détaillée : {selectedWidget}
                  </CardTitle>
                  <CardDescription>
                    Vue complète de la configuration Transform et Export
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Transform Config */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="bg-green-500/10">
                          <Settings className="w-3 h-3 mr-1" />
                          Transform
                        </Badge>
                        <span className="text-sm text-muted-foreground">Configuration de génération</span>
                      </div>
                      <ScrollArea className="h-[500px] w-full">
                        <SyntaxHighlighter
                          language="yaml"
                          style={vscDarkPlus}
                          customStyle={{
                            margin: 0,
                            borderRadius: '0.5rem',
                            fontSize: '0.7rem',
                            padding: '0.75rem'
                          }}
                          showLineNumbers
                        >
                          {yaml.dump({ [selectedWidget]: currentGroup.widgets_data[selectedWidget] }, { indent: 2, lineWidth: -1 })}
                        </SyntaxHighlighter>
                      </ScrollArea>
                    </div>

                    {/* Export Config */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="bg-purple-500/10">
                          <Package className="w-3 h-3 mr-1" />
                          Export
                        </Badge>
                        <span className="text-sm text-muted-foreground">Configuration d'affichage</span>
                      </div>
                      <ScrollArea className="h-[500px] w-full">
                        {exportConfig && exportConfig.exports && exportConfig.exports.length > 0 ? (
                          <SyntaxHighlighter
                            language="yaml"
                            style={vscDarkPlus}
                            customStyle={{
                              margin: 0,
                              borderRadius: '0.5rem',
                              fontSize: '0.7rem',
                              padding: '0.75rem'
                            }}
                            showLineNumbers
                          >
                            {(() => {
                              // Find the matching group in export config based on current group_by
                              const currentGroupBy = currentGroup.group_by
                              const exportData = exportConfig.exports[0] // First export target (web_pages)

                              if (!exportData?.groups) {
                                return '# Configuration export non disponible'
                              }

                              // Find the export group that matches the transform group_by
                              const exportGroup = exportData.groups.find((g: any) => g.group_by === currentGroupBy)

                              if (!exportGroup?.widgets) {
                                return `# Aucun groupe "${currentGroupBy}" trouvé dans la configuration export`
                              }

                              // Find widget by data_source matching the selected widget key
                              const widgetExport = exportGroup.widgets.find((w: any) =>
                                w.data_source === selectedWidget || w.widget_id === selectedWidget
                              )

                              if (widgetExport) {
                                return yaml.dump({
                                  plugin: widgetExport.plugin,
                                  data_source: widgetExport.data_source,
                                  title: widgetExport.title,
                                  description: widgetExport.description,
                                  params: widgetExport.params
                                }, { indent: 2, lineWidth: -1 })
                              }

                              return `# Widget avec data_source "${selectedWidget}" non trouvé dans la configuration export\n# Widgets disponibles:\n${exportGroup.widgets.map((w: any) => `# - ${w.data_source || w.plugin}`).join('\n')}`
                            })()}
                          </SyntaxHighlighter>
                        ) : (
                          <div className="p-4 text-sm text-muted-foreground bg-muted/50 rounded-lg">
                            Configuration export non disponible
                          </div>
                        )}
                      </ScrollArea>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="architecture">
          <Card>
            <CardHeader>
              <CardTitle>Architecture de transformation</CardTitle>
              <CardDescription>
                Comprendre comment les données circulent dans le pipeline
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Data Flow Section */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <Badge variant="outline" className="bg-blue-500/10">1</Badge>
                  Sources de données
                </h4>
                <div className="space-y-2 pl-4">
                  {currentGroup.sources?.map((source: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-muted/50 space-y-2">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-blue-500" />
                        <span className="font-medium">{source.name}</span>
                        <Badge variant="outline" className="ml-auto">{source.data}</Badge>
                      </div>
                      {source.grouping && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground ml-6">
                          <ChevronRight className="w-3 h-3" />
                          Groupé par: <Badge variant="secondary" className="text-xs">{source.grouping}</Badge>
                        </div>
                      )}
                      {source.relation && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground ml-6">
                          <ChevronRight className="w-3 h-3" />
                          Relation: <Badge variant="secondary" className="text-xs">{source.relation.plugin}</Badge>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Grouping Strategy */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-500/10">2</Badge>
                  Stratégie de groupement
                </h4>
                <div className="pl-4">
                  <div className="p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-2">
                      <Settings className="w-4 h-4 text-green-500" />
                      <span className="font-medium capitalize">Group by: {currentGroup.group_by}</span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-2 ml-6">
                      Les données seront regroupées par <span className="font-medium">{currentGroup.group_by}</span>,
                      puis chaque plugin de transformation sera exécuté pour chaque groupe.
                    </p>
                  </div>
                </div>
              </div>

              {/* Widgets Generation */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <Badge variant="outline" className="bg-purple-500/10">3</Badge>
                  Transformations générés
                </h4>
                <div className="pl-4">
                  <div className="grid grid-cols-1 gap-2">
                    {currentGroup.widgets_data && Object.entries(currentGroup.widgets_data).map(([key, widget]: [string, any]) => (
                      <div key={key} className="p-3 rounded-lg bg-muted/50">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Package className="w-4 h-4 text-purple-500" />
                            <span className="font-medium">{key}</span>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {widget.plugin}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2 ml-6">
                          Une colonne "<span className="font-medium">{key}</span>" sera créé pour chaque {currentGroup.group_by}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="graph">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="w-5 h-5" />
                Graphe de dépendances
              </CardTitle>
              <CardDescription>
                Relations entre transformations et widgets d'export
              </CardDescription>
            </CardHeader>
            <CardContent>
              {Object.keys(dependenciesByGroup).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Aucune dépendance trouvée. Chargez les configurations transform et export.
                </div>
              ) : (
                <div className="space-y-8">
                  {Object.entries(dependenciesByGroup).map(([groupBy, deps]) => (
                    <div key={groupBy} className="space-y-4">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-sm">
                          {groupBy}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {deps.length} dépendance{deps.length > 1 ? 's' : ''}
                        </span>
                      </div>

                      <div className="space-y-2">
                        {deps.map((dep, idx) => (
                          <div
                            key={`${dep.transformer}-${dep.widget}-${idx}`}
                            className="flex items-center gap-4 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                          >
                            {/* Transformer */}
                            <div className="flex items-center gap-2 flex-1">
                              <Settings className="w-4 h-4 text-green-500" />
                              <div>
                                <div className="text-sm font-medium">{dep.transformer}</div>
                                <div className="text-xs text-muted-foreground">Transform</div>
                              </div>
                            </div>

                            {/* Arrow */}
                            <ArrowRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />

                            {/* Widget */}
                            <div className="flex items-center gap-2 flex-1">
                              <BarChart3 className="w-4 h-4 text-orange-500" />
                              <div>
                                <div className="text-sm font-medium">{dep.widget}</div>
                                <div className="text-xs text-muted-foreground">Widget</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}

                  {/* Summary stats */}
                  <div className="border-t pt-4 mt-6">
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-bold text-primary">
                          {Object.keys(dependenciesByGroup).length}
                        </div>
                        <div className="text-xs text-muted-foreground">Groupes</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-primary">
                          {dependencies.length}
                        </div>
                        <div className="text-xs text-muted-foreground">Dépendances</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-primary">
                          {new Set(dependencies.map(d => d.transformer)).size}
                        </div>
                        <div className="text-xs text-muted-foreground">Transformations</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preview">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Transformation → Widget
              </CardTitle>
              <CardDescription>
                Exemple concret : de la colonne JSON aux données affichables
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Selectors */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Group By Selector */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Type d'entité</label>
                  <Select value={previewGroupBy} onValueChange={setPreviewGroupBy}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="taxon">Taxons</SelectItem>
                      <SelectItem value="plot">Parcelles</SelectItem>
                      <SelectItem value="shape">Zones</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Entity Selector */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Entité
                    {loadingEntities && <span className="ml-2 text-xs text-muted-foreground">(chargement...)</span>}
                  </label>
                  <Select
                    value={selectedEntityId?.toString() || ''}
                    onValueChange={(value) => setSelectedEntityId(parseInt(value))}
                    disabled={loadingEntities || !Array.isArray(entities) || entities.length === 0}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner une entité" />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.isArray(entities) && entities.map((entity) => (
                        <SelectItem key={entity.id} value={entity.id.toString()}>
                          {entity.display_name || entity.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Transformation Selector */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Transformation
                    {loadingEntityDetail && <span className="ml-2 text-xs text-muted-foreground">(chargement...)</span>}
                  </label>
                  <Select
                    value={selectedTransformKey || ''}
                    onValueChange={setSelectedTransformKey}
                    disabled={loadingEntityDetail || !entityDetail || Object.keys(entityDetail.widgets_data || {}).length === 0}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner une transformation" />
                    </SelectTrigger>
                    <SelectContent>
                      {entityDetail && Object.keys(entityDetail.widgets_data || {}).map((key) => (
                        <SelectItem key={key} value={key}>
                          {key}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Entity info */}
              {currentTransformationData && (
                <>
                  <div className="flex items-center gap-4 p-3 bg-muted/50 rounded-lg">
                    <div className="flex-1">
                      <div className="text-sm font-medium">Données actuelles</div>
                      <div className="text-xs text-muted-foreground">
                        Table: <Badge variant="outline">{currentTransformationData.entity.group_by}</Badge>
                        {' • '}
                        ID: {currentTransformationData.entity.id}
                        {' • '}
                        {currentTransformationData.entity.name}
                      </div>
                    </div>
                    <div className="text-sm">
                      <Settings className="w-4 h-4 inline mr-1 text-green-500" />
                      {currentTransformationData.transformation}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left: JSON data display */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-primary" />
                        <h4 className="font-semibold">Données JSON stockées</h4>
                      </div>
                      <p className="text-xs text-muted-foreground mb-3">
                        Colonne <code className="bg-muted px-1 py-0.5 rounded">{currentTransformationData.transformation}</code> dans la table <code className="bg-muted px-1 py-0.5 rounded">{currentTransformationData.entity.group_by}</code>
                      </p>
                      <ScrollArea className="h-[400px] w-full rounded-md border">
                        <pre className="p-4 text-xs">
                          {JSON.stringify(currentTransformationData.jsonData, null, 2)}
                        </pre>
                      </ScrollArea>
                    </div>

                    {/* Right: Widget preview */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="w-4 h-4 text-primary" />
                        <h4 className="font-semibold">Widget généré</h4>
                      </div>
                      <p className="text-xs text-muted-foreground mb-3">
                        Widget rendu par le plugin configuré dans export.yml
                      </p>
                      <div className="border rounded-lg bg-background overflow-hidden">
                        <iframe
                          src={`/api/entities/render-widget/${currentTransformationData.entity.group_by}/${currentTransformationData.entity.id}/${currentTransformationData.transformation}`}
                          className="w-full h-[400px] border-0"
                          title="Widget preview"
                          sandbox="allow-scripts allow-same-origin"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div className="border-t pt-4">
                    <div className="flex items-start gap-3 text-sm">
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        💡
                      </div>
                      <div className="space-y-2">
                        <div className="font-medium">Comment ça fonctionne ?</div>
                        <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
                          <li>Le plugin de transformation calcule les données pour chaque entité</li>
                          <li>Les résultats sont stockés en JSON dans la colonne <code className="bg-muted px-1 py-0.5 rounded text-xs">{currentTransformationData.transformation}</code></li>
                          <li>Le widget plugin (configuré dans export.yml) lit ces données JSON</li>
                          <li>Il génère le graphique interactif avec Plotly.js</li>
                          <li>Le widget est intégré dans les pages HTML exportées</li>
                        </ol>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* Loading or empty state */}
              {!currentTransformationData && (
                <div className="text-center py-12 text-muted-foreground">
                  {loadingEntities || loadingEntityDetail ? (
                    <div className="flex flex-col items-center gap-2">
                      <Settings className="w-8 h-8 animate-spin" />
                      <span>Chargement des données...</span>
                    </div>
                  ) : entities.length === 0 ? (
                    <div>Aucune entité trouvée avec des données de transformation</div>
                  ) : !entityDetail ? (
                    <div>Sélectionnez une entité pour voir ses données</div>
                  ) : Object.keys(entityDetail.widgets_data || {}).length === 0 ? (
                    <div>Cette entité n'a pas de données de transformation</div>
                  ) : (
                    <div>Sélectionnez une transformation pour voir ses données</div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="yaml">
          <Card>
            <CardHeader>
              <CardTitle>Configuration YAML</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px] w-full">
                <SyntaxHighlighter
                  language="yaml"
                  style={vscDarkPlus}
                  customStyle={{
                    margin: 0,
                    borderRadius: '0.5rem',
                    fontSize: '0.75rem',
                    padding: '1rem'
                  }}
                  showLineNumbers
                >
                  {yaml.dump(currentGroup, { indent: 2, lineWidth: -1 })}
                </SyntaxHighlighter>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Transformation Process */}
      <Card>
        <CardHeader>
          <CardTitle>Processus de transformation</CardTitle>
          <CardDescription>
            Calcul des statistiques et métriques
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {transforming && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Transformation en cours...</span>
                <span>{transformProgress}%</span>
              </div>
              <Progress value={transformProgress} />
              <div className="text-xs text-muted-foreground">
                {transformProgress < 25 && 'Chargement des données...'}
                {transformProgress >= 25 && transformProgress < 50 && 'Calcul des agrégations...'}
                {transformProgress >= 50 && transformProgress < 75 && 'Analyse statistique...'}
                {transformProgress >= 75 && transformProgress < 100 && 'Génération des tables...'}
                {transformProgress === 100 && 'Transformation terminée !'}
              </div>
            </div>
          )}

          {/* Stats display when complete */}
          {transformProgress === 100 && transformStarted && (
            <>
              <div className="grid grid-cols-3 gap-4 mt-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">{widgetsCounter.value.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">Transformations générés</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">{itemsCounter.value.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">Types de transformations</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">{targetMetrics.duration}s</div>
                  <p className="text-xs text-muted-foreground">Temps de calcul</p>
                </div>
              </div>

              {/* Group breakdown */}
              {Object.keys(groupMetrics).length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <h4 className="text-sm font-medium mb-3">Détail par groupe</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Object.entries(groupMetrics).map(([group, data]) => (
                      <div key={group} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="capitalize">{group}</Badge>
                          <span className="text-sm text-muted-foreground">
                            {data.count} type{data.count > 1 ? 's' : ''}
                          </span>
                        </div>
                        <div className="text-sm font-medium">
                          {data.total.toLocaleString()} transformations
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {transformProgress === 100 ? (
                <>
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span className="text-sm">Transformation réussie</span>
                </>
              ) : (
                <>
                  <Settings className="w-4 h-4 text-muted-foreground animate-spin" />
                  <span className="text-sm">Prêt à transformer</span>
                </>
              )}
            </div>
            <Button
              onClick={runTransformation}
              disabled={transforming}
            >
              <Play className="w-4 h-4 mr-2" />
              {transforming ? 'Transformation...' : 'Lancer la transformation'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
