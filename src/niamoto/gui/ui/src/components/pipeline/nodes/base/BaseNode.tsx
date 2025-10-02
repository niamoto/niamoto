import React from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { CheckCircle2, XCircle, Loader2, Circle, Settings } from 'lucide-react'
import type { PipelineNodeData, NodeStatus } from '../../types'

interface BaseNodeProps extends NodeProps<PipelineNodeData> {
  icon?: React.ComponentType<{ className?: string }>
  color?: string
  children?: React.ReactNode
}

const statusIcons: Record<NodeStatus, React.ComponentType<{ className?: string }>> = {
  idle: Circle,
  configured: Settings,
  running: Loader2,
  success: CheckCircle2,
  error: XCircle,
}

const statusColors: Record<NodeStatus, string> = {
  idle: 'text-gray-400',
  configured: 'text-blue-500',
  running: 'text-yellow-500',
  success: 'text-green-500',
  error: 'text-red-500',
}

export function BaseNode({
  data,
  selected,
  icon: Icon,
  color = 'primary',
  children
}: BaseNodeProps) {
  const StatusIcon = statusIcons[data.status]
  const statusColor = statusColors[data.status]
  const isRunning = data.status === 'running'

  const nodeColorClasses = {
    primary: 'border-primary/20 bg-primary/5',
    blue: 'border-blue-500/20 bg-blue-50 dark:bg-blue-950/20',
    green: 'border-green-500/20 bg-green-50 dark:bg-green-950/20',
    orange: 'border-orange-500/20 bg-orange-50 dark:bg-orange-950/20',
  }

  return (
    <Card className={cn(
      'min-w-[200px] transition-all',
      nodeColorClasses[color as keyof typeof nodeColorClasses] || nodeColorClasses.primary,
      selected && 'ring-2 ring-primary shadow-lg',
      data.status === 'error' && 'border-red-500',
      data.status === 'success' && 'border-green-500',
      data.status === 'configured' && 'border-blue-500'
    )}>
      <div className="p-3">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {Icon && (
              <div className={cn('rounded p-1', `bg-${color}/10`)}>
                <Icon className={cn('h-4 w-4', `text-${color}`)} />
              </div>
            )}
            <div className="flex-1">
              <div className="font-medium text-sm">{data.label}</div>
              <Badge variant="outline" className="text-xs mt-0.5">
                {data.nodeType}
              </Badge>
            </div>
          </div>
          <StatusIcon className={cn(
            'h-4 w-4',
            statusColor,
            isRunning && 'animate-spin'
          )} />
        </div>

        {/* Custom content */}
        {children}

        {/* Progress bar for running state */}
        {isRunning && (
          <Progress className="mt-2 h-1" value={50} />
        )}

        {/* Input handles */}
        {data.nodeType !== 'import' && (
          <Handle
            type="target"
            position={Position.Left}
            className="!w-3 !h-3 !bg-primary !border-2 !border-background"
          />
        )}

        {/* Output handles */}
        {data.nodeType !== 'export' && (
          <Handle
            type="source"
            position={Position.Right}
            className="!w-3 !h-3 !bg-primary !border-2 !border-background"
          />
        )}
      </div>
    </Card>
  )
}
