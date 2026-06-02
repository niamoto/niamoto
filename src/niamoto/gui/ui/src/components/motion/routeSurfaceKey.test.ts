import { describe, expect, it } from 'vitest'

import { getRouteSurfaceKey } from './routeSurfaceKey'

describe('getRouteSurfaceKey', () => {
  it('keeps nested module routes on the same transition surface', () => {
    expect(getRouteSurfaceKey('/sources')).toBe('/sources')
    expect(getRouteSurfaceKey('/sources/import')).toBe('/sources')
    expect(getRouteSurfaceKey('/sources/dataset/taxons')).toBe('/sources')
    expect(getRouteSurfaceKey('/groups/taxons?tab=data')).toBe('/groups')
    expect(getRouteSurfaceKey('/site/appearance')).toBe('/site')
    expect(getRouteSurfaceKey('/publish/history')).toBe('/publish')
    expect(getRouteSurfaceKey('/help/02-user-guide/import')).toBe('/help')
  })

  it('keeps standalone tool pages distinct', () => {
    expect(getRouteSurfaceKey('/')).toBe('/')
    expect(getRouteSurfaceKey('/tools/explorer')).toBe('/tools/explorer')
    expect(getRouteSurfaceKey('/tools/settings')).toBe('/tools/settings')
  })
})
