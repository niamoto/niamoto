import { useState, useRef, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PipelineSection } from './PipelineSection'
import { ImportDemo } from './ImportDemo'
import { TransformDemo } from './TransformDemo'
import { ExportDemo } from './ExportDemo'
import { usePipelineStore } from '@/stores/pipelineStore'
import {
  Workflow,
  FileInput,
  Settings,
  Globe,
  Loader2,
  CheckCircle
} from 'lucide-react'
import { cn } from '@/lib/utils'

export function PipelineFullSection() {
  const [activeTab, setActiveTab] = useState('overview')
  const sectionRef = useRef<HTMLDivElement>(null)
  const isInitialMount = useRef(true)
  const { currentStep, importResult, transformResult, exportResult } = usePipelineStore()

  // Helper to get step status
  const getStepStatus = (step: 'import' | 'transform' | 'export') => {
    const isRunning = currentStep === step
    let isCompleted = false

    if (step === 'import' && importResult?.status === 'completed') isCompleted = true
    if (step === 'transform' && transformResult?.status === 'completed') isCompleted = true
    if (step === 'export' && exportResult?.status === 'completed') isCompleted = true

    return { isRunning, isCompleted }
  }

  const importStatus = getStepStatus('import')
  const transformStatus = getStepStatus('transform')
  const exportStatus = getStepStatus('export')

  // Scroll to top of section when tab changes (but not on initial mount)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }

    if (sectionRef.current) {
      sectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [activeTab])

  const handleTabChange = (value: string) => {
    setActiveTab(value)
  }

  return (
    <div ref={sectionRef} className="w-full space-y-8">
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <div className="sticky top-14 z-30 flex justify-center mb-8 bg-background/95  supports-[backdrop-filter]:bg-background/60 pb-4 pt-4">
          <TabsList className="grid grid-cols-4 w-full max-w-2xl">
            <TabsTrigger value="overview" className="gap-2">
              <Workflow className="w-4 h-4" />
              <span className="hidden sm:inline">Vue d'ensemble</span>
              <span className="sm:hidden">Vue</span>
            </TabsTrigger>
            <TabsTrigger
              value="import"
              className={cn(
                "gap-2 relative",
                importStatus.isRunning && "animate-pulse bg-blue-500/20",
                importStatus.isCompleted && "text-green-600 dark:text-green-400"
              )}
            >
              {importStatus.isRunning && <Loader2 className="w-4 h-4 animate-spin" />}
              {!importStatus.isRunning && !importStatus.isCompleted && <FileInput className="w-4 h-4" />}
              {importStatus.isCompleted && !importStatus.isRunning && <CheckCircle className="w-4 h-4" />}
              Import
            </TabsTrigger>
            <TabsTrigger
              value="transform"
              className={cn(
                "gap-2 relative",
                transformStatus.isRunning && "animate-pulse bg-blue-500/20",
                transformStatus.isCompleted && "text-green-600 dark:text-green-400"
              )}
            >
              {transformStatus.isRunning && <Loader2 className="w-4 h-4 animate-spin" />}
              {!transformStatus.isRunning && !transformStatus.isCompleted && <Settings className="w-4 h-4" />}
              {transformStatus.isCompleted && !transformStatus.isRunning && <CheckCircle className="w-4 h-4" />}
              Transform
            </TabsTrigger>
            <TabsTrigger
              value="export"
              className={cn(
                "gap-2 relative",
                exportStatus.isRunning && "animate-pulse bg-blue-500/20",
                exportStatus.isCompleted && "text-green-600 dark:text-green-400"
              )}
            >
              {exportStatus.isRunning && <Loader2 className="w-4 h-4 animate-spin" />}
              {!exportStatus.isRunning && !exportStatus.isCompleted && <Globe className="w-4 h-4" />}
              {exportStatus.isCompleted && !exportStatus.isRunning && <CheckCircle className="w-4 h-4" />}
              Export
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="overview" className="mt-0">
          <PipelineSection />
        </TabsContent>

        <TabsContent value="import" className="mt-0">
          <ImportDemo />
        </TabsContent>

        <TabsContent value="transform" className="mt-0">
          <TransformDemo />
        </TabsContent>

        <TabsContent value="export" className="mt-0">
          <ExportDemo />
        </TabsContent>
      </Tabs>
    </div>
  )
}
