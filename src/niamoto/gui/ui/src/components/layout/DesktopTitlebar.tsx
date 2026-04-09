import { useState, useEffect } from 'react'
import { Minus, Square, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePlatform } from '@/shared/hooks/usePlatform'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'

interface DesktopTitlebarProps {
  title?: string
  className?: string
}

/**
 * Custom titlebar for Tauri desktop application.
 * macOS keeps a drag strip for overlay traffic lights, Windows uses custom
 * controls, and Linux falls back to native window decorations.
 */
export function DesktopTitlebar({ title = 'Niamoto', className }: DesktopTitlebarProps) {
  const { isMac, isWindows, isDesktop } = usePlatform()
  const { isDesktop: isDesktopMode } = useRuntimeMode()
  const [isMaximized, setIsMaximized] = useState(false)

  // Window control functions
  const minimizeWindow = async () => {
    if ('__TAURI__' in window) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window')
        const win = getCurrentWindow()
        await win.minimize()
      } catch (e) {
        console.error('Failed to minimize window:', e)
      }
    }
  }

  const toggleMaximize = async () => {
    if ('__TAURI__' in window) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window')
        const win = getCurrentWindow()
        if (isMaximized) {
          await win.unmaximize()
          setIsMaximized(false)
        } else {
          await win.maximize()
          setIsMaximized(true)
        }
      } catch (e) {
        console.error('Failed to toggle maximize:', e)
      }
    }
  }

  const closeWindow = async () => {
    if ('__TAURI__' in window) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window')
        const win = getCurrentWindow()
        await win.close()
      } catch (e) {
        console.error('Failed to close window:', e)
      }
    }
  }

  // Check maximized state on mount only (no listener to avoid Rust panics)
  useEffect(() => {
    if (!('__TAURI__' in window)) return

    const checkMaximized = async () => {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window')
        const win = getCurrentWindow()
        const maximized = await win.isMaximized()
        setIsMaximized(maximized)
      } catch (e) {
        console.error('Failed to check maximized state:', e)
      }
    }

    checkMaximized()
  }, [])

  // Handle window dragging (Tauri 2 requires explicit startDragging call)
  const handleMouseDown = async (e: React.MouseEvent) => {
    // Only drag if clicking directly on the titlebar, not on buttons
    if ((e.target as HTMLElement).closest('button')) return

    if ('__TAURI__' in window) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window')
        const win = getCurrentWindow()
        await win.startDragging()
      } catch (err) {
        console.error('Failed to start dragging:', err)
      }
    }
  }

  // Don't render in web mode
  if (!isDesktop && !isDesktopMode) return null

  // macOS avec titleBarStyle: "Overlay" - les traffic lights natifs sont affichés automatiquement
  // On fournit juste une zone de drag
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

  // Windows/Linux style controls
  if (isWindows) {
    return (
      <div
        className={cn(
          'flex h-8 items-center justify-between bg-background border-b select-none cursor-default',
          className
        )}
        onMouseDown={handleMouseDown}
      >
        {/* Title and icon - left side */}
        <div className="flex items-center gap-2 pl-3">
          <div className="flex h-4 w-4 items-center justify-center">
            <svg viewBox="0 0 24 24" className="h-4 w-4 text-primary" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
          </div>
          <span className="text-xs font-medium text-foreground">{title}</span>
        </div>

        {/* Window controls - right side */}
        <div className="flex items-center no-drag">
          <button
            onClick={minimizeWindow}
            className="flex h-8 w-11 items-center justify-center text-muted-foreground hover:bg-muted/50 transition-colors"
            aria-label="Minimize"
          >
            <Minus className="h-4 w-4" />
          </button>
          <button
            onClick={toggleMaximize}
            className="flex h-8 w-11 items-center justify-center text-muted-foreground hover:bg-muted/50 transition-colors"
            aria-label="Maximize"
          >
            {isMaximized ? (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <rect x="5" y="9" width="10" height="10" rx="1" />
                <path d="M9 9V6a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-3" />
              </svg>
            ) : (
              <Square className="h-3.5 w-3.5" />
            )}
          </button>
          <button
            onClick={closeWindow}
            className="flex h-8 w-11 items-center justify-center text-muted-foreground hover:bg-destructive hover:text-destructive-foreground transition-colors"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    )
  }

  // Linux keeps the native window manager titlebar to avoid duplicate chrome
  // and platform-specific inconsistencies across desktop environments.
  return null
}
