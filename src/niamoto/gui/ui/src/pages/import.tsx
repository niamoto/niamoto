import { ImportWizard, type ImportConfig } from '@/components/import-wizard/ImportWizard'

export function ImportPage() {
  const handleImportComplete = async (config: ImportConfig) => {
    console.log('Import configuration:', config)
    // TODO: Call API to execute import
  }

  return (
    <div className="h-full">
      <ImportWizard onComplete={handleImportComplete} />
    </div>
  )
}
