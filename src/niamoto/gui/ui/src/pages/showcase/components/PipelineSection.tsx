import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  FileInput,
  Settings,
  Globe,
  ArrowRight,
  CheckCircle,
  Clock,
  Play,
  RotateCcw,
  Code,
  Activity,
  Terminal,
  Loader2
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useShowcaseStore } from '@/stores/showcaseStore'
import { executeImportFromConfig } from '@/lib/api/import'
import { executeTransformAndWait } from '@/lib/api/transform'
import { executeExportAndWait } from '@/lib/api/export'
import { toast } from 'sonner'
import { PipelineMetrics } from '@/components/PipelineMetrics'
import yaml from 'js-yaml'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'


// Pipeline steps with real data integration
const createPipelineSteps = (importConfig: any, transformConfig: any, exportConfig: any) => {
  const convertToYaml = (config: any) => {
    if (!config) return 'Configuration non disponible'
    try {
      const data = config.config || config
      return yaml.dump(data, { indent: 2, lineWidth: -1 })
    } catch (error) {
      return JSON.stringify(config, null, 2)
    }
  }

  return [
    {
      id: 'import',
      title: 'Import',
      icon: FileInput,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
      description: 'Chargement des données',
      yamlSnippet: convertToYaml(importConfig)
    },
    {
      id: 'transform',
      title: 'Transform',
      icon: Settings,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/20',
      description: 'Analyse et calculs',
      yamlSnippet: convertToYaml(transformConfig)
    },
    {
      id: 'export',
      title: 'Export',
      icon: Globe,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/20',
      description: 'Génération du site',
      yamlSnippet: convertToYaml(exportConfig)
    }
  ]
}

const IMPORT_WEIGHT = 33
const TRANSFORM_WEIGHT = 33
const EXPORT_WEIGHT = 34

