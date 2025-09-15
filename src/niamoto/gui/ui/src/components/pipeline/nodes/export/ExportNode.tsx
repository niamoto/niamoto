// React is imported globally from 'react'
import { type NodeProps } from 'reactflow'
import { BaseNode } from '../base/BaseNode'
import { FileCode, FileJson, FileText, Globe } from 'lucide-react'
import type { ExportNodeData } from '../../types'

const exportIcons = {
  html: Globe,
  json: FileJson,
  csv: FileText,
  geojson: FileCode,
}

export function ExportNode(props: NodeProps<ExportNodeData>) {
  const Icon = exportIcons[props.data.format]

  return (
    <BaseNode {...props} icon={Icon} color="green">
      <div className="text-xs text-muted-foreground mt-1">
        {props.data.format && (
          <div>Format: {props.data.format.toUpperCase()}</div>
        )}
        {props.data.widgets && props.data.widgets.length > 0 && (
          <div>Widgets: {props.data.widgets.length}</div>
        )}
      </div>
    </BaseNode>
  )
}
