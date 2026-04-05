import type { LucideIcon } from 'lucide-react'
import { ChevronRight } from 'lucide-react'
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
  typeLabel: string
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
  typeLabel,
  metrics,
  statusBadge,
  actions,
  onNameClick,
}: SourceRowProps) {
  const [primaryAction, ...secondaryActions] = actions
  const PrimaryActionIcon = primaryAction?.icon

  return (
    <div className="rounded-lg border border-border/60 px-4 py-3">
      <div className="flex items-center gap-4">
        {/* Identity: icon + name + meta */}
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            {onNameClick ? (
              <button
                type="button"
                className="truncate rounded-sm text-left font-semibold hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
                onClick={onNameClick}
              >
                {name}
              </button>
            ) : (
              <div className="truncate font-semibold">{name}</div>
            )}
            <div className="text-xs text-muted-foreground">
              {typeLabel} • {metrics}
            </div>
          </div>
        </div>

        {/* Status badge */}
        {statusBadge ? (
          <Badge variant={statusBadge.variant} className="shrink-0">
            {statusBadge.label}
          </Badge>
        ) : null}

        {/* Actions: always aligned right, single row */}
        <div className="flex shrink-0 items-center gap-1">
          {secondaryActions.map((action, index) => {
            const ActionIcon = action.icon
            return (
              <Button
                key={action.id ?? `${action.label}-${index}`}
                type="button"
                variant={action.variant ?? 'ghost'}
                size="sm"
                className="h-auto px-2 py-1 text-foreground/70"
                onClick={action.onClick}
              >
                {ActionIcon ? <ActionIcon className="mr-1.5 h-3.5 w-3.5" /> : null}
                {action.label}
              </Button>
            )
          })}
          {primaryAction ? (
            primaryAction.label ? (
              <Button
                key={primaryAction.id ?? `${primaryAction.label}-primary`}
                type="button"
                variant={primaryAction.variant ?? 'default'}
                size="sm"
                onClick={primaryAction.onClick}
              >
                {PrimaryActionIcon ? <PrimaryActionIcon className="mr-1.5 h-3.5 w-3.5" /> : null}
                {primaryAction.label}
              </Button>
            ) : (
              <button
                type="button"
                className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                onClick={primaryAction.onClick}
              >
                {PrimaryActionIcon ? <PrimaryActionIcon className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
              </button>
            )
          ) : null}
        </div>
      </div>
    </div>
  )
}
