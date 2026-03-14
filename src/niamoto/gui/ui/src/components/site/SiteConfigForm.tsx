/**
 * SiteConfigForm - Form for site-wide settings
 *
 * Allows editing:
 * - Site title and language
 * - Logos (header/footer) with upload
 * - Colors (primary, navigation)
 * - External links (GitHub)
 */

import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Globe, Image, Upload, Loader2, Languages, Plus, X } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { SiteSettings } from '@/hooks/useSiteConfig'
import { useProjectFiles, useUploadFile } from '@/hooks/useSiteConfig'
import { toast } from 'sonner'

// Available languages for content generation
const AVAILABLE_LANGUAGES = [
  { code: 'fr', name: 'Francais' },
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Espanol' },
  { code: 'de', name: 'Deutsch' },
  { code: 'pt', name: 'Portugues' },
  { code: 'it', name: 'Italiano' },
]

interface SiteConfigFormProps {
  config: SiteSettings
  onChange: (config: SiteSettings) => void
}

export function SiteConfigForm({ config, onChange }: SiteConfigFormProps) {
  const { t } = useTranslation('site')

  // Refs for file inputs
  const headerInputRef = useRef<HTMLInputElement>(null)
  const footerInputRef = useRef<HTMLInputElement>(null)

  // Fetch available files for logo selection
  const { data: filesData } = useProjectFiles('files')
  const uploadMutation = useUploadFile()

  const imageFiles = filesData?.files.filter((f) =>
    ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp'].includes(f.extension)
  ) ?? []

  const updateField = <K extends keyof SiteSettings>(field: K, value: SiteSettings[K]) => {
    onChange({ ...config, [field]: value })
  }

  const handleUpload = async (file: File, field: 'logo_header' | 'logo_footer') => {
    try {
      const result = await uploadMutation.mutateAsync({ file, folder: 'files' })
      updateField(field, result.path)
      toast.success(t('siteConfig.logoUploaded'), {
        description: result.filename,
      })
    } catch (err) {
      toast.error(t('siteConfig.uploadError'), {
        description: err instanceof Error ? err.message : t('siteConfig.uploadFailed'),
      })
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, field: 'logo_header' | 'logo_footer') => {
    const file = e.target.files?.[0]
    if (file) {
      handleUpload(file, field)
    }
    // Reset input
    e.target.value = ''
  }

  return (
    <div className="space-y-6">
      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="h-4 w-4" />
            {t('siteConfig.generalSettings')}
          </CardTitle>
          <CardDescription>{t('siteConfig.generalSettingsDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="site-title">{t('siteConfig.siteTitle')}</Label>
              <Input
                id="site-title"
                value={config.title}
                onChange={(e) => updateField('title', e.target.value)}
                placeholder={t('siteConfig.siteNamePlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="site-lang">{t('siteConfig.language')}</Label>
              <Select value={config.lang} onValueChange={(v) => updateField('lang', v)}>
                <SelectTrigger id="site-lang">
                  <SelectValue placeholder={t('siteConfig.selectLanguage')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fr">Francais</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="es">Espanol</SelectItem>
                  <SelectItem value="de">Deutsch</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logos */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Image className="h-4 w-4" />
            {t('siteConfig.logos')}
          </CardTitle>
          <CardDescription>{t('siteConfig.logosDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Header Logo */}
            <div className="space-y-2">
              <Label htmlFor="logo-header">{t('siteConfig.headerLogo')}</Label>
              <div className="flex gap-2">
                <Select
                  value={config.logo_header || '__none__'}
                  onValueChange={(v) => updateField('logo_header', v === '__none__' ? null : v)}
                >
                  <SelectTrigger id="logo-header" className="flex-1 min-w-0">
                    <SelectValue placeholder={t('siteConfig.selectLogo')} className="truncate" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">{t('siteConfig.none')}</SelectItem>
                    {imageFiles.map((file) => (
                      <SelectItem key={file.path} value={file.path}>
                        <span className="truncate max-w-[200px]" title={file.name}>
                          {file.name}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <input
                  ref={headerInputRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.svg,.gif,.webp"
                  onChange={(e) => handleFileChange(e, 'logo_header')}
                  className="hidden"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => headerInputRef.current?.click()}
                  disabled={uploadMutation.isPending}
                  title={t('siteConfig.uploadLogo')}
                >
                  {uploadMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {config.logo_header && (
                <div className="flex items-center gap-2 mt-2">
                  <img
                    src={`/api/files/serve/${encodeURIComponent(config.logo_header)}`}
                    alt="Logo header"
                    className="h-10 w-auto max-w-[120px] object-contain rounded border bg-muted/30 p-1"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                  <span className="text-xs text-muted-foreground truncate" title={config.logo_header}>
                    {config.logo_header.split('/').pop()}
                  </span>
                </div>
              )}
            </div>

            {/* Footer Logo */}
            <div className="space-y-2">
              <Label htmlFor="logo-footer">{t('siteConfig.footerLogo')}</Label>
              <div className="flex gap-2">
                <Select
                  value={config.logo_footer || '__none__'}
                  onValueChange={(v) => updateField('logo_footer', v === '__none__' ? null : v)}
                >
                  <SelectTrigger id="logo-footer" className="flex-1 min-w-0">
                    <SelectValue placeholder={t('siteConfig.selectLogo')} className="truncate" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">{t('siteConfig.none')}</SelectItem>
                    {imageFiles.map((file) => (
                      <SelectItem key={file.path} value={file.path}>
                        <span className="truncate max-w-[200px]" title={file.name}>
                          {file.name}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <input
                  ref={footerInputRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.svg,.gif,.webp"
                  onChange={(e) => handleFileChange(e, 'logo_footer')}
                  className="hidden"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => footerInputRef.current?.click()}
                  disabled={uploadMutation.isPending}
                  title={t('siteConfig.uploadLogo')}
                >
                  {uploadMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {config.logo_footer && (
                <div className="flex items-center gap-2 mt-2">
                  <img
                    src={`/api/files/serve/${encodeURIComponent(config.logo_footer)}`}
                    alt="Logo footer"
                    className="h-10 w-auto max-w-[120px] object-contain rounded border bg-muted/30 p-1"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                  <span className="text-xs text-muted-foreground truncate" title={config.logo_footer}>
                    {config.logo_footer.split('/').pop()}
                  </span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Content Languages (i18n) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Languages className="h-4 w-4" />
            {t('siteConfig.contentLanguages')}
          </CardTitle>
          <CardDescription>{t('siteConfig.contentLanguagesDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current languages */}
          <div className="space-y-2">
            <Label>{t('siteConfig.generateLanguages')}</Label>
            <div className="flex flex-wrap gap-2">
              {(config.languages || [config.lang]).map((lang) => (
                <Badge
                  key={lang}
                  variant={lang === config.lang ? 'default' : 'secondary'}
                  className="flex items-center gap-1"
                >
                  {AVAILABLE_LANGUAGES.find((l) => l.code === lang)?.name || lang.toUpperCase()}
                  {lang === config.lang && (
                    <span className="text-xs opacity-70 ml-1">({t('siteConfig.default')})</span>
                  )}
                  {(config.languages?.length || 1) > 1 && lang !== config.lang && (
                    <button
                      type="button"
                      onClick={() => {
                        const newLangs = (config.languages || [config.lang]).filter((l) => l !== lang)
                        onChange({ ...config, languages: newLangs })
                      }}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </Badge>
              ))}

              {/* Add language dropdown */}
              <Select
                value=""
                onValueChange={(newLang) => {
                  if (newLang) {
                    const currentLangs = config.languages || [config.lang]
                    if (!currentLangs.includes(newLang)) {
                      onChange({ ...config, languages: [...currentLangs, newLang] })
                    }
                  }
                }}
              >
                <SelectTrigger className="w-[140px] h-7">
                  <div className="flex items-center gap-1 text-xs">
                    <Plus className="h-3 w-3" />
                    {t('common:i18n.addLanguage')}
                  </div>
                </SelectTrigger>
                <SelectContent>
                  {AVAILABLE_LANGUAGES.filter(
                    (l) => !(config.languages || [config.lang]).includes(l.code)
                  ).map((lang) => (
                    <SelectItem key={lang.code} value={lang.code}>
                      {lang.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('siteConfig.languagesHint')}
            </p>
          </div>

          {/* Language switcher toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="language-switcher">{t('siteConfig.languageSwitcher')}</Label>
              <p className="text-xs text-muted-foreground">
                {t('siteConfig.languageSwitcherDesc')}
              </p>
            </div>
            <Switch
              id="language-switcher"
              checked={config.language_switcher || false}
              onCheckedChange={(checked) => onChange({ ...config, language_switcher: checked })}
              disabled={(config.languages?.length || 1) <= 1}
            />
          </div>

          {/* Info about multi-language generation */}
          {(config.languages?.length || 1) > 1 && (
            <div className="rounded-md bg-muted/50 p-3 text-sm">
              <p className="text-muted-foreground">
                <strong>{t('siteConfig.multiLangNote')}:</strong>{' '}
                {t('siteConfig.multiLangNoteDesc', {
                  count: config.languages?.length || 1,
                  languages: (config.languages || [config.lang]).map((l) => l.toUpperCase()).join(', '),
                })}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
