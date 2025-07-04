import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarNav,
  SidebarNavItem,
  SidebarFooter,
} from '@/components/ui/sidebar'
import { cn } from '@/lib/utils'
import { Upload, Settings, Download, BarChart3 } from 'lucide-react'

const navigation = [
  { name: 'Import', href: '/import', icon: Upload },
  { name: 'Transform', href: '/transform', icon: Settings },
  { name: 'Export', href: '/export', icon: Download },
  { name: 'Visualize', href: '/visualize', icon: BarChart3 },
]

export function MainLayout() {
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar>
        <SidebarHeader>
          <h1 className="text-lg font-bold text-primary">Niamoto</h1>
        </SidebarHeader>
        <SidebarContent>
          <SidebarNav>
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  cn(isActive && "pointer-events-none")
                }
              >
                <SidebarNavItem active={location.pathname === item.href}>
                  <item.icon className="mr-3 h-4 w-4" />
                  {item.name}
                </SidebarNavItem>
              </NavLink>
            ))}
          </SidebarNav>
        </SidebarContent>
        <SidebarFooter>
          <div className="text-xs text-muted-foreground">
            Ecological Data Pipeline
          </div>
        </SidebarFooter>
      </Sidebar>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
