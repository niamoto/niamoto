import { useCallback, useDeferredValue, useMemo, useState } from 'react'
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
import { useThemeStore } from '@/stores/themeStore'
import { useFeedback, useBrowserOnline } from '@/features/feedback'
import { useHelpSearchIndex } from '@/features/help/hooks/useDocumentationContent'
import { rankHelpSearchEntries } from '@/features/help/routing'
import {
  isShellActionId,
  SHELL_ACTION_IDS,
  useShellActionRunner,
} from '@/shared/shell/shellActions'
import {
  applyUiLanguagePreference,
  getAppSettings,
  setAppSettings,
} from '@/shared/desktop/appSettings'
import { buildConfigEditorPath } from '@/features/tools/configRouting'

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
  const setThemeMode = useThemeStore((s) => s.setMode)
  const { commandPaletteOpen, setCommandPaletteOpen } = useNavigationStore()
  const feedback = useFeedback()
  const browserOnline = useBrowserOnline()
  const { runShellAction } = useShellActionRunner()
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)
  const currentLanguage = i18n.resolvedLanguage?.startsWith('fr') ? 'fr' : 'en'
  const helpSearchIndexQuery = useHelpSearchIndex(commandPaletteOpen)

  const documentationResults = useMemo(() => {
    if (!deferredSearch.trim() || !helpSearchIndexQuery.data) {
      return []
    }

    return rankHelpSearchEntries(helpSearchIndexQuery.data.entries, deferredSearch, 8)
  }, [deferredSearch, helpSearchIndexQuery.data])

  const handleSelect = useCallback((value: string) => {
    const [action, ...params] = value.split(':')

    switch (action) {
      case 'navigate':
        navigate(params.join(':'))
        setCommandPaletteOpen(false)
        break
      case 'theme':
        setThemeMode(params[0] as 'light' | 'dark' | 'system')
        setCommandPaletteOpen(false)
        break
      case 'language':
        void (async () => {
          const nextLanguage = params[0] === 'fr' ? 'fr' : 'en'
          const currentSettings = await getAppSettings()
          await setAppSettings({
            ...currentSettings,
            ui_language: nextLanguage,
          })
          await applyUiLanguagePreference(nextLanguage)
        })()
        setCommandPaletteOpen(false)
        break
      case 'shell': {
        const actionId = params.join(':')
        if (!isShellActionId(actionId)) {
          break
        }
        setCommandPaletteOpen(false)
        void runShellAction(actionId)
        break
      }
      case 'feedback':
        setCommandPaletteOpen(false)
        feedback.openWithType('bug')
        break
      default:
        break
    }
  }, [feedback, navigate, runShellAction, setCommandPaletteOpen, setThemeMode])

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
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading={t('command.workflows', 'Workflows')}>
          <CommandItem
            value="navigate:/sources/import"
            keywords={['import', 'importer', 'csv', 'upload', 'fichier', 'data']}
            onSelect={handleSelect}
          >
            <Upload className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.importData', 'Import data')}</span>
              <span className="text-xs text-muted-foreground">{t('command.importDesc', 'Add or update source files')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/groups"
            keywords={['collections', 'groups', 'widgets', 'transform', 'statistics']}
            onSelect={handleSelect}
          >
            <Layers className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.configureCollections', 'Configure collections')}</span>
              <span className="text-xs text-muted-foreground">{t('command.configureCollectionsDesc', 'Review widgets, sources, indexes and API exports')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/site/pages"
            keywords={['site', 'pages', 'content', 'markdown', 'builder']}
            onSelect={handleSelect}
          >
            <Globe className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.editSitePages', 'Edit site pages')}</span>
              <span className="text-xs text-muted-foreground">{t('command.editSitePagesDesc', 'Write content and adjust page configuration')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/publish"
            keywords={['publish', 'build', 'generate', 'export', 'site']}
            onSelect={handleSelect}
          >
            <Send className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.generateSite', 'Generate site')}</span>
              <span className="text-xs text-muted-foreground">{t('command.generateSiteDesc', 'Build the static website from current data')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/publish?panel=destinations"
            keywords={['deploy', 'publish', 'destination', 'github', 'netlify']}
            onSelect={handleSelect}
          >
            <Send className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.deploySite', 'Deploy site')}</span>
              <span className="text-xs text-muted-foreground">{t('command.deploySiteDesc', 'Open deployment destinations')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/publish?panel=history"
            keywords={['history', 'build history', 'deploy history', 'logs', 'jobs']}
            onSelect={handleSelect}
          >
            <Send className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.publishHistory', 'Publish history')}</span>
              <span className="text-xs text-muted-foreground">{t('command.publishHistoryDesc', 'Review recent builds and deployments')}</span>
            </div>
          </CommandItem>
          <CommandSeparator className="my-1" />
          <CommandItem
            value={`navigate:${buildConfigEditorPath('import')}`}
            keywords={['import.yml', 'import config', 'loader', 'config']}
            onSelect={handleSelect}
          >
            <FileCode2 className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.editImportConfig', 'Edit import.yml')}</span>
              <span className="text-xs text-muted-foreground">{t('command.editImportConfigDesc', 'Open the import configuration tab')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value={`navigate:${buildConfigEditorPath('transform')}`}
            keywords={['transform.yml', 'transform config', 'statistics', 'config']}
            onSelect={handleSelect}
          >
            <FileCode2 className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.editTransformConfig', 'Edit transform.yml')}</span>
              <span className="text-xs text-muted-foreground">{t('command.editTransformConfigDesc', 'Open the transform configuration tab')}</span>
            </div>
          </CommandItem>
          <CommandItem
            value={`navigate:${buildConfigEditorPath('export')}`}
            keywords={['export.yml', 'export config', 'publish', 'site config']}
            onSelect={handleSelect}
          >
            <FileCode2 className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.editExportConfig', 'Edit export.yml')}</span>
              <span className="text-xs text-muted-foreground">{t('command.editExportConfigDesc', 'Open the export configuration tab')}</span>
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
            value="feedback:open"
            keywords={['feedback', 'bug', 'report', 'suggestion', 'question', 'signaler', 'problème']}
            onSelect={handleSelect}
            disabled={!browserOnline || feedback.cooldownRemaining > 0}
          >
            <MessageSquarePlus className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('feedback:command_palette_label', 'Send feedback')}</span>
              <span className="text-xs text-muted-foreground">{t('feedback:type_bug', 'Bug')}, {t('feedback:type_suggestion', 'Suggestion')}, {t('feedback:type_question', 'Question')}</span>
            </div>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading={t('command.documentation', 'Documentation')}>
          <CommandItem
            value="navigate:/help"
            keywords={['documentation', 'guide', 'docs', 'manual', 'help']}
            onSelect={handleSelect}
          >
            <BookOpen className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.documentationHome', 'Documentation')}</span>
              <span className="text-xs text-muted-foreground">
                {t('command.documentationDesc', 'Guides, workflows, reference, troubleshooting')}
              </span>
            </div>
          </CommandItem>
          <CommandItem
            value="navigate:/tools/docs"
            keywords={['api', 'reference', 'endpoints', 'swagger', 'openapi']}
            onSelect={handleSelect}
          >
            <BookOpen className="!size-[18px] text-foreground/70" />
            <div className="flex flex-1 flex-col">
              <span className="font-medium">{t('command.apiDocs', 'API')}</span>
              <span className="text-xs text-muted-foreground">{t('command.docsDesc', 'Endpoints reference')}</span>
            </div>
          </CommandItem>

          {documentationResults.map((entry) => (
            <CommandItem
              key={entry.slug}
              value={`navigate:${entry.path}`}
              keywords={entry.keywords}
              onSelect={handleSelect}
            >
              <BookOpen className="!size-[18px] text-foreground/70" />
              <div className="flex flex-1 flex-col">
                <span className="font-medium">{entry.title}</span>
                <span className="text-xs text-muted-foreground">
                  {entry.section_title}
                  {entry.headings[0] ? ` · ${entry.headings[0]}` : ''}
                </span>
              </div>
            </CommandItem>
          ))}
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
            {currentLanguage === 'fr' && <CommandShortcut>actif</CommandShortcut>}
          </CommandItem>
          <CommandItem value="language:en" keywords={['english', 'anglais', 'langue']} onSelect={handleSelect}>
            <span className="flex !size-[18px] items-center justify-center text-xs font-bold text-foreground/70">EN</span>
            <span>English</span>
            {currentLanguage === 'en' && <CommandShortcut>active</CommandShortcut>}
          </CommandItem>
          <CommandSeparator className="my-1" />
          <CommandItem
            value={`shell:${SHELL_ACTION_IDS.SETTINGS_OPEN}`}
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
