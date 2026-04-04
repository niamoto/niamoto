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
  CommandShortcut,
} from '@/components/ui/command'
import {
  Home,
  Database,
  Layers,
  Globe,
  Send,
  Upload,
  Settings,
  Sun,
  Moon,
  Monitor,
  Search,
  FileCode2,
  Puzzle,
  BookOpen,
  MessageSquarePlus,
  ArrowUpDown,
  CornerDownLeft,
} from 'lucide-react'
import { useNavigationStore, navItems } from '@/stores/navigationStore'
import { useTheme } from '@/hooks/use-theme'
import { useFeedback, useBrowserOnline } from '@/features/feedback'

const navIconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  home: Home,
  data: Database,
  groups: Layers,
  site: Globe,
  publish: Send,
}

export function CommandPalette() {
  const { t, i18n } = useTranslation('common')
  const navigate = useNavigate()
  const { setTheme } = useTheme()
  const { commandPaletteOpen, setCommandPaletteOpen } = useNavigationStore()
  const feedback = useFeedback()
  const browserOnline = useBrowserOnline()
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
      case 'feedback':
        setCommandPaletteOpen(false)
        feedback.openWithType('bug')
        break
      default:
        break
    }
  }, [navigate, setTheme, i18n, setCommandPaletteOpen, feedback])

  return (
    <CommandDialog
      open={commandPaletteOpen}
      onOpenChange={setCommandPaletteOpen}
      showCloseButton={false}
      className="max-w-[540px]"
    >
      <CommandInput
        placeholder={t('command.search', 'Search for a page or tool...')}
        value={search}
        onValueChange={setSearch}
      />
      <CommandList className="max-h-[400px]">
        <CommandEmpty>
          <div className="flex flex-col items-center gap-2 py-4">
            <Search className="h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">{t('command.no_results', 'No results.')}</p>
          </div>
        </CommandEmpty>

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
                <Icon className="!size-[18px] text-foreground/70" />
                <span className="font-medium">{t(item.labelKey, item.fallbackLabel)}</span>
              </CommandItem>
            )
          })}
          <CommandItem
            value="navigate:/sources/import"
            keywords={['import', 'importer', 'csv', 'upload', 'fichier']}
            onSelect={handleSelect}
          >
            <Upload className="!size-[18px] text-foreground/70" />
            <div className="flex flex-col">
              <span className="font-medium">Import</span>
              <span className="text-xs text-muted-foreground">{t('command.importDesc', 'Import a data file')}</span>
            </div>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Tools */}
        <CommandGroup heading={t('command.tools', 'Outils')}>
          <CommandItem
            value="navigate:/tools/explorer"
            keywords={['explorer', 'sql', 'requête', 'query', 'database', 'table']}
            onSelect={handleSelect}
          >
            <Search className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">Data Explorer</span>
              <span className="text-xs text-muted-foreground">{t('command.explorerDesc', 'SQL queries on your data')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/tools/config-editor"
            keywords={['config', 'yaml', 'configuration', 'import.yml', 'transform.yml', 'export.yml']}
            onSelect={handleSelect}
          >
            <FileCode2 className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">Config Editor</span>
              <span className="text-xs text-muted-foreground">{t('command.configDesc', 'Edit YAML files')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/tools/plugins"
            keywords={['plugins', 'extensions', 'transformers', 'exporters', 'loaders']}
            onSelect={handleSelect}
          >
            <Puzzle className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">Plugins</span>
              <span className="text-xs text-muted-foreground">{t('command.pluginsDesc', 'Transformers, exporters, loaders')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/tools/docs"
            keywords={['docs', 'documentation', 'api', 'reference', 'endpoints']}
            onSelect={handleSelect}
          >
            <BookOpen className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">Documentation API</span>
              <span className="text-xs text-muted-foreground">{t('command.docsDesc', 'Endpoints reference')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="feedback:open"
            keywords={['feedback', 'bug', 'report', 'suggestion', 'question', 'signaler', 'problème']}
            onSelect={handleSelect}
            disabled={!browserOnline}
          >
            <MessageSquarePlus className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('feedback:command_palette_label', 'Send feedback')}</span>
              <span className="text-xs text-muted-foreground">{t('feedback:type_bug', 'Bug')}, {t('feedback:type_suggestion', 'Suggestion')}, {t('feedback:type_question', 'Question')}</span>
            </div>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Preferences */}
        <CommandGroup heading={t('command.preferences', 'Preferences')}>
          <CommandItem value="theme:light" keywords={['light', 'clair', 'thème']} onSelect={handleSelect}>
            <Sun className="!size-[18px] text-foreground/70" />
            <span>{t('command.light_theme', 'Light theme')}</span>
          </CommandItem>
          <CommandItem value="theme:dark" keywords={['dark', 'sombre', 'thème']} onSelect={handleSelect}>
            <Moon className="!size-[18px] text-foreground/70" />
            <span>{t('command.dark_theme', 'Dark theme')}</span>
          </CommandItem>
          <CommandItem value="theme:system" keywords={['system', 'système', 'auto', 'thème']} onSelect={handleSelect}>
            <Monitor className="!size-[18px] text-foreground/70" />
            <span>{t('command.system_theme', 'System theme')}</span>
          </CommandItem>
          <CommandSeparator className="my-1" />
          <CommandItem value="language:fr" keywords={['français', 'french', 'langue']} onSelect={handleSelect}>
            <span className="flex !size-[18px] items-center justify-center text-xs font-bold text-foreground/70">FR</span>
            <span>Français</span>
            {i18n.language === 'fr' && <CommandShortcut>actif</CommandShortcut>}
          </CommandItem>
          <CommandItem value="language:en" keywords={['english', 'anglais', 'langue']} onSelect={handleSelect}>
            <span className="flex !size-[18px] items-center justify-center text-xs font-bold text-foreground/70">EN</span>
            <span>English</span>
            {i18n.language === 'en' && <CommandShortcut>active</CommandShortcut>}
          </CommandItem>
          <CommandSeparator className="my-1" />
          <CommandItem
            value="navigate:/tools/settings"
            keywords={['settings', 'paramètres', 'configuration', 'preferences']}
            onSelect={handleSelect}
          >
            <Settings className="!size-[18px] text-foreground/70" />
            <span>{t('sidebar.footer.settings', 'Settings')}</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>

      {/* Footer with keyboard hints */}
      <div className="flex items-center gap-4 border-t px-3 py-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <ArrowUpDown className="h-3 w-3" />
          {t('command.navigate_hint', 'Naviguer')}
        </span>
        <span className="flex items-center gap-1">
          <CornerDownLeft className="h-3 w-3" />
          {t('command.select_hint', 'Select')}
        </span>
        <span className="ml-auto opacity-60">
          esc {t('command.close_hint', 'fermer')}
        </span>
      </div>
    </CommandDialog>
  )
}
