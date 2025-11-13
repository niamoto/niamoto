/**
 * Import Configuration Generator
 *
 * Transforms EntityConfigState into import.yml YAML format
 * conforming to EntityRegistry v2 specification.
 */

import type {
  EntityConfigState,
  EntityConfig,
  ConnectorConfig,
  HierarchyConfig
} from './import-config-types'

/**
 * Generate import.yml YAML from entity configuration state
 */
export function generateImportYAML(state: EntityConfigState): string {
  const config = buildConfigObject(state)
  return objectToYAML(config)
}

/**
 * Build configuration object from state
 */
function buildConfigObject(state: EntityConfigState): any {
  const config: any = {
    version: '1.0',
    entities: {
      datasets: {},
      references: {}
    }
  }

  // Process each entity
  Object.values(state.entities).forEach((entity) => {
    const entityConfig = buildEntityConfig(entity)

    if (entity.type === 'dataset') {
      config.entities.datasets[entity.name] = entityConfig
    } else if (entity.type === 'reference') {
      config.entities.references[entity.name] = entityConfig
    }
  })

  return config
}

/**
 * Build configuration for a single entity
 */
function buildEntityConfig(entity: EntityConfig): any {
  const config: any = {}

  // Add description if present
  if (entity.description) {
    config.description = entity.description
  }

  // Add kind for references
  if (entity.type === 'reference' && entity.kind) {
    config.kind = entity.kind
  }

  // Add connector
  config.connector = buildConnectorConfig(entity.connector)

  // Add schema
  config.schema = buildSchemaConfig(entity)

  // Add links for datasets
  if (entity.links && entity.links.length > 0) {
    config.links = entity.links.map((link) => ({
      entity: link.entity,
      field: link.field,
      target_field: link.target_field
    }))
  }

  // Add options if present
  if (entity.options) {
    config.options = {}
    if (entity.options.mode) {
      config.options.mode = entity.options.mode
    }
    if (entity.options.chunk_size) {
      config.options.chunk_size = entity.options.chunk_size
    }
  }

  // Add type-specific configuration
  if (entity.type === 'reference' && entity.kind === 'hierarchical' && entity.hierarchyConfig) {
    config.hierarchy = buildHierarchyConfig(entity.hierarchyConfig)
  }

  if (entity.enrichmentConfig && entity.enrichmentConfig.enabled) {
    config.enrichment = {
      plugin: entity.enrichmentConfig.plugin,
      enabled: true,
      config: entity.enrichmentConfig.config
    }
  }

  return config
}

/**
 * Build connector configuration
 */
function buildConnectorConfig(connector: ConnectorConfig): any {
  const config: any = {
    type: connector.type
  }

  switch (connector.type) {
    case 'file':
      if (connector.format) {
        config.format = connector.format
      }
      if (connector.path) {
        config.path = connector.path
      }
      break

    case 'derived':
      if (connector.source) {
        config.source = connector.source
      }
      if (connector.extraction) {
        config.extraction = connector.extraction
      }
      break

    case 'file_multi_feature':
      if (connector.sources) {
        config.sources = connector.sources.map((source) => ({
          name: source.name,
          path: source.path,
          name_field: source.name_field
        }))
      }
      break

    case 'database':
      if (connector.connection_string) {
        config.connection_string = connector.connection_string
      }
      if (connector.query) {
        config.query = connector.query
      }
      break

    case 'api':
      if (connector.url) {
        config.url = connector.url
      }
      if (connector.params) {
        config.params = connector.params
      }
      break
  }

  return config
}

/**
 * Build schema configuration
 */
function buildSchemaConfig(entity: EntityConfig): any {
  const config: any = {}

  if (entity.schema.id_field) {
    config.id_field = entity.schema.id_field
  }

  if (entity.schema.fields && entity.schema.fields.length > 0) {
    config.fields = entity.schema.fields.reduce((acc, field) => {
      acc[field.target] = field.source
      return acc
    }, {} as Record<string, string>)
  }

  if (entity.schema.geometry_field) {
    config.geometry_field = entity.schema.geometry_field
  }

  return config
}

/**
 * Build hierarchy configuration
 */
function buildHierarchyConfig(hierarchy: HierarchyConfig): any {
  const config: any = {
    strategy: hierarchy.strategy,
    levels: hierarchy.levels
  }

  if (hierarchy.incomplete_rows) {
    config.incomplete_rows = hierarchy.incomplete_rows
  }

  if (hierarchy.id_strategy) {
    config.id_strategy = hierarchy.id_strategy
  }

  if (hierarchy.id_column) {
    config.id_column = hierarchy.id_column
  }

  if (hierarchy.name_column) {
    config.name_column = hierarchy.name_column
  }

  return config
}

/**
 * Convert object to YAML string
 * Simple implementation - for production, consider using js-yaml library
 */
