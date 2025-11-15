/**
 * Tests for import-config-generator
 */

import { describe, it, expect } from 'vitest'
import {
  generateImportYAML,
  validateGeneratedYAML,
  parseYAMLForDisplay,
  generateExampleYAML
} from '../import-config-generator'
import type { EntityConfigState } from '../import-config-types'

describe('generateImportYAML', () => {
  it('generates valid YAML for simple dataset', () => {
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

    const yaml = generateImportYAML(state)

    expect(yaml).toContain('version: 1.0')
    expect(yaml).toContain('entities:')
    expect(yaml).toContain('datasets:')
    expect(yaml).toContain('occurrences:')
    expect(yaml).toContain('connector:')
    expect(yaml).toContain('type: file')
    expect(yaml).toContain('format: csv')
    expect(yaml).toContain('path: imports/occurrences.csv')
    expect(yaml).toContain('schema:')
    expect(yaml).toContain('id_field: id')
    expect(yaml).toContain('fields:')
    expect(yaml).toContain('taxon_id: taxon')
    expect(yaml).toContain('location: location')
  })

  it('generates valid YAML for hierarchical reference', () => {
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
            levels: ['family', 'genus', 'species'],
            incomplete_rows: 'skip'
          },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)

    expect(yaml).toContain('references:')
    expect(yaml).toContain('taxonomy:')
    expect(yaml).toContain('kind: hierarchical')
    expect(yaml).toContain('hierarchy:')
    expect(yaml).toContain('strategy: adjacency_list')
    expect(yaml).toContain('levels:')
    expect(yaml).toContain('- family')
    expect(yaml).toContain('- genus')
    expect(yaml).toContain('- species')
    expect(yaml).toContain('incomplete_rows: skip')
  })

  it('generates valid YAML for spatial reference', () => {
    const state: EntityConfigState = {
      entities: {
        'shapes-1': {
          id: 'shapes-1',
          name: 'shapes',
          type: 'reference',
          kind: 'spatial',
          connector: {
            type: 'file_multi_feature',
            sources: [
              {
                name: 'provinces',
                path: 'imports/provinces.shp',
                name_field: 'name'
              },
              {
                name: 'watersheds',
                path: 'imports/watersheds.shp',
                name_field: 'nom'
              }
            ]
          },
          schema: {
            fields: []
          },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)

    expect(yaml).toContain('references:')
    expect(yaml).toContain('shapes:')
    expect(yaml).toContain('kind: spatial')
    expect(yaml).toContain('type: file_multi_feature')
    expect(yaml).toContain('sources:')
    expect(yaml).toContain('- name: provinces')
    expect(yaml).toContain('path: imports/provinces.shp')
    expect(yaml).toContain('name_field: name')
    expect(yaml).toContain('- name: watersheds')
  })

  it('generates valid YAML with entity links', () => {
    const state: EntityConfigState = {
      entities: {
        'tax-1': {
          id: 'tax-1',
          name: 'taxonomy',
          type: 'reference',
          kind: 'flat',
          connector: { type: 'file', format: 'csv', path: 'imports/taxonomy.csv' },
          schema: { id_field: 'id', fields: [] },
          links: []
        },
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          type: 'dataset',
          connector: { type: 'file', format: 'csv', path: 'imports/occurrences.csv' },
          schema: {
            fields: [{ source: 'taxon', target: 'taxon_id' }]
          },
          links: [
            {
              entity: 'taxonomy',
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

    const yaml = generateImportYAML(state)

    expect(yaml).toContain('links:')
    expect(yaml).toContain('- entity: taxonomy')
    expect(yaml).toContain('field: taxon_id')
    expect(yaml).toContain('target_field: id')
  })

  it('generates valid YAML with description', () => {
    const state: EntityConfigState = {
      entities: {
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          description: 'Species occurrence data from field surveys',
          type: 'dataset',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)

    expect(yaml).toContain('description: Species occurrence data from field surveys')
  })

  it('generates valid YAML with options', () => {
    const state: EntityConfigState = {
      entities: {
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          type: 'dataset',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: [],
          options: {
            mode: 'append',
            chunk_size: 1000
          }
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)

    expect(yaml).toContain('options:')
    expect(yaml).toContain('mode: append')
    expect(yaml).toContain('chunk_size: 1000')
  })

  it('generates valid YAML with enrichment config', () => {
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
            levels: ['family', 'genus', 'species']
          },
          enrichmentConfig: {
            plugin: 'gbif_enricher',
            enabled: true,
            config: {
              api_key: 'test-key'
            }
          },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)

    expect(yaml).toContain('enrichment:')
    expect(yaml).toContain('plugin: gbif_enricher')
    expect(yaml).toContain('enabled: true')
    expect(yaml).toContain('config:')
    expect(yaml).toContain('api_key: test-key')
  })

  it('handles multiple entities of different types', () => {
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
            levels: ['family', 'genus']
          },
          links: []
        },
        'plots-1': {
          id: 'plots-1',
          name: 'plots',
          type: 'reference',
          kind: 'flat',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        },
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          type: 'dataset',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)

    // Check structure
    expect(yaml).toContain('datasets:')
    expect(yaml).toContain('references:')

    // Check all entities present
    expect(yaml).toContain('taxonomy:')
    expect(yaml).toContain('plots:')
    expect(yaml).toContain('occurrences:')

    // Check types
    expect(yaml).toContain('kind: hierarchical')
    expect(yaml).toContain('kind: flat')
  })

  it('handles derived connector', () => {
    const state: EntityConfigState = {
      entities: {
        'derived-1': {
          id: 'derived-1',
          name: 'derived_data',
          type: 'dataset',
          connector: {
            type: 'derived',
            source: 'occurrences',
            extraction: {
              method: 'filter',
              fields: ['taxon_id', 'location']
            }
          },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)

    expect(yaml).toContain('type: derived')
    expect(yaml).toContain('source: occurrences')
    expect(yaml).toContain('extraction:')
  })
})

describe('validateGeneratedYAML', () => {
  it('validates correct YAML structure', () => {
    const yaml = `version: 1.0
entities:
  datasets:
    occurrences:
      connector:
        type: file`

    const result = validateGeneratedYAML(yaml)

    expect(result).toBe(true)
  })

  it('detects missing version', () => {
    const yaml = `entities:
  datasets:
    occurrences:
      connector:
        type: file`

    const result = validateGeneratedYAML(yaml)

    expect(result).toContain('Missing version')
  })

  it('detects missing entities', () => {
    const yaml = `version: 1.0
config:
  something: else`

    const result = validateGeneratedYAML(yaml)

    expect(result).toContain('Missing entities')
  })

  it('detects invalid indentation', () => {
    const yaml = `version: 1.0
entities:
 datasets:
   occurrences:
    type: file`

    const result = validateGeneratedYAML(yaml)

    expect(result).toContain('Invalid indentation')
  })
})

describe('parseYAMLForDisplay', () => {
  it('parses YAML lines with types', () => {
    const yaml = `version: 1.0
entities:
  datasets:
    # This is a comment
    occurrences:
      - item1
      type: file`

    const lines = parseYAMLForDisplay(yaml)

    expect(lines).toHaveLength(7)
    expect(lines[0].type).toBe('value')
    expect(lines[0].text).toBe('version: 1.0')
    expect(lines[1].type).toBe('key')
    expect(lines[1].text).toBe('entities:')
    expect(lines[3].type).toBe('comment')
    expect(lines[5].type).toBe('list-item')
  })

  it('handles empty lines', () => {
    const yaml = `version: 1.0

entities:`

    const lines = parseYAMLForDisplay(yaml)

    expect(lines[1].type).toBe('empty')
  })

  it('detects indent levels', () => {
    const yaml = `root:
  level1:
    level2:
      level3: value`

    const lines = parseYAMLForDisplay(yaml)

    expect(lines[0].indent).toBe(0)
    expect(lines[1].indent).toBe(2)
    expect(lines[2].indent).toBe(4)
    expect(lines[3].indent).toBe(6)
  })
})

describe('generateExampleYAML', () => {
  it('generates example for dataset', () => {
    const yaml = generateExampleYAML('dataset')

    expect(yaml).toContain('version: 1.0')
    expect(yaml).toContain('datasets:')
    expect(yaml).toContain('my_observations:')
    expect(yaml).toContain('connector:')
    expect(yaml).toContain('type: file')
  })

  it('generates example for hierarchical reference', () => {
    const yaml = generateExampleYAML('reference', 'hierarchical')

    expect(yaml).toContain('references:')
    expect(yaml).toContain('taxonomy:')
    expect(yaml).toContain('kind: hierarchical')
    expect(yaml).toContain('hierarchy:')
    expect(yaml).toContain('strategy: adjacency_list')
    expect(yaml).toContain('levels:')
  })

  it('generates example for spatial reference', () => {
    const yaml = generateExampleYAML('reference', 'spatial')

    expect(yaml).toContain('references:')
    expect(yaml).toContain('shapes:')
    expect(yaml).toContain('kind: spatial')
    expect(yaml).toContain('type: file_multi_feature')
    expect(yaml).toContain('sources:')
  })

  it('generates example for flat reference', () => {
    const yaml = generateExampleYAML('reference', 'flat')

    expect(yaml).toContain('references:')
    expect(yaml).toContain('plots:')
    expect(yaml).toContain('kind: flat')
  })
})

describe('YAML formatting', () => {
  it('uses proper indentation (2 spaces)', () => {
    const state: EntityConfigState = {
      entities: {
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          type: 'dataset',
          connector: {
            type: 'file',
            format: 'csv'
          },
          schema: {
            fields: []
          },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)
    const lines = yaml.split('\n')

    // Check consistent 2-space indentation
    lines.forEach((line) => {
      if (line.trim().length > 0) {
        const indent = line.search(/\S/)
        if (indent > 0) {
          expect(indent % 2).toBe(0) // Should be multiple of 2
        }
      }
    })
  })

  it('quotes strings with special characters', () => {
    const state: EntityConfigState = {
      entities: {
        'occ-1': {
          id: 'occ-1',
          name: 'occurrences',
          description: 'Data with: colon and # hash',
          type: 'dataset',
          connector: { type: 'file', format: 'csv' },
          schema: { fields: [] },
          links: []
        }
      },
      currentStep: 0,
      validation: { valid: true, errors: {}, warnings: {} },
      generatedConfig: null
    }

    const yaml = generateImportYAML(state)

    // Should quote the description because it contains special chars
    expect(yaml).toContain('"Data with: colon and # hash"')
  })
})
