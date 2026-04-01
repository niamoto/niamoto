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
// UNFLATTEN: flat array → tree (rebuild from parentId relationships)
// =============================================================================

export function buildTreeFromFlat(flatItems: FlatItem[]): UnifiedTreeItem[] {
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
 *
 * @param flatItems - The current flattened tree
 * @param activeId - The item being dragged
 * @param overId - The item being dragged over
 * @param offsetLeft - Horizontal pixel offset from drag start
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

  const overItem = flatItems[overIndex]

  // Calculate projected depth from horizontal offset
  const depthFromOffset = Math.round(offsetLeft / INDENTATION_WIDTH)
  const projectedDepth = Math.max(0, Math.min(depthFromOffset + overItem.depth, MAX_DEPTH))

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
// APPLY MOVE: reorder the flat array after a drag
// =============================================================================

/**
 * Move an item in the flat array, then rebuild the tree.
 *
 * @param tree - Current tree
 * @param activeId - Item being dragged
 * @param overId - Item being dragged over
 * @param projection - Target depth and parent
 */
export function applyDragMove(
  tree: UnifiedTreeItem[],
  activeId: string,
  overId: string,
  projection: Projection,
): UnifiedTreeItem[] {
  // Remove the dragged item from the tree
  const draggedItem = findItemInTree(tree, activeId)
  if (!draggedItem) return tree

  const treeWithoutDragged = removeFromTree(tree, activeId)

  // Insert at the new position
  if (projection.parentId) {
    // Insert as child of parent
    return insertAsChild(treeWithoutDragged, projection.parentId, draggedItem, overId)
  } else {
    // Insert at root level
    return insertAtRoot(treeWithoutDragged, draggedItem, overId)
  }
}

// Helpers

function findItemInTree(items: UnifiedTreeItem[], id: string): UnifiedTreeItem | null {
  for (const item of items) {
    if (item.id === id) return { ...item, children: [...item.children] }
    const found = findItemInTree(item.children, id)
    if (found) return found
  }
  return null
}

function removeFromTree(items: UnifiedTreeItem[], id: string): UnifiedTreeItem[] {
  return items
    .filter(item => item.id !== id)
    .map(item => ({
      ...item,
      children: removeFromTree(item.children, id),
    }))
}

function insertAtRoot(tree: UnifiedTreeItem[], item: UnifiedTreeItem, overId: string): UnifiedTreeItem[] {
  const overIndex = tree.findIndex(i => i.id === overId)
  if (overIndex === -1) {
    return [...tree, { ...item, children: [] }]
  }
  const result = [...tree]
  result.splice(overIndex + 1, 0, { ...item, children: [] })
  return result
}

function insertAsChild(tree: UnifiedTreeItem[], parentId: string, item: UnifiedTreeItem, overId: string): UnifiedTreeItem[] {
  return tree.map(treeItem => {
    if (treeItem.id === parentId) {
      const children = [...treeItem.children]
      const overIndex = children.findIndex(c => c.id === overId)
      if (overIndex === -1) {
        children.push({ ...item, children: [] })
      } else {
        children.splice(overIndex + 1, 0, { ...item, children: [] })
      }
      return { ...treeItem, children }
    }
    return {
      ...treeItem,
      children: insertAsChild(treeItem.children, parentId, item, overId),
    }
  })
}
