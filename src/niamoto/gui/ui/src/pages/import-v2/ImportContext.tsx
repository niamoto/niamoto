import { createContext, useContext, useState, type ReactNode } from 'react'

export interface OccurrenceImportData {
  file: File | null
  fileAnalysis: any
  fieldMappings: Record<string, string>
  taxonomyHierarchy: {
    ranks: string[]
    mappings: Record<string, string>
  }
  apiEnrichment?: {
    enabled: boolean
    plugin: string
    api_url: string
    auth_method: 'none' | 'api_key' | 'bearer' | 'basic'
    auth_params?: {
      key?: string
      location?: 'header' | 'query'
      name?: string
      username?: string
      password?: string
    }
    query_params?: Record<string, string>
    query_field: string
    rate_limit: number
    cache_results: boolean
    response_mapping?: Record<string, string>
  }
}

export interface PlotImportData {
  file: File | null
  fileAnalysis: any
  fieldMappings: Record<string, string>
  linkField?: string
  occurrenceLinkField?: string
}

export interface ShapeImportData {
  file: File | null
  fileAnalysis: any
  fieldMappings: Record<string, string>
  type: string
  properties: string[]
}

export interface ImportV2State {
  currentStep: number
  occurrences: OccurrenceImportData
  plots?: PlotImportData
  shapes?: ShapeImportData[]
  aggregationType: 'none' | 'plots' | 'shapes' | 'both'
}

interface ImportV2ContextType {
  state: ImportV2State
  updateOccurrences: (data: Partial<OccurrenceImportData>) => void
  updatePlots: (data: Partial<PlotImportData>) => void
  updateShapes: (index: number, data: Partial<ShapeImportData>) => void
  addShape: () => void
  removeShape: (index: number) => void
  setAggregationType: (type: ImportV2State['aggregationType']) => void
  setCurrentStep: (step: number) => void
  canProceed: () => boolean
}

const ImportV2Context = createContext<ImportV2ContextType | undefined>(undefined)

export function ImportV2Provider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ImportV2State>({
    currentStep: 0,
    occurrences: {
      file: null,
      fileAnalysis: null,
      fieldMappings: {},
      taxonomyHierarchy: {
        ranks: ['family', 'genus', 'species', 'infra'],
        mappings: {}
      },
      apiEnrichment: {
        enabled: false,
        plugin: 'api_taxonomy_enricher',
        api_url: '',
        auth_method: 'none',
        query_field: 'name',
        rate_limit: 10,
        cache_results: true,
        response_mapping: {}
      }
    },
    aggregationType: 'none'
  })

  const updateOccurrences = (data: Partial<OccurrenceImportData>) => {
    setState(prev => ({
      ...prev,
      occurrences: { ...prev.occurrences, ...data }
    }))
  }

  const updatePlots = (data: Partial<PlotImportData>) => {
    setState(prev => ({
      ...prev,
      plots: prev.plots
        ? { ...prev.plots, ...data }
        : {
            file: null,
            fileAnalysis: null,
            fieldMappings: {},
            linkField: 'locality',
            occurrenceLinkField: 'plot_name',
            ...data
          }
    }))
  }

  const updateShapes = (index: number, data: Partial<ShapeImportData>) => {
    setState(prev => {
      const shapes = [...(prev.shapes || [])]
      shapes[index] = { ...shapes[index], ...data } as ShapeImportData
      return { ...prev, shapes }
    })
  }

  const addShape = () => {
    setState(prev => ({
      ...prev,
      shapes: [...(prev.shapes || []), {
        file: null,
        fileAnalysis: null,
        fieldMappings: {},
        type: 'default',
        properties: []
      }]
    }))
  }

  const removeShape = (index: number) => {
    setState(prev => ({
      ...prev,
      shapes: prev.shapes?.filter((_, i) => i !== index)
    }))
  }

  const setAggregationType = (type: ImportV2State['aggregationType']) => {
    setState(prev => ({ ...prev, aggregationType: type }))
  }

  const setCurrentStep = (step: number) => {
    setState(prev => ({ ...prev, currentStep: step }))
  }

  const canProceed = () => {
    const { currentStep, occurrences, plots, shapes, aggregationType } = state

    switch (currentStep) {
      case 0: // Overview - always can proceed
        return true

      case 1: // Occurrences
        return !!(
          occurrences.file &&
          occurrences.fieldMappings.taxon_id &&
          occurrences.fieldMappings.location &&
          occurrences.taxonomyHierarchy.ranks.length >= 2 &&
          Object.keys(occurrences.taxonomyHierarchy.mappings).length >= 2
        )

      case 2: // Aggregation
        if (aggregationType === 'none') return true
        if (aggregationType === 'plots' || aggregationType === 'both') {
          if (!plots?.file || !plots?.fieldMappings.identifier) return false
        }
        if (aggregationType === 'shapes' || aggregationType === 'both') {
          if (!shapes?.length) return false
          return shapes.every(s => s.file && s.fieldMappings.name)
        }
        return true

      case 3: // Summary
        return true

      default:
        return false
    }
  }

  return (
    <ImportV2Context.Provider value={{
      state,
      updateOccurrences,
      updatePlots,
      updateShapes,
      addShape,
      removeShape,
      setAggregationType,
      setCurrentStep,
      canProceed
    }}>
      {children}
    </ImportV2Context.Provider>
  )
}

export function useImportV2() {
  const context = useContext(ImportV2Context)
  if (!context) {
    throw new Error('useImportV2 must be used within ImportV2Provider')
  }
  return context
}
