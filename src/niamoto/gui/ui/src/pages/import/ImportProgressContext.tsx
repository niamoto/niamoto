import { createContext, useContext, useState, type ReactNode } from 'react'

export interface ImportStepProgress {
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message?: string
  count?: number
  error?: string
}

export interface ImportProgressState {
  taxonomy: ImportStepProgress
  occurrences: ImportStepProgress
  plots?: ImportStepProgress
  shapes?: ImportStepProgress[]
  overallStatus: 'idle' | 'running' | 'completed' | 'failed'
}

interface ImportProgressContextType {
  progress: ImportProgressState
  updateStepProgress: (step: keyof ImportProgressState, update: Partial<ImportStepProgress>) => void
  updateShapeProgress: (index: number, update: Partial<ImportStepProgress>) => void
  resetProgress: () => void
  initializeProgress: (hasPlots: boolean, shapesCount: number) => void
}

const initialProgress: ImportProgressState = {
  taxonomy: { status: 'pending', progress: 0 },
  occurrences: { status: 'pending', progress: 0 },
  overallStatus: 'idle'
}

const ImportProgressContext = createContext<ImportProgressContextType | undefined>(undefined)

export function ImportProgressProvider({ children }: { children: ReactNode }) {
  const [progress, setProgress] = useState<ImportProgressState>(initialProgress)

  const updateStepProgress = (step: keyof ImportProgressState, update: Partial<ImportStepProgress>) => {
    if (step === 'overallStatus') return

    setProgress(prev => ({
      ...prev,
      [step]: { ...prev[step as keyof Omit<ImportProgressState, 'overallStatus'>], ...update }
    }))
  }

  const updateShapeProgress = (index: number, update: Partial<ImportStepProgress>) => {
    setProgress(prev => {
      if (!prev.shapes) return prev
      const shapes = [...prev.shapes]
      shapes[index] = { ...shapes[index], ...update }
      return { ...prev, shapes }
    })
  }

  const resetProgress = () => {
    setProgress(initialProgress)
  }

  const initializeProgress = (hasPlots: boolean, shapesCount: number) => {
    setProgress({
      taxonomy: { status: 'pending', progress: 0 },
      occurrences: { status: 'pending', progress: 0 },
      plots: hasPlots ? { status: 'pending', progress: 0 } : undefined,
      shapes: shapesCount > 0
        ? Array(shapesCount).fill(null).map(() => ({ status: 'pending' as const, progress: 0 }))
        : undefined,
      overallStatus: 'idle'
    })
  }

  return (
    <ImportProgressContext.Provider value={{
      progress,
      updateStepProgress,
      updateShapeProgress,
      resetProgress,
      initializeProgress
    }}>
      {children}
    </ImportProgressContext.Provider>
  )
}

export function useImportProgress() {
  const context = useContext(ImportProgressContext)
  if (!context) {
    throw new Error('useImportProgress must be used within ImportProgressProvider')
  }
  return context
}
