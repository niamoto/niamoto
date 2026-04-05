/**
 * ModuleLayout - Reusable sidebar + content layout for modules
 *
 * Follows the same pattern as SiteBuilder:
 * - Left panel: Module-specific tree/sidebar navigation
 * - Right panel: Contextual content based on selection
 *
 * Used by: Data, Groups, Publish modules
 */

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
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        <ResizablePanel
          id="module-sidebar"
          order={0}
          defaultSize={sidebarDefaultSize}
          minSize={sidebarMinSize}
          maxSize={sidebarMaxSize}
        >
          <ScrollArea className="h-full">
            {sidebar}
          </ScrollArea>
        </ResizablePanel>

        <ResizableHandle withHandle />

        <ResizablePanel
          id="module-content"
          order={1}
          defaultSize={100 - sidebarDefaultSize}
          minSize={30}
          className="min-w-0 overflow-hidden"
        >
          {children}
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
