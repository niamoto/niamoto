import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Command,
  FileText,
  HelpCircle,
  Menu,
  PanelLeft,
  Search,
  WifiOff,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useNavigationStore } from '@/stores/navigationStore'
import { useNetworkStatus } from '@/shared/hooks/useNetworkStatus'
import { usePlatform } from '@/shared/hooks/usePlatform'
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
  const { setCommandPaletteOpen, sidebarMode, setSidebarMode, toggleSidebar } = useNavigationStore()
  const { isOffline } = useNetworkStatus()
  const { isMac, isDesktop } = usePlatform()
  const navigate = useNavigate()

  return (
    <header
      data-tauri-drag-region={isDesktop && isMac ? true : undefined}
      className={cn(
        'flex h-12 items-center justify-between border-b bg-background px-4',
        className
      )}
    >
      {/* Left section */}
      <div className="flex items-center gap-2">
        {/* Mobile menu button (when sidebar is hidden via responsive) */}
        {sidebarMode === 'hidden' ? (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarMode('full')}
            className="no-drag lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="no-drag -ml-3.5 hidden md:inline-flex text-foreground/75 hover:bg-transparent hover:text-foreground/75 focus-visible:bg-transparent focus-visible:text-foreground/75 active:bg-transparent active:text-foreground/75"
            title={t('sidebar.toggle', 'Toggle sidebar')}
          >
            <PanelLeft className="h-5 w-5" />
          </Button>
        )}

        {/* Mobile search button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCommandPaletteOpen(true)}
          className="no-drag md:hidden"
        >
          <Search className="h-5 w-5" />
        </Button>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-2">
        {/* Command palette trigger */}
        <Button
          variant="outline"
          className="no-drag hidden w-64 justify-start text-muted-foreground md:flex"
          onClick={() => setCommandPaletteOpen(true)}
        >
          <Search className="mr-2 h-4 w-4" />
          <span className="flex-1 text-left">{t('search.placeholder', 'Search...')}</span>
          <kbd className="pointer-events-none ml-auto inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>

        {/* Offline indicator */}
        {isOffline && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="no-drag flex items-center gap-1.5 rounded-md bg-amber-100 px-2 py-1 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
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

        {/* Notifications */}
        <div className="no-drag">
          <NotificationDropdown />
        </div>

        {/* Help menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="no-drag">
              <HelpCircle className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{t('help.title', 'Help')}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => navigate('/help')}>
              <FileText className="mr-2 h-4 w-4" />
              {t('help.documentation', 'Documentation')}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setCommandPaletteOpen(true)}>
              <Command className="mr-2 h-4 w-4" />
              {t('help.shortcuts', 'Keyboard shortcuts')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => navigate('/tools/settings')}>
              {t('help.about', 'About Niamoto')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

      </div>
    </header>
  )
}
