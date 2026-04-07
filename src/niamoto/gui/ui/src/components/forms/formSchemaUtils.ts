import type { ColumnNode } from '@/lib/api/recipes'

interface FieldSchemaLike {
  json_schema_extra?: Record<string, unknown>
}

export function getUiSchemaValue<T = unknown>(
  fieldSchema: FieldSchemaLike,
  key: string
): T | undefined {
  const rawFieldSchema = fieldSchema as Record<string, unknown>
  return (fieldSchema.json_schema_extra?.[key] as T | undefined) ?? (rawFieldSchema[key] as T | undefined)
}

export function flattenColumnTree(columns: ColumnNode[]): string[] {
  const result: string[] = []

  const visit = (nodes: ColumnNode[]) => {
    nodes.forEach((node) => {
      result.push(node.path)
      if (node.children.length > 0) {
        visit(node.children)
      }
    })
  }

  visit(columns)
  return result
}

export function mergeOptionValue<T extends string>(
  options: T[],
  currentValue?: string | null
): string[] {
  if (!currentValue || options.includes(currentValue as T)) {
    return options
  }

  return [currentValue, ...options]
}

export function humanizeFieldName(fieldName: string): string {
  return fieldName
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function normalizeConditionExpression(condition: string): string {
  return condition.replace(
    /\b([A-Za-z_][A-Za-z0-9_]*)\s+in\s+\[([^\]]+)\]/g,
    '[$2].includes($1)'
  )
}

export function evaluateUiCondition(
  condition: string | undefined,
  context: Record<string, unknown>
): boolean {
  if (!condition) {
    return true
  }

  try {
    const normalized = normalizeConditionExpression(condition)
    const keys = Object.keys(context)
    const values = keys.map((key) => context[key])
    const evaluator = new Function(
      ...keys,
      `return Boolean(${normalized});`
    ) as (...args: unknown[]) => boolean
    return evaluator(...values)
  } catch {
    return true
  }
}
