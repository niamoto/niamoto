import { useTranslation } from 'react-i18next'
import { Settings as SettingsIcon, Database, Palette, Bell, Shield, Save, Info, RefreshCw, Download, Check, Loader2 } from 'lucide-react'
import { useAppUpdater } from '@/shared/desktop/updater/useAppUpdater'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ThemeSwitcher } from '@/components/theme'

export function Settings() {
  const { t } = useTranslation()
  const { isDesktop } = useRuntimeMode()
  const { status, version: updateVersion, appVersion, checkForUpdate, installUpdate } = useAppUpdater()

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t('settings.title', 'Settings')}
          </h1>
          <p className="text-muted-foreground">
            {t('settings.description', 'Configure your Niamoto instance')}
          </p>
        </div>
        <Button>
          <Save className="mr-2 h-4 w-4" />
          {t('common.save_changes', 'Save Changes')}
        </Button>
      </div>

      {/* Settings Tabs */}
      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general">
            <SettingsIcon className="mr-2 h-4 w-4" />
            {t('settings.general', 'General')}
          </TabsTrigger>
          <TabsTrigger value="database">
            <Database className="mr-2 h-4 w-4" />
            {t('settings.database', 'Database')}
          </TabsTrigger>
          <TabsTrigger value="appearance">
            <Palette className="mr-2 h-4 w-4" />
            {t('settings.appearance', 'Appearance')}
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="mr-2 h-4 w-4" />
            {t('settings.notifications', 'Notifications')}
          </TabsTrigger>
          <TabsTrigger value="advanced">
            <Shield className="mr-2 h-4 w-4" />
            {t('settings.advanced', 'Advanced')}
          </TabsTrigger>
        </TabsList>

        {/* General Settings */}
        <TabsContent value="general" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.project_settings', 'Project Settings')}</CardTitle>
              <CardDescription>
                {t('settings.project_settings_desc', 'Basic configuration for your project')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="project-name">{t('settings.project_name', 'Project Name')}</Label>
                <Input id="project-name" placeholder="My Ecological Project" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">{t('settings.project_description', 'Description')}</Label>
                <Input id="description" placeholder="A comprehensive ecological data platform" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="language">{t('settings.default_language', 'Default Language')}</Label>
                <Select defaultValue="en">
                  <SelectTrigger id="language">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="fr">Français</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('settings.export_settings', 'Export Settings')}</CardTitle>
              <CardDescription>
                {t('settings.export_settings_desc', 'Configure default export parameters')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="output-dir">{t('settings.output_directory', 'Output Directory')}</Label>
                <Input id="output-dir" placeholder="/path/to/output" />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('settings.auto_export', 'Auto Export')}</Label>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.auto_export_desc', 'Automatically export after transforms')}
                  </p>
                </div>
                <Switch />
              </div>
            </CardContent>
          </Card>
          {isDesktop && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5" />
                {t('settings.about', 'About')}
              </CardTitle>
              <CardDescription>
                {t('settings.about_desc', 'Application version and updates')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('settings.current_version', 'Current version')}</Label>
                  <p className="text-sm font-mono text-muted-foreground">v{appVersion}</p>
                </div>
                {status === 'available' && updateVersion && (
                  <div className="text-right">
                    <p className="text-sm font-medium text-green-600">v{updateVersion} disponible</p>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                {status === 'available' ? (
                  <Button onClick={installUpdate} size="sm">
                    <Download className="mr-2 h-4 w-4" />
                    Installer v{updateVersion}
                  </Button>
                ) : status === 'downloading' ? (
                  <Button disabled size="sm">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Installation en cours...
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={checkForUpdate}
                    disabled={status === 'checking'}
                  >
                    {status === 'checking' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-2 h-4 w-4" />
                    )}
                    {t('settings.check_updates', 'Check for updates')}
                  </Button>
                )}
                {status === 'idle' && (
                  <p className="flex items-center text-sm text-muted-foreground">
                    <Check className="mr-1 h-4 w-4 text-green-500" />
                    {t('settings.up_to_date', 'Up to date')}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
          )}
        </TabsContent>

        {/* Database Settings */}
        <TabsContent value="database" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.database_config', 'Database Configuration')}</CardTitle>
              <CardDescription>
                {t('settings.database_config_desc', 'Manage your database connections and settings')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="db-path">{t('settings.database_path', 'Database Path')}</Label>
                <Input id="db-path" placeholder="/path/to/database.db" readOnly />
              </div>
              <div className="space-y-2">
                <Label>{t('settings.database_size', 'Database Size')}</Label>
                <p className="text-sm text-muted-foreground">256.3 MB</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline">
                  {t('settings.backup_database', 'Backup Database')}
                </Button>
                <Button variant="outline">
                  {t('settings.optimize_database', 'Optimize Database')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Appearance Settings */}
        <TabsContent value="appearance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.theme_settings', 'Theme Settings')}</CardTitle>
              <CardDescription>
                {t('settings.theme_settings_desc', 'Customize the appearance of your interface')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ThemeSwitcher columns={2} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('settings.display_options', 'Display Options')}</CardTitle>
              <CardDescription>
                {t('settings.display_options_desc', 'Additional display preferences')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('settings.compact_mode', 'Compact Mode')}</Label>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.compact_mode_desc', 'Use compact spacing in the interface')}
                  </p>
                </div>
                <Switch />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Settings */}
        <TabsContent value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.notification_preferences', 'Notification Preferences')}</CardTitle>
              <CardDescription>
                {t('settings.notification_preferences_desc', 'Choose what notifications you receive')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('settings.import_complete', 'Import Complete')}</Label>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.import_complete_desc', 'Notify when data import is finished')}
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('settings.transform_complete', 'Transform Complete')}</Label>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.transform_complete_desc', 'Notify when transforms are done')}
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('settings.export_complete', 'Export Complete')}</Label>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.export_complete_desc', 'Notify when site export is finished')}
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Advanced Settings */}
        <TabsContent value="advanced" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.developer_options', 'Developer Options')}</CardTitle>
              <CardDescription>
                {t('settings.developer_options_desc', 'Advanced settings for developers')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('settings.debug_mode', 'Debug Mode')}</Label>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.debug_mode_desc', 'Enable detailed logging')}
                  </p>
                </div>
                <Switch />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('settings.experimental_features', 'Experimental Features')}</Label>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.experimental_features_desc', 'Enable features in development')}
                  </p>
                </div>
                <Switch />
              </div>
              <div className="pt-4 border-t">
                <Button variant="destructive">
                  {t('settings.reset_all', 'Reset All Settings')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
