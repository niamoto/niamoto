/**
 * Tests for import-config-validator
 */

import { describe, it, expect } from 'vitest'
import { validateEntityConfig, quickValidate, getValidationSummary } from '../import-config-validator'
import type { EntityConfigState, EntityConfig } from '../import-config-types'

describe('validateEntityConfig', () => {
  it('validates a simple valid dataset', () => {
    const state: EntityConfigState = {
      entities: {
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          type: 'dataset',
          connector: {
            type: 'file',
            format: 'csv',
            path: 'imports/occurrences.csv'
          },
          schema: {
            id_field: 'id',
            fields: [
              { source: 'taxon', target: 'taxon_id' },
              { source: 'location', target: 'location' }
            ]
          },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(true)
    expect(Object.keys(result.errors)).toHaveLength(0)
  })

  it('validates a simple valid hierarchical reference', () => {
    const state: EntityConfigState = {
      entities: {
        'tax-1': {
          id: 'tax-1',
          name: 'taxonomy',
          type: 'reference',
          kind: 'hierarchical',
          connector: {
            type: 'file',
            format: 'csv',
            path: 'imports/taxonomy.csv'
          },
          schema: {
            fields: [
              { source: 'family', target: 'family' },
              { source: 'genus', target: 'genus' },
              { source: 'species', target: 'species' }
            ]
          },
          hierarchyConfig: {
            strategy: 'adjacency_list',
            levels: ['family', 'genus', 'species']
          },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(true)
    expect(Object.keys(result.errors)).toHaveLength(0)
  })

  it('detects duplicate entity names', () => {
    const state: EntityConfigState = {
      entities: {
        'e1': {
          id: 'e1',
          name: 'taxonomy',
          type: 'reference',
          kind: 'flat',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        },
        'e2': {
          id: 'e2',
          name: 'taxonomy', // Duplicate!
          type: 'reference',
          kind: 'flat',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['e2']).toBeDefined()
    expect(result.errors['e2'].some(e => e.message.includes('not unique'))).toBe(true)
  })

  it('detects invalid entity name format', () => {
    const state: EntityConfigState = {
      entities: {
        'e1': {
          id: 'e1',
          name: 'My Taxonomy', // Invalid: contains spaces and capitals
          type: 'reference',
          kind: 'flat',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['e1']).toBeDefined()
    expect(result.errors['e1'].some(e => e.message.includes('snake_case'))).toBe(true)
  })

  it('detects reserved entity names', () => {
    const state: EntityConfigState = {
      entities: {
        'e1': {
          id: 'e1',
          name: 'metadata', // Reserved name
          type: 'reference',
          kind: 'flat',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['e1']).toBeDefined()
    expect(result.errors['e1'].some(e => e.message.includes('reserved'))).toBe(true)
  })

  it('validates hierarchical reference requires hierarchy config', () => {
    const state: EntityConfigState = {
      entities: {
        'tax-1': {
          id: 'tax-1',
          name: 'taxonomy',
          type: 'reference',
          kind: 'hierarchical',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
          // Missing hierarchyConfig!
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['tax-1']).toBeDefined()
    expect(result.errors['tax-1'].some(e => e.field === 'hierarchyConfig')).toBe(true)
  })

  it('validates hierarchy levels are required', () => {
    const state: EntityConfigState = {
      entities: {
        'tax-1': {
          id: 'tax-1',
          name: 'taxonomy',
          type: 'reference',
          kind: 'hierarchical',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          hierarchyConfig: {
            strategy: 'adjacency_list',
            levels: [] // Empty levels!
          },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['tax-1']).toBeDefined()
    expect(result.errors['tax-1'].some(e => e.field === 'hierarchyConfig.levels')).toBe(true)
  })

  it('validates spatial reference requires file_multi_feature connector', () => {
    const state: EntityConfigState = {
      entities: {
        'shapes-1': {
          id: 'shapes-1',
          name: 'shapes',
          type: 'reference',
          kind: 'spatial',
          connector: { type: 'file', format: 'csv' }, // Wrong type!
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['shapes-1']).toBeDefined()
    expect(result.errors['shapes-1'].some(e => e.message.includes('file_multi_feature'))).toBe(true)
  })

  it('validates file_multi_feature requires sources', () => {
    const state: EntityConfigState = {
      entities: {
        'shapes-1': {
          id: 'shapes-1',
          name: 'shapes',
          type: 'reference',
          kind: 'spatial',
          connector: {
            type: 'file_multi_feature',
            sources: [] // Empty sources!
          },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['shapes-1']).toBeDefined()
    expect(result.errors['shapes-1'].some(e => e.field === 'connector.sources')).toBe(true)
  })

  it('validates entity links reference existing entities', () => {
    const state: EntityConfigState = {
      entities: {
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          type: 'dataset',
          connector: { type: 'file', format: 'csv' },
          schema: {
            fields: [{ source: 'taxon', target: 'taxon_id' }]
          },
          links: [
            {
              entity: 'nonexistent_taxonomy', // Entity doesn't exist!
              field: 'taxon_id',
              target_field: 'id'
            }
          ]
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['occ-1']).toBeDefined()
    expect(result.errors['occ-1'].some(e => e.message.includes('not found'))).toBe(true)
  })

  it('validates duplicate target fields in schema', () => {
    const state: EntityConfigState = {
      entities: {
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          type: 'dataset',
          connector: { type: 'file', format: 'csv' },
          schema: {
            fields: [
              { source: 'col1', target: 'taxon_id' },
              { source: 'col2', target: 'taxon_id' } // Duplicate target!
            ]
          },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['occ-1']).toBeDefined()
    expect(result.errors['occ-1'].some(e => e.message.includes('Duplicate target'))).toBe(true)
  })

  it('warns when dataset has no links', () => {
    const state: EntityConfigState = {
      entities: {
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          type: 'dataset',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: [] // No links
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(true)
    expect(result.warnings['occ-1']).toBeDefined()
    expect(result.warnings['occ-1'].some(w => w.field === 'links')).toBe(true)
  })

  it('warns when no datasets configured', () => {
    const state: EntityConfigState = {
      entities: {
        'tax-1': {
          id: 'tax-1',
          name: 'taxonomy',
          type: 'reference', // Only reference, no dataset
          kind: 'flat',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(true)
    expect(result.warnings['_global']).toBeDefined()
    expect(result.warnings['_global'].some(w => w.message.includes('No dataset'))).toBe(true)
  })

  it('detects circular dependencies in derived entities', () => {
    const state: EntityConfigState = {
      entities: {
        'e1': {
          id: 'e1',
          name: 'entity1',
          type: 'dataset',
          connector: {
            type: 'derived',
            source: 'entity2'
          },
          schema: { fields: [] },
          links: []
        },
        'e2': {
          id: 'e2',
          name: 'entity2',
          type: 'dataset',
          connector: {
            type: 'derived',
            source: 'entity1' // Circular!
          },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const result = validateEntityConfig(state)

    expect(result.valid).toBe(false)
    expect(result.errors['e1'] || result.errors['e2']).toBeDefined()
  })
})

describe('quickValidate', () => {
  it('validates entity name format quickly', () => {
    const entity: EntityConfig = {
      id: 'e1',
      name: 'Invalid Name',
      type: 'dataset',
      connector: { type: 'file', format: 'csv' },
      schema: { fields: [] },
      links: []
    }

    const errors = quickValidate(entity)

    expect(errors.length).toBeGreaterThan(0)
    expect(errors.some(e => e.field === 'name')).toBe(true)
  })

  it('detects missing required fields', () => {
    const entity: EntityConfig = {
      id: 'e1',
      name: 'valid_name',
      type: undefined as any, // Missing type
      connector: { type: undefined as any }, // Missing connector type
      schema: { fields: [] },
      links: []
    }

    const errors = quickValidate(entity)

    expect(errors.length).toBeGreaterThan(0)
    expect(errors.some(e => e.field === 'type')).toBe(true)
    expect(errors.some(e => e.field === 'connector.type')).toBe(true)
  })

  it('returns empty array for valid entity', () => {
    const entity: EntityConfig = {
      id: 'e1',
      name: 'valid_name',
      type: 'dataset',
      connector: { type: 'file', format: 'csv' },
      schema: { fields: [] },
      links: []
    }

    const errors = quickValidate(entity)

    expect(errors).toHaveLength(0)
  })
})

describe('getValidationSummary', () => {
  it('returns success message for valid config', () => {
    const validation = {
      valid: true,
      errors: {},
      warnings: {}
    }

    const summary = getValidationSummary(validation)

    expect(summary).toBe('Configuration is valid')
  })

  it('returns error count', () => {
    const validation = {
      valid: false,
      errors: {
        'e1': [
          { field: 'name', message: 'Error 1', severity: 'error' as const },
          { field: 'type', message: 'Error 2', severity: 'error' as const }
        ]
      },
      warnings: {}
    }

    const summary = getValidationSummary(validation)

    expect(summary).toBe('2 errors')
  })

  it('returns warning count', () => {
    const validation = {
      valid: true,
      errors: {},
      warnings: {
        'e1': [
          { field: 'links', message: 'Warning 1', severity: 'warning' as const }
        ]
      }
    }

    const summary = getValidationSummary(validation)

    expect(summary).toBe('1 warning')
  })

  it('returns both errors and warnings', () => {
    const validation = {
      valid: false,
      errors: {
        'e1': [
          { field: 'name', message: 'Error', severity: 'error' as const }
        ]
      },
      warnings: {
        'e2': [
          { field: 'links', message: 'Warning 1', severity: 'warning' as const },
          { field: 'schema', message: 'Warning 2', severity: 'warning' as const }
        ]
      }
    }

    const summary = getValidationSummary(validation)

    expect(summary).toBe('1 error, 2 warnings')
  })
})
