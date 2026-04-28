import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const pageState = vi.hoisted(() => ({
  value: 1,
}))

const queryState = vi.hoisted(() => ({
  columns: {
    data: {
      table: 'entity_taxons',
      columns: [
        { name: 'id', type: 'INTEGER', nullable: false, default: null },
        { name: 'parent_id', type: 'INTEGER', nullable: true, default: null },
        { name: 'level', type: 'INTEGER', nullable: true, default: null },
        { name: 'rank_name', type: 'VARCHAR', nullable: true, default: null },
        { name: 'rank_value', type: 'VARCHAR', nullable: true, default: null },
        { name: 'full_path', type: 'VARCHAR', nullable: true, default: null },
        { name: 'extra_data', type: 'JSON', nullable: true, default: null },
      ],
    },
    isLoading: false,
    isFetching: false,
    error: null,
  },
  preview: {
    data: {
      columns: ['id', 'parent_id', 'level', 'rank_name', 'rank_value', 'full_path'],
      rows: [
        {
          id: 101,
          parent_id: null,
          level: 1,
          rank_name: 'family',
          rank_value: 'Araucariaceae',
          full_path: 'Araucariaceae',
        },
      ],
      total_count: 45,
      page_count: 15,
    },
    isLoading: false,
    isFetching: true,
    error: null,
  },
}))

const queryOptionsLog = vi.hoisted(() => ({
  previewEnabled: undefined as boolean | undefined,
}))

vi.mock('react', async () => {
  const actual = await vi.importActual<typeof import('react')>('react')
  return {
    ...actual,
    useState: () => [pageState.value, vi.fn()],
  }
})

vi.mock('@tanstack/react-query', async () => {
  const actual =
    await vi.importActual<typeof import('@tanstack/react-query')>(
      '@tanstack/react-query'
    )

  return {
    ...actual,
    keepPreviousData: Symbol('keepPreviousData'),
    useQuery: (options: { queryKey: unknown[]; enabled?: boolean }) => {
      const queryKey = options.queryKey
      if (queryKey[2] === 'table-columns') {
        return queryState.columns
      }

      queryOptionsLog.previewEnabled = options.enabled
      if (options.enabled === false) {
        return {
          data: undefined,
          isLoading: false,
          isFetching: false,
          error: null,
        }
      }

      return queryState.preview
    },
  }
})

vi.mock('@/components/ui/button', () => ({
  Button: (props: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props} />
  ),
}))

vi.mock('@/components/ui/table', () => ({
  Table: (props: { children: ReactNode }) => <table>{props.children}</table>,
  TableBody: (props: { children: ReactNode }) => <tbody>{props.children}</tbody>,
  TableCell: (props: { children: ReactNode; className?: string }) => (
    <td className={props.className}>{props.children}</td>
  ),
  TableHead: (props: { children: ReactNode; className?: string }) => (
    <th className={props.className}>{props.children}</th>
  ),
  TableHeader: (props: { children: ReactNode }) => <thead>{props.children}</thead>,
  TableRow: (props: { children: ReactNode }) => <tr>{props.children}</tr>,
}))

vi.mock('lucide-react', () => ({
  ChevronLeft: () => <span>prev</span>,
  ChevronRight: () => <span>next</span>,
  ExternalLink: () => <span>open</span>,
  Loader2: () => <span>loading</span>,
}))

import { TableBrowser } from './TableBrowser'

describe('TableBrowser', () => {
  beforeEach(() => {
    pageState.value = 1
    queryOptionsLog.previewEnabled = undefined
    queryState.columns = {
      data: {
        table: 'entity_taxons',
        columns: [
          { name: 'id', type: 'INTEGER', nullable: false, default: null },
          { name: 'parent_id', type: 'INTEGER', nullable: true, default: null },
          { name: 'level', type: 'INTEGER', nullable: true, default: null },
          { name: 'rank_name', type: 'VARCHAR', nullable: true, default: null },
          { name: 'rank_value', type: 'VARCHAR', nullable: true, default: null },
          { name: 'full_path', type: 'VARCHAR', nullable: true, default: null },
          { name: 'extra_data', type: 'JSON', nullable: true, default: null },
        ],
      },
      isLoading: false,
      isFetching: false,
      error: null,
    }
    queryState.preview = {
      data: {
        columns: ['id', 'parent_id', 'level', 'rank_name', 'rank_value', 'full_path'],
        rows: [
          {
            id: 101,
            parent_id: null,
            level: 1,
            rank_name: 'family',
            rank_value: 'Araucariaceae',
            full_path: 'Araucariaceae',
          },
        ],
        total_count: 45,
        page_count: 15,
      },
      isLoading: false,
      isFetching: true,
      error: null,
    }
  })

  it('shows a page-loading state and disables pagination during refetch', () => {
    const html = renderToStaticMarkup(
      <TableBrowser tableName="entity_taxons" pageSize={15} maxColumns={6} />
    )

    expect(html).toContain('sr-only">Chargement de la page</span>')
    expect(html).toContain('Page 2 / 3')
    expect(html).toContain('+1')
    expect((html.match(/<button[^>]*disabled=""/g) ?? []).length).toBe(2)
  })

  it('does not run the preview query when the table columns are unavailable', () => {
    queryState.columns = {
      data: undefined,
      isLoading: false,
      isFetching: false,
      error: { isAxiosError: true, response: { status: 404 } },
    }

    const html = renderToStaticMarkup(
      <TableBrowser tableName="dataset_occurrences" pageSize={15} maxColumns={6} />
    )

    expect(queryOptionsLog.previewEnabled).toBe(false)
    expect(html).toContain('Table not available')
  })
})