export function PipelineSection() {
  const [activeStep, setActiveStep] = useState(0)
  const [simulationRunning, setSimulationRunning] = useState(false)
  const [simulationProgress, setSimulationProgress] = useState(0)
  const [logs, setLogs] = useState<Array<{ time: string; message: string; type: 'info' | 'success' | 'warning' }>>([])
  const lastImportStatusRef = useRef<string | null>(null)

  // Store job results for metrics display
  const [jobResults, setJobResults] = useState<{
    import?: { result: any; duration: number }
    transform?: { result: any; duration: number }
    export?: { result: any; duration: number }
  }>({})

  // Fetch real metrics and configs from store
  const {
    metricsLoading,
    loadMetrics,
    importConfig,
    transformConfig,
    exportConfig,
    loadConfiguration
  } = useShowcaseStore()

  // Load metrics and configs
  useEffect(() => {
    const loadData = async () => {
      await loadMetrics() // Load metrics from shared store
      await loadConfiguration() // Load configs from shared store
    }
    loadData()
  }, [loadMetrics, loadConfiguration])

  const pipelineSteps = createPipelineSteps(importConfig, transformConfig, exportConfig)

  const addLog = (message: string, type: 'info' | 'success' | 'warning' = 'info') => {
    const time = new Date().toLocaleTimeString('fr-FR')
    setLogs(prev => [...prev, { time, message, type }])
  }

  const runSimulation = async () => {
    await runRealPipeline()
  }

  const runRealPipeline = async () => {
    setSimulationRunning(true)
    setSimulationProgress(0)
    setActiveStep(0)
    setLogs([])
    setJobResults({}) // Reset job results
    lastImportStatusRef.current = null
    addLog('🚀 Démarrage du pipeline Niamoto', 'info')

    try {
      // Step 1: Import
      addLog('📂 Exécution de l\'import...', 'info')
      setActiveStep(0)
      const importStartTime = Date.now()

      const importResult = await executeImportFromConfig(
        {
          import_type: 'all', // Import all types from config
          file_name: 'config/import.yml',
          field_mappings: {} // Will use mappings from config file
        },
        500, // pollInterval
        300000, // maxWaitTime
        (progress: number) => {
          setSimulationProgress(prev =>
            Math.max(prev, Math.round((progress / 100) * IMPORT_WEIGHT))
          )
        },
        undefined,
        status => {
          if (status?.message && status.message !== lastImportStatusRef.current) {
            lastImportStatusRef.current = status.message
            addLog(status.message, 'info')
          }
        }
      )

      const importDuration = (Date.now() - importStartTime) / 1000
      addLog(`✅ Import terminé`, 'success')
      setSimulationProgress(prev => Math.max(prev, IMPORT_WEIGHT))
      lastImportStatusRef.current = null

      // Store import results - extract the result property from the job
      setJobResults(prev => ({
        ...prev,
        import: { result: importResult.result, duration: importDuration }
      }))

      await loadMetrics() // Refresh metrics after import

      // Step 2: Transform
      setActiveStep(1)
      addLog('🔄 Exécution des transformations...', 'info')
      const transformStartTime = Date.now()

      const transformResult = await executeTransformAndWait(
        { config_path: 'config/transform.yml' },
        (progress, message) => {
          setSimulationProgress(prev =>
            Math.max(
              prev,
              IMPORT_WEIGHT + Math.round((progress / 100) * TRANSFORM_WEIGHT)
            )
          )
          if (message) addLog(message, 'info')
        }
      )

      const transformDuration = (Date.now() - transformStartTime) / 1000
      addLog('✅ Transformations terminées', 'success')
      setSimulationProgress(prev => Math.max(prev, IMPORT_WEIGHT + TRANSFORM_WEIGHT))

      // Store transform results - extract the result property from the job
      setJobResults(prev => ({
        ...prev,
        transform: { result: transformResult.result, duration: transformDuration }
      }))

      // Step 3: Export
      setActiveStep(2)
      addLog('🌐 Génération du site statique...', 'info')
      const exportStartTime = Date.now()

      const exportResult = await executeExportAndWait(
        { config_path: 'config/export.yml' },
        (progress, message) => {
          setSimulationProgress(prev =>
            Math.max(
              prev,
              IMPORT_WEIGHT + TRANSFORM_WEIGHT + Math.round((progress / 100) * EXPORT_WEIGHT)
            )
          )
          if (message) addLog(message, 'info')
        }
      )

      const exportDuration = (Date.now() - exportStartTime) / 1000
      addLog('✅ Export terminé avec succès', 'success')
      setSimulationProgress(100)

      // Store export results - extract the result property from the job
      setJobResults(prev => ({
        ...prev,
        export: { result: exportResult.result, duration: exportDuration }
      }))

      addLog('✨ Pipeline terminé avec succès!', 'success')
      toast.success('Pipeline exécuté avec succès!')

    } catch (error) {
      addLog(`❌ Erreur: ${error instanceof Error ? error.message : 'Erreur inconnue'}`, 'warning')
      toast.error('Erreur lors de l\'exécution du pipeline')
    } finally {
      setSimulationRunning(false)
      // Ne pas réinitialiser automatiquement - garder les résultats affichés
      // L'utilisateur peut cliquer sur "Réinitialiser" s'il veut relancer
    }
  }

  const resetSimulation = () => {
    setSimulationRunning(false)
    setSimulationProgress(0)
    setActiveStep(0)
    setLogs([])
    setJobResults({}) // Reset job results
    lastImportStatusRef.current = null
    addLog('🔄 Pipeline réinitialisé', 'info')
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Pipeline de traitement</h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Processus complet de transformation des données en site web
        </p>
      </div>

      {/* Pipeline Visualization with Flow Animation */}
      <div className="relative">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 relative">
          {pipelineSteps.map((step, index) => {
            const Icon = step.icon
            const isActive = activeStep === index
            const isComplete = simulationRunning ? activeStep > index : simulationProgress > (index + 1) * 33

            return (
              <div key={step.id} className="relative group">
                {/* Connector Line */}
                {index < pipelineSteps.length - 1 && (
                  <div className="absolute left-full top-1/2 -translate-y-1/2 w-8 hidden lg:block z-0">
                    <div className="relative h-[2px] bg-border">
                      {isComplete && (
                        <div className="absolute inset-0 bg-gradient-to-r from-green-500 to-transparent" />
                      )}
                    </div>
                    <ArrowRight className={cn(
                      "absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4",
                      isComplete ? "text-green-500" : "text-muted-foreground"
                    )} />
                  </div>
                )}

                <Card
                  className={cn(
                    "transition-all duration-300 cursor-pointer relative overflow-hidden",
                    isActive && "ring-2 shadow-lg",
                    isComplete && "bg-muted/30",
                    step.id === 'import' && isActive && "ring-blue-500/50",
                    step.id === 'transform' && isActive && "ring-green-500/50",
                    step.id === 'export' && isActive && "ring-purple-500/50",
                    !simulationRunning && "hover:ring-1 hover:ring-primary/30"
                  )}
                  onClick={() => !simulationRunning && setActiveStep(index)}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between mb-2">
                      <div className={cn(
                        "w-14 h-14 rounded-full flex items-center justify-center transition-all",
                        step.bgColor,
                        isActive && "scale-110"
                      )}>
                        {isComplete ? (
                          <CheckCircle className={`w-7 h-7 ${step.color}`} />
                        ) : (
                          <Icon className={cn(
                            "w-7 h-7",
                            step.color,
                            isActive && "animate-pulse"
                          )} />
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <Badge variant={isActive ? 'default' : 'outline'}>
                          Étape {index + 1}
                        </Badge>
                        {isActive && simulationRunning && (
                          <Badge variant="outline" className="bg-green-500/10">
                            <Activity className="w-3 h-3 mr-1 animate-pulse" />
                            En cours
                          </Badge>
                        )}
                      </div>
                    </div>
                    <CardTitle className="text-xl">{step.title}</CardTitle>
                    <CardDescription>{step.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Metrics - Show PipelineMetrics when available */}
                    {jobResults[step.id as 'import' | 'transform' | 'export'] && (
                      <div className="animate-fadeIn">
                        <PipelineMetrics
                          type={step.id as 'import' | 'transform' | 'export'}
                          result={jobResults[step.id as 'import' | 'transform' | 'export']?.result}
                          duration={jobResults[step.id as 'import' | 'transform' | 'export']?.duration}
                        />
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )
          })}
        </div>
      </div>

      {/* Control Panel and Details */}
      <Tabs defaultValue="control" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="control">Contrôle</TabsTrigger>
          <TabsTrigger value="logs">Timeline</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="control">
          <Card>
            <CardHeader>
              <CardTitle>Contrôle du pipeline</CardTitle>
              <CardDescription>
                Gérez l'exécution du pipeline de traitement des données
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Progress */}
              {simulationRunning && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="flex items-center gap-2">
                      <Clock className="w-4 h-4 animate-spin" />
                      Progression globale
                    </span>
                    <span className="font-bold">{simulationProgress}%</span>
                  </div>
                  <Progress value={simulationProgress} className="h-3" />
                </div>
              )}

              {/* Controls */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {metricsLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">Chargement des métriques...</span>
                    </>
                  ) : simulationRunning ? (
                    <>
                      <Activity className="w-4 h-4 text-green-500 animate-pulse" />
                      <span className="text-sm">Pipeline en cours...</span>
                    </>
                  ) : simulationProgress === 100 && Object.keys(jobResults).length > 0 ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      <span className="text-sm">Pipeline terminé - Cliquez sur une étape pour voir les résultats</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      <span className="text-sm">Prêt à démarrer</span>
                    </>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={simulationRunning ? "outline" : "default"}
                    onClick={simulationRunning ? resetSimulation : runSimulation}
                    disabled={metricsLoading}
                  >
                    {simulationRunning ? (
                      <>
                        <RotateCcw className="w-4 h-4 mr-2" />
                        Réinitialiser
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        Lancer le pipeline
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Terminal className="w-5 h-5" />
                Timeline d'exécution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[300px] w-full rounded-md border p-4 bg-black/5 dark:bg-white/5">
                {logs.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    Aucun log disponible. Lancez le pipeline pour voir l'activité.
                  </p>
                ) : (
                  <div className="space-y-2 font-mono text-xs">
                    {logs.map((log, index) => (
                      <div
                        key={index}
                        className={cn(
                          "flex items-start gap-3 animate-fadeIn",
                          log.type === 'success' && "text-green-600 dark:text-green-400",
                          log.type === 'warning' && "text-yellow-600 dark:text-yellow-400"
                        )}
                      >
                        <span className="text-muted-foreground opacity-60">{log.time}</span>
                        <span className="flex-1">{log.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="w-5 h-5" />
                Configuration YAML
              </CardTitle>
              <CardDescription>
                Configuration de l'étape {pipelineSteps[activeStep].title}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px] w-full">
                <div className="space-y-4">
                  {pipelineSteps.map((step, index) => {
                    const Icon = step.icon
                    const isActiveStep = activeStep === index
                    const isExpanded = isActiveStep || (!simulationRunning && index === activeStep)

                    return (
                      <div
                        key={step.id}
                        className={cn(
                          "space-y-2 transition-all duration-300",
                          !isActiveStep && simulationRunning && "opacity-30"
                        )}
                      >
                        <button
                          onClick={() => !simulationRunning && setActiveStep(index)}
                          className="flex items-center gap-2 mb-2 w-full text-left hover:opacity-80 transition-opacity"
                          disabled={simulationRunning}
                        >
                          <Icon className={cn("w-4 h-4", step.color)} />
                          <h4 className="font-semibold">{step.title}</h4>
                          {isActiveStep && simulationRunning && (
                            <Badge variant="outline" className="ml-auto bg-green-500/10">
                              <Activity className="w-3 h-3 mr-1 animate-pulse" />
                              En cours
                            </Badge>
                          )}
                        </button>

                        {isExpanded && (
                          <div className="animate-fadeIn">
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
                                {step.yamlSnippet}
                              </SyntaxHighlighter>
                            </ScrollArea>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
