import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Copy, Languages, Loader2, Settings2 } from 'lucide-react'
import { useAppUpdater } from '@/shared/desktop/updater/useAppUpdater'
import {
  DEFAULT_APP_SETTINGS,
  applyUiLanguagePreference,
  getAppSettings,
  openDesktopDevtools,
  setAppSettings,
  type AppSettings,
} from '@/shared/desktop/appSettings'
import type { UiLanguage, UiLanguagePreference } from '@/i18n'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { usePlatform } from '@/shared/hooks/usePlatform'
import { AboutPanel } from '@/features/tools/components/AboutPanel'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ThemeSwitcher } from '@/components/theme'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'

const LANGUAGE_LABELS: Record<UiLanguage, string> = {
  fr: 'Français',
  en: 'English',
}

export function Settings() {
  const { t, i18n } = useTranslation('tools')
  const runtimeMode = useRuntimeMode()
  const { isDesktop, mode, project } = runtimeMode
  const { platform } = usePlatform()
  const {
    status,
    version: updateVersion,
    appVersion,
    manualUpdateUrl,
    checkForUpdate,
    installUpdate,
    restartApp,
  } = useAppUpdater()
  const [settings, setSettingsState] = useState<AppSettings>(DEFAULT_APP_SETTINGS)
  const [loading, setLoading] = useState(true)
  const [savingKey, setSavingKey] = useState<
    'ui_language' | 'auto_load_last_project' | 'debug_mode' | null
  >(null)
  const [openingDevtools, setOpeningDevtools] = useState(false)

  const debugShortcutLabel = useMemo(() => {
    if (platform === 'macos') {
      return 'Cmd+Alt+I'
    }

    if (platform === 'windows') {
      return 'Ctrl+Shift+I / F12'
    }

    return 'Ctrl+Shift+I / F12'
  }, [platform])

  const desktopDiagnostic = useMemo(() => {
    return {
      appVersion: `v${appVersion}`,
      platform,
      runtimeMode: mode,
      currentProject: project ?? t('settings.debugDiagnosticNoProject', 'Aucun projet chargé'),
      debugMode: settings.debug_mode ? 'enabled' : 'disabled',
    }
  }, [appVersion, mode, platform, project, settings.debug_mode, t])

  useEffect(() => {
    let cancelled = false

    const loadSettings = async () => {
      try {
        const nextSettings = await getAppSettings()
        if (!cancelled) {
          setSettingsState(nextSettings)
        }
      } catch (err) {
        console.error('Failed to load app settings:', err)
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadSettings()

    return () => {
      cancelled = true
    }
  }, [])

  const effectiveLanguage = useMemo<UiLanguage>(() => {
    const language = i18n.resolvedLanguage ?? i18n.language
    return language.startsWith('fr') ? 'fr' : 'en'
  }, [i18n.language, i18n.resolvedLanguage])

  const saveSettings = async (
    patch: Partial<AppSettings>,
    key: 'ui_language' | 'auto_load_last_project' | 'debug_mode'
  ) => {
    const previousSettings = settings
    const nextSettings = { ...settings, ...patch }

    setSavingKey(key)

    try {
      await setAppSettings(nextSettings)

      if (patch.ui_language) {
        await applyUiLanguagePreference(patch.ui_language)
      }

      setSettingsState(nextSettings)
    } catch (err) {
      console.error('Failed to update app settings:', err)
      setSettingsState(previousSettings)
    } finally {
      setSavingKey(null)
    }
  }

  const handleOpenDevtools = async () => {
    setOpeningDevtools(true)
    try {
      await openDesktopDevtools()
      toast.success(t('settings.debugDevtoolsOpened', 'DevTools ouvertes'))
    } catch (err) {
      console.error('Failed to open desktop DevTools:', err)
      toast.error(t('settings.debugDevtoolsOpenError', 'Impossible d’ouvrir les DevTools'), {
        description: err instanceof Error ? err.message : undefined,
      })
    } finally {
      setOpeningDevtools(false)
    }
  }

  const handleCopyDiagnostic = async () => {
    const payload = [
      `app_version: ${desktopDiagnostic.appVersion}`,
      `platform: ${desktopDiagnostic.platform}`,
      `runtime_mode: ${desktopDiagnostic.runtimeMode}`,
      `current_project: ${desktopDiagnostic.currentProject}`,
      `debug_mode: ${desktopDiagnostic.debugMode}`,
    ].join('\n')

    try {
      await navigator.clipboard.writeText(payload)
      toast.success(t('settings.debugDiagnosticCopied', 'Diagnostic copié'))
    } catch (err) {
      console.error('Failed to copy desktop diagnostic:', err)
      toast.error(t('settings.debugDiagnosticCopyError', 'Impossible de copier le diagnostic'))
    }
  }

  return (
    <div className="container mx-auto h-full space-y-4 overflow-auto p-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">
          {t('settings.title', 'Settings')}
        </h1>
        <p className="text-muted-foreground">
          {t(
            'settings.description',
            'Configure your desktop application preferences'
          )}
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Languages className="h-5 w-5" />
                {t('settings.interface', 'Interface')}
              </CardTitle>
              <CardDescription>
                {t(
                  'settings.interfaceDesc',
                  'Choose how the application language is selected.'
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ui-language">
                  {t('settings.uiLanguage', 'Application language')}
                </Label>
                <Select
                  value={settings.ui_language}
                  onValueChange={(value) =>
                    void saveSettings(
                      { ui_language: value as UiLanguagePreference },
                      'ui_language'
                    )
                  }
                  disabled={loading || savingKey === 'ui_language'}
                >
                  <SelectTrigger id="ui-language">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">
                      {t('settings.uiLanguageAuto', 'Automatic (system)')}
                    </SelectItem>
                    <SelectItem value="fr">
                      {t('settings.uiLanguageFrench', 'Français')}
                    </SelectItem>
                    <SelectItem value="en">
                      {t('settings.uiLanguageEnglish', 'English')}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground">
                  {settings.ui_language === 'auto'
                    ? t('settings.languageDetected', 'Currently using {{language}}.', {
                        language: LANGUAGE_LABELS[effectiveLanguage],
                      })
                    : t('settings.languageManual', 'Currently set to {{language}}.', {
                        language: LANGUAGE_LABELS[effectiveLanguage],
                      })}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="h-5 w-5" />
                {t('settings.appearance', 'Appearance')}
              </CardTitle>
              <CardDescription>
                {t(
                  'settings.appearanceDesc',
                  'Choose the visual theme and light or dark rendering mode.'
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ThemeSwitcher columns={2} />
            </CardContent>
          </Card>

          {isDesktop && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="h-5 w-5" />
                  {t('settings.appBehavior', 'Startup')}
                </CardTitle>
                <CardDescription>
                  {t(
                    'settings.appBehaviorDesc',
                    'Keep only desktop behaviors that are actually configurable.'
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between gap-4">
                  <div className="space-y-0.5">
                    <Label htmlFor="auto-load-last-project">
                      {t(
                        'settings.openLastProject',
                        'Open last project on startup'
                      )}
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      {t(
                        'settings.openLastProjectDesc',
                        'Automatically reopen the most recent valid project.'
                      )}
                    </p>
                  </div>
                  <Switch
                    id="auto-load-last-project"
                    checked={settings.auto_load_last_project}
                    onCheckedChange={(checked) =>
                      void saveSettings(
                        { auto_load_last_project: checked },
                        'auto_load_last_project'
                      )
                    }
                    disabled={loading || savingKey === 'auto_load_last_project'}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {isDesktop && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="h-5 w-5" />
                  {t('settings.debug', 'Debug')}
                </CardTitle>
                <CardDescription>
                  {t(
                    'settings.debugDesc',
                    'Active les outils de diagnostic desktop sans ouvrir automatiquement les DevTools.'
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="space-y-0.5">
                    <Label htmlFor="debug-mode">
                      {t('settings.debugMode', 'Mode debug desktop')}
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      {t(
                        'settings.debugModeDesc',
                        'Permet d’ouvrir les DevTools à la demande pour diagnostiquer un problème sur la build desktop.'
                      )}
                    </p>
                  </div>
                  <Switch
                    id="debug-mode"
                    checked={settings.debug_mode}
                    onCheckedChange={(checked) =>
                      void saveSettings({ debug_mode: checked }, 'debug_mode')
                    }
                    disabled={loading || savingKey === 'debug_mode'}
                  />
                </div>

                <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
                  <div className="space-y-0.5">
                    <Label>{t('settings.debugDevtools', 'DevTools desktop')}</Label>
                    <p className="text-sm text-muted-foreground">
                      {settings.debug_mode
                        ? t(
                            'settings.debugDevtoolsEnabled',
                            'Ouvrez les DevTools uniquement quand vous en avez besoin.'
                          )
                        : t(
                            'settings.debugDevtoolsDisabled',
                            'Activez d’abord le mode debug pour autoriser l’ouverture des DevTools.'
                          )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t('settings.debugShortcut', 'Raccourci : {{shortcut}}', {
                        shortcut: debugShortcutLabel,
                      })}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => void handleOpenDevtools()}
                    disabled={!settings.debug_mode || openingDevtools}
                  >
                    {openingDevtools ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Settings2 className="mr-2 h-4 w-4" />
                    )}
                    {t('settings.debugOpenDevtools', 'Ouvrir les DevTools')}
                  </Button>
                </div>

                <div className="space-y-3 rounded-lg border p-3">
                  <div className="space-y-0.5">
                    <Label>{t('settings.debugDiagnostic', 'Diagnostic desktop')}</Label>
                    <p className="text-sm text-muted-foreground">
                      {t(
                        'settings.debugDiagnosticDesc',
                        'Résumé rapide à copier pour un bug report ou un ticket de support.'
                      )}
                    </p>
                  </div>

                  <dl className="grid gap-2 text-sm sm:grid-cols-[160px_minmax(0,1fr)]">
                    <dt className="text-muted-foreground">
                      {t('settings.debugDiagnosticVersion', 'Version')}
                    </dt>
                    <dd className="font-mono">{desktopDiagnostic.appVersion}</dd>

                    <dt className="text-muted-foreground">
                      {t('settings.debugDiagnosticPlatform', 'Plateforme')}
                    </dt>
                    <dd className="font-mono">{desktopDiagnostic.platform}</dd>

                    <dt className="text-muted-foreground">
                      {t('settings.debugDiagnosticRuntime', 'Mode runtime')}
                    </dt>
                    <dd className="font-mono">{desktopDiagnostic.runtimeMode}</dd>

                    <dt className="text-muted-foreground">
                      {t('settings.debugDiagnosticProject', 'Projet courant')}
                    </dt>
                    <dd className="break-all font-mono">{desktopDiagnostic.currentProject}</dd>

                    <dt className="text-muted-foreground">
                      {t('settings.debugDiagnosticDebugMode', 'Mode debug')}
                    </dt>
                    <dd className="font-mono">{desktopDiagnostic.debugMode}</dd>
                  </dl>

                  <div className="flex justify-end">
                    <Button variant="outline" onClick={() => void handleCopyDiagnostic()}>
                      <Copy className="mr-2 h-4 w-4" />
                      {t('settings.debugDiagnosticCopy', 'Copier le diagnostic')}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {isDesktop && (
          <AboutPanel
            appVersion={appVersion}
            status={status}
            updateVersion={updateVersion}
            manualUpdateUrl={manualUpdateUrl}
            onCheckForUpdate={checkForUpdate}
            onInstallUpdate={installUpdate}
            onRestartApp={restartApp}
          />
        )}
      </div>
    </div>
  )
}
