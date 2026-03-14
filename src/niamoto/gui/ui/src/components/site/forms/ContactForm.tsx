/**
 * ContactForm - Dedicated form for contact.html template
 *
 * Manages:
 * - Title and introduction
 * - Contact info (email, address, phone)
 * - Social links
 */

import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RepeatableField } from './RepeatableField'
import { MarkdownContentField } from './MarkdownContentField'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'

// Types for contact.html context
interface SocialLink {
  platform: string
  url: string
  icon?: string
}

export interface ContactPageContext {
  title?: LocalizedString
  introduction?: LocalizedString
  content_source?: string | null
  email?: string
  address?: string
  phone?: string
  social?: SocialLink[]
  map_embed?: string
  [key: string]: unknown
}

interface ContactFormProps {
  context: ContactPageContext
  onChange: (context: ContactPageContext) => void
  pageName: string
}

const SOCIAL_PLATFORMS = [
  { value: 'twitter', label: 'Twitter / X', icon: 'fab fa-twitter' },
  { value: 'linkedin', label: 'LinkedIn', icon: 'fab fa-linkedin' },
  { value: 'github', label: 'GitHub', icon: 'fab fa-github' },
  { value: 'facebook', label: 'Facebook', icon: 'fab fa-facebook' },
  { value: 'instagram', label: 'Instagram', icon: 'fab fa-instagram' },
  { value: 'youtube', label: 'YouTube', icon: 'fab fa-youtube' },
  { value: 'researchgate', label: 'ResearchGate', icon: 'fab fa-researchgate' },
  { value: 'orcid', label: 'ORCID', icon: 'fab fa-orcid' },
  { value: 'website', label: 'Site web', icon: 'fas fa-globe' },
]

export function ContactForm({
  context,
  onChange,
  pageName,
}: ContactFormProps) {
  const { t } = useTranslation('site')

  const updateField = useCallback(
    <K extends keyof ContactPageContext>(field: K, value: ContactPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.contact.header')}</h3>

        <LocalizedInput
          value={context.title}
          onChange={(val) => updateField('title', val)}
          placeholder={t('forms.contact.pageTitlePlaceholder')}
          label={t('forms.contact.pageTitle')}
        />

        <LocalizedInput
          value={context.introduction}
          onChange={(val) => updateField('introduction', val)}
          placeholder={t('forms.contact.introPlaceholder')}
          label={t('forms.contact.introduction')}
          multiline
          rows={3}
        />

        {/* Optional markdown content */}
        <MarkdownContentField
          baseName={pageName}
          contentSource={context.content_source}
          onContentSourceChange={(source) => updateField('content_source', source)}
          label={t('forms.common.markdownContent')}
          description={t('forms.common.markdownContentDesc')}
          minHeight="150px"
        />
      </div>

      <Separator />

      {/* Contact Info Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.contact.contactInfo')}</h3>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="email">{t('forms.contact.email')}</Label>
            <Input
              id="email"
              type="email"
              value={context.email || ''}
              onChange={(e) => updateField('email', e.target.value)}
              placeholder={t('forms.contact.emailPlaceholder')}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">{t('forms.contact.phone')}</Label>
            <Input
              id="phone"
              type="tel"
              value={context.phone || ''}
              onChange={(e) => updateField('phone', e.target.value)}
              placeholder={t('forms.contact.phonePlaceholder')}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="address">{t('forms.contact.address')}</Label>
          <Textarea
            id="address"
            value={context.address || ''}
            onChange={(e) => updateField('address', e.target.value)}
            placeholder={t('forms.contact.addressPlaceholder')}
            rows={3}
          />
          <p className="text-xs text-muted-foreground">
            {t('forms.contact.addressHint')}
          </p>
        </div>
      </div>

      <Separator />

      {/* Social Links Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.contact.socialLinks')}</h3>
        <p className="text-sm text-muted-foreground">
          {t('forms.contact.socialLinksDesc', { defaultValue: 'Links to your social profiles' })}
        </p>

        <RepeatableField<SocialLink>
          items={context.social || []}
          onChange={(social) => updateField('social', social)}
          createItem={() => ({
            platform: 'twitter',
            url: '',
            icon: 'fab fa-twitter',
          })}
          addLabel={t('forms.contact.addSocialLink')}
          renderItem={(item, _index, onItemChange) => (
            <div className="grid grid-cols-[150px_1fr] gap-2">
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.contact.platform')}</Label>
                <Select
                  value={item.platform}
                  onValueChange={(value) => {
                    const platform = SOCIAL_PLATFORMS.find((p) => p.value === value)
                    onItemChange({
                      ...item,
                      platform: value,
                      icon: platform?.icon || 'fas fa-link',
                    })
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('forms.contact.selectPlatform')} />
                  </SelectTrigger>
                  <SelectContent>
                    {SOCIAL_PLATFORMS.map((platform) => (
                      <SelectItem key={platform.value} value={platform.value}>
                        {platform.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t('common:labels.url', { defaultValue: 'URL' })}</Label>
                <Input
                  value={item.url}
                  onChange={(e) => onItemChange({ ...item, url: e.target.value })}
                  placeholder={t('forms.contact.urlPlaceholder')}
                />
              </div>
            </div>
          )}
        />
      </div>

      <Separator />

      {/* Map Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.contact.map')}</h3>
        <p className="text-sm text-muted-foreground">
          {t('forms.contact.mapDesc')}
        </p>

        <div className="space-y-2">
          <Label htmlFor="map_embed">{t('forms.contact.mapEmbed')}</Label>
          <Textarea
            id="map_embed"
            value={context.map_embed || ''}
            onChange={(e) => updateField('map_embed', e.target.value)}
            placeholder='<iframe src="https://www.google.com/maps/embed?..." ...></iframe>'
            rows={4}
            className="font-mono text-xs"
          />
        </div>
      </div>
    </div>
  )
}

export default ContactForm
