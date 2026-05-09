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

function parseConditionLiteral(value: string): unknown {
  const trimmed = value.trim()

  if (
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
    || (trimmed.startsWith('"') && trimmed.endsWith('"'))
  ) {
    return trimmed.slice(1, -1)
  }

  if (trimmed === 'true') return true
  if (trimmed === 'false') return false
  if (trimmed === 'null') return null

  const numberValue = Number(trimmed)
  return Number.isFinite(numberValue) ? numberValue : undefined
}

function parseConditionList(value: string): unknown[] {
  return value
    .split(',')
    .map(parseConditionLiteral)
    .filter((item) => item !== undefined)
}

function compareConditionValues(left: unknown, operator: string, right: unknown): boolean {
  switch (operator) {
    case '===':
      return left === right
    case '!==':
      return left !== right
    case '>':
      return Number(left) > Number(right)
    case '>=':
      return Number(left) >= Number(right)
    case '<':
      return Number(left) < Number(right)
    case '<=':
      return Number(left) <= Number(right)
    default:
      return true
  }
}

function stripOuterParentheses(expression: string): string {
  let result = expression.trim()
  while (result.startsWith('(') && result.endsWith(')')) {
    result = result.slice(1, -1).trim()
  }
  return result
}

function evaluateConditionAtom(
  expression: string,
  context: Record<string, unknown>
): boolean {
  const atom = stripOuterParentheses(expression)

  const negatedIdentifier = atom.match(/^!([A-Za-z_][A-Za-z0-9_]*)$/)
  if (negatedIdentifier) {
    return !context[negatedIdentifier[1]]
  }

  const identifier = atom.match(/^([A-Za-z_][A-Za-z0-9_]*)$/)
  if (identifier) {
    return Boolean(context[identifier[1]])
  }

  const membership = atom.match(/^([A-Za-z_][A-Za-z0-9_]*)\s+in\s+\[([^\]]*)\]$/)
  if (membership) {
    return parseConditionList(membership[2]).includes(context[membership[1]])
  }

  const objectKeysLength = atom.match(
    /^Object\.keys\(([A-Za-z_][A-Za-z0-9_]*)\)\.length\s*(===|!==|>=|<=|>|<)\s*(\d+)$/
  )
  if (objectKeysLength) {
    const value = context[objectKeysLength[1]]
    const keyCount = value && typeof value === 'object'
      ? Object.keys(value).length
      : 0
    return compareConditionValues(keyCount, objectKeysLength[2], Number(objectKeysLength[3]))
  }

  const comparison = atom.match(
    /^([A-Za-z_][A-Za-z0-9_]*)\s*(===|!==|>=|<=|>|<)\s*('.*'|".*"|true|false|null|-?\d+(?:\.\d+)?)$/
  )
  if (comparison) {
    return compareConditionValues(
      context[comparison[1]],
      comparison[2],
      parseConditionLiteral(comparison[3])
    )
  }

  return true
}

function evaluateConditionConjunction(
  expression: string,
  context: Record<string, unknown>
): boolean {
  return expression
    .split(/\s+&&\s+/)
    .every((atom) => evaluateConditionAtom(atom, context))
}

export function evaluateUiCondition(
  condition: string | undefined,
  context: Record<string, unknown>
): boolean {
  if (!condition) {
    return true
  }

  try {
    return condition
      .split(/\s+\|\|\s+/)
      .some((part) => evaluateConditionConjunction(part, context))
  } catch {
    return true
  }
}
