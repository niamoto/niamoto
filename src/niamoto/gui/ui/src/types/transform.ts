// Transform Configuration Types
// Matches the structure of transform.yml

export interface TransformSource {
  name: string
  data: string
  grouping: string
  relation?: {
    plugin: string
    key?: string
    ref_field?: string
    match_field?: string
    fields?: Record<string, string | number>
  }
}

export interface WidgetData {
  plugin: string
  params?: Record<string, any>
}

export interface TransformGroup {
  group_by: string
  sources: TransformSource[]
  widgets_data: Record<string, WidgetData>
}

// UI-friendly types
export interface UIGroup {
  id: string
  name: string  // group_by value
  displayName: string
  description?: string
  sources: UISource[]
  widgets: UIWidget[]
  icon?: 'taxon' | 'plot' | 'shape' | 'custom'
}

export interface UISource {
  id: string
  name: string
  type: 'table' | 'csv' | 'excel'
  data?: string  // The actual data table (e.g., 'occurrences')
  grouping?: string  // The reference table (e.g., 'taxon_ref')
  relation?: {
    plugin: string
    key?: string  // The field linking to the reference table
    fields?: Record<string, string>  // Additional fields for plugins like nested_set
    config?: any
  }
}

export interface UIWidget {
  id: string
  name: string
  plugin: string
  params?: Record<string, any>
}

// Display names mapping
export const GROUP_DISPLAY_NAMES: Record<string, string> = {
  taxon: 'Espèces',
  plot: 'Parcelles',
  shape: 'Formes géographiques',
}

export const GROUP_DESCRIPTIONS: Record<string, string> = {
  taxon: 'Groupement par taxonomie',
  plot: 'Groupement par parcelles d\'étude',
  shape: 'Groupement par zones géographiques',
}

export const GROUP_ICONS: Record<string, 'taxon' | 'plot' | 'shape'> = {
  taxon: 'taxon',
  plot: 'plot',
  shape: 'shape',
}
