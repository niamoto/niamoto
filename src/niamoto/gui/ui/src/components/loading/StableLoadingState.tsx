import { Loader2 } from 'lucide-react'

import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface StablePageSkeletonProps {
  className?: string
  sections?: number
  header?: boolean
}

export function StablePageSkeleton({
  className,
  sections = 3,
  header = true,
}: StablePageSkeletonProps) {
  return (
    <div
      aria-busy="true"
      data-stable-loading="page"
      className={cn('h-full overflow-hidden p-4 sm:p-6', className)}
    >
      <div className="mx-auto flex h-full max-w-4xl flex-col gap-6">
        {header && (
          <div className="space-y-2">
            <Skeleton className="mx-auto h-7 w-56 max-w-full" />
            <Skeleton className="mx-auto h-4 w-full max-w-2xl" />
          </div>
        )}

        {Array.from({ length: sections }).map((_, index) => (
          <div
            key={index}
            className="rounded-lg border border-border/70 bg-background p-5 shadow-sm"
          >
            <div className="flex items-center gap-4">
              <Skeleton className="h-10 w-10 shrink-0 rounded-xl" />
              <div className="min-w-0 flex-1 space-y-2">
                <Skeleton className="h-5 w-44 max-w-full" />
                <Skeleton className="h-4 w-full max-w-xl" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

interface StablePanelSkeletonProps {
  className?: string
  rows?: number
}

export function StablePanelSkeleton({
  className,
  rows = 5,
}: StablePanelSkeletonProps) {
  return (
    <div
      aria-busy="true"
      data-stable-loading="panel"
      className={cn('h-full overflow-hidden p-4', className)}
    >
      <div className="space-y-4">
        <div className="space-y-2">
          <Skeleton className="h-6 w-52 max-w-full" />
          <Skeleton className="h-4 w-full max-w-lg" />
        </div>
        <div className="space-y-3">
          {Array.from({ length: rows }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      </div>
    </div>
  )
}

interface InlineRefreshIndicatorProps {
  active?: boolean
  label?: string
  className?: string
}

export function InlineRefreshIndicator({
  active = false,
  label = 'Actualisation',
  className,
}: InlineRefreshIndicatorProps) {
  if (!active) return null

  return (
    <div
      aria-live="polite"
      className={cn('flex items-center gap-2 text-xs text-muted-foreground', className)}
    >
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      <span>{label}</span>
    </div>
  )
}
