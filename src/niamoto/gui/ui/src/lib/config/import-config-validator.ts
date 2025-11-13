/**
 * Import Configuration Validator
 *
 * Validates entity configuration before YAML generation and import execution.
 * Provides comprehensive validation rules for entity names, schemas, connectors,
 * and inter-entity relationships.
 */

import type {
  EntityConfigState,
  EntityConfig,
  ValidationResult,
  ValidationError
} from './import-config-types'

/**
 * Validate complete entity configuration state
 */
export function validateEntityConfig(state: EntityConfigState): ValidationResult {
  const errors: Record<string, ValidationError[]> = {}
  const warnings: Record<string, ValidationError[]> = {}

  const entityNames = new Set<string>()

  // Validate each entity
  Object.entries(state.entities).forEach(([id, entity]) => {
    const entityErrors: ValidationError[] = []
    const entityWarnings: ValidationError[] = []

    // Name validation
    validateEntityName(entity, entityNames, entityErrors)
    entityNames.add(entity.name)

    // Required fields validation
    validateRequiredFields(entity, entityErrors)

    // Connector validation
    validateConnector(entity, entityErrors, entityWarnings)

    // Type-specific validation
    if (entity.type === 'reference') {
      validateReference(entity, entityErrors, entityWarnings)
    } else if (entity.type === 'dataset') {
      validateDataset(entity, entityErrors, entityWarnings)
    }

    // Schema validation
    validateSchema(entity, entityErrors, entityWarnings)

    // Links validation
    validateLinks(entity, state.entities, entityErrors, entityWarnings)

    // Store results
    if (entityErrors.length > 0) {
      errors[id] = entityErrors
    }
    if (entityWarnings.length > 0) {
      warnings[id] = entityWarnings
    }
  })

  // Global validations
  validateGlobalConstraints(state, errors, warnings)

  return {
    valid: Object.keys(errors).length === 0,
    errors,
    warnings
  }
}

/**
 * Validate entity name
 */
function validateEntityName(
  entity: EntityConfig,
  existingNames: Set<string>,
  errors: ValidationError[]
): void {
  // Required
  if (!entity.name || entity.name.trim().length === 0) {
    errors.push({
      field: 'name',
      message: 'Entity name is required',
      severity: 'error'
    })
    return
  }

  // Uniqueness
  if (existingNames.has(entity.name)) {
    errors.push({
      field: 'name',
      message: `Entity name "${entity.name}" is not unique`,
      severity: 'error'
    })
  }

  // Format: snake_case
  if (!/^[a-z][a-z0-9_]*$/.test(entity.name)) {
    errors.push({
      field: 'name',
      message: 'Entity name must be snake_case (lowercase letters, digits, underscores; must start with letter)',
      severity: 'error'
    })
  }

  // Length
  if (entity.name.length < 2) {
    errors.push({
      field: 'name',
      message: 'Entity name must be at least 2 characters',
      severity: 'error'
    })
  }

  if (entity.name.length > 64) {
    errors.push({
      field: 'name',
      message: 'Entity name must not exceed 64 characters',
      severity: 'error'
    })
  }

  // Reserved names
  const reservedNames = ['metadata', 'config', 'system', 'admin']
  if (reservedNames.includes(entity.name)) {
    errors.push({
      field: 'name',
      message: `"${entity.name}" is a reserved name and cannot be used`,
      severity: 'error'
    })
  }
}

/**
 * Validate required fields
 */
function validateRequiredFields(entity: EntityConfig, errors: ValidationError[]): void {
  if (!entity.type) {
    errors.push({
      field: 'type',
      message: 'Entity type is required (dataset or reference)',
      severity: 'error'
    })
  }

  if (!entity.connector) {
    errors.push({
      field: 'connector',
      message: 'Connector configuration is required',
      severity: 'error'
    })
  }

  if (!entity.schema) {
    errors.push({
      field: 'schema',
      message: 'Schema configuration is required',
      severity: 'error'
    })
  }
}

/**
 * Validate connector configuration
 */
