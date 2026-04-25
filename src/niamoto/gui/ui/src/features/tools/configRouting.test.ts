import { describe, expect, it } from 'vitest'

import { buildConfigEditorPath, normalizeConfigTab } from './configRouting'

describe('configRouting', () => {
  it('normalizes known config tabs', () => {
    expect(normalizeConfigTab('config')).toBe('config')
    expect(normalizeConfigTab('import')).toBe('import')
    expect(normalizeConfigTab('transform')).toBe('transform')
    expect(normalizeConfigTab('export')).toBe('export')
  })

  it('rejects missing or unknown config tabs', () => {
    expect(normalizeConfigTab(null)).toBeNull()
    expect(normalizeConfigTab(undefined)).toBeNull()
    expect(normalizeConfigTab('runtime')).toBeNull()
  })

  it('builds deep links for config editor tabs', () => {
    expect(buildConfigEditorPath('config')).toBe('/tools/config-editor')
    expect(buildConfigEditorPath('import')).toBe('/tools/config-editor?config=import')
    expect(buildConfigEditorPath('transform')).toBe('/tools/config-editor?config=transform')
    expect(buildConfigEditorPath('export')).toBe('/tools/config-editor?config=export')
  })
})
