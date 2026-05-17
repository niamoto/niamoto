export const CURRENT_COLLECTION_SOURCE = '__current_collection__'

export function buildDataSourceOptions(
  groupBy: string,
  sourceNames: string[],
  currentValue?: string,
  targetGroupNames: string[] = []
) {
  const values = new Set<string>()

  const addValue = (value?: string) => {
    const trimmed = value?.trim()
    if (trimmed) {
      values.add(trimmed)
    }
  }

  addValue(groupBy)
  sourceNames.forEach(addValue)
  targetGroupNames.forEach(addValue)
  addValue(currentValue)

  return Array.from(values).sort((left, right) => {
    if (left === groupBy) return -1
    if (right === groupBy) return 1
    return left.localeCompare(right)
  })
}