function validateConnector(
  entity: EntityConfig,
  errors: ValidationError[],
  warnings: ValidationError[]
): void {
  if (!entity.connector) return

  const { connector } = entity

  // Type required
  if (!connector.type) {
    errors.push({
      field: 'connector.type',
      message: 'Connector type is required',
      severity: 'error'
    })
    return
  }

  // Type-specific validation
  switch (connector.type) {
    case 'file':
      if (!connector.format) {
        errors.push({
          field: 'connector.format',
          message: 'File format is required for file connector',
          severity: 'error'
        })
      }
      if (!connector.path && !entity.file) {
        warnings.push({
          field: 'connector.path',
          message: 'No file path specified or file uploaded',
          severity: 'warning'
        })
      }
      break

    case 'derived':
      if (!connector.source) {
        errors.push({
          field: 'connector.source',
          message: 'Source entity is required for derived connector',
          severity: 'error'
        })
      }
      break

    case 'file_multi_feature':
      if (!connector.sources || connector.sources.length === 0) {
        errors.push({
          field: 'connector.sources',
          message: 'At least one source is required for multi-feature connector',
          severity: 'error'
        })
      } else {
        // Validate each source
        connector.sources.forEach((source, index) => {
          if (!source.name) {
            errors.push({
              field: `connector.sources[${index}].name`,
              message: 'Source name is required',
              severity: 'error'
            })
          }
          if (!source.path) {
            errors.push({
              field: `connector.sources[${index}].path`,
              message: 'Source path is required',
              severity: 'error'
            })
          }
          if (!source.name_field) {
            errors.push({
              field: `connector.sources[${index}].name_field`,
              message: 'Name field is required for source',
              severity: 'error'
            })
          }
        })
      }
      break

    case 'database':
      if (!connector.connection_string) {
        errors.push({
          field: 'connector.connection_string',
          message: 'Connection string is required for database connector',
          severity: 'error'
        })
      }
      break

    case 'api':
      if (!connector.url) {
        errors.push({
          field: 'connector.url',
          message: 'URL is required for API connector',
          severity: 'error'
        })
      }
      break
  }
}

/**
 * Validate reference-specific configuration
 */
function validateReference(
  entity: EntityConfig,
  errors: ValidationError[],
  warnings: ValidationError[]
): void {
  // Kind required for references
  if (!entity.kind) {
    errors.push({
      field: 'kind',
      message: 'Kind is required for reference entities (hierarchical, spatial, or flat)',
      severity: 'error'
    })
    return
  }

  // Kind-specific validation
  switch (entity.kind) {
    case 'hierarchical':
      validateHierarchicalReference(entity, errors, warnings)
      break

    case 'spatial':
      validateSpatialReference(entity, errors, warnings)
      break

    case 'flat':
      // Flat references have no special requirements
      break
  }
}

/**
 * Validate hierarchical reference
 */
function validateHierarchicalReference(
  entity: EntityConfig,
  errors: ValidationError[],
  warnings: ValidationError[]
): void {
  if (!entity.hierarchyConfig) {
    errors.push({
      field: 'hierarchyConfig',
      message: 'Hierarchy configuration is required for hierarchical references',
      severity: 'error'
    })
    return
  }

  const { hierarchyConfig } = entity

  // Strategy required
  if (!hierarchyConfig.strategy) {
    errors.push({
      field: 'hierarchyConfig.strategy',
      message: 'Hierarchy strategy is required (adjacency_list or nested_set)',
      severity: 'error'
    })
  }

  // Levels required and must be array with at least 2 levels
  if (!hierarchyConfig.levels || hierarchyConfig.levels.length === 0) {
    errors.push({
      field: 'hierarchyConfig.levels',
      message: 'Hierarchy levels are required',
      severity: 'error'
    })
  } else if (hierarchyConfig.levels.length < 2) {
    warnings.push({
      field: 'hierarchyConfig.levels',
      message: 'Hierarchy should have at least 2 levels',
      severity: 'warning'
    })
  }

  // Validate level names
  hierarchyConfig.levels?.forEach((level, index) => {
    if (!level || level.trim().length === 0) {
      errors.push({
        field: `hierarchyConfig.levels[${index}]`,
        message: 'Level name cannot be empty',
        severity: 'error'
      })
    }
    if (!/^[a-z][a-z0-9_]*$/.test(level)) {
      errors.push({
        field: `hierarchyConfig.levels[${index}]`,
        message: `Level name "${level}" must be snake_case`,
        severity: 'error'
      })
    }
  })

  // Check for duplicate level names
  const levelSet = new Set(hierarchyConfig.levels)
  if (levelSet.size !== hierarchyConfig.levels.length) {
    errors.push({
      field: 'hierarchyConfig.levels',
      message: 'Level names must be unique',
      severity: 'error'
    })
  }
}

/**
 * Validate spatial reference
 */
