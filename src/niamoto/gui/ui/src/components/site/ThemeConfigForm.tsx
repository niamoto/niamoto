/**
 * ThemeConfigForm - Advanced theme configuration
 *
 * Allows editing:
 * - Color scheme (primary, secondary, nav, background, text, links, footer)
 * - Typography (font family)
 * - Visual effects (widget gradient, border radius)
 * - Theme presets for quick styling
 */

import { Palette, Type, Sparkles, Paintbrush } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { SiteSettings } from '@/hooks/useSiteConfig'
import { cn } from '@/lib/utils'

interface ThemeConfigFormProps {
  config: SiteSettings
  onChange: (config: SiteSettings) => void
}

// Theme presets
const THEME_PRESETS = {
  forest: {
    name: 'Foret',
    primary_color: '#228b22',
    secondary_color: '#4caf50',
    nav_color: '#228b22',
    background_color: '#f0fdf4',
    text_color: '#14532d',
    link_color: '#16a34a',
    footer_bg_color: '#14532d',
  },
  ocean: {
    name: 'Ocean',
    primary_color: '#0369a1',
    secondary_color: '#0ea5e9',
    nav_color: '#0c4a6e',
    background_color: '#f0f9ff',
    text_color: '#0c4a6e',
    link_color: '#0284c7',
    footer_bg_color: '#0c4a6e',
  },
  sunset: {
    name: 'Crepuscule',
    primary_color: '#c2410c',
    secondary_color: '#f97316',
    nav_color: '#9a3412',
    background_color: '#fff7ed',
    text_color: '#7c2d12',
    link_color: '#ea580c',
    footer_bg_color: '#7c2d12',
  },
  lavender: {
    name: 'Lavande',
    primary_color: '#7c3aed',
    secondary_color: '#a78bfa',
    nav_color: '#5b21b6',
    background_color: '#faf5ff',
    text_color: '#4c1d95',
    link_color: '#8b5cf6',
    footer_bg_color: '#4c1d95',
  },
  earth: {
    name: 'Terre',
    primary_color: '#78350f',
    secondary_color: '#a16207',
    nav_color: '#78350f',
    background_color: '#fefce8',
    text_color: '#422006',
    link_color: '#a16207',
    footer_bg_color: '#422006',
  },
  slate: {
    name: 'Ardoise',
    primary_color: '#475569',
    secondary_color: '#64748b',
    nav_color: '#334155',
    background_color: '#f8fafc',
    text_color: '#1e293b',
    link_color: '#475569',
    footer_bg_color: '#1e293b',
  },
}

const FONT_OPTIONS = [
  { value: 'system', label: 'Systeme', preview: 'system-ui, sans-serif' },
  { value: 'serif', label: 'Serif', preview: 'Georgia, serif' },
  { value: 'mono', label: 'Monospace', preview: 'ui-monospace, monospace' },
  { value: 'inter', label: 'Inter', preview: '"Inter", sans-serif' },
  { value: 'roboto', label: 'Roboto', preview: '"Roboto", sans-serif' },
]

const RADIUS_OPTIONS = [
  { value: 'none', label: 'Aucun', preview: '0px' },
  { value: 'small', label: 'Petit', preview: '4px' },
  { value: 'medium', label: 'Moyen', preview: '8px' },
  { value: 'large', label: 'Grand', preview: '12px' },
  { value: 'full', label: 'Arrondi', preview: '9999px' },
]

