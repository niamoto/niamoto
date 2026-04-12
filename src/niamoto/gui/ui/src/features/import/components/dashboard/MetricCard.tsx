import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { ArrowRight } from 'lucide-react'

type MetricCardVariant = 'default' | 'success' | 'warning'

interface MetricCardProps {
  value: number | string
  label: string
  sublabel?: string
  onClick?: () => void
  variant?: MetricCardVariant
  actionLabel?: string
  ariaLabel?: string
}

function variantClassName(variant: MetricCardVariant) {
  switch (variant) {
    case 'success':
      return 'border-green-200 bg-green-50/40'
    case 'warning':
      return 'border-amber-200 bg-amber-50/40'
    default:
      return 'border-border/70 bg-muted/30'
  }
}

export function MetricCard({
  value,
  label,
  sublabel,
  onClick,
  variant = 'default',
  actionLabel,
  ariaLabel,
}: MetricCardProps) {
  const isInteractive = typeof onClick === 'function'

  return (
    <Card
      className={cn(
        'transition-colors',
        variantClassName(variant),
        isInteractive && 'cursor-pointer hover:bg-muted/50 focus-within:ring-2 focus-within:ring-primary/20'
      )}
    >
      <CardContent className="p-4">
        <button
          type="button"
          className={cn(
            'flex w-full flex-col items-start gap-1 rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20',
            !isInteractive && 'cursor-default'
          )}
          aria-label={ariaLabel ?? `${label}: ${value}`}
          onClick={onClick}
          disabled={!isInteractive}
        >
          <div className="text-2xl font-semibold leading-none tracking-tight">{value}</div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </div>
          {sublabel ? (
            <div className="text-[13px] text-muted-foreground">{sublabel}</div>
          ) : null}
          {isInteractive && actionLabel ? (
            <div className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-primary">
              <span>{actionLabel}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          ) : null}
        </button>
      </CardContent>
    </Card>
  )
}
