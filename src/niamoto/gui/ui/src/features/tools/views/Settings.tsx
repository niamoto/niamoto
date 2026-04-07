import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Check,
  Download,
  Info,
  Languages,
  Loader2,
  RefreshCw,
  Settings2,
} from 'lucide-react'
import { useAppUpdater } from '@/shared/desktop/updater/useAppUpdater'
import {
  DEFAULT_APP_SETTINGS,
  applyUiLanguagePreference,
  getAppSettings,
  setAppSettings,
  type AppSettings,
} from '@/shared/desktop/appSettings'
import type { UiLanguage, UiLanguagePreference } from '@/i18n'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
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

const LANGUAGE_LABELS: Record<UiLanguage, string> = {
  fr: 'Français',
  en: 'English',
}

export function Settings() {
  const { t, i18n } = useTranslation('tools')
  const { isDesktop } = useRuntimeMode()
  const { status, version: updateVersion, appVersion, checkForUpdate, installUpdate } =
    useAppUpdater()
  const [settings, setSettingsState] = useState<AppSettings>(DEFAULT_APP_SETTINGS)
  const [loading, setLoading] = useState(true)
  const [savingKey, setSavingKey] = useState<'ui_language' | 'auto_load_last_project' | null>(
    null
  )

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
    key: 'ui_language' | 'auto_load_last_project'
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

  return (
    <div className="container mx-auto h-full space-y-6 overflow-auto p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
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
        </div>

        {isDesktop && (
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5" />
                {t('settings.about', 'About')}
              </CardTitle>
              <CardDescription>
                {t('settings.aboutDesc', 'Application version and updates')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-0.5">
                  <Label>{t('settings.currentVersion', 'Current version')}</Label>
                  <p className="font-mono text-sm text-muted-foreground">v{appVersion}</p>
                </div>
                {status === 'available' && updateVersion && (
                  <div className="text-right">
                    <p className="text-sm font-medium text-green-600">
                      {t('settings.updateAvailable', 'Version {{version}} available', {
                        version: updateVersion,
                      })}
                    </p>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                {status === 'available' ? (
                  <Button onClick={installUpdate} size="sm">
                    <Download className="mr-2 h-4 w-4" />
                    {t('settings.installUpdate', 'Install v{{version}}', {
                      version: updateVersion,
                    })}
                  </Button>
                ) : status === 'downloading' ? (
                  <Button disabled size="sm">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('settings.installingUpdate', 'Installing update...')}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    onClick={checkForUpdate}
                    disabled={status === 'checking'}
                    size="sm"
                  >
                    {status === 'checking' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-2 h-4 w-4" />
                    )}
                    {t('settings.checkUpdates', 'Check for updates')}
                  </Button>
                )}

                {status === 'idle' && (
                  <p className="flex items-center text-sm text-muted-foreground">
                    <Check className="mr-1 h-4 w-4 text-green-500" />
                    {t('settings.upToDate', 'Up to date')}
                  </p>
                )}
              </div>

            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
