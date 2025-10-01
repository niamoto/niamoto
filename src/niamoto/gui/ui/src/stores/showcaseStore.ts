import { create } from 'zustand'

interface ShowcaseState {
  // Navigation
  currentSection: number
  sections: string[]

  // Configuration
  configLoaded: boolean
  isLoadingConfig: boolean
  importConfig: any
  transformConfig: any
  exportConfig: any

  // Metrics
  importMetrics: any
  metricsLoading: boolean

  // Plugins
  plugins: any[]
  pluginsLoading: boolean

  // Demo progress
  demoProgress: Record<string, number>
  activeDemo: 'import' | 'transform' | 'export' | null

  // Actions
  setCurrentSection: (section: number) => void
  loadConfiguration: () => Promise<void>
  loadMetrics: () => Promise<void>
  loadPlugins: () => Promise<void>
  setDemoProgress: (demo: string, progress: number) => void
  setActiveDemo: (demo: 'import' | 'transform' | 'export' | null) => void
  resetState: () => void
}

export const useShowcaseStore = create<ShowcaseState>((set, get) => ({
  // Initial state
  currentSection: 0,
  sections: [
    'hero',
    'architecture',
    'pipeline-overview',
    'import-demo',
    'transform-demo',
    'export-demo',
    'api-demo',
    'use-cases',
    'call-to-action'
  ],

  configLoaded: false,
  isLoadingConfig: false,
  importConfig: null,
  transformConfig: null,
  exportConfig: null,

  importMetrics: null,
  metricsLoading: false,

  plugins: [],
  pluginsLoading: false,

  demoProgress: {
    import: 0,
    transform: 0,
    export: 0
  },

  activeDemo: null,

  // Actions
  setCurrentSection: (section) => set({ currentSection: section }),

  loadConfiguration: async () => {
    if (get().configLoaded || get().isLoadingConfig) return

    set({ isLoadingConfig: true })

    try {
      // Using the config API to read configuration files
      const [importRes, transformRes, exportRes] = await Promise.all([
        fetch('/api/config/import'),
        fetch('/api/config/transform'),
        fetch('/api/config/export')
      ])

      if (importRes.ok && transformRes.ok && exportRes.ok) {
        const importData = await importRes.json()
        const transformData = await transformRes.json()
        const exportData = await exportRes.json()

        set({
          importConfig: importData,
          transformConfig: transformData,
          exportConfig: exportData,
          configLoaded: true,
          isLoadingConfig: false
        })
      } else {
        // Fallback to sample config if files cannot be loaded
        set({
          importConfig: getSampleImportConfig(),
          transformConfig: getSampleTransformConfig(),
          exportConfig: getSampleExportConfig(),
          configLoaded: true,
          isLoadingConfig: false
        })
      }
    } catch (error) {
      console.error('Failed to load configuration:', error)
      // Use sample config as fallback
      set({
        importConfig: getSampleImportConfig(),
        transformConfig: getSampleTransformConfig(),
        exportConfig: getSampleExportConfig(),
        configLoaded: true,
        isLoadingConfig: false
      })
    }
  },

  loadMetrics: async () => {
    if (get().metricsLoading) return

    set({ metricsLoading: true })

    try {
      // Fetch statistics for all key tables
      const [taxonRes, occurrencesRes, plotsRes, shapesRes] = await Promise.all([
        fetch('/api/database/tables/taxon_ref/stats').then(r => r.ok ? r.json() : null),
        fetch('/api/database/tables/occurrences/stats').then(r => r.ok ? r.json() : null),
        fetch('/api/database/tables/plot_ref/stats').then(r => r.ok ? r.json() : null),
        fetch('/api/database/tables/shape_ref/stats').then(r => r.ok ? r.json() : null)
      ])

      const metrics = {
        taxon_ref: taxonRes?.row_count || 0,
        occurrences: occurrencesRes?.row_count || 0,
        plot_ref: plotsRes?.row_count || 0,
        shape_ref: shapesRes?.row_count || 0,
        total_records: (taxonRes?.row_count || 0) +
                       (occurrencesRes?.row_count || 0) +
                       (plotsRes?.row_count || 0),
        unique_species: taxonRes?.unique_counts?.full_name || 0,
        unique_locations: plotsRes?.row_count || 0
      }

      set({ importMetrics: metrics, metricsLoading: false })
    } catch (error) {
      console.error('Failed to load metrics:', error)
      set({
        importMetrics: {
          taxon_ref: 0,
          occurrences: 0,
          plots: 0,
          shapes: 0,
          total_records: 0,
          unique_species: 0,
          unique_locations: 0
        },
        metricsLoading: false
      })
    }
  },

  loadPlugins: async () => {
    if (get().pluginsLoading) return

    set({ pluginsLoading: true })

    try {
      const response = await fetch('/api/plugins/')
      if (response.ok) {
        const data = await response.json()
        set({ plugins: data, pluginsLoading: false })
      } else {
        set({ plugins: [], pluginsLoading: false })
      }
    } catch (error) {
      console.error('Failed to load plugins:', error)
      set({ plugins: [], pluginsLoading: false })
    }
  },

  setDemoProgress: (demo, progress) => {
    set(state => ({
      demoProgress: {
        ...state.demoProgress,
        [demo]: progress
      }
    }))
  },

  setActiveDemo: (demo) => set({ activeDemo: demo }),

  resetState: () => set({
    currentSection: 0,
    demoProgress: {
      import: 0,
      transform: 0,
      export: 0
    },
    activeDemo: null
  })
}))

// Sample configurations as fallback
function getSampleImportConfig() {
  return {
    taxonomy: {
      path: 'imports/occurrences.csv',
      hierarchy: {
        levels: [
          { name: 'family', column: 'family' },
          { name: 'genus', column: 'genus' },
          { name: 'species', column: 'species' },
          { name: 'infra', column: 'infra' }
        ]
      }
    },
    occurrences: {
      type: 'csv',
      path: 'imports/occurrences.csv',
      identifier: 'id_taxonref',
      location_field: 'geo_pt'
    },
    plots: {
      type: 'csv',
      path: 'imports/plots.csv',
      identifier: 'id_plot'
    },
    shapes: [
      { type: 'Provinces', path: 'imports/shapes/provinces.gpkg', name_field: 'nom' },
      { type: 'Communes', path: 'imports/shapes/communes.gpkg', name_field: 'nom' }
    ]
  }
}

function getSampleTransformConfig() {
  return [
    {
      group_by: 'taxon',
      sources: [
        {
          name: 'occurrences',
          data: 'occurrences',
          grouping: 'taxon_ref'
        }
      ],
      widgets_data: {
        general_info: {
          plugin: 'field_aggregator',
          params: {}
        },
        distribution_map: {
          plugin: 'geospatial_extractor',
          params: {}
        }
      }
    }
  ]
}

function getSampleExportConfig() {
  return {
    exports: [
      {
        name: 'web_pages',
        enabled: true,
        exporter: 'html_page_exporter',
        params: {
          output_dir: 'exports/web',
          site: {
            title: 'Niamoto Demo',
            lang: 'fr'
          }
        }
      }
    ]
  }
}
