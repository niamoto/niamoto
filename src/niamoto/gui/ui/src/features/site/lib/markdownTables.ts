import type { JSONContent } from 'novel'

function splitMarkdownTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  const cells: string[] = []
  let current = ''

  for (let index = 0; index < trimmed.length; index += 1) {
    const char = trimmed[index]
    const next = trimmed[index + 1]

    if (char === '\\' && next === '|') {
      current += '|'
      index += 1
      continue
    }

    if (char === '|') {
      cells.push(current.trim())
      current = ''
      continue
    }

    current += char
  }

  cells.push(current.trim())
  return cells
}

function isSeparatorCell(cell: string): boolean {
  return /^:?-{3,}:?$/.test(cell.trim())
}

function normalizeTableLine(line: string): string {
  return line.trimEnd()
}

function createTableCell(type: 'tableHeader' | 'tableCell', text: string): JSONContent {
  return {
    type,
    attrs: {
      colspan: 1,
      rowspan: 1,
      colwidth: null,
    },
    content: [
      {
        type: 'paragraph',
        content: text
          ? [{ type: 'text', text }]
          : [],
      },
    ],
  }
}

function parseCellContent(
  type: 'tableHeader' | 'tableCell',
  text: string,
  parseInlineContent: (value: string) => JSONContent[]
): JSONContent {
  return {
    type,
    attrs: {
      colspan: 1,
      rowspan: 1,
      colwidth: null,
    },
    content: [
      {
        type: 'paragraph',
        content: text ? parseInlineContent(text) : [],
      },
    ],
  }
}

export function parseMarkdownTable(
  markdown: string,
  parseInlineContent: (value: string) => JSONContent[]
): JSONContent | null {
  const lines = markdown
    .split('\n')
    .map(normalizeTableLine)
    .filter((line) => line.trim().length > 0)

  if (lines.length < 2) {
    return null
  }

  if (!lines.every((line) => line.includes('|'))) {
    return null
  }

  const headerCells = splitMarkdownTableRow(lines[0])
  const separatorCells = splitMarkdownTableRow(lines[1])

  if (
    headerCells.length === 0
    || separatorCells.length === 0
    || headerCells.length !== separatorCells.length
    || !separatorCells.every(isSeparatorCell)
  ) {
    return null
  }

  const bodyRows = lines.slice(2).map(splitMarkdownTableRow)
  const columnCount = Math.max(
    headerCells.length,
    ...bodyRows.map((row) => row.length),
  )

  const normalizeRow = (cells: string[]) =>
    Array.from({ length: columnCount }, (_, index) => cells[index] ?? '')

  return {
    type: 'table',
    content: [
      {
        type: 'tableRow',
        content: normalizeRow(headerCells).map((cell) =>
          parseCellContent('tableHeader', cell, parseInlineContent)
        ),
      },
      ...bodyRows.map((row) => ({
        type: 'tableRow',
        content: normalizeRow(row).map((cell) =>
          parseCellContent('tableCell', cell, parseInlineContent)
        ),
      })),
    ],
  }
}

function extractTableCellText(
  cell: JSONContent,
  getText: (node: JSONContent) => string
): string {
  const text = getText(cell)
  return text.replace(/\s*\n+\s*/g, ' ').trim()
}

function escapeMarkdownTableCell(text: string): string {
  return text.replace(/\|/g, '\\|')
}

function padRow(cells: string[], columnCount: number): string[] {
  return Array.from({ length: columnCount }, (_, index) => cells[index] ?? '')
}

export function tableNodeToMarkdown(
  node: JSONContent,
  getText: (node: JSONContent) => string
): string {
  const rows = node.content ?? []
  if (rows.length === 0) {
    return ''
  }

  const cellRows = rows.map((row) =>
    (row.content ?? []).map((cell) =>
      escapeMarkdownTableCell(extractTableCellText(cell, getText))
    )
  )

  const columnCount = Math.max(...cellRows.map((row) => row.length))
  const normalizedRows = cellRows.map((row) => padRow(row, columnCount))
  const columnWidths = Array.from({ length: columnCount }, (_, columnIndex) =>
    Math.max(
      3,
      ...normalizedRows.map((row) => row[columnIndex]?.length ?? 0)
    )
  )

  const renderRow = (row: string[]) =>
    `| ${row.map((cell, columnIndex) => cell.padEnd(columnWidths[columnIndex])).join(' | ')} |`

  const separator = `| ${columnWidths.map((width) => '-'.repeat(width)).join(' | ')} |`

  return [
    renderRow(normalizedRows[0] ?? []),
    separator,
    ...normalizedRows.slice(1).map(renderRow),
  ].join('\n')
}

export const markdownTableTestUtils = {
  createTableCell,
  escapeMarkdownTableCell,
  splitMarkdownTableRow,
}
