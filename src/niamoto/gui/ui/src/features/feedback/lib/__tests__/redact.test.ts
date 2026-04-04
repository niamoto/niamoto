import { describe, expect, it } from 'vitest'
import { redact, redactObject } from '../redact'

describe('redact', () => {
  it('redacts macOS user paths', () => {
    expect(redact('/Users/julien/Dev/niamoto/db.duckdb')).toBe('<user>/Dev/niamoto/db.duckdb')
  })

  it('redacts Windows user paths', () => {
    expect(redact('C:\\Users\\John\\Documents\\niamoto\\data.csv')).toBe('<user>\\Documents\\niamoto\\data.csv')
  })

  it('redacts Windows paths case-insensitively', () => {
    expect(redact('c:\\users\\admin\\Desktop\\file.txt')).toBe('<user>\\Desktop\\file.txt')
  })

  it('redacts tilde paths', () => {
    expect(redact('~/niamoto-data/import.yml')).toBe('<home>/import.yml')
  })

  it('handles multiple paths in a string', () => {
    const input = 'Error at /Users/alice/src/main.ts and /Users/alice/config.yml'
    const expected = 'Error at <user>/src/main.ts and <user>/config.yml'
    expect(redact(input)).toBe(expected)
  })

  it('leaves strings without paths unchanged', () => {
    expect(redact('TypeError: Cannot read property data')).toBe('TypeError: Cannot read property data')
  })

  it('handles paths in stack traces', () => {
    const stack = `TypeError: Cannot read property 'data' of undefined
    at TaxonChart (/Users/dev/niamoto/src/TaxonChart.tsx:42:15)
    at renderWithHooks (/Users/dev/niamoto/node_modules/react/index.js:100:1)`
    const result = redact(stack)
    expect(result).not.toContain('/Users/dev/')
    expect(result).toContain('<user>/niamoto/src/TaxonChart.tsx:42:15')
  })
})

describe('redactObject', () => {
  it('redacts strings in objects recursively', () => {
    const input = {
      path: '/Users/julien/project/db.duckdb',
      nested: {
        file: 'C:\\Users\\Admin\\data.csv',
      },
    }
    const result = redactObject(input)
    expect(result.path).toBe('<user>/project/db.duckdb')
    expect(result.nested.file).toBe('<user>\\data.csv')
  })

  it('redacts strings in arrays', () => {
    const input = ['/Users/alice/a.txt', '/Users/bob/b.txt']
    const result = redactObject(input)
    expect(result).toEqual(['<user>/a.txt', '<user>/b.txt'])
  })

  it('preserves non-string primitives', () => {
    const input = { count: 42, active: true, label: null }
    expect(redactObject(input)).toEqual(input)
  })
})
