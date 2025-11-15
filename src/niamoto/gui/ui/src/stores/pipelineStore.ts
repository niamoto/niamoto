import { create } from 'zustand'

type PipelineStatus = 'idle' | 'running' | 'completed' | 'error'
type StepStatus = 'idle' | 'running' | 'completed' | 'error'

interface LogEntry {
  time: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
}

interface StepResult {
  status: StepStatus
  result: any
  duration: number
  error?: string
}

interface PipelineState {
  // Overall pipeline status
  status: PipelineStatus
  currentStep: 'import' | 'transform' | 'export' | null
  activeStepIndex: number // 0 = import, 1 = transform, 2 = export

  // Step results
  importResult: StepResult | null
  transformResult: StepResult | null
  exportResult: StepResult | null

  // Progress tracking
  progress: number

  // Logs - shared across all tabs
  logs: LogEntry[]

  // Actions
  setStatus: (status: PipelineStatus) => void
  setCurrentStep: (step: 'import' | 'transform' | 'export' | null) => void
  setActiveStepIndex: (index: number) => void
  setImportResult: (result: StepResult) => void
  setTransformResult: (result: StepResult) => void
  setExportResult: (result: StepResult) => void
  setProgress: (progress: number | ((prev: number) => number)) => void
  addLog: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
  clearLogs: () => void
  reset: () => void
  resetStep: (step: 'import' | 'transform' | 'export') => void
}

export const usePipelineStore = create<PipelineState>((set) => ({
  // Initial state
  status: 'idle',
  currentStep: null,
  activeStepIndex: 0,
  importResult: null,
  transformResult: null,
  exportResult: null,
  progress: 0,
  logs: [],

  // Actions
  setStatus: (status) => set({ status }),

  setCurrentStep: (step) => set({ currentStep: step }),

  setActiveStepIndex: (index) => set({ activeStepIndex: index }),

  setImportResult: (result) => set({ importResult: result }),

  setTransformResult: (result) => set({ transformResult: result }),

  setExportResult: (result) => set({ exportResult: result }),

  setProgress: (progress) => set((state) => ({
    progress: typeof progress === 'function' ? progress(state.progress) : progress
  })),

  addLog: (message, type = 'info') => set((state) => ({
    logs: [...state.logs, {
      time: new Date().toLocaleTimeString('fr-FR'),
      message,
      type
    }]
  })),

  clearLogs: () => set({ logs: [] }),

  reset: () => set({
    status: 'idle',
    currentStep: null,
    activeStepIndex: 0,
    importResult: null,
    transformResult: null,
    exportResult: null,
    progress: 0,
    logs: []
  }),

  resetStep: (step) => set(() => {
    const updates: Partial<PipelineState> = {}

    if (step === 'import') {
      updates.importResult = null
    } else if (step === 'transform') {
      updates.transformResult = null
    } else if (step === 'export') {
      updates.exportResult = null
    }

    return updates
  })
}))
