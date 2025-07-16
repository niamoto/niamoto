import { useState } from 'react'
import { useImportV2 } from './ImportContext'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { executeImportAndWait } from '@/lib/api/import'
import { Loader2, ArrowRight, Check, AlertCircle } from 'lucide-react'

interface ImportProgress {
  status: 'idle' | 'running' | 'completed' | 'failed'
  currentStep: string
  progress: number
  message: string
  errors: string[]
}

export function ImportButton() {
  const { state } = useImportV2()
  const [importProgress, setImportProgress] = useState<ImportProgress>({
    status: 'idle',
    currentStep: '',
    progress: 0,
    message: '',
    errors: []
  })

  const handleImport = async () => {
    const { occurrences, plots, shapes, aggregationType } = state
    const errors: string[] = []

    setImportProgress({
      status: 'running',
      currentStep: 'taxonomy',
      progress: 10,
      message: 'Extraction de la taxonomie...',
      errors: []
    })

    try {
      // 1. Import de la taxonomie (extraite des occurrences)
      if (occurrences.file) {
        setImportProgress(prev => ({
          ...prev,
          currentStep: 'taxonomy',
          progress: 20,
          message: 'Import de la taxonomie...'
        }))

        // Construire les field_mappings complets pour la taxonomie
        const taxonomyFieldMappings = {
          ...occurrences.fieldMappings,
          ...occurrences.taxonomyHierarchy.mappings
        }

        await executeImportAndWait({
          import_type: 'taxonomy',
          file_name: occurrences.file.name,
          field_mappings: taxonomyFieldMappings,
          advanced_options: {
            ranks: occurrences.taxonomyHierarchy.ranks,
            apiEnrichment: occurrences.apiEnrichment
          }
        }, occurrences.file)

        // 2. Import des occurrences
        setImportProgress(prev => ({
          ...prev,
          currentStep: 'occurrences',
          progress: 40,
          message: 'Import des occurrences...'
        }))

        await executeImportAndWait({
          import_type: 'occurrences',
          file_name: occurrences.file.name,
          field_mappings: occurrences.fieldMappings
        }, occurrences.file)
      }

      // 3. Import des plots si configuré
      if ((aggregationType === 'plots' || aggregationType === 'both') && plots?.file) {
        setImportProgress(prev => ({
          ...prev,
          currentStep: 'plots',
          progress: 60,
          message: 'Import des plots...'
        }))

        await executeImportAndWait({
          import_type: 'plots',
          file_name: plots.file.name,
          field_mappings: plots.fieldMappings,
          advanced_options: {
            linkField: plots.linkField,
            occurrenceLinkField: plots.occurrenceLinkField,
            hierarchy: plots.hierarchy
          }
        }, plots.file)
      }

      // 4. Import des shapes si configuré
      if ((aggregationType === 'shapes' || aggregationType === 'both') && shapes && shapes.length > 0) {
        let shapeProgress = 80
        const progressIncrement = 20 / shapes.length

        for (const [index, shape] of shapes.entries()) {
          if (shape.file) {
            setImportProgress(prev => ({
              ...prev,
              currentStep: 'shapes',
              progress: shapeProgress,
              message: `Import des shapes ${shape.type} (${index + 1}/${shapes.length})...`
            }))

            try {
              await executeImportAndWait({
                import_type: 'shapes',
                file_name: shape.file.name,
                field_mappings: shape.fieldMappings,
                advanced_options: {
                  shape_type: shape.type
                }
              }, shape.file)
            } catch (error) {
              errors.push(`Erreur shape ${shape.type}: ${error instanceof Error ? error.message : 'Erreur inconnue'}`)
            }

            shapeProgress += progressIncrement
          }
        }
      }

      setImportProgress({
        status: errors.length > 0 ? 'completed' : 'completed',
        currentStep: 'done',
        progress: 100,
        message: errors.length > 0 ? 'Import terminé avec des avertissements' : 'Import terminé avec succès !',
        errors
      })
    } catch (error) {
      setImportProgress(prev => ({
        ...prev,
        status: 'failed',
        errors: [error instanceof Error ? error.message : 'Une erreur est survenue']
      }))
    }
  }

  if (importProgress.status === 'running') {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm font-medium">{importProgress.message}</span>
        </div>
        <Progress value={importProgress.progress} className="h-2" />
        <Button disabled className="w-full">
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          Import en cours...
        </Button>
      </div>
    )
  }

  if (importProgress.status === 'completed') {
    return (
      <div className="space-y-4">
        {importProgress.errors.length > 0 && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-1">
                <p>Certains imports ont échoué :</p>
                <ul className="list-disc list-inside text-sm">
                  {importProgress.errors.map((error, i) => (
                    <li key={i}>{error}</li>
                  ))}
                </ul>
              </div>
            </AlertDescription>
          </Alert>
        )}
        <div className="flex items-center gap-2 text-green-600">
          <Check className="w-5 h-5" />
          <span className="font-medium">{importProgress.message}</span>
        </div>
        <Button variant="outline" onClick={() => window.location.href = '/transform'} className="w-full">
          Aller aux transformations
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    )
  }

  if (importProgress.status === 'failed') {
    return (
      <div className="space-y-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {importProgress.errors.join(', ')}
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
