import type { Node, Edge } from 'reactflow'

// Node Types
export type NodeType = 'import' | 'transform' | 'export'
export type NodeStatus = 'idle' | 'configured' | 'running' | 'success' | 'error'

// Import Node Types
export type ImportSubType = 'taxonomy' | 'occurrences' | 'plots' | 'shapes' | 'layers'

export interface ImportNodeData {
  nodeType: 'import'
  subType: ImportSubType
  status: NodeStatus
  label: string
  config?: any
  output?: {
    format: 'table' | 'geometry' | 'raster' | 'hierarchical'
    schema?: any
    preview?: any
  }
}

// Transform Node Types
export interface TransformNodeData {
  nodeType: 'transform'
  pluginId: string
  pluginType: 'loader' | 'transformer' | 'aggregator'
  status: NodeStatus
  label: string
  config?: {
    group_by?: 'taxon' | 'plot' | 'shape'
    sources?: Array<{
      name: string
      data: string
      grouping: string
      relation?: any
    }>
    widget?: {
      name: string
      plugin: string
      params: Record<string, any>
    }
  }
  inputRequirements?: {
    dataFormat?: string[]
    requiredFields?: string[]
    optional?: boolean
  }
  output?: {
    widgetType?: string
    dataStructure?: any
  }
}

// Export Node Types
export interface ExportNodeData {
  nodeType: 'export'
  format: 'html' | 'json' | 'csv' | 'geojson'
  status: NodeStatus
  label: string
  config?: any
  widgets?: string[]
}

// Union type for all node data
export type PipelineNodeData = ImportNodeData | TransformNodeData | ExportNodeData

// Custom Node Type
export type PipelineNode = Node<PipelineNodeData>

// Pipeline State
export interface PipelineState {
  nodes: PipelineNode[]
  edges: Edge[]
  isValid: boolean
  errors: string[]
}

// Import Configuration
export interface ImportConfig {
  name?: string
  file?: string
  mapping?: Record<string, string>
  encoding?: string
  updateExisting?: boolean
  createMissingParents?: boolean
  [key: string]: any
}

// Catalog Item for drag & drop
export interface CatalogItem {
  type: NodeType
  subType?: string
  label: string
  description?: string
  icon?: React.ComponentType<{ className?: string }>
  defaultConfig?: any
  pluginId?: string
  format?: string
}

// Layout Configuration
export interface LayoutConfig {
  type: 'side-panel' | 'modal' | 'bottom-panel'
  position?: 'left' | 'right' | 'top' | 'bottom'
  size?: 'sm' | 'md' | 'lg' | 'xl'
  collapsible?: boolean
  defaultCollapsed?: boolean
}

// Validation Result
export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings?: string[]
}

// Data Compatibility
export interface DataCompatibility {
  formats: Record<string, string[]>
  pluginRequirements: Record<string, string[]>
  widgetRequirements: Record<string, {
    required: string[]
    format: string
  }>
}
