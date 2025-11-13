import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useShowcaseStore } from '@/stores/showcaseStore'
import { usePipelineStore } from '@/stores/pipelineStore'
import {
  MapPin,
  Trees,
  Mountain,
  CheckCircle,
  Upload,
  FileText,
  Database,
  AlertCircle,
  Sparkles,
  Clock,
  Activity,
  Loader2
} from 'lucide-react'
import * as yaml from 'js-yaml'
import { useProgressiveCounter } from '@/hooks/useProgressiveCounter'
import { executeImportFromConfig } from '@/lib/api/import'
import { toast } from 'sonner'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface ImportDemoProps {}

export function ImportDemo({}: ImportDemoProps) {
  const {
    importConfig,
    setDemoProgress,
    importMetrics: metrics,
    metricsLoading,
    loadMetrics
  } = useShowcaseStore()

  // Use shared pipeline store
  const {
    importResult,
    setImportResult,
    setCurrentStep: setPipelineStep
  } = usePipelineStore()

  const [activeTab, setActiveTab] = useState('overview')
  const [importProgress, setImportProgress] = useState(0)
  const [importing, setImporting] = useState(false)
  const [importStarted, setImportStarted] = useState(false)
  const [currentStep, setCurrentStep] = useState('')
  const [importLogs, setImportLogs] = useState<string[]>([])
  const [targetMetrics, setTargetMetrics] = useState<any>(null)
  const lastStatusMessageRef = useRef<string | null>(null)

  // Load metrics on mount
  useEffect(() => {
    loadMetrics()
  }, [loadMetrics])

  // Check for existing import result from pipeline store
  useEffect(() => {
    if (importResult && importResult.result?.metrics) {
      // NOTE: Showcase uses specific entity names for display.
      // For production, use EntityRegistry v2 to load entities dynamically.
      const newMetrics = {
        occurrences: importResult.result.metrics.occurrences || 0,
        taxonomy: importResult.result.metrics.taxonomy || 0,
        plots: importResult.result.metrics.plots || 0,
        shapes: importResult.result.metrics.shapes || 0,
        // Capture any additional custom entities dynamically
        ...Object.fromEntries(
          Object.entries(importResult.result.metrics).filter(
            ([key]) => !['occurrences', 'taxonomy', 'plots', 'shapes'].includes(key)
          )
        )
      }
      setTargetMetrics(newMetrics)
      setImportStarted(true)
      setImportProgress(100)
      setCurrentStep('Import terminé!')
    }
  }, [importResult])

  // Set target metrics based on real data
  useEffect(() => {
    if (metrics && !targetMetrics && !importResult) {
      setTargetMetrics(metrics)
    }
  }, [metrics, targetMetrics, importResult])

  // Progressive counters based on real data
  const occurrencesCounter = useProgressiveCounter(
    importStarted ? (targetMetrics?.occurrences || 0) : 0,
    3000,
    importStarted
  )
  const taxaCounter = useProgressiveCounter(
    importStarted ? (targetMetrics?.taxonomy || 0) : 0,
    2500,
    importStarted
  )
  const plotsCounter = useProgressiveCounter(
    importStarted ? (targetMetrics?.plots || 0) : 0,
    1500,
    importStarted
  )
  const shapesCounter = useProgressiveCounter(
    importStarted ? (targetMetrics?.shapes || 0) : 0,
    1000,
    importStarted
  )

  const handleImport = async () => {
    setImporting(true)
    setPipelineStep('import') // Signal to pipeline store that import is running
    setImportStarted(false) // Reset counters first
    setImportProgress(0)
    setImportLogs([])
    lastStatusMessageRef.current = null

    const startTime = Date.now()

    // Real import execution
    try {
        setCurrentStep('Exécution de l\'import réel...')
        setImportLogs(['🚀 Démarrage de l\'import réel...'])

        const result = await executeImportFromConfig(
          {
            // TODO: This showcase uses old API - will be replaced with EntityRegistry v2
            file_name: 'config/import.yml',
            field_mappings: {}
          } as any,
          500, // pollInterval
          300000, // maxWaitTime
          (progress: number) => {
            const nextProgress = Math.max(
              0,
              Math.min(100, Math.round(progress))
            )
            setImportProgress(nextProgress)
            setDemoProgress('import', nextProgress)
          },
          undefined,
          status => {
            if (typeof status?.progress === 'number') {
              const nextProgress = Math.max(
                0,
                Math.min(100, Math.round(status.progress))
              )
              setImportProgress(nextProgress)
              setDemoProgress('import', nextProgress)
            }

            if (status?.message && status.message !== lastStatusMessageRef.current) {
              lastStatusMessageRef.current = status.message
              setCurrentStep(status.message)
              setImportLogs(prev => [...prev, status.message])
            }
          }
        )

        // Refresh metrics after import
        await loadMetrics()

        // Calculate duration
        const duration = (Date.now() - startTime) / 1000

        // Save to shared pipeline store
        setImportResult({
          status: 'completed',
          result: result.result,
          duration: duration
        })

        // Update target metrics with real import results
        // result is the full job object, metrics are in result.result.metrics
        if (result.result?.metrics) {
          const newMetrics = {
            occurrences: result.result.metrics.occurrences || 0,
            taxonomy: result.result.metrics.taxonomy || 0,
            plots: result.result.metrics.plots || 0,
            shapes: result.result.metrics.shapes || 0,
            // Capture any additional custom entities dynamically
            ...Object.fromEntries(
              Object.entries(result.result.metrics).filter(
                ([key]) => !['occurrences', 'taxonomy', 'plots', 'shapes'].includes(key)
              )
            )
          }
          setTargetMetrics(newMetrics)

          // Start the counters after metrics are updated
          // Use a small delay to ensure state is updated
          setTimeout(() => {
            setImportStarted(true)
          }, 100)
        } else {
          console.log('ImportDemo - No metrics found in result!')
        }

        setImportLogs(prev => [...prev,
          `✅ Import terminé: ${result.summary?.total_records || 0} enregistrements`,
          `🎆 Succès!`
        ])
        setImportProgress(100)
        setCurrentStep('Import terminé!')
        await loadMetrics() // Refresh metrics from database
        toast.success('Import réel exécuté avec succès!')
      } catch (error) {
        setImportLogs(prev => [...prev, `❌ Erreur: ${error instanceof Error ? error.message : 'Erreur inconnue'}`])
        toast.error('Erreur lors de l\'import réel')
      } finally {
        setImporting(false)
        setPipelineStep(null) // Clear running state
      }
  }



  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Import des données</h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Chargement et validation des données écologiques depuis la configuration
        </p>
        <div className="flex justify-center gap-2">
          {importStarted && (
            <Badge variant="outline" className="bg-green-500/10">
              <Sparkles className="w-3 h-3 mr-1" />
              La taxonomie est créée automatiquement
            </Badge>
          )}
          {metricsLoading && (
            <Badge variant="outline">
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              Chargement des métriques...
            </Badge>
          )}
          {metrics && (
            <Badge variant="outline" className="bg-blue-500/10">
              <Database className="w-3 h-3 mr-1" />
              {metrics.total_records} enregistrements en base
            </Badge>
          )}
        </div>
      </div>

      {/* Statistics Cards with Progressive Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-primary">
              {occurrencesCounter.value.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">Occurrences importées</p>
            <MapPin className="w-4 h-4 mt-2 text-blue-500" />
            {occurrencesCounter.isAnimating && (
              <Activity className="absolute top-2 right-2 w-3 h-3 text-primary animate-pulse" />
            )}
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-primary">
              {taxaCounter.value.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">Taxa détectés</p>
            <Trees className="w-4 h-4 mt-2 text-green-500" />
            {taxaCounter.isAnimating && (
              <Activity className="absolute top-2 right-2 w-3 h-3 text-primary animate-pulse" />
            )}
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-primary">
              {plotsCounter.value.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">Parcelles créées</p>
            <Database className="w-4 h-4 mt-2 text-purple-500" />
            {plotsCounter.isAnimating && (
              <Activity className="absolute top-2 right-2 w-3 h-3 text-primary animate-pulse" />
            )}
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-primary">
              {shapesCounter.value.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">Formes géographiques</p>
            <Mountain className="w-4 h-4 mt-2 text-orange-500" />
            {shapesCounter.isAnimating && (
              <Activity className="absolute top-2 right-2 w-3 h-3 text-primary animate-pulse" />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Import Configuration Display */}
      {/* NOTE: Tabs are hardcoded for showcase purposes.
           For production apps, generate tabs dynamically from EntityRegistry v2. */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Vue d'ensemble</TabsTrigger>
          <TabsTrigger value="taxonomy">Taxonomie</TabsTrigger>
          <TabsTrigger value="occurrences">Occurrences</TabsTrigger>
          <TabsTrigger value="shapes">Formes</TabsTrigger>
          <TabsTrigger value="yaml">Configuration YAML</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Sources de données configurées</CardTitle>
              <CardDescription>
                Configuration chargée depuis /test-instance/niamoto-nc/config/import.yml
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {importConfig && Object.entries(importConfig).map(([key, value]: [string, any]) => (
                  <div key={key} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-3">
                      <FileText className="w-4 h-4 text-muted-foreground" />
                      <div>
                        <p className="font-medium">{key}</p>
                        <p className="text-sm text-muted-foreground">
                          {(value && (value.path || value.file)) || 'Configuration complexe'}
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Configuré
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="taxonomy">
          <Card>
            <CardHeader>
              <CardTitle>Configuration taxonomique</CardTitle>
              <CardDescription>Hiérarchie et enrichissement API</CardDescription>
            </CardHeader>
            <CardContent>
              {importConfig?.taxonomy && (
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-2">Hiérarchie</h4>
                    <div className="space-y-2">
                      {importConfig.taxonomy.hierarchy?.levels?.map((level: any, idx: number) => (
                        <div key={idx} className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs">
                            {idx + 1}
                          </div>
                          <Badge variant="secondary">{level.name}</Badge>
                          <span className="text-sm text-muted-foreground">→ {level.column}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  {importConfig.taxonomy.api_enrichment && (
                    <div>
                      <h4 className="font-medium mb-2">Enrichissement API</h4>
                      <Badge variant={importConfig.taxonomy.api_enrichment.enabled ? 'default' : 'secondary'}>
                        {importConfig.taxonomy.api_enrichment.enabled ? 'Activé' : 'Désactivé'}
                      </Badge>
                      {importConfig.taxonomy.api_enrichment.api_url && (
                        <p className="text-sm text-muted-foreground mt-2">
                          {importConfig.taxonomy.api_enrichment.api_url}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="occurrences">
          <Card>
            <CardHeader>
              <CardTitle>Configuration des occurrences</CardTitle>
            </CardHeader>
            <CardContent>
              {importConfig?.occurrences && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Type</p>
                      <Badge>{importConfig.occurrences.type}</Badge>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Identifiant</p>
                      <Badge variant="outline">{importConfig.occurrences.identifier}</Badge>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Champ de localisation</p>
                      <Badge variant="outline">{importConfig.occurrences.location_field}</Badge>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Fichier</p>
                      <code className="text-xs bg-muted p-1 rounded">
                        {importConfig.occurrences.path}
                      </code>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="shapes">
          <Card>
            <CardHeader>
              <CardTitle>Formes géographiques</CardTitle>
              <CardDescription>Couches vectorielles et raster</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {importConfig?.shapes && (
                  <div>
                    <h4 className="font-medium mb-2">Shapes ({importConfig.shapes.length})</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {importConfig.shapes.map((shape: any, idx: number) => (
                        <div key={idx} className="p-2 rounded bg-muted/50">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">{shape.type}</span>
                            <Badge variant="outline" className="text-xs">
                              {shape.path.split('.').pop()}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {importConfig?.layers && (
                  <div>
                    <h4 className="font-medium mb-2">Layers ({importConfig.layers.length})</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {importConfig.layers.map((layer: any, idx: number) => (
                        <div key={idx} className="p-2 rounded bg-muted/50">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">{layer.name}</span>
                            <Badge variant="outline" className="text-xs">
                              {layer.type}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="yaml">
          <Card>
            <CardHeader>
              <CardTitle>Configuration YAML brute</CardTitle>
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
                  {yaml.dump(importConfig, { indent: 2, lineWidth: -1 })}
                </SyntaxHighlighter>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Import Simulation with Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Processus d'import</CardTitle>
          <CardDescription>
            Visualisez le processus d'import des données en temps réel
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {(importing || importProgress === 100) && (
            <div className="space-y-4">
              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {currentStep}
                  </span>
                  <span>{importProgress}%</span>
                </div>
                <Progress value={importProgress} className="h-3" />
              </div>

              {/* Import Logs */}
              {importLogs.length > 0 && (
                <ScrollArea className="h-[200px] rounded-md border p-4 bg-muted/20">
                  <div className="space-y-1 font-mono text-xs">
                    {importLogs.map((log, idx) => (
                      <div key={idx} className="animate-fadeIn">
                        {log}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </div>
          )}

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {importProgress === 100 ? (
                <>
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span className="text-sm">Import réussi</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm">Prêt à importer</span>
                </>
              )}
            </div>
            <Button
              onClick={handleImport}
              disabled={importing}
            >
              <Upload className="w-4 h-4 mr-2" />
              {importing ? 'Import en cours...' : 'Lancer l\'import'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