function validateSpatialReference(
  entity: EntityConfig,
  errors: ValidationError[],
  warnings: ValidationError[]
): void {
  // Must use file_multi_feature connector
  if (entity.connector.type !== 'file_multi_feature') {
    errors.push({
      field: 'connector.type',
      message: 'Spatial references must use file_multi_feature connector',
      severity: 'error'
    })
  }

  // Validate spatialConfig if present
  if (entity.spatialConfig) {
    if (!entity.spatialConfig.sources || entity.spatialConfig.sources.length === 0) {
      warnings.push({
        field: 'spatialConfig.sources',
        message: 'No spatial sources configured',
        severity: 'warning'
      })
    }
  }
}

/**
 * Validate dataset-specific configuration
 */
function validateDataset(
  entity: EntityConfig,
  _errors: ValidationError[],
  warnings: ValidationError[]
): void {
  // Datasets should have at least one link to a reference
  if (!entity.links || entity.links.length === 0) {
    warnings.push({
      field: 'links',
      message: 'Dataset has no links to reference entities - this may limit analysis capabilities',
      severity: 'warning'
    })
  }
}

/**
 * Validate schema configuration
 */
function validateSchema(
  entity: EntityConfig,
  errors: ValidationError[],
  warnings: ValidationError[]
): void {
  if (!entity.schema) return

  const { schema } = entity

  // Fields validation
  if (!schema.fields || schema.fields.length === 0) {
    warnings.push({
      field: 'schema.fields',
      message: 'No field mappings defined',
      severity: 'warning'
    })
  } else {
    // Check for duplicate target fields
    const targetFields = schema.fields.map((f) => f.target)
    const uniqueTargets = new Set(targetFields)
    if (uniqueTargets.size !== targetFields.length) {
      errors.push({
        field: 'schema.fields',
        message: 'Duplicate target field names found',
        severity: 'error'
      })
    }

    // Validate field names
    schema.fields.forEach((field, index) => {
      if (!field.source) {
        errors.push({
          field: `schema.fields[${index}].source`,
          message: 'Source field name is required',
          severity: 'error'
        })
      }
      if (!field.target) {
        errors.push({
          field: `schema.fields[${index}].target`,
          message: 'Target field name is required',
          severity: 'error'
        })
      }
      // Target must be snake_case
      if (field.target && !/^[a-z][a-z0-9_]*$/.test(field.target)) {
        errors.push({
          field: `schema.fields[${index}].target`,
          message: `Target field "${field.target}" must be snake_case`,
          severity: 'error'
        })
      }
    })
  }

  // ID field validation
  if (!schema.id_field) {
    warnings.push({
      field: 'schema.id_field',
      message: 'No ID field specified - auto-generated IDs will be used',
      severity: 'warning'
    })
  }

  // Geometry field for spatial data
  if (entity.type === 'reference' && entity.kind === 'spatial') {
    if (!schema.geometry_field && entity.connector.type === 'file' && entity.connector.format === 'geojson') {
      warnings.push({
        field: 'schema.geometry_field',
        message: 'No geometry field specified for spatial data',
        severity: 'warning'
      })
    }
  }
}

/**
 * Validate entity links
 */
function validateLinks(
  entity: EntityConfig,
  allEntities: Record<string, EntityConfig>,
  errors: ValidationError[],
  warnings: ValidationError[]
): void {
  if (!entity.links || entity.links.length === 0) return

  entity.links.forEach((link, index) => {
    // Required fields
    if (!link.entity) {
      errors.push({
        field: `links[${index}].entity`,
        message: 'Target entity name is required',
        severity: 'error'
      })
    }
    if (!link.field) {
      errors.push({
        field: `links[${index}].field`,
        message: 'Source field is required',
        severity: 'error'
      })
    }
    if (!link.target_field) {
      errors.push({
        field: `links[${index}].target_field`,
        message: 'Target field is required',
        severity: 'error'
      })
    }

    // Check target entity exists
    if (link.entity) {
      const targetEntity = Object.values(allEntities).find((e) => e.name === link.entity)
      if (!targetEntity) {
        errors.push({
          field: `links[${index}].entity`,
          message: `Linked entity "${link.entity}" not found`,
          severity: 'error'
        })
      } else {
        // Validate link is to a reference
        if (targetEntity.type !== 'reference') {
          warnings.push({
            field: `links[${index}].entity`,
            message: `Linking to dataset "${link.entity}" instead of reference - this is unusual`,
            severity: 'warning'
          })
        }

        // Check target field exists in target entity
        if (link.target_field) {
          const hasTargetField =
            targetEntity.schema.id_field === link.target_field ||
            targetEntity.schema.fields.some((f) => f.target === link.target_field)

          if (!hasTargetField) {
            warnings.push({
              field: `links[${index}].target_field`,
              message: `Target field "${link.target_field}" not found in entity "${link.entity}"`,
              severity: 'warning'
            })
          }
        }
      }
    }

    // Check source field exists in current entity
    if (link.field) {
      const hasSourceField = entity.schema.fields.some((f) => f.target === link.field)
      if (!hasSourceField) {
        warnings.push({
          field: `links[${index}].field`,
          message: `Source field "${link.field}" not found in current entity schema`,
          severity: 'warning'
        })
      }
    }
  })

  // Check for duplicate links
  const linkKeys = entity.links.map((l) => `${l.entity}:${l.field}`)
  const uniqueLinks = new Set(linkKeys)
  if (uniqueLinks.size !== entity.links.length) {
    warnings.push({
      field: 'links',
      message: 'Duplicate links detected',
      severity: 'warning'
    })
  }
}

