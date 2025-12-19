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
import { Globe, Image, Palette, Link2, Upload, Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
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

interface SiteConfigFormProps {
  config: SiteSettings
  onChange: (config: SiteSettings) => void
}

export function SiteConfigForm({ config, onChange }: SiteConfigFormProps) {
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
      toast.success('Logo uploade', {
        description: result.filename,
      })
    } catch (err) {
      toast.error('Erreur upload', {
        description: err instanceof Error ? err.message : 'Echec de l\'upload',
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
            Parametres generaux
          </CardTitle>
          <CardDescription>Titre et langue du site</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="site-title">Titre du site</Label>
              <Input
                id="site-title"
                value={config.title}
                onChange={(e) => updateField('title', e.target.value)}
                placeholder="Niamoto"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="site-lang">Langue</Label>
              <Select value={config.lang} onValueChange={(v) => updateField('lang', v)}>
                <SelectTrigger id="site-lang">
                  <SelectValue placeholder="Choisir une langue" />
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
            Logos
          </CardTitle>
          <CardDescription>Logos pour l'en-tete et le pied de page</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Header Logo */}
            <div className="space-y-2">
              <Label htmlFor="logo-header">Logo en-tete</Label>
              <div className="flex gap-2">
                <Select
                  value={config.logo_header || '__none__'}
                  onValueChange={(v) => updateField('logo_header', v === '__none__' ? null : v)}
                >
                  <SelectTrigger id="logo-header" className="flex-1 min-w-0">
                    <SelectValue placeholder="Selectionner un logo" className="truncate" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">Aucun</SelectItem>
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
                  title="Uploader un logo"
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
              <Label htmlFor="logo-footer">Logo pied de page</Label>
              <div className="flex gap-2">
                <Select
                  value={config.logo_footer || '__none__'}
                  onValueChange={(v) => updateField('logo_footer', v === '__none__' ? null : v)}
                >
                  <SelectTrigger id="logo-footer" className="flex-1 min-w-0">
                    <SelectValue placeholder="Selectionner un logo" className="truncate" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">Aucun</SelectItem>
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
                  title="Uploader un logo"
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

      {/* Colors */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Palette className="h-4 w-4" />
            Couleurs
          </CardTitle>
          <CardDescription>Couleurs du theme</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="primary-color">Couleur primaire</Label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  id="primary-color"
                  value={config.primary_color}
                  onChange={(e) => updateField('primary_color', e.target.value)}
                  className="h-10 w-14 cursor-pointer rounded border bg-transparent p-1"
                />
                <Input
                  value={config.primary_color}
                  onChange={(e) => updateField('primary_color', e.target.value)}
                  placeholder="#228b22"
                  className="font-mono"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="nav-color">Couleur navigation</Label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  id="nav-color"
                  value={config.nav_color}
                  onChange={(e) => updateField('nav_color', e.target.value)}
                  className="h-10 w-14 cursor-pointer rounded border bg-transparent p-1"
                />
                <Input
                  value={config.nav_color}
                  onChange={(e) => updateField('nav_color', e.target.value)}
                  placeholder="#228b22"
                  className="font-mono"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* External Links */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4" />
            Liens externes
          </CardTitle>
          <CardDescription>Liens vers des ressources externes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="github-url">URL GitHub</Label>
            <Input
              id="github-url"
              type="url"
              value={config.github_url || ''}
              onChange={(e) => updateField('github_url', e.target.value || null)}
              placeholder="https://github.com/niamoto/niamoto"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
