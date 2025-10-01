import { create } from 'zustand'

export type WidgetType =
  | 'hierarchical_nav'
  | 'interactive_map'
  | 'info_cards'
  | 'horizontal_bar_chart'
  | 'histogram'
  | 'vertical_bar_chart'
  | 'pie_chart'
  | 'donut_chart'
  | 'stacked_bar_chart'
  | 'circular_gauge'
  | 'linear_gauge'
  | 'stat_card'
  | 'table'
  | 'heatmap'

export interface WidgetInstance {
  id: string
  type: WidgetType
  x: number
  y: number
  w: number
  h: number
  config: Record<string, any>
}

export interface RequiredTransform {
  plugin: string
  params: Record<string, any>
  fields: string[]
}

export interface GeneratedConfig {
  imports: any
  transforms: RequiredTransform[]
  exports: any
}

interface GoalDrivenState {
  // Page building
  widgets: WidgetInstance[]
  selectedWidgetId: string | null

  // Preview mode
  previewMode: boolean

  // Generated requirements
  requiredFields: Set<string>
  requiredTransforms: RequiredTransform[]
  generatedConfig: GeneratedConfig | null

  // Actions
  addWidget: (type: WidgetType, position?: { x: number; y: number }) => void
  removeWidget: (id: string) => void
  updateWidget: (id: string, updates: Partial<WidgetInstance>) => void
  updateWidgetLayout: (id: string, layout: { x: number; y: number; w: number; h: number }) => void
  updateWidgetConfig: (id: string, config: Record<string, any>) => void
  selectWidget: (id: string | null) => void

  // Preview
  setPreviewMode: (enabled: boolean) => void

  // Config generation
  generateRequirements: () => void
  generateYAML: () => string

  // Reset
  reset: () => void
}

