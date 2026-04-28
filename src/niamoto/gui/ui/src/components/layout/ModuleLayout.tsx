/**
 * ModuleLayout - Reusable sidebar + content layout for modules
 *
 * Follows the same pattern as SiteBuilder:
 * - Left panel: Module-specific tree/sidebar navigation
 * - Right panel: Contextual content based on selection
 *
 * Used by: Data, Groups, Publish modules
 */

import { useEffect, useRef } from 'react'
import type { PanelImperativeHandle } from 'react-resizable-panels'
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable'
import { ScrollArea } from '@/components/ui/scroll-area'

interface ModuleLayoutProps {
  sidebar: React.ReactNode
  children: React.ReactNode
  sidebarDefaultSize?: number
  sidebarMinSize?: number
  sidebarMaxSize?: number
}

export function ModuleLayout({
  sidebar,
  children,
  sidebarDefaultSize = 15,
  sidebarMinSize = 12,
  sidebarMaxSize = 25,
}: ModuleLayoutProps) {
  const groupRef = useRef<HTMLDivElement | null>(null)
  const sidebarPanelRef = useRef<PanelImperativeHandle | null>(null)
  const sidebarContentRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const groupElement = groupRef.current
    const panel = sidebarPanelRef.current
    const contentElement = sidebarContentRef.current

    if (!groupElement || !panel || !contentElement) {
      return
    }

    const deadline = window.setTimeout(() => {
      resizeObserver.disconnect()
    }, 1500)

    const measureAndResize = () => {
      const groupWidth = groupElement.clientWidth
      if (groupWidth === 0) return

      const contentWidth = contentElement.scrollWidth
      const visibleWidth = contentElement.clientWidth
      const overflowWidth = contentWidth - visibleWidth

      // Only auto-grow when the sidebar actually clips its content.
      // Using descendant scrollWidth causes a feedback loop with w-full items.
      if (contentWidth === 0 || overflowWidth <= 8) return

      const targetSize = Math.min(
        sidebarMaxSize,
        Math.max(
          sidebarMinSize,
          ((contentWidth + 24) / groupWidth) * 100
        )
      )

      const currentSize = panel.getSize().asPercentage
      if (targetSize > currentSize + 1) {
        panel.resize(`${targetSize}%`)
      }
    }

    const scheduleMeasurement = () => {
      window.requestAnimationFrame(measureAndResize)
    }

    const resizeObserver = new ResizeObserver(scheduleMeasurement)
    resizeObserver.observe(groupElement)
    resizeObserver.observe(contentElement)

    scheduleMeasurement()

    return () => {
      window.clearTimeout(deadline)
      resizeObserver.disconnect()
    }
  }, [sidebar, sidebarMinSize, sidebarMaxSize])

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <ResizablePanelGroup
        direction="horizontal"
        className="min-h-0 flex-1 overflow-hidden"
        elementRef={groupRef}
      >
        <ResizablePanel
          panelRef={sidebarPanelRef}
          id="module-sidebar"
          defaultSize={`${sidebarDefaultSize}%`}
          minSize={`${sidebarMinSize}%`}
          maxSize={`${sidebarMaxSize}%`}
        >
          <ScrollArea className="h-full">
            <div ref={sidebarContentRef} className="h-full">
              {sidebar}
            </div>
          </ScrollArea>
        </ResizablePanel>

        <ResizableHandle withHandle />

        <ResizablePanel
          id="module-content"
          defaultSize={`${100 - sidebarDefaultSize}%`}
          minSize="30%"
          className="min-w-0 overflow-hidden"
        >
          {children}
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
