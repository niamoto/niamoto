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
import { useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowLeft,
  ChevronRight,
  Settings2,
  Copy,
  ChevronDown,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PanelTransition } from '@/components/motion/PanelTransition'
import { Textarea } from '@/components/ui/textarea'
import { type AutoConfigureResponse } from '@/features/import/api/smart-config'
import { apiClient } from '@/shared/lib/api/client'
import {
  FileUploadZone,
  ExistingFilesSection,
  AutoConfigDisplay,
  YamlPreview,
} from '@/features/import/components'
import type { FileAnalysisStatus } from '@/features/import/components/upload/FileUploadZone'
import { useAutoConfigureJob } from '@/features/import/hooks/useAutoConfigureJob'
import { useImportJob } from '@/features/import/hooks/useImportJob'
import { requestBugReport } from '@/features/feedback'
import { useDatasets } from '@/hooks/useDatasets'
import { useReferences } from '@/hooks/useReferences'

type ImportPhase =
  | 'idle'
  | 'uploading'
  | 'configuring'
  | 'reviewing'
  | 'editing'
  | 'importing'
  | 'complete'
  | 'error'

type ImportEntityStatus = 'imported' | 'failed' | 'pending'

const MAX_FEEDBACK_DESCRIPTION_LENGTH = 5000

