import type { LucideIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

type SourceRowBadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline'

interface SourceRowAction {
  id?: string
  label: string
  icon?: LucideIcon
  onClick: () => void
  variant?: 'default' | 'outline' | 'ghost'
}

interface SourceRowProps {
  icon: LucideIcon
  name: string
  typeBadge: string
  metrics: string
  statusBadge?: {
    label: string
    variant: SourceRowBadgeVariant
  }
  actions: SourceRowAction[]
  onNameClick?: () => void
}

export function SourceRow({
  icon: Icon,
  name,
  typeBadge,
  metrics,
  statusBadge,
  actions,
  onNameClick,
}: SourceRowProps) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          {onNameClick ? (
            <button
              type="button"
              className="truncate rounded-sm text-left font-medium hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
              onClick={onNameClick}
            >
              {name}
            </button>
          ) : (
            <div className="truncate font-medium">{name}</div>
          )}
          <Badge variant="outline">{typeBadge}</Badge>
          {statusBadge ? <Badge variant={statusBadge.variant}>{statusBadge.label}</Badge> : null}
        </div>
        <div className="mt-1 text-sm text-muted-foreground">{metrics}</div>
      </div>

      <div className="flex flex-wrap gap-2 lg:justify-end">
        {actions.map((action, index) => {
          const ActionIcon = action.icon
          return (
            <Button
              key={action.id ?? `${action.label}-${index}`}
              type="button"
              variant={action.variant ?? 'ghost'}
              size="sm"
              onClick={action.onClick}
            >
              {ActionIcon ? <ActionIcon className="mr-2 h-4 w-4" /> : null}
              {action.label}
            </Button>
          )
        })}
      </div>
    </div>
  )
}