export const useGoalDrivenStore = create<GoalDrivenState>((set, get) => ({
  // Initial state
  widgets: [],
  selectedWidgetId: null,
  previewMode: false,
  requiredFields: new Set(),
  requiredTransforms: [],
  generatedConfig: null,

  // Actions
  addWidget: (type, position) => {
    const id = `${type}_${Date.now()}`

    // Determine default size based on widget type
    let defaultW = 6
    let defaultH = 4

    switch (type) {
      case 'interactive_map':
        defaultW = 12
        defaultH = 6
        break
      case 'info_cards':
        defaultW = 12
        defaultH = 2
        break
      case 'circular_gauge':
      case 'stat_card':
        defaultW = 3
        defaultH = 3
        break
      case 'horizontal_bar_chart':
      case 'vertical_bar_chart':
      case 'histogram':
        defaultW = 6
        defaultH = 4
        break
      case 'pie_chart':
      case 'donut_chart':
        defaultW = 6
        defaultH = 4
        break
      case 'table':
        defaultW = 12
        defaultH = 5
        break
      case 'heatmap':
        defaultW = 8
        defaultH = 5
        break
    }

    const newWidget: WidgetInstance = {
      id,
      type,
      x: position?.x ?? 0,
      y: position?.y ?? get().widgets.length * 2,
      w: defaultW,
      h: defaultH,
      config: {}
    }
    set((state) => ({
      widgets: [...state.widgets, newWidget],
      selectedWidgetId: id
    }))
  },

  removeWidget: (id) => set((state) => ({
    widgets: state.widgets.filter(w => w.id !== id),
    selectedWidgetId: state.selectedWidgetId === id ? null : state.selectedWidgetId
  })),

  updateWidget: (id, updates) => set((state) => ({
    widgets: state.widgets.map(w =>
      w.id === id ? { ...w, ...updates } : w
    )
  })),

  updateWidgetLayout: (id, layout) => set((state) => ({
    widgets: state.widgets.map(w =>
      w.id === id ? { ...w, ...layout } : w
    )
  })),

  updateWidgetConfig: (id, config) => set((state) => ({
    widgets: state.widgets.map(w =>
      w.id === id ? { ...w, config } : w
    )
  })),

  selectWidget: (id) => set({ selectedWidgetId: id }),

  setPreviewMode: (enabled) => set({ previewMode: enabled }),

  generateRequirements: () => {
    const { widgets } = get()
    const fields = new Set<string>()
    const transforms: RequiredTransform[] = []

    // Map widgets to their required fields and transforms
    widgets.forEach(widget => {
      switch (widget.type) {
        case 'hierarchical_nav':
          fields.add('taxon_ref')
          fields.add('rank_name')
          fields.add('full_name')
          break

        case 'interactive_map':
          fields.add('geo_pt')
          fields.add('latitude')
          fields.add('longitude')
          transforms.push({
            plugin: 'geospatial_extractor',
            params: {},
            fields: ['geo_pt', 'latitude', 'longitude']
          })
          break

        case 'info_cards':
          fields.add('occurrences')
          fields.add('taxon_ref')
          transforms.push({
            plugin: 'field_aggregator',
            params: {},
            fields: ['occurrences', 'taxon_ref']
          })
          break

        case 'horizontal_bar_chart':
        case 'vertical_bar_chart':
          const barField = widget.config.field || 'dbh'
          const groupBy = widget.config.groupBy || 'shape'
          fields.add(barField)
          fields.add(groupBy)
          transforms.push({
            plugin: 'group_by_aggregator',
            params: {
              field: barField,
              groupBy: groupBy
            },
            fields: [barField, groupBy]
          })
          break

        case 'histogram':
          const histField = widget.config.field || 'dbh'
          fields.add(histField)
          transforms.push({
            plugin: 'binned_distribution',
            params: {
              field: histField,
              bins: widget.config.bins || [10, 20, 30, 40, 50, 75, 100, 200]
            },
            fields: [histField]
          })
          break

        case 'pie_chart':
        case 'donut_chart':
          const pieField = widget.config.field || 'substrate'
          fields.add(pieField)
          transforms.push({
            plugin: 'categorical_distribution',
            params: {
              field: pieField
            },
            fields: [pieField]
          })
          break

        case 'stacked_bar_chart':
          const stackField = widget.config.field || 'height'
          const stackGroupBy = widget.config.groupBy || 'stratum'
          fields.add(stackField)
          fields.add(stackGroupBy)
          transforms.push({
            plugin: 'stacked_aggregator',
            params: {
              field: stackField,
              groupBy: stackGroupBy
            },
            fields: [stackField, stackGroupBy]
          })
          break

        case 'circular_gauge':
        case 'linear_gauge':
          const gaugeField = widget.config.field || 'height'
          fields.add(gaugeField)
          transforms.push({
            plugin: 'statistical_summary',
            params: {
              field: gaugeField,
              operation: widget.config.operation || 'max'
            },
            fields: [gaugeField]
          })
          break

        case 'stat_card':
          const statField = widget.config.field || 'occurrences'
          fields.add(statField)
          transforms.push({
            plugin: 'field_aggregator',
            params: {
              field: statField,
              operation: widget.config.operation || 'count'
            },
            fields: [statField]
          })
          break

        case 'table':
          const tableFields = widget.config.fields || ['species', 'dbh', 'height']
          tableFields.forEach((f: string) => fields.add(f))
          transforms.push({
            plugin: 'table_data_extractor',
            params: {
              fields: tableFields
            },
            fields: tableFields
          })
          break

        case 'heatmap':
          const heatX = widget.config.xField || 'elevation'
          const heatY = widget.config.yField || 'rainfall'
          fields.add(heatX)
          fields.add(heatY)
          transforms.push({
            plugin: 'heatmap_aggregator',
            params: {
              xField: heatX,
              yField: heatY
            },
            fields: [heatX, heatY]
          })
          break
      }
    })

    set({
      requiredFields: fields,
      requiredTransforms: transforms
    })
  },

  generateYAML: () => {
    const { widgets, requiredTransforms } = get()

    const config = {
      imports: {
        taxonomy: {
          path: 'imports/occurrences.csv',
          hierarchy: {
            levels: [
              { name: 'family', column: 'family' },
              { name: 'genus', column: 'genus' },
              { name: 'species', column: 'species' }
            ]
          }
        },
        occurrences: {
          type: 'csv',
          path: 'imports/occurrences.csv',
          identifier: 'id_taxonref',
          location_field: 'geo_pt'
        }
      },
      transforms: requiredTransforms,
      exports: {
        name: 'web_pages',
        enabled: true,
        exporter: 'html_page_exporter',
        params: {
          output_dir: 'exports/web',
          widgets: widgets.map(w => ({
            type: w.type,
            config: w.config
          }))
        }
      }
    }

    set({ generatedConfig: config })

    return JSON.stringify(config, null, 2)
  },

  reset: () => set({
    widgets: [],
    selectedWidgetId: null,
    previewMode: false,
    requiredFields: new Set(),
    requiredTransforms: [],
    generatedConfig: null
  })
}))
