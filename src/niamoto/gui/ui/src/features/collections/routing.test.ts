import { describe, expect, it } from 'vitest'

import {
  buildCollectionsPath,
  normalizeCollectionTab,
  selectionFromPath,
} from './routing'

describe('collections routing helpers', () => {
  it('extracts collection selection from the pathname', () => {
    expect(selectionFromPath('/groups')).toEqual({ type: 'overview' })
    expect(selectionFromPath('/groups/api-settings')).toEqual({
      type: 'api-settings',
    })
    expect(selectionFromPath('/groups/taxons')).toEqual({
      type: 'collection',
      name: 'taxons',
    })
  })

  it('accepts only known collection tabs', () => {
    expect(normalizeCollectionTab('content')).toBe('content')
    expect(normalizeCollectionTab('index')).toBe('index')
    expect(normalizeCollectionTab('api')).toBe('api')
    expect(normalizeCollectionTab('unknown')).toBeUndefined()
    expect(normalizeCollectionTab(null)).toBeUndefined()
  })

  it('builds collection paths with a stable tab query string', () => {
    expect(buildCollectionsPath({ type: 'overview' }, 'api')).toBe('/groups')
    expect(
      buildCollectionsPath({ type: 'collection', name: 'taxons' }, 'content')
    ).toBe('/groups/taxons')
    expect(
      buildCollectionsPath({ type: 'collection', name: 'taxons' }, 'index')
    ).toBe('/groups/taxons?tab=index')
    expect(
      buildCollectionsPath({ type: 'collection', name: 'plots hierarchy' }, 'api')
    ).toBe('/groups/plots%20hierarchy?tab=api')
  })
})
