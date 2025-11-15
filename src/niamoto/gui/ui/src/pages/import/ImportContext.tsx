import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { configService } from '@/services/configService'

export interface OccurrenceImportData {
  file: File | null
  fileAnalysis: any
  configPath?: string
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
  configPath?: string
  fieldMappings: Record<string, string>
  linkField?: string
  occurrenceLinkField?: string
  hierarchy?: {
    enabled: boolean
    levels: string[]
    aggregate_geometry: boolean
  }
}

export interface ShapeImportData {
  file: File | null
  fileAnalysis: any
  configPath?: string
  fieldMappings: Record<string, string>
  type: string
  properties: string[]
}

export interface ImportState {
  currentStep: number
  occurrences: OccurrenceImportData
  plots?: PlotImportData
  shapes?: ShapeImportData[]
}

interface ImportContextType {
  state: ImportState
  updateOccurrences: (data: Partial<OccurrenceImportData>) => void
  updatePlots: (data: Partial<PlotImportData>) => void
  updateShapes: (index: number, data: Partial<ShapeImportData>) => void
  addShape: () => void
  removeShape: (index: number) => void
  setCurrentStep: (step: number) => void
  canProceed: () => boolean
  configLoading: boolean
  configError: string | null
}

const ImportContext = createContext<ImportContextType | undefined>(undefined)

export function ImportProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ImportState>({
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
    }
  })

  const [configLoading, setConfigLoading] = useState(true)
  const [configError, setConfigError] = useState<string | null>(null)

  // Load existing configuration on mount
  useEffect(() => {
    const loadExistingConfig = async () => {
      try {
        setConfigLoading(true)
        const config = await configService.getImportConfig()

        if (config && Object.keys(config).length > 0) {
          // Parse config to state format
          const parsedState = configService.parseImportConfigToState(config)

          // Update state with existing configuration
          setState(prev => ({
            ...prev,
            occurrences: parsedState.occurrences || prev.occurrences,
            plots: parsedState.plots,
            shapes: parsedState.shapes
          }))
        }
      } catch (error) {
        console.error('Failed to load existing configuration:', error)
        setConfigError(error instanceof Error ? error.message : 'Failed to load configuration')
      } finally {
        setConfigLoading(false)
      }
    }

    loadExistingConfig()
  }, [])

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
        type: '',  // Empty string instead of 'default'
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


  const setCurrentStep = (step: number) => {
    setState(prev => ({ ...prev, currentStep: step }))
  }

  const canProceed = () => {
    const { currentStep, occurrences, shapes } = state

    switch (currentStep) {
      case 0: // Overview - always can proceed
        return true

      case 1: // Occurrences
        // Check if we have a file OR a loaded configuration
        const hasOccurrenceSource = occurrences.file || occurrences.fileAnalysis?.fromConfig

        return !!(
          hasOccurrenceSource &&
          occurrences.fieldMappings.taxon_id &&
          occurrences.fieldMappings.location &&
          occurrences.taxonomyHierarchy.ranks.length >= 2 &&
          Object.keys(occurrences.taxonomyHierarchy.mappings).length >= 2
        )

      case 2: // Aggregation
        // Aggregation is optional, but if shapes are added, they must be valid
        if (shapes && shapes.length > 0) {
          // All shapes must have required fields mapped
          return shapes.every(shape => {
            // Shape must have a file OR a loaded configuration
            const hasShapeSource = shape.file || shape.fileAnalysis?.fromConfig
            if (!hasShapeSource) return false

            // Shape must have required fields mapped (type and name)
            const mappings = shape.fieldMappings || {}
            return mappings.type && mappings.name
          })
        }
        // If no shapes (and plots are optional), can proceed
        return true

      case 3: // Summary
        return true

      default:
        return false
    }
  }

  return (
    <ImportContext.Provider value={{
      state,
      updateOccurrences,
      updatePlots,
      updateShapes,
      addShape,
      removeShape,
      setCurrentStep,
      canProceed,
      configLoading,
      configError
    }}>
      {children}
    </ImportContext.Provider>
  )
}

export function useImport() {
  const context = useContext(ImportContext)
  if (!context) {
    throw new Error('useImport must be used within ImportProvider')
  }
  return context
}
