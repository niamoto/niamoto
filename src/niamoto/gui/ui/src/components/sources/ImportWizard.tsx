/**
 * ImportWizard - Dedicated import workflow panel
 *
 * Steps:
 * 1. Select files (existing or upload new)
 * 2. Auto-configure with review (Config/YAML tabs)
 * 3. Execute import with progress
 */

import { useState, useCallback } from 'react'
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
import { autoConfigureEntities, type AutoConfigureResponse } from '@/lib/api/smart-config'
import { apiClient } from '@/lib/api/client'
import {
  FileUploadZone,
  ExistingFilesSection,
  AutoConfigDisplay,
  YamlPreview,
  ImportProgress,
} from '@/components/sources'

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

  // Handle files ready from upload
  const handleFilesReady = useCallback(
    async (_files: any[], paths: string[]) => {
      setFilePaths(paths)
      setPhase('configuring')
      setError(null)

      try {
        const result = await autoConfigureEntities({ files: paths })
        if (!result.success) {
          throw new Error('Auto-configuration failed')
        }
        setConfigResult(result)
        setPhase('reviewing')
      } catch (err: any) {
        setError(err.message || t('wizard.autoConfigError'))
        setPhase('error')
      }
    },
    [t]
  )

  // Handle existing files selected for re-import
  const handleExistingFilesSelected = useCallback(
    async (paths: string[]) => {
      setFilePaths(paths)
      setPhase('configuring')
      setError(null)

      try {
        const result = await autoConfigureEntities({ files: paths })
        if (!result.success) {
          throw new Error('Auto-configuration failed')
        }
        setConfigResult(result)
        setPhase('reviewing')
      } catch (err: any) {
        setError(err.message || t('wizard.autoConfigError'))
        setPhase('error')
      }
    },
    [t]
  )

  // Start import from review phase
  const startImport = () => {
    if (configResult) {
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
    setPhase('idle')
    setError(null)
    setConfigResult(null)
    setFilePaths([])
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
      handleExistingFilesSelected(filePaths)
    } else {
      resetToIdle()
    }
  }

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
      <Card>
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
        <CardContent>
          {/* Error Alert */}
          {error && phase === 'error' && (
            <div className="space-y-4">
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
            <AutoConfigDisplay result={null} isLoading={true} />
          )}

          {/* Reviewing Phase */}
          {phase === 'reviewing' && configResult && (
            <div className="space-y-4">
              <Tabs defaultValue="config" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="config">Configuration</TabsTrigger>
                  <TabsTrigger value="yaml">YAML</TabsTrigger>
                </TabsList>

                <TabsContent value="config" className="mt-4">
                  <AutoConfigDisplay
                    result={configResult}
                    editable={true}
                    onReclassify={handleReclassify}
                    detectedColumns={configResult.detected_columns || {}}
                  />
                </TabsContent>

                <TabsContent value="yaml" className="mt-4">
                  <YamlPreview result={configResult} maxHeight="300px" />
                </TabsContent>
              </Tabs>

              <div className="flex items-center justify-between border-t pt-4">
                <Button variant="outline" onClick={resetToIdle}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  {t('common:actions.cancel')}
                </Button>
                <Button onClick={startImport} size="lg">
                  <Sparkles className="mr-2 h-4 w-4" />
                  {t('wizard.startImport')}
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Editing Phase */}
          {phase === 'editing' && configResult && (
            <div className="space-y-4">
              <Alert>
                <Settings2 className="h-4 w-4" />
                <AlertDescription>
                  {t('wizard.editExistingConfigDesc')}
                </AlertDescription>
              </Alert>

              <Tabs defaultValue="config" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="config">Configuration</TabsTrigger>
                  <TabsTrigger value="yaml">YAML</TabsTrigger>
                </TabsList>

                <TabsContent value="config" className="mt-4">
                  <AutoConfigDisplay
                    result={configResult}
                    editable={true}
                    onReclassify={handleReclassify}
                    detectedColumns={configResult.detected_columns || {}}
                  />
                </TabsContent>

                <TabsContent value="yaml" className="mt-4">
                  <YamlPreview result={configResult} maxHeight="300px" />
                </TabsContent>
              </Tabs>

              <div className="flex items-center justify-between border-t pt-4">
                <Button variant="outline" onClick={resetToIdle}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  {t('common:actions.cancel')}
                </Button>
                <Button onClick={startImport} size="lg">
                  <Sparkles className="mr-2 h-4 w-4" />
                  {t('wizard.saveAndReimport')}
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Importing Phase */}
          {phase === 'importing' && configResult && (
            <ImportProgress
              config={configResult}
              onComplete={handleImportComplete}
              onError={handleImportError}
              autoStart={true}
            />
          )}

          {/* Complete Phase */}
          {phase === 'complete' && (
            <div className="flex items-center gap-2 rounded-md bg-success/10 p-4 text-success">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-medium">{t('wizard.importSuccess')}</span>
            </div>
          )}

          {/* Idle Phase */}
          {phase === 'idle' && (
            <div className="space-y-6">
              <ExistingFilesSection
                onFilesSelected={handleExistingFilesSelected}
                disabled={isProcessing}
              />

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">{t('wizard.or')}</span>
                </div>
              </div>

              <div>
                <h4 className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <Upload className="h-4 w-4" />
                  {t('wizard.addNewFiles')}
                </h4>
                <FileUploadZone
                  onFilesReady={handleFilesReady}
                  onError={(err) => setError(err)}
                  disabled={isProcessing}
                  compact={true}
                />
              </div>
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

      {/* Help Section */}
      {phase === 'idle' && (
        <div className="rounded-lg bg-muted/50 p-4">
          <h3 className="mb-2 font-medium">{t('wizard.howItWorks')}</h3>
          <ol className="list-inside list-decimal space-y-1 text-sm text-muted-foreground">
            {(t('wizard.howItWorksSteps', { returnObjects: true }) as string[]).map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}
