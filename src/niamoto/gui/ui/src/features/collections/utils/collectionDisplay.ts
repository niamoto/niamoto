import type { ReferenceInfo } from '@/hooks/useReferences'
import type {
  CollectionCatalogEntry,
  CollectionSourceType,
} from '@/features/collections/hooks/useCollectionsCatalog'

export interface CollectionDisplayItem extends ReferenceInfo {
  catalogOnly: boolean
  displayName: string
  collectionMetadata?: CollectionCatalogEntry
}

export function buildCollectionDisplayItems(
  references: ReferenceInfo[],
  collections: CollectionCatalogEntry[],
): CollectionDisplayItem[] {
  const collectionByName = new Map(
    collections.map((collection) => [collection.name, collection]),
  )
  const referenceNames = new Set(references.map((reference) => reference.name))

  const referenceItems = references.map((reference) => {
    const collectionMetadata = collectionByName.get(reference.name)
    return {
      ...reference,
      catalogOnly: false,
      displayName: collectionMetadata?.label || reference.name,
      collectionMetadata,
    }
  })

  const catalogOnlyItems = collections
    .filter((collection) => collection.visible && !referenceNames.has(collection.name))
    .map(collectionDisplayItemFromCatalog)

  return [...referenceItems, ...catalogOnlyItems].sort((left, right) =>
    left.displayName.localeCompare(right.displayName),
  )
}

export function defaultCollectionTab(_item: CollectionDisplayItem) {
  return undefined
}

export function canRunCollectionTransform(item: CollectionDisplayItem) {
  return !item.catalogOnly || item.collectionMetadata?.source_type === 'transform_group'
}

function collectionDisplayItemFromCatalog(
  collection: CollectionCatalogEntry,
): CollectionDisplayItem {
  return {
    name: collection.name,
    table_name: collection.source_name,
    kind: kindFromCollection(collection.grain, collection.source_type),
    description: collection.description ?? undefined,
    schema_fields: [],
    entity_count: undefined,
    can_enrich: false,
    enrichment_enabled: false,
    catalogOnly: true,
    displayName: collection.label || collection.name,
    collectionMetadata: collection,
  }
}

function kindFromCollection(
  grain: string,
  sourceType: CollectionSourceType,
): ReferenceInfo['kind'] {
  if (sourceType === 'transform_group') {
    return 'generic'
  }
  if (grain === 'hierarchy' || grain === 'taxon') {
    return 'hierarchical'
  }
  if (grain === 'site' || grain === 'spatial') {
    return 'spatial'
  }
  return 'generic'
}
