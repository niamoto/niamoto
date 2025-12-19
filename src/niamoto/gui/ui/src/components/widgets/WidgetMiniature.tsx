/**
 * WidgetMiniature - Miniature preview of a widget using lazy-loaded iframe
 *
 * Displays a scaled-down preview of the widget that loads only when visible.
 * Uses IntersectionObserver for performance optimization.
 */
import { useState, useRef, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface WidgetMiniatureProps {
  templateId: string
  groupBy?: string  // Reference name for correct data filtering
  className?: string
  onClick?: () => void
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
}

const SIZES = {
  sm: { width: 90, height: 68, scale: 0.225 },
  md: { width: 120, height: 90, scale: 0.3 },
  lg: { width: 160, height: 120, scale: 0.4 },
}

// Base iframe dimensions before scaling
const IFRAME_WIDTH = 400
const IFRAME_HEIGHT = 300

export function WidgetMiniature({
  templateId,
  groupBy,
  className,
  onClick,
  size = 'md',
}: WidgetMiniatureProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const [hasError, setHasError] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const dimensions = SIZES[size]

  // Lazy loading with IntersectionObserver
  useEffect(() => {
    const element = ref.current
    if (!element) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '100px' } // Pre-load when within 100px of viewport
    )

    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  // Reset loading state when templateId changes
  useEffect(() => {
    setIsLoaded(false)
    setHasError(false)
  }, [templateId])

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    onClick?.()
  }

  return (
    <div
      ref={ref}
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
      {/* Loading indicator */}
      {!isLoaded && !hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/80 z-10">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Error state */}
      {hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/80 z-10">
          <span className="text-[10px] text-muted-foreground">Erreur</span>
        </div>
      )}

      {/* Iframe - only render when visible */}
      {isVisible && (
        <iframe
          src={`/api/templates/preview/${templateId}${groupBy ? `?group_by=${encodeURIComponent(groupBy)}` : ''}`}
          className="pointer-events-none origin-top-left"
          style={{
            width: IFRAME_WIDTH,
            height: IFRAME_HEIGHT,
            transform: `scale(${dimensions.scale})`,
            border: 'none',
          }}
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
          title={`Preview ${templateId}`}
        />
      )}
    </div>
  )
}