export function ImportWizard() {
  const { t } = useTranslation(['sources', 'common', 'feedback'])
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const autoStartedRef = useRef(false)

  const [phase, setPhase] = useState<ImportPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [configResult, setConfigResult] = useState<AutoConfigureResponse | null>(null)
  const [filePaths, setFilePaths] = useState<string[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; path: string; size?: number }>>([])
  const [showImportErrorDetails, setShowImportErrorDetails] = useState(false)
  const [reviewTab, setReviewTab] = useState<'config' | 'yaml'>('config')
  const autoConfigureJob = useAutoConfigureJob()
  const importJob = useImportJob()
  const { data: datasetsData } = useDatasets()
  const { data: referencesData } = useReferences()

  const hasExistingImportConfig =
    (datasetsData?.datasets?.length ?? 0) > 0 || (referencesData?.references?.length ?? 0) > 0

  const incomingState = location.state as
    | {
        autoStart?: boolean
        filePaths?: string[]
        uploadedFiles?: Array<{ name: string; path: string; size?: number }>
      }
    | null

  const runAutoConfigure = useCallback(
    async (paths: string[]) => {
      setFilePaths(paths)
      setPhase('configuring')
      setError(null)

      try {
        const result = await autoConfigureJob.start(paths, {
          failed: t('wizard.autoConfigError'),
          timedOut: t('wizard.autoConfigTimeout'),
        })
        setConfigResult(result)
        setPhase('reviewing')
      } catch (err: any) {
        setError(err.message || autoConfigureJob.error || t('wizard.autoConfigError'))
        setPhase('error')
      }
    },
    [autoConfigureJob, t]
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
      importJob.reset()
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
    queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })

    // Redirect to sources dashboard after short delay
    setTimeout(() => {
      navigate('/sources')
    }, 1500)
  }, [queryClient, navigate])

  // Handle import error
  const handleImportError = useCallback((errMsg: string) => {
    setError(errMsg)
    setShowImportErrorDetails(Boolean(importJob.state.errorDetails))
    setPhase('error')
  }, [importJob.state.errorDetails])

  // Reset to idle
  const resetToIdle = () => {
    autoConfigureJob.reset()
    importJob.reset()
    setPhase('idle')
    setError(null)
    setShowImportErrorDetails(false)
    setConfigResult(null)
    setFilePaths([])
    setUploadedFiles([])
  }

  const importErrorDetailsJson = importJob.state.errorDetails
    ? JSON.stringify(importJob.state.errorDetails, null, 2)
    : ''

  const copyImportErrorDetails = useCallback(async () => {
    if (!importErrorDetailsJson) return
    await navigator.clipboard.writeText(importErrorDetailsJson)
  }, [importErrorDetailsJson])

  const sendImportErrorFeedback = useCallback(() => {
    const errorDetails = importJob.state.errorDetails
    if (!errorDetails) return

    const entityName =
      typeof errorDetails.details?.entity_name === 'string'
        ? errorDetails.details.entity_name
        : importJob.state.currentEntity || undefined

    const summary = errorDetails.user_message || errorDetails.message || error || t('wizard.importFailed')
    const title = entityName
      ? t('wizard.feedbackErrorTitleWithEntity', { entity: entityName })
      : t('wizard.feedbackErrorTitle')

    const descriptionSections = [
      t('wizard.feedbackErrorIntro'),
      '',
      t('wizard.feedbackErrorSummaryLabel'),
      summary,
      entityName ? `${t('wizard.feedbackErrorEntityLabel')}\n${entityName}` : null,
      importJob.state.phase
        ? `${t('wizard.feedbackErrorPhaseLabel')}\n${importJob.state.phase}`
        : null,
      errorDetails.error_type
        ? `${t('wizard.feedbackErrorTypeLabel')}\n${errorDetails.error_type}`
        : null,
      '',
      `${t('wizard.feedbackErrorTechnicalDetailsLabel')}\n\`\`\`json\n${importErrorDetailsJson}\n\`\`\``,
    ].filter(Boolean)

    const description = descriptionSections.join('\n\n')
    requestBugReport({
      title,
      description:
        description.length > MAX_FEEDBACK_DESCRIPTION_LENGTH
          ? `${description.slice(0, MAX_FEEDBACK_DESCRIPTION_LENGTH - 27)}\n\n[technical details truncated]`
          : description,
    })
  }, [error, importErrorDetailsJson, importJob.state.currentEntity, importJob.state.errorDetails, importJob.state.phase, t])

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
    if (
      phase === 'idle' &&
      !autoStartedRef.current &&
      incomingState?.autoStart &&
      incomingState.filePaths &&
      incomingState.filePaths.length > 0
    ) {
      autoStartedRef.current = true
      setUploadedFiles(incomingState.uploadedFiles ?? [])
      void runAutoConfigure(incomingState.filePaths)
      navigate(location.pathname, { replace: true, state: null })
    }
  }, [incomingState, location.pathname, navigate, phase, runAutoConfigure])

  useEffect(() => {
    if (phase === 'importing' && configResult && importJob.state.status === 'idle') {
      void importJob.start(configResult, {
        writingImportYml: t('wizard.writingImportYml'),
        importJobStarting: t('wizard.importJobStarting'),
        savingConfigDone: t('wizard.savingConfigDone'),
        importFailed: t('wizard.importFailed'),
        importTimedOut: t('wizard.importTimedOut'),
      })
        .then(() => {
          handleImportComplete()
        })
        .catch((err: any) => {
          handleImportError(err.message || importJob.state.error || t('wizard.importFailed'))
        })
    }
  }, [configResult, handleImportComplete, handleImportError, importJob, phase, t])

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

  const importExecutionSummary = (() => {
    if (!configResult || phase !== 'error') return null

    const plannedEntities = [
      ...Object.keys(configResult.entities.datasets || {}).map((name) => ({
        name,
        type: 'dataset' as const,
      })),
      ...Object.keys(configResult.entities.references || {}).map((name) => ({
        name,
        type: 'reference' as const,
      })),
    ]

    if (plannedEntities.length === 0) return null

    const importedNames = new Set(
      importJob.state.events
        .filter((event) => event.entity_name && event.kind === 'finding' && event.message.startsWith('Imported '))
        .map((event) => event.entity_name as string)
    )

    const failedNames = new Set(
      importJob.state.events
        .filter((event) => event.entity_name && event.kind === 'error')
        .map((event) => event.entity_name as string)
    )

    const entities = plannedEntities.map((entity) => {
      let status: ImportEntityStatus = 'pending'
      if (failedNames.has(entity.name)) {
        status = 'failed'
      } else if (importedNames.has(entity.name)) {
        status = 'imported'
      }

      return { ...entity, status }
    })

    const importedCount = entities.filter((entity) => entity.status === 'imported').length
    const failedCount = entities.filter((entity) => entity.status === 'failed').length
    const pendingCount = entities.filter((entity) => entity.status === 'pending').length

    return {
      entities,
      importedCount,
      failedCount,
      pendingCount,
      errorCount: importJob.state.events.filter((event) => event.kind === 'error').length,
    }
  })()

  for (const event of autoConfigureJob.events) {
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
    <div className="flex h-full flex-col overflow-auto p-6">
      <div className="space-y-6">
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
              {importExecutionSummary && (
                <div className="rounded-md border bg-muted/20 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-sm font-medium">{t('wizard.importExecutionSummary')}</div>
                    <Badge variant="secondary">
                      {t('wizard.importedCount', { count: importExecutionSummary.importedCount })}
                    </Badge>
                    <Badge variant={importExecutionSummary.failedCount > 0 ? 'destructive' : 'secondary'}>
                      {t('wizard.failedCount', { count: importExecutionSummary.failedCount })}
                    </Badge>
                    <Badge variant="outline">
                      {t('wizard.pendingCount', { count: importExecutionSummary.pendingCount })}
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {t('wizard.importStopsOnFirstError')}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {importExecutionSummary.entities.map((entity) => {
                      const variant =
                        entity.status === 'failed'
                          ? 'destructive'
                          : entity.status === 'imported'
                            ? 'default'
                            : 'outline'

                      const label =
                        entity.status === 'failed'
                          ? t('wizard.entityStatusFailed')
                          : entity.status === 'imported'
                            ? t('wizard.entityStatusImported')
                            : t('wizard.entityStatusPending')

                      return (
                        <div
                          key={`${entity.type}:${entity.name}`}
                          className="flex items-center gap-2 rounded-md border bg-background px-2.5 py-1.5 text-sm"
                        >
                          <span className="font-medium">{entity.name}</span>
                          <Badge variant={variant}>{label}</Badge>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
              {importJob.state.errorDetails && (
                <Collapsible
                  open={showImportErrorDetails}
                  onOpenChange={setShowImportErrorDetails}
                  className="rounded-md border bg-muted/30"
                >
                  <div className="flex items-center justify-between gap-3 px-4 py-3">
                    <CollapsibleTrigger className="flex flex-1 items-center justify-between text-left">
                      <div>
                        <div className="text-sm font-medium">{t('wizard.importErrorDetails')}</div>
                        <div className="text-xs text-muted-foreground">
                          {importJob.state.errorDetails.error_type || t('wizard.importFailed')}
                        </div>
                      </div>
                      <ChevronDown
                        className={`h-4 w-4 text-muted-foreground transition-transform ${showImportErrorDetails ? 'rotate-180' : ''}`}
                      />
                    </CollapsibleTrigger>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={sendImportErrorFeedback}
                      >
                        {t('wizard.sendErrorFeedback')}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => void copyImportErrorDetails()}
                      >
                        <Copy className="mr-2 h-4 w-4" />
                        {t('wizard.copyErrorDetails')}
                      </Button>
                    </div>
                  </div>
                  <CollapsibleContent className="px-4 pb-4">
                    <Textarea
                      readOnly
                      value={importErrorDetailsJson}
                      className="min-h-[260px] font-mono text-xs"
                    />
                  </CollapsibleContent>
                </Collapsible>
              )}
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
                  {autoConfigureJob.stage || t('autoConfig.loading.description')}
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

              <Tabs value={reviewTab} onValueChange={(value) => setReviewTab(value as 'config' | 'yaml')} className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="config">{t('wizard.configurationTab')}</TabsTrigger>
                  <TabsTrigger value="yaml">{t('wizard.yamlTab')}</TabsTrigger>
                </TabsList>

                <PanelTransition transitionKey={reviewTab} className="mt-4">
                  {reviewTab === 'config' ? (
                    <AutoConfigDisplay
                      result={configResult}
                      editable={phase !== 'importing'}
                      onReclassify={handleReclassify}
                      detectedColumns={configResult.detected_columns || {}}
                      importState={
                        phase === 'importing'
                          ? {
                              active: true,
                              phase: importJob.state.phase,
                              message: importJob.state.message,
                              progress: importJob.state.progress,
                              processedEntities: importJob.state.processedEntities,
                              totalEntities: importJob.state.totalEntities,
                              currentEntity: importJob.state.currentEntity,
                              currentEntityType: importJob.state.currentEntityType,
                              events: importJob.state.events,
                            }
                          : undefined
                      }
                    />
                  ) : (
                    <YamlPreview result={configResult} maxHeight="300px" />
                  )}
                </PanelTransition>
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
      {phase === 'idle' && hasExistingImportConfig && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={loadExistingConfig}>
            <Settings2 className="mr-2 h-4 w-4" />
            {t('wizard.modifyExistingConfig')}
          </Button>
        </div>
      )}
      </div>
    </div>
  )
}
