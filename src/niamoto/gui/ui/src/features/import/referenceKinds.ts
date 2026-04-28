export function hasHierarchyInspection(kind?: string) {
  return kind === 'hierarchical' || kind === 'nested'
}
