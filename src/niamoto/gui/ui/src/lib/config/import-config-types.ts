/**
 * TypeScript types for Entity Configuration System
 *
 * These types define the structure of the entity configuration state
 * used by the import wizard to generate import.yml for EntityRegistry v2.
 */

/**
 * Entity type classification
 */
type EntityType = 'reference' | 'dataset'

/**
 * Entity kind classification (for references)
 */
type EntityKind = 'hierarchical' | 'spatial' | 'categorical' | 'generic'

/**
 * Import mode
 */
type ImportMode = 'replace' | 'append'

/**
 * Hierarchy strategy
 */
type HierarchyStrategy = 'adjacency_list' | 'nested_set' | 'hybrid'

/**
 * Incomplete rows handling
 */
type IncompleteRowsStrategy = 'skip' | 'fill_unknown' | 'error'

/**
 * ID generation strategy
 */
type IdStrategy = 'hash' | 'sequence' | 'external'

/**
 * Connector type
 */
type ConnectorType =
  | 'file'
  | 'duckdb_csv'
  | 'vector'
  | 'api'
  | 'plugin'
  | 'derived'
  | 'file_multi_feature'

/**
 * File format
 */
type FileFormat = 'csv' | 'excel' | 'json' | 'geojson'

/**
 * Field mapping from source to target
 */
interface FieldMapping {
  source: string
  target: string
  type?: string
  transform?: string
}

/**
 * File analysis result
 */
interface FileAnalysis {
  columns: string[]
  rowCount?: number
  sampleData?: Record<string, unknown>[]
  detectedTypes?: Record<string, string>
  hasGeometry?: boolean
  geometryType?: string
  crs?: string
}

/**
 * Multi-feature source for spatial entities
 */
interface MultiFeatureSource {
  name: string
  path: string
  name_field: string
}

/**
 * Extraction configuration for derived entities
 */
interface ExtractionConfig {
  method?: string
  fields?: string[]
  transform?: Record<string, unknown>
}

/**
 * Connector configuration
 */
export interface ConnectorConfig {
  type: ConnectorType

  // For type: file/duckdb_csv/vector
  format?: FileFormat
  path?: string

  // For type: derived
  source?: string
  extraction?: ExtractionConfig

  // For type: file_multi_feature
  sources?: MultiFeatureSource[]

  // For type: api
  url?: string
  params?: Record<string, unknown>
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
interface SpatialConfig {
  sources: Array<{
    name: string
    path: string
    name_field: string
  }>
}

/**
 * API enrichment configuration
 */
interface EnrichmentConfig {
  id?: string
  label?: string
  plugin: string
  enabled: boolean
  config: Record<string, unknown>
}

/**
 * Entity link to another entity
 */
interface EntityLink {
  entity: string
  field: string
  target_field: string
}

/**
 * Entity schema definition
 */
interface EntitySchema {
  id_field?: string
  fields: FieldMapping[]
  geometry_field?: string
}

/**
 * Import options
 */
interface ImportOptions {
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
