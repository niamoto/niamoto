import { describe, expect, it } from 'vitest'

import { buildImportInventory, summarizeInventory } from './importInventory'
import type { AutoConfigureResponse } from '@/features/import/api/smart-config'
import { getFilePreflightKey } from '@/features/import/components/upload/filePreflight'

describe('buildImportInventory', () => {
  it('turns selected mixed files into compact inventory items', () => {
    const occurrences = new File(['id,id_taxonref,family,genus,species\n1,12,A,B,C'], 'occurrences.csv', {
      type: 'text/csv',
    })
    const communes = new File(['gpkg'], 'communes.gpkg')
    const rainfall = new File(['tif'], 'rainfall.tif')

    const inventory = buildImportInventory({
      selectedFiles: [occurrences, communes, rainfall],
      filePreflight: {
        [getFilePreflightKey(occurrences)]: {
          fileName: 'occurrences.csv',
          status: 'ready',
          badges: ['headers', 'identifiers', 'taxonomyFromOccurrences'],
          tips: [],
        },
      },
    })

    expect(inventory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          name: 'occurrences.csv',
          role: 'occurrences',
          status: 'ready',
          quality: 'good',
        }),
        expect.objectContaining({
          name: 'communes.gpkg',
          role: 'spatial_layer',
          status: 'selected',
        }),
        expect.objectContaining({
          name: 'rainfall.tif',
          role: 'raster_layer',
          status: 'selected',
        }),
      ])
    )
  })

  it('updates uploaded files from auto-configuration events', () => {
    const inventory = buildImportInventory({
      uploadedFiles: [
        {
          filename: 'occurrences.csv',
          path: 'imports/occurrences.csv',
          size: 100,
          type: 'csv',
        },
      ],
      autoConfigEvents: [
        {
          kind: 'detail',
          message: 'Reading headers',
          timestamp: 1,
          file: 'imports/occurrences.csv',
        },
        {
          kind: 'finding',
          message: 'Review recommended for occurrences',
          timestamp: 2,
          entity: 'occurrences',
        },
      ],
    })

    expect(inventory).toHaveLength(1)
    expect(inventory[0]).toMatchObject({
      name: 'occurrences.csv',
      status: 'needs_attention',
      quality: 'review',
      primaryMessage: 'Review recommended for occurrences',
    })
  })

  it('marks selected files as uploading while the parent upload is running', () => {
    const occurrences = new File(['id,id_taxonref\n1,12'], 'occurrences.csv', {
      type: 'text/csv',
    })

    const inventory = buildImportInventory({
      selectedFiles: [occurrences],
      selectedFilesUploading: true,
      filePreflight: {
        [getFilePreflightKey(occurrences)]: {
          fileName: 'occurrences.csv',
          status: 'ready',
          badges: ['headers'],
          tips: [],
        },
      },
    })

    expect(inventory[0]).toMatchObject({
      name: 'occurrences.csv',
      status: 'uploading',
      quality: 'info',
      primaryMessage: 'uploading',
    })
  })

  it('creates analysed role-based items from auto-configuration results', () => {
    const result: AutoConfigureResponse = {
      success: true,
      entities: {
        datasets: {
          occurrences: {
            connector: {
              path: 'imports/occurrences.csv',
              format: 'csv',
            },
            schema: {
              id_field: 'id',
            },
          },
        },
        references: {
          provinces: {
            kind: 'spatial',
            connector: {
              path: 'imports/provinces.gpkg',
              format: 'gpkg',
            },
          },
        },
        metadata: {
          layers: [
            {
              name: 'rainfall',
              type: 'raster',
              path: 'imports/rainfall.tif',
              format: 'tif',
            },
          ],
        },
      },
      auxiliary_sources: [
        {
          name: 'raw_plot_stats',
          data: 'imports/raw_plot_stats.csv',
          grouping: 'plots',
          relation: {
            plugin: 'join',
            key: 'plot_id',
            ref_field: 'id',
            match_field: 'plot_id',
          },
        },
      ],
      decision_summary: {
        occurrences: {
          final_entity_type: 'dataset',
          heuristic_entity_type: 'dataset',
          heuristic_confidence: 0.92,
          review_required: true,
          review_level: 'review',
          review_reasons: ['Taxonomy derived from occurrences'],
        },
      },
      confidence: 0.9,
      warnings: [],
    }

    const inventory = buildImportInventory({ autoConfigResult: result })

    expect(inventory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: 'dataset:occurrences',
          role: 'occurrences',
          status: 'needs_attention',
        }),
        expect.objectContaining({
          id: 'reference:provinces',
          role: 'spatial_layer',
          status: 'analysed',
        }),
        expect.objectContaining({
          id: 'auxiliary:raw_plot_stats:0',
          role: 'class_values',
          status: 'analysed',
        }),
        expect.objectContaining({
          id: 'layer:rainfall:0',
          role: 'raster_layer',
          status: 'analysed',
        }),
      ])
    )
    expect(summarizeInventory(inventory)).toMatchObject({
      total: 4,
      needs_attention: 1,
      attention: 1,
    })
  })

  it('keeps notice-level review reasons as non-blocking notes', () => {
    const result: AutoConfigureResponse = {
      success: true,
      entities: {
        datasets: {},
        references: {
          plots: {
            kind: 'generic',
            connector: {
              path: 'imports/plots.csv',
              format: 'csv',
            },
          },
        },
        metadata: {},
      },
      auxiliary_sources: [],
      decision_summary: {
        plots: {
          final_entity_type: 'reference',
          heuristic_entity_type: 'reference',
          heuristic_confidence: 0.9,
          review_required: false,
          review_level: 'notice',
          review_reasons: [
            'Reference enriched with measurements or geometry; ML also saw dataset-like signals (100%).',
          ],
        },
      },
      confidence: 0.9,
      warnings: [],
    }

    const inventory = buildImportInventory({ autoConfigResult: result })

    expect(inventory[0]).toMatchObject({
      id: 'reference:plots',
      status: 'analysed',
      quality: 'info',
    })
    expect(inventory[0].details).toContainEqual(
      expect.objectContaining({
        label: 'notice',
        tone: 'info',
      })
    )
    expect(inventory[0].details).not.toContainEqual(
      expect.objectContaining({
        label: 'review',
      })
    )
    expect(inventory[0].tips).toEqual([])
    expect(summarizeInventory(inventory)).toMatchObject({
      needs_attention: 0,
      attention: 0,
      analysed: 1,
    })
  })

  it('keeps uploaded files as the primary inventory after auto-configuration', () => {
    const result: AutoConfigureResponse = {
      success: true,
      entities: {
        datasets: {
          occurrences: {
            connector: {
              path: 'imports/occurrences.csv',
              format: 'csv',
            },
          },
        },
        references: {
          taxons: {
            kind: 'hierarchical',
            connector: {
              type: 'derived',
              source: 'occurrences',
            },
          },
          shapes: {
            kind: 'spatial',
            connector: {
              type: 'file_multi_feature',
              sources: [
                { path: 'imports/countries.gpkg' },
                { path: 'imports/communes.gpkg' },
              ],
            },
          },
        },
        metadata: {
          layers: [
            {
              name: 'rainfall',
              type: 'raster',
              path: 'imports/rainfall.tif',
              format: 'tif',
            },
          ],
        },
      },
      confidence: 0.9,
      warnings: [],
    }

    const inventory = buildImportInventory({
      uploadedFiles: [
        { filename: 'occurrences.csv', path: 'imports/occurrences.csv', type: 'csv' },
        { filename: 'rainfall.tif', path: 'imports/rainfall.tif', type: 'tif' },
        { filename: 'countries.gpkg', path: 'imports/countries.gpkg', type: 'gpkg' },
        { filename: 'communes.gpkg', path: 'imports/communes.gpkg', type: 'gpkg' },
        { filename: 'unused.gpkg', path: 'imports/unused.gpkg', type: 'gpkg' },
      ],
      autoConfigResult: result,
    })

    expect(inventory).toHaveLength(5)
    expect(inventory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          name: 'occurrences.csv',
          detectedEntityName: 'occurrences',
          role: 'occurrences',
          status: 'analysed',
        }),
        expect.objectContaining({
          name: 'rainfall.tif',
          detectedEntityName: 'rainfall',
          role: 'raster_layer',
          status: 'analysed',
        }),
        expect.objectContaining({
          name: 'countries.gpkg',
          detectedEntityName: 'shapes',
          role: 'spatial_layer',
          status: 'analysed',
        }),
        expect.objectContaining({
          name: 'communes.gpkg',
          detectedEntityName: 'shapes',
          role: 'spatial_layer',
          status: 'analysed',
        }),
        expect.objectContaining({
          name: 'unused.gpkg',
          role: 'spatial_layer',
          status: 'not_configured',
          quality: 'info',
          primaryMessage: 'not_configured',
        }),
      ])
    )
    expect(inventory.some((item) => item.name === 'taxons')).toBe(false)
  })

  it('maps import events onto analysed items', () => {
    const result: AutoConfigureResponse = {
      success: true,
      entities: {
        datasets: {
          occurrences: {
            connector: {
              path: 'imports/occurrences.csv',
              format: 'csv',
            },
          },
          plots: {
            connector: {
              path: 'imports/plots.csv',
              format: 'csv',
            },
          },
        },
        references: {},
      },
      confidence: 1,
      warnings: [],
    }

    const inventory = buildImportInventory({
      autoConfigResult: result,
      importing: true,
      importEvents: [
        {
          timestamp: '2026-05-21T00:00:00Z',
          kind: 'finding',
          message: 'Imported occurrences',
          entity_name: 'occurrences',
        },
        {
          timestamp: '2026-05-21T00:00:01Z',
          kind: 'error',
          message: 'Import failed for plots',
          entity_name: 'plots',
        },
      ],
    })

    expect(inventory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: 'occurrences', status: 'imported', quality: 'good' }),
        expect.objectContaining({ name: 'plots', status: 'failed', quality: 'error' }),
      ])
    )
  })

  it('keeps same-basename files matched to their exact detected source', () => {
    const result: AutoConfigureResponse = {
      success: true,
      entities: {
        datasets: {
          sampling_table: {
            connector: {
              path: 'imports/plots.csv',
              format: 'csv',
            },
          },
        },
        references: {
          plot_shapes: {
            kind: 'spatial',
            connector: {
              path: 'imports/plots.gpkg',
              format: 'gpkg',
            },
          },
        },
      },
      confidence: 0.9,
      warnings: [],
    }

    const inventory = buildImportInventory({
      uploadedFiles: [
        { filename: 'plots.gpkg', path: 'imports/plots.gpkg', type: 'gpkg' },
        { filename: 'plots.csv', path: 'imports/plots.csv', type: 'csv' },
      ],
      autoConfigResult: result,
    })

    expect(inventory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          name: 'plots.gpkg',
          detectedEntityName: 'plot_shapes',
          role: 'sites',
        }),
        expect.objectContaining({
          name: 'plots.csv',
          detectedEntityName: 'sampling_table',
          role: 'dataset',
        }),
      ])
    )
  })

  it('does not fall back to basename when both uploaded and detected files have different concrete paths', () => {
    const result: AutoConfigureResponse = {
      success: true,
      entities: {
        datasets: {
          north_sampling: {
            connector: {
              path: 'imports/north/plots.csv',
              format: 'csv',
            },
          },
          south_sampling: {
            connector: {
              path: 'imports/south/plots.csv',
              format: 'csv',
            },
          },
        },
        references: {},
      },
      confidence: 0.9,
      warnings: [],
    }

    const inventory = buildImportInventory({
      uploadedFiles: [
        { filename: 'plots.csv', path: 'imports/south/plots.csv', type: 'csv' },
        { filename: 'plots.csv', path: 'imports/north/plots.csv', type: 'csv' },
      ],
      autoConfigResult: result,
    })

    expect(inventory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          sourcePath: 'imports/south/plots.csv',
          detectedEntityName: 'south_sampling',
        }),
        expect.objectContaining({
          sourcePath: 'imports/north/plots.csv',
          detectedEntityName: 'north_sampling',
        }),
      ])
    )
  })

  it('applies import events to every uploaded file that belongs to the same multi-source entity', () => {
    const result: AutoConfigureResponse = {
      success: true,
      entities: {
        datasets: {},
        references: {
          shapes: {
            kind: 'spatial',
            connector: {
              type: 'file_multi_feature',
              sources: [
                { path: 'imports/countries.gpkg' },
                { path: 'imports/communes.gpkg' },
              ],
            },
          },
        },
      },
      confidence: 0.9,
      warnings: [],
    }

    const inventory = buildImportInventory({
      uploadedFiles: [
        { filename: 'countries.gpkg', path: 'imports/countries.gpkg', type: 'gpkg' },
        { filename: 'communes.gpkg', path: 'imports/communes.gpkg', type: 'gpkg' },
      ],
      autoConfigResult: result,
      importing: true,
      importEvents: [
        {
          timestamp: '2026-05-21T00:00:00Z',
          kind: 'finding',
          message: 'Imported shapes',
          entity_name: 'shapes',
        },
      ],
    })

    expect(inventory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          name: 'countries.gpkg',
          detectedEntityName: 'shapes',
          status: 'imported',
        }),
        expect.objectContaining({
          name: 'communes.gpkg',
          detectedEntityName: 'shapes',
          status: 'imported',
        }),
      ])
    )
  })
})
