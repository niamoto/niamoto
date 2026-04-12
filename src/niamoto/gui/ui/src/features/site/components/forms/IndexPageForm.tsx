/**
 * IndexPageForm - Dedicated form for index.html template
 *
 * Manages:
 * - Hero section (title, subtitle, background image)
 * - Stats list (label, value, icon)
 * - Content (markdown editor via content_source)
 * - Features list (title, description, icon, url)
 */

import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { RepeatableField } from './RepeatableField'
import { LucideIconPicker } from './LucideIconPicker'
import { ImagePickerField } from './ImagePickerField'
import { MarkdownContentField } from './MarkdownContentField'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'

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

interface PartnerItem {
  name: string
  logo: string
  url: string
}

export interface IndexPageContext {
  title?: LocalizedString
  subtitle?: LocalizedString
  hero_image?: string
  partners?: PartnerItem[]
  stats?: StatItem[]
  features?: FeatureItem[]
  content_source?: string
  content_markdown?: string
  [key: string]: unknown // Allow additional fields for compatibility
}

interface IndexPageFormProps {
  context: IndexPageContext
  onChange: (context: IndexPageContext) => void
  pageName?: string
}

export function IndexPageForm({
  context,
  onChange,
  pageName = 'home',
}: IndexPageFormProps) {
  const { t } = useTranslation('site')
  const updateField = useCallback(
    <K extends keyof IndexPageContext>(field: K, value: IndexPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  return (
    <div className="space-y-4">
      {/* Hero Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.indexPage.heroSection')}</h3>

        <LocalizedInput
          value={context.title}
          onChange={(val) => updateField('title', val)}
          placeholder={t('forms.indexPage.mainTitlePlaceholder')}
          label={t('forms.indexPage.mainTitle')}
        />

        <LocalizedInput
          value={context.subtitle}
          onChange={(val) => updateField('subtitle', val)}
          placeholder={t('forms.indexPage.subtitlePlaceholder')}
          label={t('forms.indexPage.subtitle')}
          multiline
          rows={2}
        />

        <div className="space-y-2">
          <Label>{t('forms.indexPage.heroImage')}</Label>
          <ImagePickerField
            value={context.hero_image || ''}
            onChange={(path) => updateField('hero_image', path || undefined)}
            folder="files"
            placeholder={t('forms.indexPage.heroImagePlaceholder')}
          />
          <p className="text-xs text-muted-foreground">
            {t('forms.indexPage.heroImageHint')}
          </p>
        </div>

      </div>

      <Separator />

      {/* Partners Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.indexPage.partners')}</h3>
        <p className="text-sm text-muted-foreground">
          {t('forms.indexPage.partnersDescription')}
        </p>

        <RepeatableField<PartnerItem>
          items={context.partners || []}
          onChange={(partners) => updateField('partners', partners)}
          createItem={() => ({ name: '', logo: '', url: '' })}
          addLabel={t('forms.indexPage.addPartner')}
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.indexPage.partnerName')}</Label>
                  <Input
                    value={item.name}
                    onChange={(e) => onItemChange({ ...item, name: e.target.value })}
                    placeholder={t('forms.indexPage.partnerNamePlaceholder')}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.indexPage.partnerUrl')}</Label>
                  <Input
                    value={item.url}
                    onChange={(e) => onItemChange({ ...item, url: e.target.value })}
                    placeholder="https://..."
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.indexPage.partnerLogo')}</Label>
                <ImagePickerField
                  value={item.logo}
                  onChange={(path) => onItemChange({ ...item, logo: path || '' })}
                  folder="files"
                  placeholder={t('forms.indexPage.partnerLogoPlaceholder')}
                />
              </div>
            </div>
          )}
        />
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

      {/* Content Section */}
      <div className="space-y-4">
        <MarkdownContentField
          baseName={pageName}
          contentSource={context.content_source}
          onContentSourceChange={(source) => updateField('content_source', source ?? undefined)}
          label={t('forms.indexPage.contentSection')}
          description={t('forms.indexPage.contentDescription')}
          minHeight="250px"
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
