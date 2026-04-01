/**
 * treeDnd - Flattened tree utilities for drag-and-drop with nesting
 *
 * Provides flatten/unflatten + getProjection to determine drop depth
 * from horizontal mouse offset. Max depth = 1 (one level of submenus).
 */

import type { UnifiedTreeItem } from '../hooks/useUnifiedSiteTree'

export const INDENTATION_WIDTH = 24
export const MAX_DEPTH = 1

// =============================================================================
// FLAT ITEM
// =============================================================================

export interface FlatItem {
  item: UnifiedTreeItem
  parentId: string | null
  depth: number
  index: number
}

// =============================================================================
// FLATTEN: tree → flat array
// =============================================================================

export function flattenTree(
  items: UnifiedTreeItem[],
  parentId: string | null = null,
  depth: number = 0,
): FlatItem[] {
  const result: FlatItem[] = []
  let index = 0

  for (const item of items) {
    result.push({ item, parentId, depth, index: index++ })
    if (item.children.length > 0) {
      result.push(...flattenTree(item.children, item.id, depth + 1))
    }
  }

  return result
}

// =============================================================================
// PROJECTION: determine target depth + parent from drag position
// =============================================================================

export interface Projection {
  depth: number
  parentId: string | null
  overId: string
}

/**
 * Calculate where an item should be placed based on horizontal offset.
 */
export function getProjection(
  flatItems: FlatItem[],
  activeId: string,
  overId: string,
  offsetLeft: number,
): Projection {
  const overIndex = flatItems.findIndex(f => f.item.id === overId)
  if (overIndex === -1) {
    return { depth: 0, parentId: null, overId }
  }

  const activeFlat = flatItems.find(f => f.item.id === activeId)
  const overItem = flatItems[overIndex]

  // Items with children cannot be nested (would violate MAX_DEPTH=1)
  const activeHasChildren = activeFlat ? activeFlat.item.children.length > 0 : false
  const maxAllowedDepth = activeHasChildren ? 0 : MAX_DEPTH

  // Calculate projected depth from horizontal offset
  const depthFromOffset = Math.round(offsetLeft / INDENTATION_WIDTH)
  const projectedDepth = Math.max(0, Math.min(depthFromOffset + overItem.depth, maxAllowedDepth))

  // Determine parent based on projected depth
  let parentId: string | null = null

  if (projectedDepth > 0) {
    // Look backwards for a root-level item to be the parent
    for (let i = overIndex; i >= 0; i--) {
      const candidate = flatItems[i]
      if (candidate.item.id === activeId) continue
      if (candidate.depth === 0) {
        parentId = candidate.item.id
        break
      }
    }
  }

  return { depth: projectedDepth, parentId, overId }
}

// =============================================================================
// APPLY MOVE: reorder using the flat representation, then rebuild
// =============================================================================

/**
 * Move an item in the tree based on a DnD projection.
 *
 * Strategy: work on the flattened visible items to compute the new order,
 * then rebuild the tree and append hidden items unchanged.
 */
export function applyDragMove(
  tree: UnifiedTreeItem[],
  activeId: string,
  overId: string,
  projection: Projection,
): UnifiedTreeItem[] {
  // Separate visible (menu) and hidden items
  const visibleItems = tree.filter(i => i.visible)
  const hiddenItems = tree.filter(i => !i.visible)

  // Flatten visible items
  const flat = flattenTree(visibleItems)

  // Remove the active item from the flat list
  const activeIndex = flat.findIndex(f => f.item.id === activeId)
  if (activeIndex === -1) return tree
  const activeFlat = flat[activeIndex]
  const activeFlatItems = [activeFlat, ...flat.filter(f => f.parentId === activeId)]
  const flatWithout = flat.filter(f => f.item.id !== activeId && f.parentId !== activeId)

  // Find where to insert — direction determines before vs after
  const overIndex = flatWithout.findIndex(f => f.item.id === overId)
  if (overIndex === -1) return tree

  const overOriginalIndex = flat.findIndex(f => f.item.id === overId)
  const isDraggingDown = activeIndex < overOriginalIndex
  const insertIndex = isDraggingDown ? overIndex + 1 : overIndex

  // Rebuild: assign new parentId and depth based on projection
  const newFlat: FlatItem[] = [
    ...flatWithout.slice(0, insertIndex),
    {
      ...activeFlat,
      parentId: projection.parentId,
      depth: projection.depth,
    },
    // If the active item had children and is being moved to root, keep them
    ...(projection.depth === 0
      ? activeFlatItems.filter(f => f.item.id !== activeId).map(f => ({
          ...f,
          parentId: activeId,
          depth: 1,
        }))
      : [] // Nesting under parent: children dropped (MAX_DEPTH enforced)
    ),
    ...flatWithout.slice(insertIndex),
  ]

  // Rebuild tree from flat
  const newVisible = buildTreeFromFlat(newFlat)
  return [...newVisible, ...hiddenItems]
}

/**
 * Rebuild a tree from a flat array using parentId relationships.
 */
function buildTreeFromFlat(flatItems: FlatItem[]): UnifiedTreeItem[] {
  const itemMap = new Map<string, UnifiedTreeItem>()
  const roots: UnifiedTreeItem[] = []

  // First pass: create all items with empty children
  for (const flat of flatItems) {
    itemMap.set(flat.item.id, { ...flat.item, children: [] })
  }

  // Second pass: attach children to parents
  for (const flat of flatItems) {
    const item = itemMap.get(flat.item.id)!
    if (flat.parentId === null) {
      roots.push(item)
    } else {
      const parent = itemMap.get(flat.parentId)
      if (parent) {
        parent.children.push(item)
      } else {
        roots.push(item) // orphan fallback
      }
    }
  }

  return roots
}