/**
 * Validate global constraints across all entities
 */
function validateGlobalConstraints(
  state: EntityConfigState,
  errors: Record<string, ValidationError[]>,
  warnings: Record<string, ValidationError[]>
): void {
  const entities = Object.values(state.entities)

  // Check if at least one entity exists
  if (entities.length === 0) {
    errors['_global'] = [
      {
        field: 'entities',
        message: 'At least one entity must be configured',
        severity: 'error'
      }
    ]
    // Early return - remaining validations need entities
    return
  }

  // errors and warnings are used below in circular dependency and entity type checks

  // Check for circular dependencies in derived connectors
  const derivedEntities = entities.filter((e) => e.connector.type === 'derived')
  derivedEntities.forEach((entity) => {
    if (entity.connector.source) {
      const circular = checkCircularDependency(entity, entities, new Set())
      if (circular) {
        if (!errors[entity.id]) errors[entity.id] = []
        errors[entity.id].push({
          field: 'connector.source',
          message: 'Circular dependency detected in derived entity chain',
          severity: 'error'
        })
      }
    }
  })

  // Warn if no datasets
  const hasDatasets = entities.some((e) => e.type === 'dataset')
  if (!hasDatasets) {
    if (!warnings['_global']) warnings['_global'] = []
    warnings['_global'].push({
      field: 'entities',
      message: 'No dataset entities configured - consider adding observation or occurrence data',
      severity: 'warning'
    })
  }

  // Warn if no references
  const hasReferences = entities.some((e) => e.type === 'reference')
  if (!hasReferences) {
    if (!warnings['_global']) warnings['_global'] = []
    warnings['_global'].push({
      field: 'entities',
      message: 'No reference entities configured - consider adding taxonomy or location references',
      severity: 'warning'
    })
  }
}

/**
 * Check for circular dependencies in derived entities
 */
function checkCircularDependency(
  entity: EntityConfig,
  allEntities: EntityConfig[],
  visited: Set<string>
): boolean {
  if (visited.has(entity.id)) {
    return true // Circular dependency detected
  }

  if (entity.connector.type !== 'derived' || !entity.connector.source) {
    return false // Not derived or no source
  }

  visited.add(entity.id)

  const sourceEntity = allEntities.find((e) => e.name === entity.connector.source)
  if (!sourceEntity) {
    return false // Source not found (will be caught by other validation)
  }

  return checkCircularDependency(sourceEntity, allEntities, visited)
}

/**
 * Quick validation - checks only critical errors
 * Useful for real-time validation during user input
 */
export function quickValidate(entity: EntityConfig): ValidationError[] {
  const errors: ValidationError[] = []

  // Name format
  if (entity.name && !/^[a-z][a-z0-9_]*$/.test(entity.name)) {
    errors.push({
      field: 'name',
      message: 'Must be snake_case',
      severity: 'error'
    })
  }

  // Required fields
  if (!entity.type) {
    errors.push({ field: 'type', message: 'Required', severity: 'error' })
  }
  if (!entity.connector?.type) {
    errors.push({ field: 'connector.type', message: 'Required', severity: 'error' })
  }

  return errors
}

/**
 * Get validation summary
 */
export function getValidationSummary(validation: ValidationResult): string {
  const errorCount = Object.values(validation.errors).reduce(
    (sum, errs) => sum + errs.length,
    0
  )
  const warningCount = Object.values(validation.warnings).reduce(
    (sum, warns) => sum + warns.length,
    0
  )

  if (errorCount === 0 && warningCount === 0) {
    return 'Configuration is valid'
  }

  const parts: string[] = []
  if (errorCount > 0) {
    parts.push(`${errorCount} error${errorCount > 1 ? 's' : ''}`)
  }
  if (warningCount > 0) {
    parts.push(`${warningCount} warning${warningCount > 1 ? 's' : ''}`)
  }

  return parts.join(', ')
}
