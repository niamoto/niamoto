import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { CheckCircle2, Loader2, AlertCircle, Rocket, ExternalLink } from 'lucide-react'
import type { WizardState } from '../QuickSetupWizard'
import { createEntitiesBulk } from '@/lib/api/smart-config'
import { executeImportAll, getImportStatus } from '@/lib/api/import'

interface ImportStepProps {
  wizardState: WizardState
  updateState: (_updates: Partial<WizardState>) => void
  onComplete: () => void
  onBack: () => void
}

export default function ImportStep({ wizardState, onComplete, onBack }: ImportStepProps) {
  const [step, setStep] = useState<'saving' | 'saved' | 'importing' | 'complete' | 'error'>('saving')
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [importDetails, setImportDetails] = useState<{
    totalEntities: number
    processedEntities: number
    currentEntity?: string
  }>({ totalEntities: 0, processedEntities: 0 })

  useEffect(() => {
    executeImport()
  }, [])

  const executeImport = async () => {
    try {
      setStep('saving')
      setProgress(10)

      // Step 1: Save entities to import.yml
      const result = wizardState.autoConfigResult
      if (!result) {
        throw new Error('No configuration to save')
      }

      await createEntitiesBulk(result.entities)

      setProgress(30)
      setStep('saved')

      // Step 2: Execute the real import
      setStep('importing')
      const importResponse = await executeImportAll(false)
      const jobId = importResponse.job_id

      // Step 3: Poll for import status
      const pollInterval = 500 // Poll every 500ms
      const maxWaitTime = 600000 // 10 minutes max
      const startTime = Date.now()

      let lastProgress = 30

      while (Date.now() - startTime < maxWaitTime) {
        const status = await getImportStatus(jobId)

        // Update import details
        setImportDetails({
          totalEntities: status.total_entities || 0,
          processedEntities: status.processed_entities || 0,
          currentEntity: status.current_entity
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
          return
        } else if (status.status === 'failed') {
          throw new Error(status.errors?.join(', ') || 'Import failed')
        }

        // Wait before polling again
        await new Promise(resolve => setTimeout(resolve, pollInterval))
      }

      throw new Error('Import timed out')

    } catch (err: any) {
      setError(err.message || 'Failed to execute import')
      setStep('error')
    }
  }

  if (step === 'error') {
    return (
      <div className="py-8 space-y-4">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 mx-auto text-destructive mb-4" />
          <h3 className="text-xl font-semibold mb-2">Import Failed</h3>
        </div>

        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>

        <div className="flex gap-2 justify-center">
          <Button variant="outline" onClick={onBack}>
            Go Back
          </Button>
          <Button onClick={executeImport}>
            Retry
          </Button>
        </div>
      </div>
    )
  }

  if (step === 'complete') {
    const datasetCount = Object.keys(wizardState.autoConfigResult?.entities.datasets || {}).length
    const referenceCount = Object.keys(wizardState.autoConfigResult?.entities.references || {}).length

    return (
      <div className="py-8 space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-500/10 mb-4 animate-bounce">
            <CheckCircle2 className="w-10 h-10 text-green-500" />
          </div>
          <h2 className="text-3xl font-bold mb-2">Setup Complete!</h2>
          <p className="text-muted-foreground text-lg">
            Your Niamoto instance is ready to use
          </p>
        </div>

        <div className="bg-accent rounded-lg p-6 space-y-4">
          <h3 className="font-semibold text-lg">What we configured:</h3>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
              <div>
                <div className="font-medium">{datasetCount} Dataset{datasetCount !== 1 ? 's' : ''}</div>
                <div className="text-sm text-muted-foreground">Primary data tables</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
              <div>
                <div className="font-medium">{referenceCount} Reference{referenceCount !== 1 ? 's' : ''}</div>
                <div className="text-sm text-muted-foreground">Lookup tables</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
              <div>
                <div className="font-medium">Configuration saved</div>
                <div className="text-sm text-muted-foreground">to config/import.yml</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
              <div>
                <div className="font-medium">Auto-detected</div>
                <div className="text-sm text-muted-foreground">Hierarchies & relationships</div>
              </div>
            </div>
          </div>
        </div>

        <Alert>
          <Rocket className="w-4 h-4" />
          <AlertDescription>
            <strong>Next steps:</strong>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>Run the import to load your data into the database</li>
              <li>Configure transformations to generate statistics</li>
              <li>Set up exports to create your website</li>
            </ul>
          </AlertDescription>
        </Alert>

        <div className="flex flex-col gap-3">
          <Button onClick={onComplete} size="lg" className="w-full">
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Go to Entity Manager
          </Button>

          <Button variant="outline" size="lg" className="w-full">
            <ExternalLink className="w-4 h-4 mr-2" />
            View Documentation
          </Button>
        </div>
      </div>
    )
  }

  // Saving/importing state
  return (
    <div className="py-12 space-y-6">
      <div className="text-center">
        <Loader2 className="w-16 h-16 mx-auto animate-spin text-primary mb-4" />
        <h3 className="text-xl font-semibold mb-2">
          {step === 'saving' && 'Saving configuration...'}
          {step === 'saved' && 'Configuration saved!'}
          {step === 'importing' && 'Importing data...'}
        </h3>
        <p className="text-muted-foreground">
          {step === 'saving' && 'Writing entities to import.yml'}
          {step === 'saved' && 'Starting import process'}
          {step === 'importing' && importDetails.currentEntity && `Importing ${importDetails.currentEntity}...`}
          {step === 'importing' && !importDetails.currentEntity && 'Processing entities...'}
        </p>
      </div>

      <div className="max-w-md mx-auto">
        <Progress value={progress} className="h-3" />
        <p className="text-center text-sm text-muted-foreground mt-2">
          {progress}% complete
          {importDetails.totalEntities > 0 && (
            <span className="ml-2">
              ({importDetails.processedEntities}/{importDetails.totalEntities} entities)
            </span>
          )}
        </p>
      </div>

      <div className="max-w-md mx-auto space-y-2 text-sm">
        <div className={`flex items-center gap-2 ${progress >= 30 ? 'text-green-600' : 'text-muted-foreground'}`}>
          {progress >= 30 ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : (
            <Loader2 className="w-4 h-4 animate-spin" />
          )}
          Creating entities in import.yml
        </div>

        <div className={`flex items-center gap-2 ${step === 'importing' || progress >= 100 ? 'text-green-600' : progress >= 30 ? 'text-primary' : 'text-muted-foreground'}`}>
          {progress >= 100 ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : step === 'importing' || progress >= 30 ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <div className="w-4 h-4" />
          )}
          Importing data to database
          {importDetails.processedEntities > 0 && step === 'importing' && (
            <span className="text-xs ml-1">({importDetails.processedEntities} done)</span>
          )}
        </div>

        <div className={`flex items-center gap-2 ${progress >= 100 ? 'text-green-600' : 'text-muted-foreground'}`}>
          {progress >= 100 ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : (
            <div className="w-4 h-4" />
          )}
          Import complete
        </div>
      </div>
    </div>
  )
}
