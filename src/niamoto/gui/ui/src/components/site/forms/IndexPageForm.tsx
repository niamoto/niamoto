/**
 * IndexPageForm - Dedicated form for index.html template
 *
 * Manages:
 * - Title and subtitle
 * - Stats list (label, value, icon)
 * - Features list (title, description, icon, url)
 */

import { useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { RepeatableField } from './RepeatableField'
import { LucideIconPicker } from './LucideIconPicker'

// Types for index.html context
interface StatItem {
  label: string
  value: string
  icon: string
}

interface FeatureItem {
  title: string
  description: string
  icon: string
  url: string
}

export interface IndexPageContext {
  title?: string
  subtitle?: string
  stats?: StatItem[]
  features?: FeatureItem[]
  content_source?: string
  content_markdown?: string
  [key: string]: unknown // Allow additional fields for compatibility
}

interface IndexPageFormProps {
  context: IndexPageContext
  onChange: (context: IndexPageContext) => void
}

export function IndexPageForm({ context, onChange }: IndexPageFormProps) {
  const updateField = useCallback(
    <K extends keyof IndexPageContext>(field: K, value: IndexPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Section Hero</h3>

        <div className="space-y-2">
          <Label htmlFor="title">Titre principal</Label>
          <Input
            id="title"
            value={context.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="Bienvenue sur Niamoto"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="subtitle">Sous-titre</Label>
          <Textarea
            id="subtitle"
            value={context.subtitle || ''}
            onChange={(e) => updateField('subtitle', e.target.value)}
            placeholder="Plateforme de donnees ecologiques de Nouvelle-Caledonie"
            rows={2}
          />
        </div>
      </div>

      <Separator />

      {/* Stats Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Statistiques</h3>
        <p className="text-sm text-muted-foreground">
          Chiffres cles affiches sur la page d'accueil
        </p>

        <RepeatableField<StatItem>
          items={context.stats || []}
          onChange={(stats) => updateField('stats', stats)}
          createItem={() => ({ label: '', value: '', icon: 'bar-chart' })}
          addLabel="Ajouter une statistique"
          renderItem={(item, _index, onItemChange) => (
            <div className="grid grid-cols-[auto_1fr_1fr] gap-3 items-end">
              <div className="space-y-1">
                <Label className="text-xs">Icone</Label>
                <LucideIconPicker
                  value={item.icon}
                  onChange={(icon) => onItemChange({ ...item, icon })}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Valeur</Label>
                <Input
                  value={item.value}
                  onChange={(e) => onItemChange({ ...item, value: e.target.value })}
                  placeholder="1,234"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Label</Label>
                <Input
                  value={item.label}
                  onChange={(e) => onItemChange({ ...item, label: e.target.value })}
                  placeholder="Especes"
                />
              </div>
            </div>
          )}
        />
      </div>

      <Separator />

      {/* Features Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Fonctionnalites</h3>
        <p className="text-sm text-muted-foreground">
          Liens vers les principales sections du site
        </p>

        <RepeatableField<FeatureItem>
          items={context.features || []}
          onChange={(features) => updateField('features', features)}
          createItem={() => ({ title: '', description: '', icon: 'leaf', url: '' })}
          addLabel="Ajouter une fonctionnalite"
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              <div className="grid grid-cols-[auto_1fr] gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-xs">Icone</Label>
                  <LucideIconPicker
                    value={item.icon}
                    onChange={(icon) => onItemChange({ ...item, icon })}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Titre</Label>
                  <Input
                    value={item.title}
                    onChange={(e) => onItemChange({ ...item, title: e.target.value })}
                    placeholder="Explorer les taxons"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Description</Label>
                <Input
                  value={item.description}
                  onChange={(e) => onItemChange({ ...item, description: e.target.value })}
                  placeholder="Decouvrez la flore de Nouvelle-Caledonie"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">URL</Label>
                <Input
                  value={item.url}
                  onChange={(e) => onItemChange({ ...item, url: e.target.value })}
                  placeholder="taxons/index.html"
                />
              </div>
            </div>
          )}
        />
      </div>
    </div>
  )
}

export default IndexPageForm
