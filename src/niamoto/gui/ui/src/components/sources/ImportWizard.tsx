/**
 * ImportWizard - Dedicated import workflow panel
 *
 * Steps:
 * 1. Select files (existing or upload new)
 * 2. Auto-configure with review (Config/YAML tabs)
 * 3. Execute import with progress
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowLeft,
  ChevronRight,
  Settings2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  getAutoConfigureJob,
  startAutoConfigureJob,
  subscribeToAutoConfigureJobEvents,
  type AutoConfigureProgressEvent,
  type AutoConfigureResponse,
  createEntitiesBulk,
} from '@/lib/api/smart-config'
import { apiClient } from '@/lib/api/client'
import {
  executeImportAll,
  getImportStatus,
  type ImportJobEvent,
} from '@/lib/api/import'
import {
  FileUploadZone,
  ExistingFilesSection,
  AutoConfigDisplay,
  YamlPreview,
} from '@/components/sources'
import type { FileAnalysisStatus } from '@/components/sources/FileUploadZone'

type ImportPhase =
  | 'idle'
  | 'uploading'
  | 'configuring'
  | 'reviewing'
  | 'editing'
  | 'importing'
  | 'complete'
  | 'error'

export function ImportWizard() {
  const { t } = useTranslation(['sources', 'common'])
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [phase, setPhase] = useState<ImportPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [configResult, setConfigResult] = useState<AutoConfigureResponse | null>(null)
  const [filePaths, setFilePaths] = useState<string[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; path: string; size?: number }>>([])
  const [analysisEvents, setAnalysisEvents] = useState<AutoConfigureProgressEvent[]>([])
  const [analysisStage, setAnalysisStage] = useState<string | null>(null)
  const [importDetails, setImportDetails] = useState<{
    totalEntities: number
    processedEntities: number
    currentEntity?: string
    currentEntityType?: string
    phase?: string | null
    message?: string
    progress?: number
    events: ImportJobEvent[]
  }>({ totalEntities: 0, processedEntities: 0, events: [] })
  const analysisEventSourceRef = useRef<EventSource | null>(null)
  const importStartedRef = useRef(false)

  const closeAnalysisStream = useCallback(() => {
    analysisEventSourceRef.current?.close()
    analysisEventSourceRef.current = null
  }, [])

  const runAutoConfigure = useCallback(
    async (paths: string[]) => {
      setFilePaths(paths)
      setPhase('configuring')
      setError(null)
      setAnalysisEvents([])
      setAnalysisStage(null)
      closeAnalysisStream()

      try {
        const job = await startAutoConfigureJob({ files: paths })
        const eventSource = subscribeToAutoConfigureJobEvents(job.job_id, (event) => {
          setAnalysisEvents((previous) => [...previous, event].slice(-30))
          if (event.kind === 'stage') {
            setAnalysisStage(event.message)
          }
        })
        analysisEventSourceRef.current = eventSource

        const startTime = Date.now()
        while (Date.now() - startTime < 180000) {
          const status = await getAutoConfigureJob(job.job_id)
          if (status.status === 'completed' && status.result) {
            closeAnalysisStream()
            setConfigResult(status.result)
            setPhase('reviewing')
            return
          }
          if (status.status === 'failed') {
            throw new Error(status.error || t('wizard.autoConfigError'))
          }
          await new Promise((resolve) => setTimeout(resolve, 400))
        }

        throw new Error(t('wizard.autoConfigTimeout'))
      } catch (err: any) {
        closeAnalysisStream()
        setError(err.message || t('wizard.autoConfigError'))
        setPhase('error')
      }
    },
    [closeAnalysisStream, t]
  )

  // Handle files ready from upload
  const handleFilesReady = useCallback(
    async (files: any[], paths: string[]) => {
      setUploadedFiles(
        files.map((file) => ({
          name: file.filename,
          path: file.path,
          size: file.size,
        }))
      )
      await runAutoConfigure(paths)
    },
    [runAutoConfigure]
  )

  // Handle existing files selected for re-import
  const handleExistingFilesSelected = useCallback(
    async (paths: string[]) => {
      setUploadedFiles(
        paths.map((path) => ({
          name: path.split('/').pop() || path,
          path,
        }))
      )
      await runAutoConfigure(paths)
    },
    [runAutoConfigure]
  )

  // Start import from review phase
  const startImport = () => {
    if (configResult) {
      importStartedRef.current = false
      setImportDetails({
        totalEntities: 0,
        processedEntities: 0,
        phase: 'saving',
        message: t('wizard.writingImportYml'),
        progress: 0,
        events: [],
      })
      setPhase('importing')
    }
  }

  // Handle import complete
  const handleImportComplete = useCallback(async () => {
    setPhase('complete')

    // Refresh all data queries
    queryClient.invalidateQueries({ queryKey: ['entities'] })
    queryClient.invalidateQueries({ queryKey: ['references'] })
    queryClient.invalidateQueries({ queryKey: ['datasets'] })

    // Redirect to sources dashboard after short delay
    setTimeout(() => {
      navigate('/sources')
    }, 1500)
  }, [queryClient, navigate])

  // Handle import error
  const handleImportError = useCallback((errMsg: string) => {
    setError(errMsg)
    setPhase('error')
  }, [])

  // Reset to idle
  const resetToIdle = () => {
    closeAnalysisStream()
    setPhase('idle')
    setError(null)
    setConfigResult(null)
    setFilePaths([])
    setUploadedFiles([])
    setAnalysisEvents([])
    setAnalysisStage(null)
    setImportDetails({ totalEntities: 0, processedEntities: 0, events: [] })
    importStartedRef.current = false
  }

  // Load existing configuration for editing
  const loadExistingConfig = useCallback(async () => {
    setPhase('configuring')
    setError(null)

    try {
      const response = await apiClient.get('/config/import')
      const importConfig = response.data

      if (!importConfig || !importConfig.entities) {
        throw new Error(t('wizard.invalidConfig'))
      }

      // Analyze datasets to get their columns
      const detectedColumns: Record<string, string[]> = {}
      const datasets = importConfig.entities?.datasets || {}

      for (const [name, config] of Object.entries(datasets)) {
        const dsConfig = config as { connector?: { path?: string } }
        if (dsConfig.connector?.path) {
          try {
            const analysisResponse = await apiClient.post('/smart/analyze-file', {
              filepath: dsConfig.connector.path
            })
            if (analysisResponse.data?.columns) {
              detectedColumns[name] = analysisResponse.data.columns
            }
          } catch {
            // Ignore analysis errors
          }
        }
      }

      const configResponse: AutoConfigureResponse = {
        success: true,
        entities: {
          datasets: importConfig.entities?.datasets || {},
          references: importConfig.entities?.references || {},
          metadata: importConfig.metadata || {},
        },
        detected_columns: detectedColumns,
        confidence: 1.0,
        warnings: [],
      }

      setConfigResult(configResponse)
      setPhase('editing')
    } catch (err: any) {
      setError(err.message || t('wizard.loadConfigError'))
      setPhase('error')
    }
  }, [t])

  // Retry from error
  const retryFromError = () => {
    if (filePaths.length > 0) {
      void handleExistingFilesSelected(filePaths)
    } else {
      resetToIdle()
    }
  }

  useEffect(() => {
    return () => {
      closeAnalysisStream()
    }
  }, [closeAnalysisStream])

  const executeImport = useCallback(async () => {
    if (!configResult) return

    try {
      setError(null)
      setImportDetails({
        totalEntities: 0,
        processedEntities: 0,
        phase: 'saving',
        message: t('wizard.writingImportYml'),
        progress: 0,
        currentEntity: undefined,
        currentEntityType: undefined,
        events: [
          {
            timestamp: new Date().toISOString(),
            kind: 'stage' as const,
            message: t('wizard.writingImportYml'),
            phase: 'saving',
          },
        ],
      })

      await createEntitiesBulk({
        entities: configResult.entities,
        auxiliary_sources: configResult.auxiliary_sources || [],
      })

      setImportDetails((previous) => ({
        ...previous,
        phase: 'importing',
        message: t('wizard.importJobStarting'),
        events: [
          ...previous.events,
          {
            timestamp: new Date().toISOString(),
            kind: 'finding' as const,
            message: t('wizard.savingConfigDone'),
            phase: 'saving',
          },
          {
            timestamp: new Date().toISOString(),
            kind: 'detail' as const,
            message: t('wizard.importJobStarting'),
            phase: 'importing',
          },
        ].slice(-30),
      }))

      const importResponse = await executeImportAll(false)
      const jobId = importResponse.job_id
      const pollInterval = 500
      const maxWaitTime = 600000
      const startTime = Date.now()

      while (Date.now() - startTime < maxWaitTime) {
        const status = await getImportStatus(jobId)

        setImportDetails({
          totalEntities: status.total_entities || 0,
          processedEntities: status.processed_entities || 0,
          currentEntity: status.current_entity || undefined,
          currentEntityType: status.current_entity_type || undefined,
          phase: status.phase,
          message: status.message,
          progress: status.progress,
          events: status.events || [],
        })

        if (status.status === 'completed') {
          handleImportComplete()
          return
        }

        if (status.status === 'failed') {
          throw new Error(status.errors?.join(', ') || t('wizard.importFailed'))
        }

        await new Promise((resolve) => setTimeout(resolve, pollInterval))
      }

      throw new Error(t('wizard.importTimedOut'))
    } catch (err: any) {
      handleImportError(err.message || t('wizard.importFailed'))
    }
  }, [configResult, handleImportComplete, handleImportError, t])

  useEffect(() => {
    if (phase === 'importing' && configResult && !importStartedRef.current) {
      importStartedRef.current = true
      void executeImport()
    }
  }, [configResult, executeImport, phase])

  // Handle entity reclassification
  const handleReclassify = useCallback(
    (updatedEntities: AutoConfigureResponse['entities']) => {
      if (!configResult) return
      setConfigResult({
        ...configResult,
        entities: updatedEntities,
      })
    },
    [configResult]
  )

  const isProcessing = ['uploading', 'configuring', 'importing', 'editing'].includes(phase)
  const showCardHeader = phase !== 'configuring'
  const phaseTransitionClassName =
    'animate-in fade-in-0 slide-in-from-bottom-1 duration-300'

  const fileAnalysisStatuses: Record<string, FileAnalysisStatus> = uploadedFiles.reduce(
    (acc, file) => {
      acc[file.name] = {
        state: 'queued',
        message: t('upload.status.queued'),
      }
      return acc
    },
    {} as Record<string, FileAnalysisStatus>
  )

  for (const event of analysisEvents) {
    const eventFile = event.file ? event.file.split('/').pop() : undefined
    const eventEntity = event.entity
    const targetFileName =
      eventFile
      || uploadedFiles.find((file) => {
        const baseName = file.name.replace(/\.[^.]+$/, '')
        return eventEntity === baseName
      })?.name

    if (!targetFileName || !fileAnalysisStatuses[targetFileName]) {
      continue
    }

    if (event.kind === 'detail') {
      fileAnalysisStatuses[targetFileName] = {
        state: 'analyzing',
        message: event.message,
      }
      continue
    }

    if (event.kind === 'finding') {
      const lowered = event.message.toLowerCase()
      const state: FileAnalysisStatus['state'] =
        lowered.includes('review') ? 'review' : 'detected'
      fileAnalysisStatuses[targetFileName] = {
        state,
        message: event.message,
      }
      continue
    }

    if (event.kind === 'complete') {
      for (const key of Object.keys(fileAnalysisStatuses)) {
        fileAnalysisStatuses[key] = {
          state: 'done',
          message: t('upload.status.ready'),
        }
      }
    }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">{t('wizard.importData')}</h1>
        <p className="text-muted-foreground">
          {t('wizard.importDescription')}
        </p>
      </div>

      {/* Import Card */}
      <Card className={phase === 'configuring' ? 'overflow-hidden border-border/60' : undefined}>
        {showCardHeader && (
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              {phase === 'editing' ? <Settings2 className="h-4 w-4" /> : <Upload className="h-4 w-4" />}
              {phase === 'editing'
                ? t('wizard.editConfig')
                : phase === 'reviewing'
                  ? t('wizard.configDetected')
                  : phase === 'importing'
                    ? t('wizard.importInProgress')
                    : phase === 'complete'
                      ? t('wizard.importComplete')
                      : t('wizard.addData')}
            </CardTitle>
            {phase === 'idle' && (
              <CardDescription>
                {t('wizard.dropFilesToStart')}
              </CardDescription>
            )}
          </CardHeader>
        )}
        <CardContent className={phase === 'configuring' ? 'px-6 py-8 sm:px-10' : undefined}>
          {/* Error Alert */}
          {error && phase === 'error' && (
            <div className={`space-y-4 ${phaseTransitionClassName}`}>
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
              <div className="flex gap-2">
                <Button variant="outline" onClick={resetToIdle}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  {t('wizard.back')}
                </Button>
                <Button onClick={retryFromError}>{t('common:actions.retry')}</Button>
              </div>
            </div>
          )}

          {/* Configuring Phase */}
          {phase === 'configuring' && (
            <div className={`space-y-6 ${phaseTransitionClassName}`}>
              <div className="text-center">
                <div className="mx-auto mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                  <Sparkles className="h-6 w-6 animate-pulse text-primary" />
                </div>
                <h3 className="text-lg font-semibold">{t('autoConfig.loading.title')}</h3>
                <p className="text-sm text-muted-foreground">
                  {analysisStage || t('autoConfig.loading.description')}
                </p>
              </div>

              <FileUploadZone
                onFilesReady={handleFilesReady}
                onError={(err) => setError(err)}
                disabled={true}
                compact={true}
                analysisMode={true}
                hideActions={true}
                fileStatuses={fileAnalysisStatuses}
                initialFiles={uploadedFiles}
              />
            </div>
          )}

          {/* Reviewing / Editing / Importing Phases */}
          {['reviewing', 'editing', 'importing'].includes(phase) && configResult && (
            <div className={`space-y-4 ${phaseTransitionClassName}`}>
              {phase === 'editing' && (
                <Alert>
                  <Settings2 className="h-4 w-4" />
                  <AlertDescription>
                    {t('wizard.editExistingConfigDesc')}
                  </AlertDescription>
                </Alert>
              )}

              <Tabs defaultValue="config" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="config">{t('wizard.configurationTab')}</TabsTrigger>
                  <TabsTrigger value="yaml">{t('wizard.yamlTab')}</TabsTrigger>
                </TabsList>

                <TabsContent value="config" className="mt-4">
                  <AutoConfigDisplay
                    result={configResult}
                    editable={phase !== 'importing'}
                    onReclassify={handleReclassify}
                    detectedColumns={configResult.detected_columns || {}}
                    importState={
                      phase === 'importing'
                        ? {
                            active: true,
                            phase: importDetails.phase,
                            message: importDetails.message,
                            progress: importDetails.progress,
                            processedEntities: importDetails.processedEntities,
                            totalEntities: importDetails.totalEntities,
                            currentEntity: importDetails.currentEntity,
                            currentEntityType: importDetails.currentEntityType,
                            events: importDetails.events,
                          }
                        : undefined
                    }
                  />
                </TabsContent>

                <TabsContent value="yaml" className="mt-4">
                  <YamlPreview result={configResult} maxHeight="300px" />
                </TabsContent>
              </Tabs>

              {phase !== 'importing' && (
                <div className="flex items-center justify-between border-t pt-4">
                  <Button variant="outline" onClick={resetToIdle}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                  <Button onClick={startImport} size="lg">
                    <Sparkles className="mr-2 h-4 w-4" />
                    {phase === 'editing' ? t('wizard.saveAndReimport') : t('wizard.startImport')}
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Complete Phase */}
          {phase === 'complete' && (
            <div className={`flex items-center gap-2 rounded-md bg-success/10 p-4 text-success ${phaseTransitionClassName}`}>
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-medium">{t('wizard.importSuccess')}</span>
            </div>
          )}

          {/* Idle Phase */}
          {phase === 'idle' && (
            <div className={`space-y-6 ${phaseTransitionClassName}`}>
              <ExistingFilesSection
                onFilesSelected={handleExistingFilesSelected}
                disabled={isProcessing}
              />

              <FileUploadZone
                onFilesReady={handleFilesReady}
                onError={(err) => setError(err)}
                disabled={isProcessing}
                compact={true}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit existing config button */}
      {phase === 'idle' && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={loadExistingConfig}>
            <Settings2 className="mr-2 h-4 w-4" />
            {t('wizard.modifyExistingConfig')}
          </Button>
        </div>
      )}

    </div>
  )
}
