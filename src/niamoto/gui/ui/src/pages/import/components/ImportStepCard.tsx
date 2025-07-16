import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CircularProgress } from '@/components/ui/circular-progress'
import { Check, AlertCircle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ImportStepProgress } from '../ImportProgressContext'
import type { ReactNode } from 'react'

interface ImportStepCardProps {
  title: string
  icon: ReactNode
  status?: ImportStepProgress
  children: ReactNode
  variant?: 'default' | 'success'
}

export function ImportStepCard({
  title,
  icon,
  status,
  children,
  variant = 'default'
}: ImportStepCardProps) {
  const isRunning = status?.status === 'running'
  const isCompleted = status?.status === 'completed'
  const isFailed = status?.status === 'failed'

  return (
    <Card className={cn(
      "relative overflow-hidden transition-all duration-300",
      isRunning && "ring-2 ring-primary ring-offset-2",
      isCompleted && "border-green-200 bg-green-50/50 dark:bg-green-900/10",
      isFailed && "border-red-200 bg-red-50/50 dark:bg-red-900/10",
      variant === 'success' && !status && "border-green-200 bg-green-50/50 dark:bg-green-900/10"
    )}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          {icon}
          {title}
          {status && isRunning && (
            <Loader2 className="w-4 h-4 animate-spin text-primary ml-1" />
          )}
          {status && isCompleted && (
            <Check className="w-4 h-4 text-green-600 ml-1" />
          )}
          {status && isFailed && (
            <AlertCircle className="w-4 h-4 text-red-600 ml-1" />
          )}
          {variant === 'success' && !status && (
            <Badge variant="secondary" className="ml-auto">Auto-extraite</Badge>
          )}
          {status?.count !== undefined && isCompleted && (
            <Badge variant="outline" className="ml-auto bg-green-100 text-green-700 border-green-300">
              {status.count.toLocaleString()}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {status?.status === 'running' && (
          <div className="absolute top-2 right-2">
            <CircularProgress
              indeterminate={true}
              size={36}
              className="text-primary"
            />
          </div>
        )}

        {status?.message && isRunning && (
          <div className="text-xs text-muted-foreground mb-2 italic">
            {status.message}
          </div>
        )}

        {status?.error && isFailed && (
          <div className="text-xs text-red-600 mb-2">
            {status.error}
          </div>
        )}

        <div className={cn(
          "transition-opacity duration-300",
          isRunning && "opacity-50"
        )}>
          {children}
        </div>
      </CardContent>

      {/* Progress bar at bottom for running state */}
      {isRunning && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-muted">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${status.progress}%` }}
          />
        </div>
      )}
    </Card>
  )
}
