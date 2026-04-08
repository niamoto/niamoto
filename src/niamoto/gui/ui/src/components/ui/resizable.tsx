import * as React from "react"
import { GripVerticalIcon } from "lucide-react"
import {
  Group as ResizableGroupPrimitive,
  Panel as ResizablePanelPrimitive,
  Separator as ResizableSeparatorPrimitive,
  type GroupProps as ResizableGroupProps,
  type PanelImperativeHandle,
  type PanelProps as ResizablePanelProps,
  type SeparatorProps as ResizableSeparatorProps,
} from "react-resizable-panels"

import { cn } from "@/lib/utils"

type ResizablePanelGroupProps = Omit<ResizableGroupProps, "orientation"> & {
  direction?: "horizontal" | "vertical"
}

function ResizablePanelGroup({
  className,
  direction = "horizontal",
  ...props
}: ResizablePanelGroupProps) {
  return (
    <ResizableGroupPrimitive
      data-slot="resizable-panel-group"
      data-panel-group-direction={direction}
      className={cn(
        "group flex h-full w-full data-[panel-group-direction=vertical]:flex-col",
        className
      )}
      orientation={direction}
      {...props}
    />
  )
}

const ResizablePanel = React.forwardRef<PanelImperativeHandle, ResizablePanelProps>(
  ({ ...props }, ref) => (
    <ResizablePanelPrimitive data-slot="resizable-panel" panelRef={ref} {...props} />
  )
)

ResizablePanel.displayName = "ResizablePanel"

function ResizableHandle({
  withHandle,
  className,
  ...props
}: ResizableSeparatorProps & {
  withHandle?: boolean
}) {
  return (
    <ResizableSeparatorPrimitive
      data-slot="resizable-handle"
      className={cn(
        "bg-border relative flex w-px items-center justify-center after:absolute after:inset-y-0 after:left-1/2 after:w-3 after:-translate-x-1/2 focus-visible:outline-hidden group-data-[panel-group-direction=vertical]:h-px group-data-[panel-group-direction=vertical]:w-full group-data-[panel-group-direction=vertical]:after:left-0 group-data-[panel-group-direction=vertical]:after:h-3 group-data-[panel-group-direction=vertical]:after:w-full group-data-[panel-group-direction=vertical]:after:translate-x-0 group-data-[panel-group-direction=vertical]:after:-translate-y-1/2 group-data-[panel-group-direction=vertical]:[&>div]:rotate-90",
        className
      )}
      {...props}
    >
      {withHandle && (
        <div className="bg-border pointer-events-none z-10 flex h-4 w-3 items-center justify-center rounded-xs border">
          <GripVerticalIcon className="size-2.5" />
        </div>
      )}
    </ResizableSeparatorPrimitive>
  )
}

export { ResizablePanelGroup, ResizablePanel, ResizableHandle }
