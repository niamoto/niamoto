/**
 * IndexPageForm - Dedicated form for index.html template
 *
 * Manages:
 * - Title and subtitle
 * - Stats list (label, value, icon)
 * - Features list (title, description, icon, url)
 */

import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation('site')
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
        <h3 className="text-lg font-semibold">{t('forms.indexPage.heroSection')}</h3>

        <div className="space-y-2">
          <Label htmlFor="title">{t('forms.indexPage.mainTitle')}</Label>
          <Input
            id="title"
            value={context.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder={t('forms.indexPage.mainTitlePlaceholder')}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="subtitle">{t('forms.indexPage.subtitle')}</Label>
          <Textarea
            id="subtitle"
            value={context.subtitle || ''}
            onChange={(e) => updateField('subtitle', e.target.value)}
            placeholder={t('forms.indexPage.subtitlePlaceholder')}
            rows={2}
          />
        </div>
      </div>

      <Separator />

      {/* Stats Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.indexPage.statistics')}</h3>
        <p className="text-sm text-muted-foreground">
          {t('forms.indexPage.statisticsDescription')}
        </p>

        <RepeatableField<StatItem>
          items={context.stats || []}
          onChange={(stats) => updateField('stats', stats)}
          createItem={() => ({ label: '', value: '', icon: 'bar-chart' })}
          addLabel={t('forms.indexPage.addStat')}
          renderItem={(item, _index, onItemChange) => (
            <div className="grid grid-cols-[auto_1fr_1fr] gap-3 items-end">
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.indexPage.icon')}</Label>
                <LucideIconPicker
                  value={item.icon}
                  onChange={(icon) => onItemChange({ ...item, icon })}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.indexPage.value')}</Label>
                <Input
                  value={item.value}
                  onChange={(e) => onItemChange({ ...item, value: e.target.value })}
                  placeholder={t('forms.indexPage.valuePlaceholder')}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.indexPage.label')}</Label>
                <Input
                  value={item.label}
                  onChange={(e) => onItemChange({ ...item, label: e.target.value })}
                  placeholder={t('forms.indexPage.labelPlaceholder')}
                />
              </div>
            </div>
          )}
        />
      </div>

      <Separator />

      {/* Features Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.indexPage.features')}</h3>
        <p className="text-sm text-muted-foreground">
          {t('forms.indexPage.featuresDescription')}
        </p>

        <RepeatableField<FeatureItem>
          items={context.features || []}
          onChange={(features) => updateField('features', features)}
          createItem={() => ({ title: '', description: '', icon: 'leaf', url: '' })}
          addLabel={t('forms.indexPage.addFeature')}
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              <div className="grid grid-cols-[auto_1fr] gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.indexPage.icon')}</Label>
                  <LucideIconPicker
                    value={item.icon}
                    onChange={(icon) => onItemChange({ ...item, icon })}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.indexPage.title')}</Label>
                  <Input
                    value={item.title}
                    onChange={(e) => onItemChange({ ...item, title: e.target.value })}
                    placeholder={t('forms.indexPage.titlePlaceholder')}
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.indexPage.description')}</Label>
                <Input
                  value={item.description}
                  onChange={(e) => onItemChange({ ...item, description: e.target.value })}
                  placeholder={t('forms.indexPage.descriptionPlaceholder')}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.indexPage.url')}</Label>
                <Input
                  value={item.url}
                  onChange={(e) => onItemChange({ ...item, url: e.target.value })}
                  placeholder={t('forms.indexPage.urlPlaceholder')}
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
