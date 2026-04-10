import { cn } from '@/lib/utils'
import { usePlatform } from '@/shared/hooks/usePlatform'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'

interface DesktopTitlebarProps {
  title?: string
  className?: string
}

/**
 * Custom titlebar for Tauri desktop application.
 * macOS keeps a drag strip for overlay traffic lights, while Windows and Linux
 * use native window decorations to avoid duplicate chrome.
 */
export function DesktopTitlebar({ title = 'Niamoto', className }: DesktopTitlebarProps) {
  const { isMac, isDesktop } = usePlatform()
  const { isDesktop: isDesktopMode } = useRuntimeMode()

  // Don't render in web mode
  if (!isDesktop && !isDesktopMode) return null

  // Keep the custom drag strip only on macOS, where Tauri overlays the native
  // traffic lights inside the webview.
  if (isMac) {
    return (
      <div
        data-tauri-drag-region
        className={cn(
          'h-8 w-full select-none cursor-default shrink-0',
          className
        )}
      />
    )
  }

  // Windows and Linux keep native window manager chrome to avoid duplicate
  // titlebars and platform-specific inconsistencies.
  return null
}