function objectToYAML(obj: any, indent = 0): string {
  const indentStr = '  '.repeat(indent)
  let yaml = ''

  if (Array.isArray(obj)) {
    obj.forEach((item) => {
      if (typeof item === 'object' && item !== null) {
        yaml += `${indentStr}- ${objectToYAML(item, indent + 1).trim()}\n`
      } else {
        yaml += `${indentStr}- ${formatValue(item)}\n`
      }
    })
  } else if (typeof obj === 'object' && obj !== null) {
    Object.entries(obj).forEach(([key, value]) => {
      if (value === undefined) return

      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        yaml += `${indentStr}${key}:\n`
        yaml += objectToYAML(value, indent + 1)
      } else if (Array.isArray(value)) {
        yaml += `${indentStr}${key}:\n`
        yaml += objectToYAML(value, indent + 1)
      } else {
        yaml += `${indentStr}${key}: ${formatValue(value)}\n`
      }
    })
  } else {
    yaml += `${indentStr}${formatValue(obj)}\n`
  }

  return yaml
}

/**
 * Format a value for YAML
 */
function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return 'null'
  }
  if (typeof value === 'string') {
    // Check if string needs quoting
    if (
      value.includes(':') ||
      value.includes('#') ||
      value.includes('\n') ||
      value.startsWith('[') ||
      value.startsWith('{')
    ) {
      return `"${value.replace(/"/g, '\\"')}"`
    }
    return value
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  return String(value)
}

/**
 * Validate generated YAML structure
 * Returns true if valid, otherwise returns error message
 */
export function validateGeneratedYAML(yaml: string): true | string {
  try {
    // Basic validation checks
    if (!yaml.includes('version:')) {
      return 'Missing version field'
    }

    if (!yaml.includes('entities:')) {
      return 'Missing entities field'
    }

    // Check for balanced indentation
    const lines = yaml.split('\n')
    for (const line of lines) {
      if (line.trim().length === 0) continue

      const currentIndent = line.search(/\S/)
      if (currentIndent !== -1 && currentIndent % 2 !== 0) {
        return 'Invalid indentation (must be multiples of 2)'
      }
    }

    return true
  } catch (error) {
    return `Validation error: ${error}`
  }
}

/**
 * Pretty print YAML with syntax highlighting hints
 * Returns object with line types for syntax highlighting
 */
export interface YAMLLine {
  text: string
  type: 'key' | 'value' | 'comment' | 'list-item' | 'empty'
  indent: number
}

export function parseYAMLForDisplay(yaml: string): YAMLLine[] {
  const lines = yaml.split('\n')
  return lines.map((line) => {
    const trimmed = line.trim()
    const indent = line.search(/\S/)

    if (trimmed.length === 0) {
      return { text: line, type: 'empty' as const, indent: 0 }
    }

    if (trimmed.startsWith('#')) {
      return { text: line, type: 'comment' as const, indent }
    }

    if (trimmed.startsWith('-')) {
      return { text: line, type: 'list-item' as const, indent }
    }

    if (trimmed.includes(':')) {
      const hasValue = trimmed.split(':')[1]?.trim().length > 0
      return {
        text: line,
        type: hasValue ? ('value' as const) : ('key' as const),
        indent
      }
    }

    return { text: line, type: 'value' as const, indent }
  })
}

/**
 * Generate example YAML for a specific entity type
 * Useful for showing users what the config will look like
 */
export function generateExampleYAML(
  entityType: 'dataset' | 'reference',
  entityKind?: 'hierarchical' | 'spatial' | 'flat'
): string {
  const examples: Record<string, any> = {
    dataset: {
      version: '1.0',
      entities: {
        datasets: {
          my_observations: {
            description: 'Species observation data',
            connector: {
              type: 'file',
              format: 'csv',
              path: 'imports/observations.csv'
            },
            schema: {
              id_field: 'id',
              fields: {
                taxon_id: 'taxon',
                location: 'location',
                date: 'observation_date'
              }
            },
            links: [
              {
                entity: 'taxonomy',
                field: 'taxon_id',
                target_field: 'id'
              }
            ]
          }
        }
      }
    },
    'reference-hierarchical': {
      version: '1.0',
      entities: {
        references: {
          taxonomy: {
            kind: 'hierarchical',
            connector: {
              type: 'file',
              format: 'csv',
              path: 'imports/taxonomy.csv'
            },
            schema: {
              fields: {
                family: 'family',
                genus: 'genus',
                species: 'species'
              }
            },
            hierarchy: {
              strategy: 'adjacency_list',
              levels: ['family', 'genus', 'species'],
              incomplete_rows: 'skip'
            }
          }
        }
      }
    },
    'reference-spatial': {
      version: '1.0',
      entities: {
        references: {
          shapes: {
            kind: 'spatial',
            connector: {
              type: 'file_multi_feature',
              sources: [
                {
                  name: 'provinces',
                  path: 'imports/provinces.shp',
                  name_field: 'name'
                }
              ]
            }
          }
        }
      }
    },
    'reference-flat': {
      version: '1.0',
      entities: {
        references: {
          plots: {
            kind: 'flat',
            connector: {
              type: 'file',
              format: 'csv',
              path: 'imports/plots.csv'
            },
            schema: {
              id_field: 'plot_id',
              fields: {
                name: 'plot_name',
                location: 'location'
              }
            }
          }
        }
      }
    }
  }

  const key = entityType === 'dataset' ? 'dataset' : `reference-${entityKind}`
  const example = examples[key] || examples.dataset

  return objectToYAML(example)
}
