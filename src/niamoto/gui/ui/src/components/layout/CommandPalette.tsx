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
  Database,
  Layers,
  Globe,
  Rocket,
  Upload,
  Settings,
  Sun,
  Moon,
  Search,
  Eye,
  FileText,
  Puzzle,
  BookOpen,
} from 'lucide-react'
import { useNavigationStore, navItems } from '@/stores/navigationStore'
import { useTheme } from '@/hooks/use-theme'

export function CommandPalette() {
  const { t, i18n } = useTranslation('common')
  const navigate = useNavigate()
  const { setTheme } = useTheme()
  const { commandPaletteOpen, setCommandPaletteOpen } = useNavigationStore()
  const [search, setSearch] = useState('')

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
      case 'preview':
        window.open('/preview', '_blank')
        setCommandPaletteOpen(false)
        break
      default:
        break
    }
  }, [navigate, setTheme, i18n, setCommandPaletteOpen])

  // Icon mapping for nav items
  const navIconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    data: Database,
    groups: Layers,
    site: Globe,
    publish: Rocket,
  }

  return (
    <CommandDialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <CommandInput
        placeholder={t('command.search', 'Rechercher une page ou un outil...')}
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>{t('command.no_results', 'Aucun résultat.')}</CommandEmpty>

        {/* Navigation */}
        <CommandGroup heading={t('command.navigation', 'Navigation')}>
          {navItems.map((item) => {
            const Icon = navIconMap[item.id] || Database
            return (
              <CommandItem
                key={item.id}
                value={`navigate:${item.path}`}
                keywords={[item.fallbackLabel, item.id]}
                onSelect={handleSelect}
              >
                <Icon className="mr-2 h-4 w-4" />
                <span>{t(item.labelKey, item.fallbackLabel)}</span>
              </CommandItem>
            )
          })}
          <CommandItem value="navigate:/sources/import" keywords={['import', 'importer', 'csv']} onSelect={handleSelect}>
            <Upload className="mr-2 h-4 w-4" />
            <span>Import</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Tools (formerly in sidebar TOOLS section) */}
        <CommandGroup heading={t('command.tools', 'Outils')}>
          <CommandItem value="navigate:/tools/explorer" keywords={['explorer', 'sql', 'requête', 'query', 'database']} onSelect={handleSelect}>
            <Search className="mr-2 h-4 w-4" />
            <span>Data Explorer</span>
          </CommandItem>
          <CommandItem value="navigate:/tools/config-editor" keywords={['config', 'yaml', 'configuration', 'import.yml', 'transform.yml', 'export.yml']} onSelect={handleSelect}>
            <FileText className="mr-2 h-4 w-4" />
            <span>Config Editor</span>
          </CommandItem>
          <CommandItem value="navigate:/tools/plugins" keywords={['plugins', 'extensions', 'transformers', 'exporters']} onSelect={handleSelect}>
            <Puzzle className="mr-2 h-4 w-4" />
            <span>Plugins</span>
          </CommandItem>
          <CommandItem value="navigate:/tools/docs" keywords={['docs', 'documentation', 'api', 'reference']} onSelect={handleSelect}>
            <BookOpen className="mr-2 h-4 w-4" />
            <span>Documentation API</span>
          </CommandItem>
          <CommandItem value="preview:" keywords={['preview', 'aperçu', 'site', 'visualiser']} onSelect={handleSelect}>
            <Eye className="mr-2 h-4 w-4" />
            <span>{t('sidebar.footer.previewSite', 'Aperçu du site')}</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Preferences */}
        <CommandGroup heading={t('command.preferences', 'Préférences')}>
          <CommandItem value="theme:light" onSelect={handleSelect}>
            <Sun className="mr-2 h-4 w-4" />
            <span>{t('command.light_theme', 'Thème clair')}</span>
          </CommandItem>
          <CommandItem value="theme:dark" onSelect={handleSelect}>
            <Moon className="mr-2 h-4 w-4" />
            <span>{t('command.dark_theme', 'Thème sombre')}</span>
          </CommandItem>
          <CommandItem value="theme:system" onSelect={handleSelect}>
            <Settings className="mr-2 h-4 w-4" />
            <span>{t('command.system_theme', 'Thème système')}</span>
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
