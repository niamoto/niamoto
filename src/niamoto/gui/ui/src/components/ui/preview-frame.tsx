/**
 * PreviewFrame - Reusable preview component for HTML content
 *
 * Features:
 * - Responsive device selection (mobile/tablet/desktop)
 * - Auto-scaling to fit container
 * - Refresh and close buttons
 * - Loading and empty states
 * - Link click interception
 */

import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Monitor,
  Tablet,
  Smartphone,
  Loader2,
  RotateCcw,
  PanelRightClose,
  Eye,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { cn } from '@/lib/utils'

export type DeviceSize = 'mobile' | 'tablet' | 'desktop'

// Device dimensions (real viewport sizes)
const DEVICE_DIMENSIONS = {
  mobile: { width: 375, height: 667 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1440, height: 900 },
}

export interface PreviewFrameProps {
  /** HTML content to display in the iframe */
  html: string | null
  /** Whether content is currently loading */
  isLoading?: boolean
  /** Current device size */
  device: DeviceSize
  /** Callback when device size changes */
  onDeviceChange: (device: DeviceSize) => void
  /** Callback to refresh the preview */
  onRefresh?: () => void
  /** Callback to close/hide the preview panel */
  onClose?: () => void
  /** Callback when a link is clicked in the preview */
  onLinkClick?: (href: string) => void
  /** Title for the preview (shown in header) */
  title?: string
  /** Message to show when no content is available */
  emptyMessage?: string
  /** Message to show while loading */
  loadingMessage?: string
  /** Additional class name for the container */
  className?: string
}

export function PreviewFrame({
  html,
  isLoading = false,
  device,
  onDeviceChange,
  onRefresh,
  onClose,
  onLinkClick,
  title,
  emptyMessage,
  loadingMessage,
  className,
}: PreviewFrameProps) {
  const { t } = useTranslation(['common', 'site'])
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  const currentDimensions = DEVICE_DIMENSIONS[device]

  // Calculate scale based on container size
  useEffect(() => {
    const updateScale = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth - 32 // padding
        const containerHeight = containerRef.current.clientHeight - 32
        const targetWidth = currentDimensions.width
        const targetHeight = currentDimensions.height

        // Scale to fit both width and height
        const scaleX = containerWidth / targetWidth
        const scaleY = containerHeight / targetHeight
        const newScale = Math.min(scaleX, scaleY, 1) // Don't scale up, only down

        setScale(newScale)
      }
    }

    updateScale()

    // Use ResizeObserver for panel resizing
    const resizeObserver = new ResizeObserver(updateScale)
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current)
    }

    return () => resizeObserver.disconnect()
  }, [device, currentDimensions.width, currentDimensions.height])

  // Listen for messages from iframe (link clicks)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Accepter uniquement les messages de notre origine ou des iframes srcDoc (origin null)
      if (event.origin !== window.location.origin && event.origin !== 'null') return
      if (event.data?.type === 'preview-link-click' && event.data?.href) {
        onLinkClick?.(event.data.href)
      }
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [onLinkClick])

  return (
    <div className={cn('flex h-full flex-col bg-muted/30', className)}>
      {/* Preview Header */}
      <div className="flex items-center justify-between border-b bg-background px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {title || t('common:actions.preview')}
          </span>
          <span className="text-xs text-muted-foreground">
            {currentDimensions.width}x{currentDimensions.height} ({Math.round(scale * 100)}%)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ToggleGroup
            type="single"
            value={device}
            onValueChange={(v) => v && onDeviceChange(v as DeviceSize)}
            size="sm"
          >
            <ToggleGroupItem value="mobile" aria-label="Mobile">
              <Smartphone className="h-4 w-4" />
            </ToggleGroupItem>
            <ToggleGroupItem value="tablet" aria-label="Tablet">
              <Tablet className="h-4 w-4" />
            </ToggleGroupItem>
            <ToggleGroupItem value="desktop" aria-label="Desktop">
              <Monitor className="h-4 w-4" />
            </ToggleGroupItem>
          </ToggleGroup>
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              title={t('common:actions.refresh')}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
            </Button>
          )}
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              title={t('common:actions.close')}
            >
              <PanelRightClose className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Preview Content */}
      <div
        ref={containerRef}
        className="flex-1 p-4 overflow-hidden flex items-center justify-center"
      >
        {isLoading ? (
          <div className="flex flex-col items-center justify-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              {loadingMessage || t('site:preview.generatingPreview')}
            </span>
          </div>
        ) : html ? (
          <div
            className="relative flex items-center justify-center"
            style={{
              width: currentDimensions.width * scale,
              height: currentDimensions.height * scale,
            }}
          >
            <div
              className="absolute rounded-lg border bg-white shadow-sm overflow-hidden"
              style={{
                width: currentDimensions.width,
                height: currentDimensions.height,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
                top: 0,
                left: 0,
              }}
            >
              <iframe
                srcDoc={html}
                className="w-full h-full border-0"
                title="Preview"
                sandbox="allow-scripts"
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Eye className="h-10 w-10 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">
              {emptyMessage || t('site:preview.noPreviewAvailable')}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export { DEVICE_DIMENSIONS }
