/**
 * ImportProgress - Shows import execution progress
 *
 * With steps indicator and current entity display
 */

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react'
import { createEntitiesBulk } from '@/lib/api/smart-config'
import { executeImportAll, getImportStatus } from '@/lib/api/import'
import type { AutoConfigureResponse } from '@/lib/api/smart-config'

type ImportStep = 'idle' | 'saving' | 'importing' | 'complete' | 'error'

interface ImportProgressProps {
  config: AutoConfigureResponse
  onComplete: () => void
  onError: (error: string) => void
  autoStart?: boolean
}

export function ImportProgress({
  config,
  onComplete,
  onError,
  autoStart = true,
}: ImportProgressProps) {
  const [step, setStep] = useState<ImportStep>('idle')
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [importDetails, setImportDetails] = useState<{
    totalEntities: number
    processedEntities: number
    currentEntity?: string
  }>({ totalEntities: 0, processedEntities: 0 })

  const executeImport = useCallback(async () => {
    try {
      setStep('saving')
      setProgress(10)
      setError(null)

      // Step 1: Save entities to import.yml
      await createEntitiesBulk(config.entities)

      setProgress(30)

      // Step 2: Execute the real import
      setStep('importing')
      const importResponse = await executeImportAll(false)
      const jobId = importResponse.job_id

      // Step 3: Poll for import status
      const pollInterval = 500
      const maxWaitTime = 600000 // 10 minutes max
      const startTime = Date.now()

      let lastProgress = 30

      while (Date.now() - startTime < maxWaitTime) {
        const status = await getImportStatus(jobId)

        // Update import details
        setImportDetails({
          totalEntities: status.total_entities || 0,
          processedEntities: status.processed_entities || 0,
          currentEntity: status.current_entity,
        })

        // Calculate progress (30% already done for config save, 30-100% for import)
        if (status.total_entities > 0) {
          const importProgress = (status.processed_entities / status.total_entities) * 70
          lastProgress = 30 + importProgress
          setProgress(Math.round(lastProgress))
        }

        if (status.status === 'completed') {
          setProgress(100)
          setStep('complete')
          onComplete()
          return
        } else if (status.status === 'failed') {
          throw new Error(status.errors?.join(', ') || 'Import failed')
        }

        await new Promise((resolve) => setTimeout(resolve, pollInterval))
      }

      throw new Error('Import timed out')
    } catch (err: any) {
      const errMsg = err.message || 'Failed to execute import'
      setError(errMsg)
      setStep('error')
      onError(errMsg)
    }
  }, [config, onComplete, onError])

  useEffect(() => {
    if (autoStart && step === 'idle') {
      executeImport()
    }
  }, [autoStart, step, executeImport])

  if (step === 'error') {
    return (
      <div className="space-y-4 py-4">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-2 h-10 w-10 text-destructive" />
          <h3 className="font-semibold">Import echoue</h3>
        </div>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>

        <div className="flex justify-center gap-2">
          <Button onClick={executeImport}>Reessayer</Button>
        </div>
      </div>
    )
  }

  if (step === 'complete') {
    const datasetCount = Object.keys(config.entities.datasets || {}).length
    const referenceCount = Object.keys(config.entities.references || {}).length

    return (
      <div className="space-y-4 py-4">
        <div className="text-center">
          <div className="mx-auto mb-2 inline-flex h-14 w-14 animate-bounce items-center justify-center rounded-full bg-green-500/10">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
          </div>
          <h3 className="text-lg font-semibold">Import termine!</h3>
          <p className="text-sm text-muted-foreground">
            {datasetCount} dataset(s) et {referenceCount} reference(s) importe(s)
          </p>
        </div>
      </div>
    )
  }

  // Saving/importing state
  return (
    <div className="space-y-4 py-4">
      <div className="text-center">
        <Loader2 className="mx-auto mb-2 h-10 w-10 animate-spin text-primary" />
        <h3 className="font-semibold">
          {step === 'saving' && 'Sauvegarde de la configuration...'}
          {step === 'importing' && 'Import des donnees...'}
          {step === 'idle' && 'Preparation...'}
        </h3>
        <p className="text-sm text-muted-foreground">
          {step === 'saving' && 'Ecriture dans import.yml'}
          {step === 'importing' &&
            importDetails.currentEntity &&
            `Import de ${importDetails.currentEntity}...`}
          {step === 'importing' && !importDetails.currentEntity && 'Traitement des entites...'}
        </p>
      </div>

      <div className="mx-auto max-w-md">
        <Progress value={progress} className="h-2" />
        <p className="mt-1 text-center text-xs text-muted-foreground">
          {progress}%
          {importDetails.totalEntities > 0 && (
            <span className="ml-1">
              ({importDetails.processedEntities}/{importDetails.totalEntities})
            </span>
          )}
        </p>
      </div>

      {/* Steps indicator */}
      <div className="mx-auto max-w-md space-y-1 text-sm">
        <div
          className={`flex items-center gap-2 ${progress >= 30 ? 'text-green-600' : 'text-muted-foreground'}`}
        >
          {progress >= 30 ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <Loader2 className="h-4 w-4 animate-spin" />
          )}
          Sauvegarde de la configuration
        </div>

        <div
          className={`flex items-center gap-2 ${
            step === 'importing' || progress >= 100
              ? progress >= 100
                ? 'text-green-600'
                : 'text-primary'
              : 'text-muted-foreground'
          }`}
        >
          {progress >= 100 ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : step === 'importing' ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <div className="h-4 w-4" />
          )}
          Import des donnees
          {importDetails.processedEntities > 0 && step === 'importing' && (
            <span className="text-xs">({importDetails.processedEntities})</span>
          )}
        </div>

        <div className={`flex items-center gap-2 ${progress >= 100 ? 'text-green-600' : 'text-muted-foreground'}`}>
          {progress >= 100 ? <CheckCircle2 className="h-4 w-4" /> : <div className="h-4 w-4" />}
          Termine
        </div>
      </div>
    </div>
  )
}
