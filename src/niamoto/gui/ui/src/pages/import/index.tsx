import { useTranslation } from 'react-i18next'
import { ImportProvider, useImport } from './ImportContext'
import { ImportProgressProvider } from './ImportProgressContext'
import { Overview } from './Overview'
import { OccurrencesStep } from './OccurrencesStep'
import { AggregationStep } from './AggregationStep'
import { SummaryStep } from './SummaryStep'
import { ImportButton } from './ImportButton'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

function ImportContent() {
  const { t } = useTranslation(['import', 'common'])
  const { state, setCurrentStep, canProceed } = useImport()
  const { currentStep } = state

  const steps = [
    { title: t('navigation.overview.title'), description: t('navigation.overview.subtitle') },
    { title: t('navigation.occurrences.title'), description: t('navigation.occurrences.subtitle') },
    { title: t('navigation.aggregations.title'), description: t('navigation.aggregations.subtitle') },
    { title: t('navigation.summary.title'), description: t('navigation.summary.subtitle') }
  ]

  const handleNext = () => {
    if (currentStep < steps.length - 1 && canProceed()) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return <Overview />
      case 1:
        return <OccurrencesStep />
      case 2:
        return <AggregationStep />
      case 3:
        return <SummaryStep />
      default:
        return null
    }
  }

  return (
    <div className="container max-w-6xl mx-auto py-8 space-y-8">
      {/* Header with old import link */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">{t('title')}</h1>
          <p className="text-muted-foreground mt-2">
            {t('subtitle')}
          </p>
        </div>
      </div>

      {/* Progress indicator */}
      <div className="space-y-4">
        <Progress value={(currentStep + 1) / steps.length * 100} />

        <div className="grid grid-cols-4 gap-4">
          {steps.map((step, index) => (
            <div
              key={index}
              className={cn(
                "text-center space-y-1",
                index === currentStep && "font-medium",
                index < currentStep && "text-muted-foreground",
                index > currentStep && "text-muted-foreground/50"
              )}
            >
              <div className="flex justify-center">
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-sm",
                  index === currentStep && "bg-primary text-primary-foreground",
                  index < currentStep && "bg-primary/20 text-primary",
                  index > currentStep && "bg-muted text-muted-foreground"
                )}>
                  {index < currentStep ? <Check className="w-4 h-4" /> : index + 1}
                </div>
              </div>
              <div className="text-sm">{step.title}</div>
              <div className="text-xs text-muted-foreground">{step.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Step content */}
      <div className="min-h-[400px]">
        {renderStep()}
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-8 border-t">
        <Button
          variant="outline"
          onClick={handlePrevious}
          disabled={currentStep === 0}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t('common:actions.previous')}
        </Button>

        <div className="flex gap-2">
          {currentStep < steps.length - 1 ? (
            <Button
              onClick={handleNext}
              disabled={!canProceed()}
            >
              {t('common:actions.next')}
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          ) : (
            <ImportButton />
          )}
        </div>
      </div>
    </div>
  )
}

export function ImportPage() {
  return (
    <ImportProvider>
      <ImportProgressProvider>
        <ImportContent />
      </ImportProgressProvider>
    </ImportProvider>
  )
}
