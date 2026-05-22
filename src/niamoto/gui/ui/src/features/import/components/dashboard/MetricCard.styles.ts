type MetricCardVariant = 'default' | 'success' | 'warning'

export function variantClassName(variant: MetricCardVariant) {
  switch (variant) {
    case 'success':
      return 'border-emerald-200/80 bg-emerald-50/70 dark:border-emerald-500/30 dark:bg-emerald-500/10'
    case 'warning':
      return 'border-amber-200/80 bg-amber-50/70 dark:border-amber-500/30 dark:bg-amber-500/10'
    default:
      return 'border-border/70 bg-muted/30'
  }
}

export function hoverClassName(variant: MetricCardVariant) {
  switch (variant) {
    case 'success':
      return 'hover:bg-emerald-100/80 dark:hover:bg-emerald-500/14'
    case 'warning':
      return 'hover:bg-amber-100/80 dark:hover:bg-amber-500/14'
    default:
      return 'hover:bg-muted/50'
  }
}

export type { MetricCardVariant }
