import React from 'react'
import { type NodeProps } from 'reactflow'
import { BaseNode } from '../base/BaseNode'
import { Settings2, BarChart, Map, Calculator, TreePine, Layers, Filter } from 'lucide-react'
import type { TransformNodeData } from '../../types'

const pluginIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  field_aggregator: Layers,
  top_ranking: BarChart,
  geospatial_extractor: Map,
  statistical_summary: Calculator,
  nested_set: TreePine,
  filter_plugin: Filter,
  default: Settings2,
}

export function TransformNode(props: NodeProps<TransformNodeData>) {
  const Icon = pluginIcons[props.data.pluginId] || pluginIcons.default

  return (
    <BaseNode {...props} icon={Icon} color="primary">
      <div className="text-xs text-muted-foreground mt-1">
        {props.data.config?.widget && (
          <div className="font-medium text-primary">
            Widget: {props.data.config.widget.name}
          </div>
        )}
        {props.data.pluginType && (
          <div>Type: {props.data.pluginType}</div>
        )}
      </div>
    </BaseNode>
  )
}
