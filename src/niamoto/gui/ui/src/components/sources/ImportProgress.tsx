/**
 * ImportProgress - Shows import execution progress
 *
 * With steps indicator and current entity display
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react'
import { createEntitiesBulk } from '@/lib/api/smart-config'
import {
  executeImportAll,
  getImportStatus,
  type ImportJobEvent,
} from '@/lib/api/import'
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
  const { t } = useTranslation('sources')
  const [step, setStep] = useState<ImportStep>('idle')
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [importDetails, setImportDetails] = useState<{
    totalEntities: number
    processedEntities: number
    currentEntity?: string
    phase?: string | null
    message?: string
    events: ImportJobEvent[]
  }>({ totalEntities: 0, processedEntities: 0, events: [] })

  // Guard against React 18 StrictMode double-mount
  const importStarted = useRef(false)

  const executeImport = useCallback(async () => {
    try {
      setStep('saving')
      setProgress(0)
      setError(null)
      setImportDetails({
        totalEntities: 0,
        processedEntities: 0,
        phase: 'saving',
        message: t('wizard.writingImportYml'),
        events: [
          {
            timestamp: new Date().toISOString(),
            kind: 'stage',
            message: t('wizard.writingImportYml'),
            phase: 'saving',
          },
        ],
      })

      // Step 1: Save entities to import.yml
      await createEntitiesBulk({
        entities: config.entities,
        auxiliary_sources: config.auxiliary_sources || [],
      })

      setImportDetails((previous) => ({
        ...previous,
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

      // Step 2: Execute the real import
      setStep('importing')
      const importResponse = await executeImportAll(false)
      const jobId = importResponse.job_id

      // Step 3: Poll for import status
      const pollInterval = 500
      const maxWaitTime = 600000 // 10 minutes max
      const startTime = Date.now()

      let lastProgress = 0

      while (Date.now() - startTime < maxWaitTime) {
        const status = await getImportStatus(jobId)

        // Update import details
        setImportDetails({
          totalEntities: status.total_entities || 0,
          processedEntities: status.processed_entities || 0,
          currentEntity: status.current_entity || undefined,
          phase: status.phase,
          message: status.message,
          events: status.events || [],
        })

        if (typeof status.progress === 'number' && status.progress > 0) {
          lastProgress = Math.max(lastProgress, status.progress)
          setProgress(Math.round(lastProgress))
        } else if ((status.total_entities || 0) > 0 && (status.processed_entities || 0) > 0) {
          const importProgress =
            ((status.processed_entities || 0) / (status.total_entities || 1)) * 100
          lastProgress = Math.max(lastProgress, importProgress)
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
    if (autoStart && step === 'idle' && !importStarted.current) {
      importStarted.current = true
      executeImport()
    }
  }, [autoStart, step, executeImport])

  if (step === 'error') {
    return (
      <div className="space-y-4 py-4">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-2 h-10 w-10 text-destructive" />
          <h3 className="font-semibold">{t('wizard.importFailed')}</h3>
        </div>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>

        <div className="flex justify-center gap-2">
          <Button onClick={executeImport}>{t('wizard.retry')}</Button>
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
          <h3 className="text-lg font-semibold">{t('wizard.importComplete')}</h3>
          <p className="text-sm text-muted-foreground">
            {t('wizard.importedSummary', { datasets: datasetCount, references: referenceCount })}
          </p>
        </div>
      </div>
    )
  }

  // Saving/importing state
  const latestEvents = importDetails.events.slice(-8)
  const showMeasuredProgress =
    progress > 0

  return (
    <div className="space-y-6 py-4">
      <div className="text-center">
        <Loader2 className="mx-auto mb-2 h-10 w-10 animate-spin text-primary" />
        <h3 className="font-semibold">
          {step === 'saving' && t('wizard.savingConfig')}
          {step === 'importing' && t('wizard.importingData')}
          {step === 'idle' && t('wizard.preparing')}
        </h3>
        <p className="text-sm text-muted-foreground">
          {step === 'saving' && t('wizard.writingImportYml')}
          {step === 'importing' &&
            (importDetails.message
              || (importDetails.currentEntity
                ? t('wizard.importingEntity', { entity: importDetails.currentEntity })
                : t('wizard.processingEntities')))}
        </p>
      </div>

      {showMeasuredProgress ? (
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
      ) : (
        <div className="mx-auto max-w-md rounded-md border bg-muted/30 px-3 py-2 text-center text-xs text-muted-foreground">
          {t('wizard.progressWillAppear')}
        </div>
      )}

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
          {t('wizard.savingConfigStep')}
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
          {t('wizard.importDataStep')}
          {importDetails.processedEntities > 0 && step === 'importing' && (
            <span className="text-xs">({importDetails.processedEntities})</span>
          )}
        </div>

        <div className={`flex items-center gap-2 ${progress >= 100 ? 'text-green-600' : 'text-muted-foreground'}`}>
          {progress >= 100 ? <CheckCircle2 className="h-4 w-4" /> : <div className="h-4 w-4" />}
          {t('wizard.complete')}
        </div>
      </div>

      <div className="mx-auto w-full max-w-2xl rounded-lg border bg-muted/30 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-medium">{t('wizard.importLiveFeed')}</div>
          <div className="text-xs text-muted-foreground">
            {importDetails.phase || step}
          </div>
        </div>
        <div className="space-y-2">
          {latestEvents.length > 0 ? (
            latestEvents.map((event, index) => (
              <div
                key={`${event.timestamp}-${index}`}
                className="flex items-start gap-3 rounded-md bg-background/80 px-3 py-2 text-sm"
              >
                <div className="pt-0.5">
                  {event.kind === 'finding' || event.kind === 'complete' ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : event.kind === 'error' ? (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  ) : event.kind === 'detail' ? (
                    <div className="mt-1 h-2 w-2 rounded-full bg-muted-foreground/60" />
                  ) : (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-foreground">{event.message}</div>
                  {(event.entity_name || event.entity_type) && (
                    <div className="text-xs text-muted-foreground">
                      {[event.entity_name, event.entity_type].filter(Boolean).join(' • ')}
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('wizard.waitingForImportEvents')}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
