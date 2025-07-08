import { useState } from 'react'
import { useImportV2 } from './ImportContext'
import { Button } from '@/components/ui/button'
import { executeImport } from '@/lib/api/import'
import { Loader2, ArrowRight, Check } from 'lucide-react'

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
    const { occurrences } = state

    setImportProgress({
      status: 'running',
      currentStep: 'occurrences',
      progress: 10,
      message: 'Import des occurrences...',
      errors: []
    })

    try {
      // Import logic here (simplified for the button)
      if (occurrences.file) {
        await executeImport({
          import_type: 'taxonomy',
          file_name: occurrences.file.name,
          field_mappings: occurrences.fieldMappings,
          advanced_options: {
            ranks: occurrences.taxonomyHierarchy.ranks,
            ...occurrences.taxonomyHierarchy.mappings
          }
        }, occurrences.file)
      }

      setImportProgress({
        status: 'completed',
        currentStep: 'done',
        progress: 100,
        message: 'Import terminé avec succès !',
        errors: []
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
      <Button disabled>
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        Import en cours...
      </Button>
    )
  }

  if (importProgress.status === 'completed') {
    return (
      <Button variant="outline" onClick={() => window.location.href = '/transform'}>
        Aller aux transformations
        <ArrowRight className="w-4 h-4 ml-2" />
      </Button>
    )
  }

  return (
    <Button onClick={handleImport}>
      <Check className="w-4 h-4 mr-2" />
      Lancer l'import
    </Button>
  )
}
