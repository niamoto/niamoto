import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
import { LanguageSwitcher } from '@/components/language-switcher'

const navigation = [
  { name: 'import' as const, href: '/import', icon: Upload },
  { name: 'transform' as const, href: '/transform', icon: Settings },
  { name: 'export' as const, href: '/export', icon: Download },
  { name: 'visualize' as const, href: '/visualize', icon: BarChart3 },
]

export function MainLayout() {
  const location = useLocation()
  const { t } = useTranslation()

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar>
        <SidebarHeader>
          <h1 className="text-lg font-bold text-primary">{t('app.title')}</h1>
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
                  {t(`navigation.${item.name}` as const)}
                </SidebarNavItem>
              </NavLink>
            ))}
          </SidebarNav>
        </SidebarContent>
        <SidebarFooter>
          <div className="mb-3">
            <LanguageSwitcher />
          </div>
          <div className="text-xs text-muted-foreground">
            {t('app.description')}
          </div>
        </SidebarFooter>
      </Sidebar>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
