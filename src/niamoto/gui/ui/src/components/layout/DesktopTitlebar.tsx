import { useState, useEffect } from 'react'
import { Minus, Square, X, Maximize2, Minimize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePlatform } from '@/hooks/usePlatform'
import { useRuntimeMode } from '@/hooks/useRuntimeMode'

interface DesktopTitlebarProps {
  title?: string
  className?: string
}

/**
 * Custom titlebar for Tauri desktop application
 * Provides native-looking window controls for macOS and Windows
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

  // macOS style controls (traffic lights) - minimal, no title, no border
  if (isMac) {
    return (
      <div
        className={cn(
          'flex h-10 items-center select-none cursor-default shrink-0',
          className
        )}
        onMouseDown={handleMouseDown}
      >
        {/* Traffic lights */}
        <div className="flex items-center gap-2 pl-4 no-drag">
          <button
            onClick={closeWindow}
            className="group flex h-3 w-3 items-center justify-center rounded-full bg-[#ff5f57] hover:bg-[#ff5f57]/80 transition-colors"
            aria-label="Close"
          >
            <X className="h-2 w-2 text-[#4d0000] opacity-0 group-hover:opacity-100" strokeWidth={3} />
          </button>
          <button
            onClick={minimizeWindow}
            className="group flex h-3 w-3 items-center justify-center rounded-full bg-[#febc2e] hover:bg-[#febc2e]/80 transition-colors"
            aria-label="Minimize"
          >
            <Minus className="h-2 w-2 text-[#995700] opacity-0 group-hover:opacity-100" strokeWidth={3} />
          </button>
          <button
            onClick={toggleMaximize}
            className="group flex h-3 w-3 items-center justify-center rounded-full bg-[#28c840] hover:bg-[#28c840]/80 transition-colors"
            aria-label="Maximize"
          >
            {isMaximized ? (
              <Minimize2 className="h-1.5 w-1.5 text-[#006500] opacity-0 group-hover:opacity-100" strokeWidth={3} />
            ) : (
              <Maximize2 className="h-1.5 w-1.5 text-[#006500] opacity-0 group-hover:opacity-100" strokeWidth={3} />
            )}
          </button>
        </div>
        {/* Flexible drag area */}
        <div className="flex-1 h-full" />
      </div>
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

  // Linux/Generic style - similar to Windows
  return (
    <div
      className={cn(
        'flex h-8 items-center justify-between bg-background border-b select-none cursor-default',
        className
      )}
      onMouseDown={handleMouseDown}
    >
      {/* Title - left side */}
      <div className="flex items-center gap-2 pl-3">
        <span className="text-xs font-medium text-foreground">{title}</span>
      </div>

      {/* Window controls - right side */}
      <div className="flex items-center no-drag">
        <button
          onClick={minimizeWindow}
          className="flex h-8 w-10 items-center justify-center text-muted-foreground hover:bg-muted/50 transition-colors"
          aria-label="Minimize"
        >
          <Minus className="h-4 w-4" />
        </button>
        <button
          onClick={toggleMaximize}
          className="flex h-8 w-10 items-center justify-center text-muted-foreground hover:bg-muted/50 transition-colors"
          aria-label="Maximize"
        >
          {isMaximized ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </button>
        <button
          onClick={closeWindow}
          className="flex h-8 w-10 items-center justify-center text-muted-foreground hover:bg-destructive hover:text-destructive-foreground transition-colors"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
