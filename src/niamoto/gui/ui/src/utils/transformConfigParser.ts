import type {
  TransformGroup,
  UIGroup,
  UISource,
  UIWidget
} from '@/types/transform'
import {
  GROUP_DISPLAY_NAMES,
  GROUP_DESCRIPTIONS,
  GROUP_ICONS
} from '@/types/transform'

/**
 * Parse transform.yml format to UI-friendly format
 */
export function parseTransformConfig(config: TransformGroup[] | null): UIGroup[] {
  if (!config || !Array.isArray(config)) {
    return []
  }

  return config.map((group, index) => ({
    id: `group-${group.group_by}-${index}`,
    name: group.group_by,
    displayName: GROUP_DISPLAY_NAMES[group.group_by] || group.group_by,
    description: GROUP_DESCRIPTIONS[group.group_by],
    icon: GROUP_ICONS[group.group_by] || 'custom',
    sources: parseSources(group.sources || []),
    widgets: parseWidgets(group.widgets_data || {}),
  }))
}

/**
 * Parse sources from YAML format to UI format
 */
function parseSources(sources: any[]): UISource[] {
  if (!Array.isArray(sources)) {
    return []
  }

  return sources.map((source, index) => {
    // Determine source type based on data field
    let type: 'table' | 'csv' | 'excel' = 'table'
    if (source.data?.endsWith('.csv')) {
      type = 'csv'
    } else if (source.data?.endsWith('.xlsx') || source.data?.endsWith('.xls')) {
      type = 'excel'
    }

    return {
      id: `source-${index}-${Date.now()}`,
      name: source.name || source.data || `Source ${index + 1}`,
      type,
      data: source.data,
      groupingField: source.grouping,
      relation: source.relation ? {
        plugin: source.relation.plugin,
        config: source.relation
      } : undefined
    }
  })
}

/**
 * Parse widgets_data to UI format
 */
function parseWidgets(widgetsData: Record<string, any>): UIWidget[] {
  return Object.entries(widgetsData).map(([name, widget]) => ({
    id: `widget-${name}-${Date.now()}`,
    name,
    plugin: widget.plugin || '',
    params: widget.params || {}
  }))
}

/**
 * Serialize UI format back to transform.yml format
 */
export function serializeTransformConfig(groups: UIGroup[]): TransformGroup[] {
  return groups.map(group => ({
    group_by: group.name,
    sources: serializeSources(group.sources),
    widgets_data: serializeWidgets(group.widgets)
  }))
}

/**
 * Serialize UI sources to YAML format
 */
function serializeSources(sources: UISource[]): any[] {
  return sources.map(source => {
    const result: any = {
      name: source.name,
      data: source.data || source.name,
      grouping: source.grouping || source.name
    }

    if (source.relation) {
      result.relation = {
        plugin: source.relation.plugin,
        ...(source.relation.key && { key: source.relation.key }),
        ...(source.relation.fields && { fields: source.relation.fields }),
        ...(source.relation.config && source.relation.config)
      }
    }

    return result
  })
}

/**
 * Serialize UI widgets to YAML format
 */
function serializeWidgets(widgets: UIWidget[]): Record<string, any> {
  const result: Record<string, any> = {}

  widgets.forEach(widget => {
    result[widget.name] = {
      plugin: widget.plugin,
      params: widget.params || {}
    }
  })

  return result
}

/**
 * Validate transform configuration
 */
export function validateTransformConfig(config: any): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!Array.isArray(config)) {
    errors.push('Configuration must be an array of transform groups')
    return { valid: false, errors }
  }

  config.forEach((group, index) => {
    if (!group.group_by) {
      errors.push(`Group ${index + 1}: Missing 'group_by' field`)
    }

    if (!group.sources || !Array.isArray(group.sources)) {
      errors.push(`Group ${index + 1}: 'sources' must be an array`)
    } else {
      group.sources.forEach((source: any, sourceIndex: number) => {
        if (!source.name) {
          errors.push(`Group ${index + 1}, Source ${sourceIndex + 1}: Missing 'name' field`)
        }
        if (!source.data) {
          errors.push(`Group ${index + 1}, Source ${sourceIndex + 1}: Missing 'data' field`)
        }
      })
    }

    if (!group.widgets_data || typeof group.widgets_data !== 'object') {
      errors.push(`Group ${index + 1}: 'widgets_data' must be an object`)
    }
  })

  return {
    valid: errors.length === 0,
    errors
  }
}
