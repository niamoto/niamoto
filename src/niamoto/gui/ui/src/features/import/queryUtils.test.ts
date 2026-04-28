import { describe, expect, it, vi } from 'vitest'

import {
  hierarchyInspectionInfiniteQueryOptions,
  hierarchyInspectionQueryOptions,
  spatialMapLayerSummaryQueryOptions,
  spatialMapPageQueryOptions,
  spatialMapSummaryQueryOptions,
  tableColumnsQueryOptions,
  tablePreviewQueryOptions,
} from '@/features/import/queryUtils'
import {
  getTableColumns,
  queryTable,
} from '@/features/import/api/data-explorer'
import { getHierarchyInspection } from '@/features/import/api/hierarchy'
import {
  getSpatialMapInspection,
  type SpatialMapInspection,
} from '@/features/import/api/spatial-map'

vi.mock('@/features/import/api/data-explorer', () => ({
  getTableColumns: vi.fn(),
  listTables: vi.fn(),
  queryTable: vi.fn(),
}))

vi.mock('@/features/import/api/hierarchy', () => ({
  getHierarchyInspection: vi.fn(),
}))

vi.mock('@/features/import/api/spatial-map', () => ({
  getSpatialMapInspection: vi.fn(),
}))

const spatialMapInspection: SpatialMapInspection = {
  reference_name: 'shapes',
  table_name: 'entity_shapes',
  is_mappable: true,
  reason: null,
  geometry_column: 'geometry',
  geometry_storage: 'wkt',
  geometry_kind: 'polygon',
  geometry_types: ['POLYGON'],
  id_column: 'id',
  name_column: 'name',
  type_column: 'type',
  layer_column: 'type',
  selected_layer: null,
  layers: [],
  total_features: 0,
  with_geometry: 0,
  without_geometry: 0,
  bounding_box: null,
  feature_collection: {
    type: 'FeatureCollection',
    features: [],
  },
  limit: 0,
  offset: 0,
  result_count: 0,
  has_more: false,
  next_offset: null,
}

