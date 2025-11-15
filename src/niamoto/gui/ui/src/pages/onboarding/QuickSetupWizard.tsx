import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { ChevronLeft, ChevronRight } from 'lucide-react'

import WelcomeStep from './steps/WelcomeStep'
import AutoConfigureStep from './steps/AutoConfigureStep'
import PreviewStep from './steps/PreviewStep'
import ImportStep from './steps/ImportStep'

export interface WizardState {
  step: number
  scannedFiles: any[]
  selectedFiles: string[]
  autoConfigResult: any | null
  importProgress: any | null
}

const STEPS = [
  { id: 'welcome', title: 'Welcome', description: 'Scan your files' },
  { id: 'configure', title: 'Auto-Configure', description: 'Smart detection' },
  { id: 'preview', title: 'Review', description: 'Check configuration' },
  { id: 'import', title: 'Import', description: 'Execute import' }
]

export default function QuickSetupWizard() {
  const navigate = useNavigate()
  const [wizardState, setWizardState] = useState<WizardState>({
    step: 0,
    scannedFiles: [],
    selectedFiles: [],
    autoConfigResult: null,
    importProgress: null
  })

  const progress = ((wizardState.step + 1) / STEPS.length) * 100

  const updateState = (updates: Partial<WizardState>) => {
    setWizardState(prev => ({ ...prev, ...updates }))
  }

  const nextStep = () => {
    if (wizardState.step < STEPS.length - 1) {
      updateState({ step: wizardState.step + 1 })
    }
  }

  const prevStep = () => {
    if (wizardState.step > 0) {
      updateState({ step: wizardState.step - 1 })
    }
  }

  const handleComplete = () => {
    // TODO: Navigate to transform/export configuration once implemented
    // For now, redirect to transform page as placeholder
    navigate('/setup/transform')
  }

  return (
    <div className="container mx-auto p-6 max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Quick Setup Wizard</h1>
        <p className="text-muted-foreground">
          Let's configure your Niamoto instance in less than 5 minutes
        </p>
      </div>

      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex justify-between mb-2">
          {STEPS.map((step, index) => (
            <div
              key={step.id}
              className={`flex-1 text-center ${
                index <= wizardState.step ? 'text-primary' : 'text-muted-foreground'
              }`}
            >
              <div className="text-sm font-medium">{step.title}</div>
              <div className="text-xs">{step.description}</div>
            </div>
          ))}
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Step content */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          {wizardState.step === 0 && (
            <WelcomeStep
              wizardState={wizardState}
              updateState={updateState}
              onNext={nextStep}
            />
          )}

          {wizardState.step === 1 && (
            <AutoConfigureStep
              wizardState={wizardState}
              updateState={updateState}
              onNext={nextStep}
              onBack={prevStep}
            />
          )}

          {wizardState.step === 2 && (
            <PreviewStep
              wizardState={wizardState}
              updateState={updateState}
              onNext={nextStep}
              onBack={prevStep}
            />
          )}

          {wizardState.step === 3 && (
            <ImportStep
              wizardState={wizardState}
              updateState={updateState}
              onComplete={handleComplete}
              onBack={prevStep}
            />
          )}
        </CardContent>
      </Card>

      {/* Navigation buttons - shown only if step component doesn't provide them */}
      {wizardState.step > 0 && wizardState.step < 3 && (
        <div className="flex justify-between">
          <Button variant="outline" onClick={prevStep}>
            <ChevronLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <Button onClick={nextStep}>
            Next
            <ChevronRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      )}
    </div>
  )
}
