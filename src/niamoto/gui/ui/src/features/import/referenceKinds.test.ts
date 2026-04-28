import { describe, expect, it } from 'vitest'

import { hasHierarchyInspection } from './referenceKinds'

describe('reference kind helpers', () => {
  it('treats hierarchical and nested references as hierarchy inspectable', () => {
    expect(hasHierarchyInspection('hierarchical')).toBe(true)
    expect(hasHierarchyInspection('nested')).toBe(true)
    expect(hasHierarchyInspection('spatial')).toBe(false)
    expect(hasHierarchyInspection('generic')).toBe(false)
  })
})
