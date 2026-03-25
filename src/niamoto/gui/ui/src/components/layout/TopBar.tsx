import { useTranslation } from 'react-i18next'
import { Command, Search, User, HelpCircle, Menu, WifiOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useNavigationStore } from '@/stores/navigationStore'
import { LanguageSwitcher, ProjectSwitcher } from '@/components/common'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { useNetworkStatus } from '@/shared/hooks/useNetworkStatus'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { NotificationDropdown } from './NotificationDropdown'

interface TopBarProps {
  className?: string
}

export function TopBar({ className }: TopBarProps) {
  const { t } = useTranslation()
  const { setCommandPaletteOpen, sidebarMode, setSidebarMode } = useNavigationStore()
  const { features } = useRuntimeMode()
  const { isOffline } = useNetworkStatus()

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
        {/* Offline indicator */}
        {isOffline && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5 rounded-md bg-amber-100 px-2 py-1 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                <WifiOff className="h-4 w-4" />
                <span className="hidden text-xs font-medium sm:inline">
                  {t('network.offline', 'Offline')}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-64">
              <div className="space-y-1">
                <p className="font-medium">{t('network.offline_title', 'Offline mode')}</p>
                <ul className="list-inside list-disc text-xs opacity-80">
                  <li>{t('network.enrichment_unavailable', 'API enrichment: unavailable')}</li>
                  <li>{t('network.deploy_unavailable', 'Deployment: unavailable')}</li>
                  <li>{t('network.tiles_unavailable', 'Map tiles: unavailable')}</li>
                </ul>
              </div>
            </TooltipContent>
          </Tooltip>
        )}

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
        <NotificationDropdown />

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
