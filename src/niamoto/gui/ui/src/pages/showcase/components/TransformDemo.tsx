import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { useShowcaseStore } from '@/stores/showcaseStore'
import { useProgressiveCounter } from '@/hooks/useProgressiveCounter'
import {
  Settings,
  BarChart3,
  MapPin,
  TrendingUp,
  Clock,
  Package,
  ChevronRight,
  Play,
  CheckCircle
} from 'lucide-react'
import * as yaml from 'js-yaml'
import { executeTransformAndWait } from '@/lib/api/transform'
import { toast } from 'sonner'

interface TransformDemoProps {}

export function TransformDemo({}: TransformDemoProps) {
  const { transformConfig, setDemoProgress } = useShowcaseStore()
  const [activeGroup, setActiveGroup] = useState(0)
  const [transforming, setTransforming] = useState(false)
  const [transformProgress, setTransformProgress] = useState(0)
  const [transformStarted, setTransformStarted] = useState(false)
  const [targetMetrics, setTargetMetrics] = useState<{
    widgets: number
    items: number
    duration: number
  }>({ widgets: 0, items: 0, duration: 0 })
  const [groupMetrics, setGroupMetrics] = useState<{
    [group: string]: { count: number; total: number }
  }>({})

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

  const runTransformation = async () => {
    setTransforming(true)
    setTransformStarted(false)
    setTransformProgress(0)

    const startTime = Date.now()

    try {
      const result = await executeTransformAndWait(
        { config_path: 'config/transform.yml' },
        (progress, message) => {
          setTransformProgress(progress)
          console.log('Transform progress:', progress, message)
        }
      )

      console.log('Transform completed:', result)
      console.log('Transform result.result:', result.result)

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

        console.log('TransformDemo - Metrics:', { totalWidgets, totalItems, duration, groups })

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
                  {Object.keys(group.widgets_data).length} widgets
                </Badge>
              )}
            </Button>
          ))}
        </div>
      )}

      {/* Transformation Details */}
      <Tabs defaultValue="widgets" className="w-full">
        <TabsList>
          <TabsTrigger value="widgets">Widgets configurés</TabsTrigger>
          <TabsTrigger value="dependencies">Dépendances</TabsTrigger>
          <TabsTrigger value="yaml">Configuration YAML</TabsTrigger>
        </TabsList>

        <TabsContent value="widgets">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {currentGroup.widgets_data && Object.entries(currentGroup.widgets_data).map(([key, widget]: [string, any]) => (
              <Card key={key}>
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
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="dependencies">
          <Card>
            <CardHeader>
              <CardTitle>Flux de données</CardTitle>
              <CardDescription>
                Dépendances entre transformations et widgets
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {currentGroup.sources?.map((source: any, idx: number) => (
                  <div key={idx} className="flex items-center gap-4">
                    <Badge variant="outline">{source.name}</Badge>
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    <Badge>{source.grouping}</Badge>
                    {source.relation && (
                      <>
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                        <Badge variant="secondary">{source.relation.plugin}</Badge>
                      </>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-6 pt-6 border-t">
                <h4 className="font-medium mb-3">Widgets compatibles</h4>
                <div className="grid grid-cols-2 gap-2">
                  {currentGroup.widgets_data && Object.entries(currentGroup.widgets_data).map(([key]: [string, any]) => (
                    <div key={key} className="flex items-center justify-between p-2 rounded bg-muted/50">
                      <span className="text-sm">{key}</span>
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="yaml">
          <Card>
            <CardHeader>
              <CardTitle>Configuration YAML</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px] w-full rounded-md border p-4">
                <pre className="text-xs font-mono">
                  <code>{yaml.dump(currentGroup, { indent: 2 })}</code>
                </pre>
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
                {transformProgress >= 75 && transformProgress < 100 && 'Génération des widgets...'}
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
                  <p className="text-xs text-muted-foreground">Widgets générés</p>
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
                          {data.total.toLocaleString()} widgets
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
