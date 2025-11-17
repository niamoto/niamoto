import { useTranslation } from 'react-i18next'
import { Command, Search, Bell, User, HelpCircle, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useNavigationStore } from '@/stores/navigationStore'
import { LanguageSwitcher } from '@/components/language-switcher'
import { ProjectSwitcher } from '@/components/project-switcher'
import { useRuntimeMode } from '@/hooks/useRuntimeMode'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface TopBarProps {
  className?: string
}

export function TopBar({ className }: TopBarProps) {
  const { t } = useTranslation()
  const { setCommandPaletteOpen, sidebarMode, setSidebarMode } = useNavigationStore()
  const { features } = useRuntimeMode()

  return (
    <header
      className={cn(
        'flex h-14 items-center justify-between border-b bg-background px-4',
        className
      )}
    >
      {/* Left section */}
      <div className="flex items-center gap-4">
        {/* Mobile menu button */}
        {sidebarMode === 'hidden' && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarMode('full')}
            className="lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>
        )}

        {/* Command palette trigger */}
        <Button
          variant="outline"
          className="hidden w-64 justify-start text-muted-foreground md:flex"
          onClick={() => setCommandPaletteOpen(true)}
        >
          <Search className="mr-2 h-4 w-4" />
          <span className="flex-1 text-left">{t('search.placeholder', 'Search...')}</span>
          <kbd className="pointer-events-none ml-auto inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>

        {/* Mobile search button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCommandPaletteOpen(true)}
          className="md:hidden"
        >
          <Search className="h-5 w-5" />
        </Button>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-2">
        {/* Project switcher (desktop mode only) */}
        {features.project_switching && (
          <div className="hidden md:block">
            <ProjectSwitcher />
          </div>
        )}

        {/* Language switcher */}
        <div className="hidden md:block">
          <LanguageSwitcher />
        </div>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel>{t('notifications.title', 'Notifications')}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium">
                  {t('notifications.import_complete', 'Import completed')}
                </span>
                <span className="text-xs text-muted-foreground">
                  {t('notifications.time_ago', '2 minutes ago')}
                </span>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium">
                  {t('notifications.transform_ready', 'Transform ready')}
                </span>
                <span className="text-xs text-muted-foreground">
                  {t('notifications.time_ago', '1 hour ago')}
                </span>
              </div>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Help menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <HelpCircle className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{t('help.title', 'Help')}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <FileText className="mr-2 h-4 w-4" />
              {t('help.documentation', 'Documentation')}
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Command className="mr-2 h-4 w-4" />
              {t('help.shortcuts', 'Keyboard shortcuts')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              {t('help.about', 'About Niamoto')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <User className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{t('user.account', 'My Account')}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              {t('user.settings', 'Settings')}
            </DropdownMenuItem>
            <DropdownMenuItem className="md:hidden">
              <Globe className="mr-2 h-4 w-4" />
              {t('user.language', 'Language')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              {t('user.logout', 'Log out')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

// Import missing icons
import { FileText, Settings, Globe } from 'lucide-react'