describe('import query utils', () => {
  it('requests preview pages with only the visible columns', async () => {
    vi.mocked(queryTable).mockResolvedValue({
      columns: ['id', 'full_name'],
      rows: [],
      total_count: 0,
      page_count: 0,
    })

    const options = tablePreviewQueryOptions('entity_taxons', 1, 15, [
      'id',
      'full_name',
    ])

    expect(options.queryKey).toEqual([
      'import',
      'data-preview',
      'table',
      'entity_taxons',
      1,
      15,
      ['id', 'full_name'],
    ])

    await options.queryFn()

    expect(queryTable).toHaveBeenCalledWith({
      table: 'entity_taxons',
      columns: ['id', 'full_name'],
      limit: 15,
      offset: 15,
    })
  })

  it('fetches dedicated column metadata for a table preview', async () => {
    vi.mocked(getTableColumns).mockResolvedValue({
      table: 'entity_taxons',
      columns: [
        { name: 'id', type: 'INTEGER', nullable: false, default: null },
        { name: 'full_name', type: 'VARCHAR', nullable: true, default: null },
      ],
    })

    const options = tableColumnsQueryOptions('entity_taxons')

    expect(options.queryKey).toEqual([
      'import',
      'data-preview',
      'table-columns',
      'entity_taxons',
    ])

    await options.queryFn()

    expect(getTableColumns).toHaveBeenCalledWith('entity_taxons')
  })

  it('does not retry column metadata when the table is missing', () => {
    const options = tableColumnsQueryOptions('dataset_occurrences') as ReturnType<
      typeof tableColumnsQueryOptions
    > & {
      retry?: (failureCount: number, error: unknown) => boolean
    }
    const retry = options.retry

    expect(retry).toBeTypeOf('function')
    expect(
      retry?.(0, { isAxiosError: true, response: { status: 404 } })
    ).toBe(false)
    expect(retry?.(0, new Error('temporary failure'))).toBe(true)
    expect(retry?.(2, new Error('temporary failure'))).toBe(false)
  })

  it('builds hierarchy inspection queries by mode', async () => {
    vi.mocked(getHierarchyInspection).mockResolvedValue({
      reference_name: 'taxons',
      table_name: 'entity_taxons',
      is_hierarchical: true,
      metadata_available: true,
      mode: 'children',
      search: null,
      parent_id: 101,
      total_nodes: 4,
      root_count: 1,
      orphan_count: 0,
      levels: [],
      nodes: [],
      limit: 100,
      offset: 0,
      result_count: 0,
      has_more: false,
      next_offset: null,
    })

    const options = hierarchyInspectionQueryOptions('taxons', {
      mode: 'children',
      parentId: 101,
      limit: 25,
      offset: 50,
    })

    expect(options.queryKey).toEqual([
      'import',
      'hierarchy',
      'taxons',
      'children',
      '101',
      25,
      50,
    ])

    await options.queryFn()

    expect(getHierarchyInspection).toHaveBeenCalledWith('taxons', {
      mode: 'children',
      parentId: 101,
      limit: 25,
      offset: 50,
    })
  })

  it('builds pageable hierarchy inspection queries', async () => {
    vi.mocked(getHierarchyInspection).mockResolvedValue({
      reference_name: 'taxons',
      table_name: 'entity_taxons',
      is_hierarchical: true,
      metadata_available: true,
      mode: 'search',
      search: 'Araucaria',
      parent_id: null,
      total_nodes: 4,
      root_count: 1,
      orphan_count: 0,
      levels: [],
      nodes: [],
      limit: 25,
      offset: 25,
      result_count: 30,
      has_more: true,
      next_offset: 50,
    })

    const options = hierarchyInspectionInfiniteQueryOptions('taxons', {
      mode: 'search',
      search: '  Araucaria  ',
      limit: 25,
    })

    expect(options.queryKey).toEqual([
      'import',
      'hierarchy',
      'taxons',
      'search',
      'Araucaria',
      25,
      0,
    ])
    expect(options.initialPageParam).toBe(0)

    await options.queryFn({ pageParam: 25 })

    expect(getHierarchyInspection).toHaveBeenCalledWith('taxons', {
      mode: 'search',
      search: 'Araucaria',
      limit: 25,
      offset: 25,
    })
  })

  it('builds spatial map summary queries', async () => {
    vi.mocked(getSpatialMapInspection).mockResolvedValue(spatialMapInspection)

    const summaryOptions = spatialMapSummaryQueryOptions('shapes')
    const layerOptions = spatialMapLayerSummaryQueryOptions('shapes', 'province')

    expect(summaryOptions.queryKey).toEqual([
      'import',
      'spatial-map',
      'shapes',
      'summary',
    ])
    expect(layerOptions.queryKey).toEqual([
      'import',
      'spatial-map',
      'shapes',
      'summary',
      'province',
    ])

    await summaryOptions.queryFn()
    await layerOptions.queryFn()

    expect(getSpatialMapInspection).toHaveBeenNthCalledWith(1, 'shapes', {
      limit: 0,
    })
    expect(getSpatialMapInspection).toHaveBeenNthCalledWith(2, 'shapes', {
      limit: 0,
      layer: 'province',
    })
  })

  it('builds spatial map page queries', async () => {
    vi.mocked(getSpatialMapInspection).mockResolvedValue(spatialMapInspection)

    const options = spatialMapPageQueryOptions('shapes', 250, 1000, 'province')

    expect(options.queryKey).toEqual([
      'import',
      'spatial-map',
      'shapes',
      1000,
      250,
      'province',
    ])

    await options.queryFn()

    expect(getSpatialMapInspection).toHaveBeenCalledWith('shapes', {
      limit: 1000,
      offset: 250,
      layer: 'province',
    })
  })
})
