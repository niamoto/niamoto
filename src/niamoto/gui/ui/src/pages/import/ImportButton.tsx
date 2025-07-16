import { useState } from 'react'
import { useImport } from './ImportContext'
import { useImportProgress } from './ImportProgressContext'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { executeImportAndWait } from '@/lib/api/import'
import { Loader2, ArrowRight, Check, AlertCircle } from 'lucide-react'

export function ImportButton() {
  const { state } = useImport()
  const { updateStepProgress, updateShapeProgress, initializeProgress } = useImportProgress()
  const [overallStatus, setOverallStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle')
  const [errors, setErrors] = useState<string[]>([])

  const handleImport = async () => {
    const { occurrences, plots, shapes, aggregationType } = state
    const localErrors: string[] = []

    // Initialize progress tracking
    const hasPlots = (aggregationType === 'plots' || aggregationType === 'both') && !!plots?.file
    const shapesCount = (aggregationType === 'shapes' || aggregationType === 'both') ? (shapes?.length || 0) : 0
    initializeProgress(hasPlots, shapesCount)

    setOverallStatus('running')
    setErrors([])

    try {
      // 1. Import de la taxonomie (extraite des occurrences)
      if (occurrences.file) {
        // Start taxonomy extraction
        updateStepProgress('taxonomy', {
          status: 'running',
          progress: 0,
          message: 'Extraction de la taxonomie...'
        })

        const taxonomyFieldMappings = {
          ...occurrences.fieldMappings,
          ...occurrences.taxonomyHierarchy.mappings
        }

        try {
          const taxonomyResult = await executeImportAndWait(
            {
              import_type: 'taxonomy',
              file_name: occurrences.file.name,
              field_mappings: taxonomyFieldMappings,
              advanced_options: {
                ranks: occurrences.taxonomyHierarchy.ranks,
                apiEnrichment: occurrences.apiEnrichment
              }
            },
            occurrences.file,
            1000,
            300000,
            (progress) => updateStepProgress('taxonomy', { progress })
          )

          updateStepProgress('taxonomy', {
            status: 'completed',
            progress: 100,
            count: taxonomyResult.count
          })
        } catch (error) {
          updateStepProgress('taxonomy', {
            status: 'failed',
            error: error instanceof Error ? error.message : 'Erreur inconnue'
          })
          throw error
        }

        // 2. Import des occurrences
        updateStepProgress('occurrences', {
          status: 'running',
          progress: 0,
          message: 'Import des occurrences...'
        })

        try {
          const occurrencesResult = await executeImportAndWait(
            {
              import_type: 'occurrences',
              file_name: occurrences.file.name,
              field_mappings: occurrences.fieldMappings
            },
            occurrences.file,
            1000,
            300000,
            (progress) => updateStepProgress('occurrences', { progress })
          )

          updateStepProgress('occurrences', {
            status: 'completed',
            progress: 100,
            count: occurrencesResult.count
          })
        } catch (error) {
          updateStepProgress('occurrences', {
            status: 'failed',
            error: error instanceof Error ? error.message : 'Erreur inconnue'
          })
          throw error
        }
      }

      // 3. Import des plots si configuré
      if (hasPlots && plots?.file) {
        updateStepProgress('plots', {
          status: 'running',
          progress: 0,
          message: 'Import des plots...'
        })

        try {
          const plotsResult = await executeImportAndWait(
            {
              import_type: 'plots',
              file_name: plots.file.name,
              field_mappings: plots.fieldMappings,
              advanced_options: {
                linkField: plots.fieldMappings?.link_field || plots.linkField,
                occurrenceLinkField: plots.fieldMappings?.occurrence_link_field || plots.occurrenceLinkField,
                hierarchy: plots.hierarchy
              }
            },
            plots.file,
            1000,
            300000,
            (progress) => updateStepProgress('plots', { progress })
          )

          updateStepProgress('plots', {
            status: 'completed',
            progress: 100,
            count: plotsResult.count
          })
        } catch (error) {
          updateStepProgress('plots', {
            status: 'failed',
            error: error instanceof Error ? error.message : 'Erreur inconnue'
          })
          localErrors.push(`Erreur plots: ${error instanceof Error ? error.message : 'Erreur inconnue'}`)
        }
      }

      // 4. Import des shapes si configuré
      if (shapesCount > 0 && shapes) {
        for (const [index, shape] of shapes.entries()) {
          if (shape.file) {
            updateShapeProgress(index, {
              status: 'running',
              progress: 0,
              message: `Import de ${shape.type || `shape ${index + 1}`}...`
            })

            try {
              const shapeResult = await executeImportAndWait(
                {
                  import_type: 'shapes',
                  file_name: shape.file.name,
                  field_mappings: shape.fieldMappings,
                  advanced_options: {
                    shape_type: shape.fieldMappings?.type || shape.type
                  }
                },
                shape.file,
                1000,
                300000,
                (progress) => updateShapeProgress(index, { progress })
              )

              updateShapeProgress(index, {
                status: 'completed',
                progress: 100,
                count: shapeResult.count
              })
            } catch (error) {
              updateShapeProgress(index, {
                status: 'failed',
                error: error instanceof Error ? error.message : 'Erreur inconnue'
              })
              localErrors.push(`Erreur shape ${shape.type || index + 1}: ${error instanceof Error ? error.message : 'Erreur inconnue'}`)
            }
          }
        }
      }

      // Set final status
      if (localErrors.length > 0) {
        setErrors(localErrors)
        setOverallStatus('completed')
      } else {
        setOverallStatus('completed')
      }
    } catch (error) {
      setOverallStatus('failed')
      setErrors([error instanceof Error ? error.message : 'Une erreur est survenue'])
    }
  }

  if (overallStatus === 'running') {
    return (
      <div className="space-y-4">
        <Button disabled className="w-full">
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          Import en cours...
        </Button>
      </div>
    )
  }

  if (overallStatus === 'completed') {
    return (
      <div className="space-y-4">
        {errors.length > 0 && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-1">
                <p>Certains imports ont échoué :</p>
                <ul className="list-disc list-inside text-sm">
                  {errors.map((error, i) => (
                    <li key={i}>{error}</li>
                  ))}
                </ul>
              </div>
            </AlertDescription>
          </Alert>
        )}
        <div className="flex items-center gap-2 text-green-600">
          <Check className="w-5 h-5" />
          <span className="font-medium">
            {errors.length > 0 ? 'Import terminé avec des avertissements' : 'Import terminé avec succès !'}
          </span>
        </div>
        <Button variant="outline" onClick={() => window.location.href = '/transform'} className="w-full">
          Aller aux transformations
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    )
  }

  if (overallStatus === 'failed') {
    return (
      <div className="space-y-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {errors.join(', ')}
          </AlertDescription>
        </Alert>
        <Button onClick={handleImport} variant="destructive" className="w-full">
          Réessayer l'import
        </Button>
      </div>
    )
  }

  return (
    <Button onClick={handleImport} className="w-full">
      <Check className="w-4 h-4 mr-2" />
      Lancer l'import
    </Button>
  )
}
