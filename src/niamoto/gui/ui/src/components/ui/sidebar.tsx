import * as React from "react"
import { cn } from "@/lib/utils"

type SidebarProps = React.HTMLAttributes<HTMLDivElement>

export function Sidebar({ className, ...props }: SidebarProps) {
  return (
    <div
      className={cn(
        "flex h-full w-64 flex-col border-r bg-background",
        className
      )}
      {...props}
    />
  )
}

type SidebarHeaderProps = React.HTMLAttributes<HTMLDivElement>

export function SidebarHeader({ className, ...props }: SidebarHeaderProps) {
  return (
    <div
      className={cn("flex h-16 items-center border-b px-6", className)}
      {...props}
    />
  )
}

type SidebarContentProps = React.HTMLAttributes<HTMLDivElement>

export function SidebarContent({ className, ...props }: SidebarContentProps) {
  return (
    <div
      className={cn("flex-1 overflow-auto py-4", className)}
      {...props}
    />
  )
}

type SidebarNavProps = React.HTMLAttributes<HTMLElement>

export function SidebarNav({ className, ...props }: SidebarNavProps) {
  return (
    <nav
      className={cn("space-y-1 px-3", className)}
      {...props}
    />
  )
}

interface SidebarNavItemProps extends React.HTMLAttributes<HTMLDivElement> {
  active?: boolean
}

export function SidebarNavItem({
  className,
  active,
  ...props
}: SidebarNavItemProps) {
  return (
    <div
      className={cn(
        "flex cursor-pointer items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-secondary text-secondary-foreground"
          : "text-muted-foreground hover:bg-secondary/50 hover:text-secondary-foreground",
        className
      )}
      {...props}
    />
  )
}

type SidebarFooterProps = React.HTMLAttributes<HTMLDivElement>

export function SidebarFooter({ className, ...props }: SidebarFooterProps) {
  return (
    <div
      className={cn("border-t p-4", className)}
      {...props}
    />
  )
}
