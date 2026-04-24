import { describe, expect, it } from 'vitest'
import type { JSONContent } from 'novel'

import { markdownTableTestUtils, parseMarkdownTable, tableNodeToMarkdown } from './markdownTables'

function parseInlineContent(text: string): JSONContent[] {
  return text ? [{ type: 'text', text }] : []
}

function getText(node: JSONContent): string {
  if (node.text) {
    return node.text
  }
  if (!node.content) {
    return ''
  }
  return node.content.map(getText).join('')
}

describe('markdownTables', () => {
  it('parses a markdown table into a Tiptap table node', () => {
    const parsed = parseMarkdownTable(
      [
        '| Taxon | Count |',
        '| --- | --- |',
        '| Lycophytes | 2 |',
        '| Ferns | 32 |',
      ].join('\n'),
      parseInlineContent,
    )

    expect(parsed?.type).toBe('table')
    expect(parsed?.content?.[0]?.content?.[0]?.type).toBe('tableHeader')
    expect(parsed?.content?.[1]?.content?.[0]?.type).toBe('tableCell')
    expect(getText(parsed?.content?.[1]?.content?.[0] as JSONContent)).toBe('Lycophytes')
  })

  it('serializes a table node back to markdown table syntax', () => {
    const tableNode: JSONContent = {
      type: 'table',
      content: [
        {
          type: 'tableRow',
          content: [
            markdownTableTestUtils.createTableCell('tableHeader', 'Taxon'),
            markdownTableTestUtils.createTableCell('tableHeader', 'Count'),
          ],
        },
        {
          type: 'tableRow',
          content: [
            markdownTableTestUtils.createTableCell('tableCell', 'Lycophytes'),
            markdownTableTestUtils.createTableCell('tableCell', '2'),
          ],
        },
      ],
    }

    expect(tableNodeToMarkdown(tableNode, getText)).toContain('| Taxon')
    expect(tableNodeToMarkdown(tableNode, getText)).toContain('| Lycophytes')
    expect(tableNodeToMarkdown(tableNode, getText)).toContain('---')
  })

  it('escapes literal pipes when serializing table cells', () => {
    const tableNode: JSONContent = {
      type: 'table',
      content: [
        {
          type: 'tableRow',
          content: [
            markdownTableTestUtils.createTableCell('tableHeader', 'Label'),
            markdownTableTestUtils.createTableCell('tableHeader', 'Value'),
          ],
        },
        {
          type: 'tableRow',
          content: [
            markdownTableTestUtils.createTableCell('tableCell', 'Alpha | Beta'),
            markdownTableTestUtils.createTableCell('tableCell', '42'),
          ],
        },
      ],
    }

    const markdown = tableNodeToMarkdown(tableNode, getText)

    expect(markdown).toContain('Alpha \\| Beta')

    const parsed = parseMarkdownTable(markdown, parseInlineContent)
    expect(getText(parsed?.content?.[1]?.content?.[0] as JSONContent)).toBe('Alpha | Beta')
    expect(parsed?.content?.[1]?.content).toHaveLength(2)
  })
})
