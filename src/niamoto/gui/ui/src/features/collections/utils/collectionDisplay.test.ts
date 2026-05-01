import { describe, expect, it } from 'vitest'

import type { ReferenceInfo } from '@/hooks/useReferences'
import type { CollectionCatalogEntry } from '@/features/collections/hooks/useCollectionsCatalog'

import {
  buildCollectionDisplayItems,
  canRunCollectionTransform,
  defaultCollectionTab,
} from './collectionDisplay'

describe('collectionDisplay', () => {
  it('adds visible manual collections that are not references', () => {
    const references: ReferenceInfo[] = [
      {
        name: 'plots',
        table_name: 'plots',
        kind: 'generic',
        schema_fields: [],
        entity_count: 22,
      },
    ]
    const collections: CollectionCatalogEntry[] = [
      {
        name: 'occurrences_publication',
        label: 'Occurrences publication',
        source_type: 'dataset',
        source_name: 'occurrences',
        grain: 'occurrence',
        roles: ['api', 'standard', 'site'],
        visible: true,
        review_status: 'accepted',
        confidence: 1,
        description: null,
        evidence: [],
      },
      {
        name: 'technical_occurrences',
        label: 'Technical occurrences',
        source_type: 'dataset',
        source_name: 'occurrences',
        grain: 'occurrence',
        roles: ['technical'],
        visible: false,
        review_status: 'accepted',
        confidence: 1,
        description: null,
        evidence: [],
      },
    ]

    const items = buildCollectionDisplayItems(references, collections)
    const manualItem = items.find((item) => item.name === 'occurrences_publication')

    expect(items.map((item) => item.name)).toEqual([
      'occurrences_publication',
      'plots',
    ])
    expect(manualItem?.catalogOnly).toBe(true)
    expect(manualItem?.displayName).toBe('Occurrences publication')
    expect(defaultCollectionTab(manualItem!)).toBeUndefined()
    expect(canRunCollectionTransform(manualItem!)).toBe(false)
  })
})
