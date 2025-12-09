/**
 * Data Panel - Import workflow for Flow
 *
 * Features:
 * - Current import status (datasets & references with counts)
 * - Re-import from existing files
 * - Upload new files with drag & drop
 * - Auto-configure with review (Config/YAML tabs)
 * - Import execution with progress
 */

import { useState, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Upload,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Database,
  AlertCircle,
  Sparkles,
  ArrowLeft,
  ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { getEntities } from '@/lib/api/import'
import { autoConfigureEntities, type AutoConfigureResponse } from '@/lib/api/smart-config'
import {
  FileUploadZone,
  ExistingFilesSection,
  AutoConfigDisplay,
  YamlPreview,
  ImportProgress,
} from '@/components/import'

type ImportPhase =
  | 'idle'
  | 'uploading'
  | 'configuring'
  | 'reviewing'
  | 'importing'
  | 'complete'
  | 'error'

export function DataPanel() {
  const queryClient = useQueryClient()

  // Fetch current entities status
  const {
    data: entities,
    isLoading: entitiesLoading,
    refetch: refetchEntities,
  } = useQuery({
    queryKey: ['entities'],
    queryFn: getEntities,
    staleTime: 10000,
  })

  // Local state
  const [phase, setPhase] = useState<ImportPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [configResult, setConfigResult] = useState<AutoConfigureResponse | null>(null)
  const [filePaths, setFilePaths] = useState<string[]>([])

  const hasData =
    (entities?.datasets?.length ?? 0) > 0 || (entities?.references?.length ?? 0) > 0

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
        setError(err.message || 'Erreur lors de la configuration automatique')
        setPhase('error')
      }
    },
    []
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
        setError(err.message || 'Erreur lors de la configuration automatique')
        setPhase('error')
      }
    },
    []
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

    // Refresh entities list
    await refetchEntities()
    queryClient.invalidateQueries({ queryKey: ['references'] })

    // Reset after delay
    setTimeout(() => {
      setPhase('idle')
      setConfigResult(null)
      setFilePaths([])
    }, 2000)
  }, [refetchEntities, queryClient])

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

  // Retry from error
  const retryFromError = () => {
    if (filePaths.length > 0) {
      handleExistingFilesSelected(filePaths)
    } else {
      resetToIdle()
    }
  }

  // Handle entity reclassification (move between datasets and references)
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

  const isProcessing = ['uploading', 'configuring', 'importing'].includes(phase)

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Donnees</h1>
        <p className="text-muted-foreground">Importez vos donnees et gerez les sources.</p>
      </div>

      {/* Current Status */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-4 w-4" />
              Etat actuel
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetchEntities()}
              disabled={entitiesLoading}
            >
              <RefreshCw className={`h-4 w-4 ${entitiesLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {entitiesLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : !hasData ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              Aucune donnee importee. Commencez par ajouter des fichiers ci-dessous.
            </p>
          ) : (
            <div className="space-y-3">
              {/* Datasets */}
              {entities?.datasets && entities.datasets.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">
                    Datasets
                  </p>
                  <div className="space-y-1">
                    {entities.datasets.map((ds) => (
                      <div
                        key={ds.name}
                        className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-success" />
                          <span className="font-medium">{ds.name}</span>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {ds.connector_type}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* References */}
              {entities?.references && entities.references.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">
                    References
                  </p>
                  <div className="space-y-1">
                    {entities.references.map((ref) => (
                      <div
                        key={ref.name}
                        className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-success" />
                          <span className="font-medium">{ref.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {ref.kind && (
                            <Badge variant="secondary" className="text-xs">
                              {ref.kind}
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Import Section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Upload className="h-4 w-4" />
            {phase === 'reviewing'
              ? 'Configuration detectee'
              : phase === 'importing'
                ? 'Import en cours'
                : phase === 'complete'
                  ? 'Import termine'
                  : hasData
                    ? 'Mettre a jour les donnees'
                    : 'Ajouter des donnees'}
          </CardTitle>
          {phase === 'idle' && (
            <CardDescription>
              {hasData
                ? 'Ajoutez de nouveaux fichiers ou reimportez les fichiers existants.'
                : 'Glissez-deposez vos fichiers pour commencer.'}
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
                  Retour
                </Button>
                <Button onClick={retryFromError}>Reessayer</Button>
              </div>
            </div>
          )}

          {/* Configuring Phase */}
          {phase === 'configuring' && (
            <AutoConfigDisplay result={null} isLoading={true} />
          )}

          {/* Reviewing Phase - Tabs Config/YAML */}
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
                  />
                </TabsContent>

                <TabsContent value="yaml" className="mt-4">
                  <YamlPreview result={configResult} maxHeight="300px" />
                </TabsContent>
              </Tabs>

              {/* Actions */}
              <div className="flex items-center justify-between border-t pt-4">
                <Button variant="outline" onClick={resetToIdle}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Annuler
                </Button>
                <Button onClick={startImport} size="lg">
                  <Sparkles className="mr-2 h-4 w-4" />
                  Lancer l'import
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
              <span className="font-medium">Import termine avec succes !</span>
            </div>
          )}

          {/* Idle Phase - Show existing files + upload zone */}
          {phase === 'idle' && (
            <div className="space-y-6">
              {/* Existing files for re-import */}
              <ExistingFilesSection
                onFilesSelected={handleExistingFilesSelected}
                disabled={isProcessing}
              />

              {/* Separator */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">ou</span>
                </div>
              </div>

              {/* Upload new files */}
              <div>
                <h4 className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <Upload className="h-4 w-4" />
                  Ajouter de nouveaux fichiers
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

      {/* Help Section */}
      {!hasData && phase === 'idle' && (
        <div className="rounded-lg bg-muted/50 p-4">
          <h3 className="mb-2 font-medium">Comment ca marche ?</h3>
          <ol className="list-inside list-decimal space-y-1 text-sm text-muted-foreground">
            <li>Ajoutez vos fichiers (CSV pour les donnees, GeoPackage pour les shapes)</li>
            <li>La configuration est analysee et affichee pour validation</li>
            <li>Les donnees sont importees dans la base</li>
            <li>Les groupes de reference apparaissent dans le menu lateral</li>
          </ol>
        </div>
      )}
    </div>
  )
}
