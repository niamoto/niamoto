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
  SHELL_ACTION_IDS,
  useShellActionRunner,
} from '@/shared/shell/shellActions'
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
  const sidebarMode = useNavigationStore((state) => state.sidebarMode)
  const { isMac, isDesktop } = usePlatform()
  const { runShellAction } = useShellActionRunner()
  const commandShortcutLabel = isMac ? '⌘K' : 'Ctrl+K'

  return (
    <header
      data-tauri-drag-region={isDesktop && isMac ? true : undefined}
      className={cn(
        'flex items-center justify-between bg-transparent px-3',
        isDesktop && isMac ? 'h-[38px]' : 'h-10',
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
            onClick={() => void runShellAction(SHELL_ACTION_IDS.SHELL_TOGGLE_SIDEBAR)}
            className="no-drag lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void runShellAction(SHELL_ACTION_IDS.SHELL_TOGGLE_SIDEBAR)}
            className="no-drag hidden h-8 w-8 md:inline-flex text-foreground/70 hover:bg-background/75 hover:text-foreground"
            title={t('sidebar.toggle', 'Toggle sidebar')}
          >
            <PanelLeft className="h-5 w-5" />
          </Button>
        )}

        {/* Mobile search button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => void runShellAction(SHELL_ACTION_IDS.COMMAND_PALETTE_OPEN)}
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
          className="no-drag hidden h-8 justify-start gap-2 rounded-full border-border/70 bg-background/70 px-3 text-muted-foreground shadow-none md:inline-flex"
          onClick={() => void runShellAction(SHELL_ACTION_IDS.COMMAND_PALETTE_OPEN)}
        >
          <Command className="h-3.5 w-3.5" />
          <span className="hidden text-left lg:inline">
            {t('command.search', 'Command palette')}
          </span>
          <kbd className="pointer-events-none inline-flex h-5 select-none items-center rounded border border-border/80 bg-background/80 px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
            {commandShortcutLabel}
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
              <HelpCircle className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{t('help.title', 'Help')}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() => void runShellAction(SHELL_ACTION_IDS.HELP_DOCUMENTATION)}
            >
              <FileText className="mr-2 h-4 w-4" />
              {t('help.documentation', 'Documentation')}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => void runShellAction(SHELL_ACTION_IDS.HELP_SHORTCUTS)}
            >
              <Command className="mr-2 h-4 w-4" />
              {t('help.shortcuts', 'Keyboard shortcuts')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() => void runShellAction(SHELL_ACTION_IDS.HELP_ABOUT)}
            >
              {t('help.about', 'About Niamoto')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

      </div>
    </header>
  )
}