// Color picker component with label
function ColorPicker({
  label,
  value,
  onChange,
  description,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  description?: string
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{label}</Label>
        {description && (
          <span className="text-xs text-muted-foreground">{description}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <div className="relative">
          <input
            type="color"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="h-10 w-14 cursor-pointer rounded-md border bg-transparent p-1"
          />
        </div>
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="#228b22"
          className="font-mono text-sm flex-1"
        />
      </div>
    </div>
  )
}

export function ThemeConfigForm({ config, onChange }: ThemeConfigFormProps) {
  const updateField = <K extends keyof SiteSettings>(field: K, value: SiteSettings[K]) => {
    onChange({ ...config, [field]: value })
  }

  const applyPreset = (presetKey: keyof typeof THEME_PRESETS) => {
    const preset = THEME_PRESETS[presetKey]
    onChange({
      ...config,
      primary_color: preset.primary_color,
      secondary_color: preset.secondary_color,
      nav_color: preset.nav_color,
      background_color: preset.background_color,
      text_color: preset.text_color,
      link_color: preset.link_color,
      footer_bg_color: preset.footer_bg_color,
    })
  }

  // Get current values with defaults
  const primaryColor = config.primary_color || '#228b22'
  const secondaryColor = (config.secondary_color as string) || '#4caf50'
  const navColor = config.nav_color || '#228b22'
  const backgroundColor = (config.background_color as string) || '#f9fafb'
  const textColor = (config.text_color as string) || '#111827'
  const linkColor = (config.link_color as string) || '#228b22'
  const footerBgColor = (config.footer_bg_color as string) || '#1f2937'
  const widgetGradient = (config.widget_header_gradient as boolean) ?? true
  const borderRadius = (config.border_radius as string) || 'medium'
  const fontFamily = (config.font_family as string) || 'system'

  return (
    <div className="space-y-6">
      {/* Theme Presets */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Paintbrush className="h-4 w-4" />
            Presets de theme
          </CardTitle>
          <CardDescription>Choisir un theme predefinipour commencer</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(THEME_PRESETS).map(([key, preset]) => (
              <Button
                key={key}
                variant="outline"
                className="h-auto flex-col items-start gap-2 p-3"
                onClick={() => applyPreset(key as keyof typeof THEME_PRESETS)}
              >
                <div className="flex items-center gap-2 w-full">
                  <div
                    className="h-4 w-4 rounded-full border"
                    style={{ backgroundColor: preset.primary_color }}
                  />
                  <div
                    className="h-4 w-4 rounded-full border"
                    style={{ backgroundColor: preset.secondary_color }}
                  />
                  <div
                    className="h-4 w-4 rounded-full border"
                    style={{ backgroundColor: preset.nav_color }}
                  />
                </div>
                <span className="text-xs font-medium">{preset.name}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Color Scheme */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Palette className="h-4 w-4" />
            Couleurs
          </CardTitle>
          <CardDescription>Personnaliser les couleurs du site</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Primary colors row */}
          <div className="grid gap-4 md:grid-cols-2">
            <ColorPicker
              label="Couleur primaire"
              value={primaryColor}
              onChange={(v) => updateField('primary_color', v)}
              description="Boutons, accents"
            />
            <ColorPicker
              label="Couleur secondaire"
              value={secondaryColor}
              onChange={(v) => updateField('secondary_color', v)}
              description="Hover, variations"
            />
          </div>

          {/* Navigation colors */}
          <div className="grid gap-4 md:grid-cols-2">
            <ColorPicker
              label="Barre de navigation"
              value={navColor}
              onChange={(v) => updateField('nav_color', v)}
              description="Menu principal"
            />
            <ColorPicker
              label="Pied de page"
              value={footerBgColor}
              onChange={(v) => updateField('footer_bg_color', v)}
              description="Fond du footer"
            />
          </div>

          {/* Content colors */}
          <div className="grid gap-4 md:grid-cols-3">
            <ColorPicker
              label="Fond de page"
              value={backgroundColor}
              onChange={(v) => updateField('background_color', v)}
            />
            <ColorPicker
              label="Texte"
              value={textColor}
              onChange={(v) => updateField('text_color', v)}
            />
            <ColorPicker
              label="Liens"
              value={linkColor}
              onChange={(v) => updateField('link_color', v)}
            />
          </div>

          {/* Preview */}
          <div className="mt-4 rounded-lg border p-4" style={{ backgroundColor }}>
            <div
              className="rounded-md p-3 mb-3"
              style={{ backgroundColor: navColor }}
            >
              <span className="text-white font-medium text-sm">Barre de navigation</span>
            </div>
            <h3 className="font-semibold mb-2" style={{ color: textColor }}>
              Apercu des couleurs
            </h3>
            <p className="text-sm mb-2" style={{ color: textColor }}>
              Voici un exemple de texte avec un{' '}
              <span style={{ color: linkColor }} className="underline cursor-pointer">
                lien cliquable
              </span>{' '}
              pour visualiser le rendu.
            </p>
            <div className="flex gap-2">
              <button
                className="px-3 py-1.5 rounded text-white text-sm font-medium"
                style={{ backgroundColor: primaryColor }}
              >
                Bouton primaire
              </button>
              <button
                className="px-3 py-1.5 rounded text-white text-sm font-medium"
                style={{ backgroundColor: secondaryColor }}
              >
                Bouton secondaire
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Typography */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Type className="h-4 w-4" />
            Typographie
          </CardTitle>
          <CardDescription>Police de caracteres du site</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Police principale</Label>
              <Select value={fontFamily} onValueChange={(v) => updateField('font_family', v as SiteSettings['font_family'])}>
                <SelectTrigger>
                  <SelectValue placeholder="Choisir une police" />
                </SelectTrigger>
                <SelectContent>
                  {FONT_OPTIONS.map((font) => (
                    <SelectItem key={font.value} value={font.value}>
                      <span style={{ fontFamily: font.preview }}>{font.label}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Font preview */}
            <div className="rounded-lg border p-4 bg-muted/30">
              <p
                className="text-lg mb-1"
                style={{
                  fontFamily: FONT_OPTIONS.find((f) => f.value === fontFamily)?.preview,
                }}
              >
                Apercu de la police selectionnee
              </p>
              <p
                className="text-sm text-muted-foreground"
                style={{
                  fontFamily: FONT_OPTIONS.find((f) => f.value === fontFamily)?.preview,
                }}
              >
                ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Visual Effects */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4" />
            Effets visuels
          </CardTitle>
          <CardDescription>Style des widgets et composants</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Widget gradient toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Gradient anime sur les widgets</Label>
              <p className="text-sm text-muted-foreground">
                Effet de degradeen-tete des widgets
              </p>
            </div>
            <Switch
              checked={widgetGradient}
              onCheckedChange={(v) => updateField('widget_header_gradient', v)}
            />
          </div>

          {/* Border radius */}
          <div className="space-y-2">
            <Label>Arrondi des coins</Label>
            <div className="flex gap-2">
              {RADIUS_OPTIONS.map((option) => (
                <Button
                  key={option.value}
                  variant={borderRadius === option.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => updateField('border_radius', option.value as SiteSettings['border_radius'])}
                  className={cn(
                    'flex-1',
                    borderRadius === option.value && 'ring-2 ring-primary ring-offset-2'
                  )}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Radius preview */}
          <div className="flex gap-4 pt-2">
            {['small', 'medium', 'large'].map((size) => {
              const radius = RADIUS_OPTIONS.find((r) => r.value === size)?.preview || '8px'
              return (
                <div
                  key={size}
                  className={cn(
                    'h-16 w-16 border-2 flex items-center justify-center text-xs',
                    borderRadius === size ? 'border-primary bg-primary/10' : 'border-muted'
                  )}
                  style={{ borderRadius: radius }}
                >
                  {radius}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
