import { useEffect, useRef } from 'react'
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
import { useShowcaseStore } from '../showcaseStore'
import { usePipelineStore } from '../pipelineStore'
import { executeImportFromConfig } from '@/lib/api/import'
import { executeTransformAndWait } from '@/lib/api/transform'
import { executeExportAndWait } from '@/lib/api/export'
import { toast } from 'sonner'
import { PipelineMetrics } from './PipelineMetrics'
import yaml from 'js-yaml'
import { YamlEditor } from '@/components/data'
import { useConfig } from '@/hooks/useConfig'
import type { ConfigType } from '@/hooks/useConfig'


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

// Config Editor Tab Component
function ConfigEditorTab({ configName, disabled }: { configName: ConfigType; disabled: boolean }) {
  const { config, loading, updateConfig } = useConfig(configName)

  const handleSave = async (yamlContent: string) => {
    try {
      // Parse YAML to validate and convert to JSON
      const content = yaml.load(yamlContent) as Record<string, any>

      const result = await updateConfig({ content, backup: true })
      toast.success('Configuration sauvegardée', {
        description: result.backup_path
          ? `Backup créé: ${result.backup_path.split('/').pop()}`
          : 'Configuration sauvegardée avec succès'
      })
    } catch (error) {
      if (error instanceof Error) {
        toast.error('Erreur lors de la sauvegarde', {
          description: error.message
        })
      }
      throw error
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Convert config object to YAML string
  const yamlContent = config ? yaml.dump(config, { indent: 2, lineWidth: -1 }) : ''

  return (
    <div className={cn(disabled && "opacity-50 pointer-events-none")}>
      <YamlEditor
        value={yamlContent}
        onSave={handleSave}
        configName={configName}
        showToolbar={true}
        height="500px"
        readOnly={disabled}
      />
      {disabled && (
        <p className="text-sm text-amber-600 dark:text-amber-400 mt-2 text-center">
          ⚠️ L'édition est désactivée pendant l'exécution du pipeline
        </p>
      )}
    </div>
  )
}

export function PipelineSection() {
  const lastImportStatusRef = useRef<string | null>(null)

  // Use shared pipeline store
  const {
    status,
    setStatus,
    activeStepIndex,
    setActiveStepIndex,
    progress,
    setProgress,
    logs,
    addLog,
    clearLogs,
    importResult,
    transformResult,
    exportResult,
    setImportResult,
    setTransformResult,
    setExportResult,
    setCurrentStep,
    reset
  } = usePipelineStore()

  // Fetch real metrics and configs from showcase store
  const {
    metricsLoading,
    loadMetrics,
    importConfig,
    transformConfig,
    exportConfig,
    loadConfiguration
  } = useShowcaseStore()

  const simulationRunning = status === 'running'

  // Load metrics and configs
  useEffect(() => {
    const loadData = async () => {
      await loadMetrics() // Load metrics from shared store
      await loadConfiguration() // Load configs from shared store
    }
    loadData()
  }, [loadMetrics, loadConfiguration])

  const pipelineSteps = createPipelineSteps(importConfig, transformConfig, exportConfig)

  // Helper to get result from store by step id
  const getStepResult = (stepId: string) => {
    if (stepId === 'import') return importResult
    if (stepId === 'transform') return transformResult
    if (stepId === 'export') return exportResult
    return null
  }

  // Helper to check if we have any results
  const hasAnyResults = importResult || transformResult || exportResult

  const runSimulation = async () => {
    await runRealPipeline()
  }

  const runRealPipeline = async () => {
    setStatus('running')
    setProgress(0)
    setActiveStepIndex(0)
    clearLogs()
    lastImportStatusRef.current = null
    addLog('🚀 Démarrage du pipeline Niamoto', 'info')

    try {
      // Step 1: Import
      addLog('📂 Exécution de l\'import...', 'info')
      setActiveStepIndex(0)
      setCurrentStep('import') // Signal import running to tabs
      const importStartTime = Date.now()

      const importJobResult = await executeImportFromConfig(
        {
          // TODO: This showcase uses old API - will be replaced with EntityRegistry v2
          file_name: 'config/import.yml',
          field_mappings: {} // Will use mappings from config file
        } as any,
        500, // pollInterval
        300000, // maxWaitTime
        (progress: number) => {
          setProgress(prev =>
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
      setProgress(prev => Math.max(prev, IMPORT_WEIGHT))
      lastImportStatusRef.current = null

      // Store import results
      setImportResult({
        status: 'completed',
        result: importJobResult.result,
        duration: importDuration
      })

      await loadMetrics() // Refresh metrics after import

      // Step 2: Transform
      setActiveStepIndex(1)
      setCurrentStep('transform') // Signal transform running to tabs
      addLog('🔄 Exécution des transformations...', 'info')
      const transformStartTime = Date.now()

      const transformJobResult = await executeTransformAndWait(
        { config_path: 'config/transform.yml' },
        (progress, message) => {
          setProgress(prev =>
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
      setProgress(prev => Math.max(prev, IMPORT_WEIGHT + TRANSFORM_WEIGHT))

      // Store transform results
      setTransformResult({
        status: 'completed',
        result: transformJobResult.result,
        duration: transformDuration
      })

      // Step 3: Export
      setActiveStepIndex(2)
      setCurrentStep('export') // Signal export running to tabs
      addLog('🌐 Génération du site statique...', 'info')
      const exportStartTime = Date.now()

      const exportJobResult = await executeExportAndWait(
        { config_path: 'config/export.yml' },
        (progress, message) => {
          setProgress(prev =>
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
      setProgress(100)

      // Store export results
      setExportResult({
        status: 'completed',
        result: exportJobResult.result,
        duration: exportDuration
      })

      addLog('✨ Pipeline terminé avec succès!', 'success')
      setStatus('completed')
      setCurrentStep(null) // Clear running state
      toast.success('Pipeline exécuté avec succès!')

    } catch (error) {
      addLog(`❌ Erreur: ${error instanceof Error ? error.message : 'Erreur inconnue'}`, 'error')
      setStatus('error')
      setCurrentStep(null) // Clear running state
      toast.error('Erreur lors de l\'exécution du pipeline')
    } finally {
      // Ne pas réinitialiser automatiquement - garder les résultats affichés
      // L'utilisateur peut cliquer sur "Réinitialiser" s'il veut relancer
    }
  }

  const resetSimulation = () => {
    reset()
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
            const isActive = activeStepIndex === index
            const isComplete = simulationRunning ? activeStepIndex > index : progress > (index + 1) * 33

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
                  onClick={() => !simulationRunning && setActiveStepIndex(index)}
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
                    {getStepResult(step.id) && (
                      <div className="animate-fadeIn">
                        <PipelineMetrics
                          type={step.id as 'import' | 'transform' | 'export'}
                          result={getStepResult(step.id)?.result}
                          duration={getStepResult(step.id)?.duration}
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
                    <span className="font-bold">{progress}%</span>
                  </div>
                  <Progress value={progress} className="h-3" />
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
                  ) : progress === 100 && hasAnyResults ? (
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
                Éditeur de Configuration
              </CardTitle>
              <CardDescription>
                Modifiez les configurations avant de lancer le pipeline
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs value={pipelineSteps[activeStepIndex].id} onValueChange={(value) => {
                const index = pipelineSteps.findIndex(s => s.id === value)
                if (index >= 0) setActiveStepIndex(index)
              }}>
                <TabsList className="grid w-full grid-cols-3 mb-4">
                  {pipelineSteps.map((step) => {
                    const Icon = step.icon
                    return (
                      <TabsTrigger key={step.id} value={step.id} className="gap-2">
                        <Icon className={cn("w-4 h-4", step.color)} />
                        {step.title}
                      </TabsTrigger>
                    )
                  })}
                </TabsList>

                {pipelineSteps.map((step) => (
                  <TabsContent key={step.id} value={step.id} className="mt-0">
                    <ConfigEditorTab
                      configName={step.id as ConfigType}
                      disabled={simulationRunning}
                    />
                  </TabsContent>
                ))}
              </Tabs>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
