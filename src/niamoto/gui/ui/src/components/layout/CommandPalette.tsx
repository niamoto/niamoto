import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import {
  Upload,
  Settings,
  Download,
  Search,
  Eye,
  Wrench,
  FileText,
  Home,
  Sun,
  Moon,
  Globe,
  Layers
} from 'lucide-react'
import { useNavigationStore, navigationSections } from '@/stores/navigationStore'
import { useTheme } from '@/hooks/use-theme'

// Icon mapping
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  import: Upload,
  transform: Settings,
  export: Download,
  explorer: Search,
  preview: Eye,
  settings: Wrench,
  plugins: Layers,
  docs: FileText
}

export function CommandPalette() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { setTheme } = useTheme()
  const { commandPaletteOpen, setCommandPaletteOpen } = useNavigationStore()
  const [search, setSearch] = useState('')

  // Keyboard shortcut
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setCommandPaletteOpen(!commandPaletteOpen)
      }
    }

    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [commandPaletteOpen, setCommandPaletteOpen])

  const handleSelect = useCallback((value: string) => {
    const [action, ...params] = value.split(':')

    switch (action) {
      case 'navigate':
        navigate(params.join(':'))
        setCommandPaletteOpen(false)
        break
      case 'theme':
        setTheme(params[0] as 'light' | 'dark' | 'system')
        setCommandPaletteOpen(false)
        break
      case 'language':
        i18n.changeLanguage(params[0])
        setCommandPaletteOpen(false)
        break
      default:
        break
    }
  }, [navigate, setTheme, i18n, setCommandPaletteOpen])

  return (
    <CommandDialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <CommandInput
        placeholder={t('command.search', 'Type a command or search...')}
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>{t('command.no_results', 'No results found.')}</CommandEmpty>

        {/* Navigation */}
        <CommandGroup heading={t('command.navigation', 'Navigation')}>
          <CommandItem value="navigate:/" onSelect={handleSelect}>
            <Home className="mr-2 h-4 w-4" />
            <span>{t('command.home', 'Home')}</span>
          </CommandItem>
          {navigationSections.map((section) => (
            section.items.map((item) => {
              const ItemIcon = iconMap[item.id] || FileText
              return (
                <CommandItem
                  key={item.id}
                  value={`navigate:${item.path}`}
                  onSelect={handleSelect}
                >
                  <ItemIcon className="mr-2 h-4 w-4" />
                  <span>{t(`navigation.${item.id}`, item.label)}</span>
                  {item.badge && (
                    <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs">
                      {item.badge}
                    </span>
                  )}
                </CommandItem>
              )
            })
          ))}
        </CommandGroup>

        <CommandSeparator />

        {/* Actions */}
        <CommandGroup heading={t('command.actions', 'Actions')}>
          <CommandItem value="action:new-import" disabled>
            <Upload className="mr-2 h-4 w-4" />
            <span>{t('command.new_import', 'New Import')}</span>
          </CommandItem>
          <CommandItem value="action:new-transform" disabled>
            <Settings className="mr-2 h-4 w-4" />
            <span>{t('command.new_transform', 'New Transform')}</span>
          </CommandItem>
          <CommandItem value="action:export-site" disabled>
            <Download className="mr-2 h-4 w-4" />
            <span>{t('command.export_site', 'Export Site')}</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Preferences */}
        <CommandGroup heading={t('command.preferences', 'Preferences')}>
          <CommandItem value="theme:light" onSelect={handleSelect}>
            <Sun className="mr-2 h-4 w-4" />
            <span>{t('command.light_theme', 'Light Theme')}</span>
          </CommandItem>
          <CommandItem value="theme:dark" onSelect={handleSelect}>
            <Moon className="mr-2 h-4 w-4" />
            <span>{t('command.dark_theme', 'Dark Theme')}</span>
          </CommandItem>
          <CommandItem value="theme:system" onSelect={handleSelect}>
            <Settings className="mr-2 h-4 w-4" />
            <span>{t('command.system_theme', 'System Theme')}</span>
          </CommandItem>
          <CommandSeparator className="my-2" />
          <CommandItem value="language:en" onSelect={handleSelect}>
            <Globe className="mr-2 h-4 w-4" />
            <span>English</span>
          </CommandItem>
          <CommandItem value="language:fr" onSelect={handleSelect}>
            <Globe className="mr-2 h-4 w-4" />
            <span>Français</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
