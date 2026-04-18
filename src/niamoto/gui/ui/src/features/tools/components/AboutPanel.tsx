import { useTranslation } from 'react-i18next'
import { Check, Download, Info, Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import type { UpdateInfo } from '@/shared/desktop/updater/useAppUpdater'
import { openExternalUrl } from '@/shared/desktop/openExternalUrl'
import {
  getAboutContent,
  resolveAboutLocale,
} from '@/features/tools/content/aboutContent'
import { AboutPartnersSection } from './AboutPartnersSection'
import { AboutTeamSection } from './AboutTeamSection'

interface AboutPanelProps {
  appVersion: string
  status: UpdateInfo['status']
  updateVersion?: string
  manualUpdateUrl?: string
  onCheckForUpdate: () => Promise<void>
  onInstallUpdate: () => Promise<void>
  onRestartApp: () => Promise<void>
}

export function AboutPanel({
  appVersion,
  status,
  updateVersion,
  manualUpdateUrl,
  onCheckForUpdate,
  onInstallUpdate,
  onRestartApp,
}: AboutPanelProps) {
  const { t, i18n } = useTranslation('tools')
  const locale = resolveAboutLocale(i18n.resolvedLanguage ?? i18n.language)
  const content = getAboutContent(locale)

  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Info className="h-5 w-5" />
          {t('settings.about', 'About')}
        </CardTitle>
        <CardDescription>
          {t('settings.aboutDesc', 'Application version, team, and institutional partners')}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label>{t('settings.currentVersion', 'Current version')}</Label>
            <p className="font-mono text-sm text-muted-foreground">v{appVersion}</p>
          </div>
          {(status === 'available' || status === 'restart_required') && updateVersion ? (
            <div className="text-right">
              {status === 'available' ? (
                <p className="text-sm font-medium text-green-600">
                  {t('settings.updateAvailable', 'Version {{version}} available', {
                    version: updateVersion,
                  })}
                </p>
              ) : (
                <p className="text-sm font-medium text-amber-600">
                  {t('settings.restartRequired', 'Restart required to use v{{version}}', {
                    version: updateVersion,
                  })}
                </p>
              )}
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          {status === 'available' ? (
            manualUpdateUrl ? (
              <Button
                variant="outline"
                onClick={() => void openExternalUrl(manualUpdateUrl)}
                size="sm"
              >
                <Download className="mr-2 h-4 w-4" />
                {t('settings.downloadUpdate', 'Télécharger v{{version}}', {
                  version: updateVersion,
                })}
              </Button>
            ) : (
              <Button onClick={onInstallUpdate} size="sm">
                <Download className="mr-2 h-4 w-4" />
                {t('settings.installUpdate', 'Install v{{version}}', {
                  version: updateVersion,
                })}
              </Button>
            )
          ) : status === 'restart_required' ? (
            <Button onClick={onRestartApp} size="sm">
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('settings.restartNow', 'Restart now')}
            </Button>
          ) : status === 'downloading' || status === 'installing' ? (
            <Button disabled size="sm">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {status === 'installing'
                ? t('settings.installingUpdate', 'Installing update...')
                : t('settings.downloadingUpdate', 'Downloading update...')}
            </Button>
          ) : (
            <Button
              variant="outline"
              onClick={onCheckForUpdate}
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

          {status === 'idle' ? (
            <p className="flex items-center text-sm text-muted-foreground">
              <Check className="mr-1 h-4 w-4 text-green-500" />
              {t('settings.upToDate', 'Up to date')}
            </p>
          ) : null}
        </div>

        {manualUpdateUrl ? (
          <p className="text-sm text-amber-700">
            {t(
              'settings.windowsManualUpdateNotice',
              'Les mises à jour automatiques sont désactivées sur Windows pour éviter les redémarrages système déclenchés par l’installateur MSI. Téléchargez la nouvelle version manuellement.'
            )}
          </p>
        ) : null}

        <Separator />

        <p className="text-sm text-muted-foreground">{content.summary}</p>

        <AboutTeamSection
          title={content.teamTitle}
          intro={content.teamIntro}
          members={content.members}
        />

        <Separator />

        <AboutPartnersSection
          title={content.partnersTitle}
          intro={content.partnersIntro}
          organizations={content.organizations}
        />
      </CardContent>
    </Card>
  )
}
