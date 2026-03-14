/**
 * WidgetMiniature - Miniature preview of a widget using PreviewTile
 *
 * Thin wrapper around PreviewTile that adds click handling and size variants.
 */
import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { PreviewTile } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'

interface WidgetMiniatureProps {
  templateId: string
  groupBy?: string  // Reference name for correct data filtering
  className?: string
  onClick?: () => void
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
}

const SIZES = {
  sm: { width: 90, height: 68 },
  md: { width: 120, height: 90 },
  lg: { width: 160, height: 120 },
}

export function WidgetMiniature({
  templateId,
  groupBy,
  className,
  onClick,
  size = 'md',
}: WidgetMiniatureProps) {
  const dimensions = SIZES[size]

  const descriptor: PreviewDescriptor = useMemo(() => ({
    templateId,
    groupBy,
    mode: 'thumbnail' as const,
  }), [templateId, groupBy])

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    onClick?.()
  }

  return (
    <div
      className={cn(
        'relative rounded-lg border overflow-hidden bg-muted/50',
        'cursor-pointer hover:border-primary hover:shadow-md transition-all',
        className
      )}
      style={{
        width: dimensions.width,
        height: dimensions.height,
      }}
      onClick={handleClick}
    >
      <PreviewTile
        descriptor={descriptor}
        width={dimensions.width}
        height={dimensions.height}
      />
    </div>
  )
}
