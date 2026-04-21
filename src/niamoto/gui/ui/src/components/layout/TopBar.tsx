import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Command,
  FileText,
  HelpCircle,
  Menu,
  PanelLeft,
  Search,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useNavigationStore } from '@/stores/navigationStore'
import { usePlatform } from '@/shared/hooks/usePlatform'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { NotificationDropdown } from './NotificationDropdown'

interface TopBarProps {
  className?: string
}

export function TopBar({ className }: TopBarProps) {
  const { t } = useTranslation()
  const { setCommandPaletteOpen, sidebarMode, setSidebarMode, toggleSidebar } = useNavigationStore()
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
