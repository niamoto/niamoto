/**
 * TypeScript types for Entity Configuration System
 *
 * These types define the structure of the entity configuration state
 * used by the import wizard to generate import.yml for EntityRegistry v2.
 */

/**
 * Entity type classification
 */
export type EntityType = 'reference' | 'dataset'

/**
 * Entity kind classification (for references)
 */
export type EntityKind = 'hierarchical' | 'spatial' | 'flat'

/**
 * Import mode
 */
export type ImportMode = 'replace' | 'append'

/**
 * Hierarchy strategy
 */
export type HierarchyStrategy = 'adjacency_list' | 'nested_set'

/**
 * Incomplete rows handling
 */
export type IncompleteRowsStrategy = 'skip' | 'keep'

/**
 * ID generation strategy
 */
export type IdStrategy = 'hash' | 'auto'

/**
 * Connector type
 */
export type ConnectorType = 'file' | 'derived' | 'file_multi_feature' | 'database' | 'api'

/**
 * File format
 */
export type FileFormat = 'csv' | 'excel' | 'json' | 'geojson'

/**
 * Field mapping from source to target
 */
export interface FieldMapping {
  source: string
  target: string
  type?: string
  transform?: string
}

/**
 * File analysis result
 */
export interface FileAnalysis {
  columns: string[]
  rowCount?: number
  sampleData?: Record<string, any>[]
  detectedTypes?: Record<string, string>
  hasGeometry?: boolean
  geometryType?: string
  crs?: string
}

/**
 * Multi-feature source for spatial entities
 */
export interface MultiFeatureSource {
  name: string
  path: string
  name_field: string
}

/**
 * Extraction configuration for derived entities
 */
export interface ExtractionConfig {
  method?: string
  fields?: string[]
  transform?: Record<string, any>
}

/**
 * Connector configuration
 */
export interface ConnectorConfig {
  type: ConnectorType

  // For type: file
  format?: FileFormat
  path?: string

  // For type: derived
  source?: string
  extraction?: ExtractionConfig

  // For type: file_multi_feature
  sources?: MultiFeatureSource[]

  // For type: database
  connection_string?: string
  query?: string

  // For type: api
  url?: string
  params?: Record<string, any>
}

/**
 * Hierarchy configuration for hierarchical references
 */
export interface HierarchyConfig {
  strategy: HierarchyStrategy
  levels: string[]
  incomplete_rows?: IncompleteRowsStrategy
  id_strategy?: IdStrategy
  id_column?: string
  name_column?: string
}

/**
 * Spatial configuration for spatial references
 */
export interface SpatialConfig {
  sources: Array<{
    name: string
    path: string
    name_field: string
  }>
}

/**
 * API enrichment configuration
 */
export interface EnrichmentConfig {
  plugin: string
  enabled: boolean
  config: Record<string, any>
}

/**
 * Entity link to another entity
 */
export interface EntityLink {
  entity: string
  field: string
  target_field: string
}

/**
 * Entity schema definition
 */
export interface EntitySchema {
  id_field?: string
  fields: FieldMapping[]
  geometry_field?: string
}

/**
 * Import options
 */
export interface ImportOptions {
  mode?: ImportMode
  chunk_size?: number
  validate?: boolean
  dry_run?: boolean
}

/**
 * Complete entity configuration
 */
export interface EntityConfig {
  // Identifier (unique key in entities record)
  id: string

  // Metadata
  name: string
  displayName?: string
  description?: string

  // Type and kind
  type: EntityType
  kind?: EntityKind

  // Source file
  file?: File
  fileAnalysis?: FileAnalysis
  configPath?: string

  // Schema mapping
  schema: EntitySchema

  // Connector configuration
  connector: ConnectorConfig

  // Links to other entities
  links: EntityLink[]

  // Import options
  options?: ImportOptions

  // Type-specific configuration
  hierarchyConfig?: HierarchyConfig
  spatialConfig?: SpatialConfig
  enrichmentConfig?: EnrichmentConfig
}

/**
 * Validation error
 */
export interface ValidationError {
  field: string
  message: string
  severity: 'error' | 'warning'
}

/**
 * Validation result
 */
export interface ValidationResult {
  valid: boolean
  errors: Record<string, ValidationError[]>
  warnings: Record<string, ValidationError[]>
}

/**
 * Entity configuration state
 */
export interface EntityConfigState {
  // Map of entity ID to entity configuration
  entities: Record<string, EntityConfig>

  // Current wizard step
  currentStep: number

  // Validation state
  validation: ValidationResult

  // Generated YAML preview
  generatedConfig: string | null

  // Import execution state
  execution?: {
    status: 'idle' | 'uploading' | 'configuring' | 'importing' | 'complete' | 'error'
    progress: Record<string, number>
    logs: string[]
    errors: string[]
  }
}

/**
 * Context actions
 */
export interface EntityConfigActions {
  // Entity management
  addEntity: (entity: EntityConfig) => void
  updateEntity: (id: string, updates: Partial<EntityConfig>) => void
  removeEntity: (id: string) => void

  // Navigation
  setStep: (step: number) => void
  nextStep: () => void
  previousStep: () => void

  // Validation
  validateConfig: () => Promise<ValidationResult>
  setValidation: (validation: ValidationResult) => void

  // Configuration
  generateYAML: () => string
  setGeneratedConfig: (config: string) => void

  // Execution
  saveConfig: () => Promise<boolean>
  executeImport: () => Promise<void>
  updateProgress: (entityId: string, progress: number) => void
  addLog: (message: string) => void
  addError: (message: string) => void

  // Reset
  reset: () => void
}

/**
 * Combined context value
 */
export interface EntityConfigContextValue {
  state: EntityConfigState
  actions: EntityConfigActions
}

/**
 * Predefined entity template
 */
export interface EntityTemplate {
  id: string
  label: string
  description: string
  type: EntityType
  kind?: EntityKind
  icon?: string
  defaultName: string
  suggestedFields?: string[]
}

/**
 * Available entity templates
 */
export const ENTITY_TEMPLATES: EntityTemplate[] = [
  {
    id: 'occurrences',
    label: 'Occurrences / Observations',
    description: 'Species occurrence data with coordinates',
    type: 'dataset',
    icon: 'database',
    defaultName: 'occurrences',
    suggestedFields: ['taxon', 'location', 'date']
  },
  {
    id: 'taxonomy',
    label: 'Taxonomie Hiérarchique',
    description: 'Hierarchical taxonomy (family, genus, species)',
    type: 'reference',
    kind: 'hierarchical',
    icon: 'hierarchy',
    defaultName: 'taxonomy',
    suggestedFields: ['family', 'genus', 'species']
  },
  {
    id: 'plots',
    label: 'Sites / Parcelles',
    description: 'Study sites or plots',
    type: 'reference',
    kind: 'flat',
    icon: 'map-pin',
    defaultName: 'plots',
    suggestedFields: ['name', 'location', 'area']
  },
  {
    id: 'shapes',
    label: 'Formes Spatiales',
    description: 'Spatial polygons (provinces, watersheds, etc.)',
    type: 'reference',
    kind: 'spatial',
    icon: 'map',
    defaultName: 'shapes',
    suggestedFields: ['name', 'geometry']
  }
]
