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
    <div className="rounded-lg border border-border/60 px-4 py-4">
      <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[minmax(0,1fr)_auto_auto] lg:items-center lg:gap-6">
        <div className="min-w-0">
          <div className="flex min-w-0 items-start gap-3">
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
              <Icon className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0 space-y-1">
              {onNameClick ? (
                <button
                  type="button"
                  className="truncate rounded-sm text-left text-xl font-semibold hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
                  onClick={onNameClick}
                >
                  {name}
                </button>
              ) : (
                <div className="truncate text-xl font-semibold">{name}</div>
              )}
              <div className="text-sm text-muted-foreground">
                {typeLabel} • {metrics}
              </div>
            </div>
          </div>
        </div>

        {statusBadge ? (
          <div className="lg:justify-self-start">
            <Badge variant={statusBadge.variant}>{statusBadge.label}</Badge>
          </div>
        ) : (
          <div />
        )}

        <div className="flex flex-col items-start gap-2 lg:items-end">
          {primaryAction ? (
            <Button
              key={primaryAction.id ?? `${primaryAction.label}-primary`}
              type="button"
              variant={primaryAction.variant ?? 'default'}
              size="sm"
              onClick={primaryAction.onClick}
            >
              {PrimaryActionIcon ? <PrimaryActionIcon className="mr-2 h-4 w-4" /> : null}
              {primaryAction.label}
            </Button>
          ) : null}

          {secondaryActions.length > 0 ? (
            <div className="flex flex-wrap items-center gap-x-1 gap-y-1 lg:justify-end">
              {secondaryActions.map((action, index) => {
                const ActionIcon = action.icon
                return (
                  <Button
                    key={action.id ?? `${action.label}-${index}`}
                    type="button"
                    variant={action.variant ?? 'ghost'}
                    size="sm"
                    className="h-auto px-2 py-1 text-foreground/90"
                    onClick={action.onClick}
                  >
                    {ActionIcon ? <ActionIcon className="mr-2 h-4 w-4" /> : null}
                    {action.label}
                  </Button>
                )
              })}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
