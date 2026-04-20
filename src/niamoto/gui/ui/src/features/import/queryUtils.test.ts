import { describe, expect, it, vi } from 'vitest'

import {
  tableColumnsQueryOptions,
  tablePreviewQueryOptions,
} from '@/features/import/queryUtils'
import {
  getTableColumns,
  queryTable,
} from '@/features/import/api/data-explorer'

vi.mock('@/features/import/api/data-explorer', () => ({
  getTableColumns: vi.fn(),
  listTables: vi.fn(),
  queryTable: vi.fn(),
}))

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
})
