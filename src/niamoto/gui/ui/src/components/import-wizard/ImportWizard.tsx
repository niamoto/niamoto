import { useState } from 'react'
import { ChevronRight, ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { FileSelection } from './FileSelection'
import { ColumnMapper } from './ColumnMapper'
import { AdvancedOptions } from './AdvancedOptions'
import { ReviewImport } from './ReviewImport'

export type ImportType = 'taxonomy' | 'plots' | 'occurrences' | 'shapes'

export interface ImportConfig {
  importType: ImportType
  file?: File
  fileAnalysis?: any
  fieldMappings?: Record<string, string>
  advancedOptions?: any
}

interface ImportWizardProps {
  onComplete: (config: ImportConfig) => void
}

const steps = [
  { id: 'source', title: 'Data Source', description: 'Choose what type of data to import' },
  { id: 'file', title: 'File Selection', description: 'Upload and analyze your data file' },
  { id: 'mapping', title: 'Field Mapping', description: 'Map columns to database fields' },
  { id: 'options', title: 'Advanced Options', description: 'Configure additional settings' },
  { id: 'review', title: 'Review & Import', description: 'Preview and execute import' },
]

export function ImportWizard({ onComplete }: ImportWizardProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [config, setConfig] = useState<ImportConfig>({
    importType: 'taxonomy'
  })

  const canProceed = () => {
    switch (steps[currentStep].id) {
      case 'source':
        return config.importType !== undefined
      case 'file':
        return config.file !== undefined && config.fileAnalysis !== undefined
      case 'mapping':
        return config.fieldMappings !== undefined && Object.keys(config.fieldMappings).length > 0
      default:
        return true
    }
  }

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      onComplete(config)
    }
  }

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const updateConfig = (updates: Partial<ImportConfig>) => {
    setConfig({ ...config, ...updates })
  }

  return (
    <div className="flex h-full flex-col">
      {/* Progress Steps */}
      <div className="border-b p-6">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={cn(
                "flex flex-1 flex-col items-center",
                index !== steps.length - 1 && "relative"
              )}
            >
              <div
                className={cn(
                  "mb-2 flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-medium",
                  index < currentStep
                    ? "border-primary bg-primary text-primary-foreground"
                    : index === currentStep
                    ? "border-primary text-primary"
                    : "border-muted text-muted-foreground"
                )}
              >
                {index + 1}
              </div>
              <div className="text-center">
                <div className={cn(
                  "text-sm font-medium",
                  index === currentStep ? "text-foreground" : "text-muted-foreground"
                )}>
                  {step.title}
                </div>
                <div className="text-xs text-muted-foreground hidden sm:block">
                  {step.description}
                </div>
              </div>
              {index !== steps.length - 1 && (
                <div
                  className={cn(
                    "absolute left-[50%] top-5 h-0.5 w-full",
                    index < currentStep ? "bg-primary" : "bg-muted"
                  )}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="flex-1 overflow-auto p-6">
        {steps[currentStep].id === 'source' && (
          <SourceSelection
            selectedType={config.importType}
            onSelect={(importType) => updateConfig({ importType })}
          />
        )}
        {steps[currentStep].id === 'file' && (
          <FileSelection
            importType={config.importType}
            onFileSelected={(file, analysis) =>
              updateConfig({ file, fileAnalysis: analysis })
            }
          />
        )}
        {steps[currentStep].id === 'mapping' && config.fileAnalysis && (
          <ColumnMapper
            importType={config.importType}
            fileAnalysis={config.fileAnalysis}
            onMappingComplete={(mappings) => updateConfig({ fieldMappings: mappings })}
          />
        )}
        {steps[currentStep].id === 'options' && (
          <AdvancedOptions
            config={config}
            onUpdate={updateConfig}
          />
        )}
        {steps[currentStep].id === 'review' && (
          <ReviewImport
            config={config}
            onImport={() => onComplete(config)}
          />
        )}
      </div>

      {/* Navigation */}
      <div className="border-t p-6">
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={currentStep === 0}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <Button
            onClick={handleNext}
            disabled={!canProceed()}
          >
            {currentStep === steps.length - 1 ? 'Import' : 'Next'}
            {currentStep < steps.length - 1 && <ChevronRight className="ml-2 h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  )
}

interface SourceSelectionProps {
  selectedType?: ImportType
  onSelect: (type: ImportType) => void
}

function SourceSelection({ selectedType, onSelect }: SourceSelectionProps) {
  const sources = [
    {
      type: 'taxonomy' as ImportType,
      title: 'Taxonomy',
      description: 'Import taxonomic reference data for species classification',
      details: 'CSV file with hierarchical taxonomy (family, genus, species)',
    },
    {
      type: 'plots' as ImportType,
      title: 'Plots',
      description: 'Import plot locations and metadata',
      details: 'CSV or spatial file with plot coordinates and attributes',
    },
    {
      type: 'occurrences' as ImportType,
      title: 'Occurrences',
      description: 'Import species occurrence observations',
      details: 'CSV file with species observations and locations',
    },
    {
      type: 'shapes' as ImportType,
      title: 'Shapes',
      description: 'Import geographic boundaries and regions',
      details: 'Shapefile, GeoPackage, or GeoJSON with spatial data',
    },
  ]

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">Select Data Source</h2>
      <div className="grid gap-4 md:grid-cols-2">
        {sources.map((source) => (
          <button
            key={source.type}
            onClick={() => onSelect(source.type)}
            className={cn(
              "rounded-lg border p-4 text-left transition-colors hover:bg-accent",
              selectedType === source.type && "border-primary bg-accent"
            )}
          >
            <h3 className="font-medium">{source.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {source.description}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {source.details}
            </p>
          </button>
        ))}
      </div>
    </div>
  )
}
