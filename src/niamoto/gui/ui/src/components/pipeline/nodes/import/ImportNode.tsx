// React is imported globally from 'react'
import { type NodeProps } from 'reactflow'
import { BaseNode } from '../base/BaseNode'
import { Database, FileText, FileSpreadsheet, Map, Layers } from 'lucide-react'
import type { ImportNodeData } from '../../types'

const importIcons = {
  taxonomy: Database,
  occurrences: FileText,
  plots: FileSpreadsheet,
  shapes: Map,
  layers: Layers,
}

export function ImportNode(props: NodeProps<ImportNodeData>) {
  const Icon = importIcons[props.data.subType]

  return (
    <BaseNode {...props} icon={Icon} color="blue">
      <div className="text-xs text-muted-foreground mt-1">
        {props.data.config?.path && (
          <div>Path: {props.data.config.path.split('/').pop()}</div>
        )}
        {props.data.output?.format && (
          <div>Format: {props.data.output.format}</div>
        )}
      </div>
    </BaseNode>
  )
}
