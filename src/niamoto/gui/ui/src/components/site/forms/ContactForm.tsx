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

// Types for contact.html context
interface SocialLink {
  platform: string
  url: string
  icon?: string
}

export interface ContactPageContext {
  title?: string
  introduction?: string
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

export function ContactForm({ context, onChange }: ContactFormProps) {
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
        <h3 className="text-lg font-semibold">En-tete</h3>

        <div className="space-y-2">
          <Label htmlFor="title">Titre de la page</Label>
          <Input
            id="title"
            value={context.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder={t('forms.contact.pageTitlePlaceholder')}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="introduction">Introduction</Label>
          <Textarea
            id="introduction"
            value={context.introduction || ''}
            onChange={(e) => updateField('introduction', e.target.value)}
            placeholder={t('forms.contact.introPlaceholder')}
            rows={3}
          />
        </div>
      </div>

      <Separator />

      {/* Contact Info Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Informations de contact</h3>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={context.email || ''}
              onChange={(e) => updateField('email', e.target.value)}
              placeholder={t('forms.contact.emailPlaceholder')}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">Telephone</Label>
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
          <Label htmlFor="address">Adresse</Label>
          <Textarea
            id="address"
            value={context.address || ''}
            onChange={(e) => updateField('address', e.target.value)}
            placeholder={t('forms.contact.addressPlaceholder')}
            rows={3}
          />
          <p className="text-xs text-muted-foreground">
            Utilisez des retours a la ligne pour separer les lignes de l'adresse
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
        <h3 className="text-lg font-semibold">Carte (optionnel)</h3>
        <p className="text-sm text-muted-foreground">
          Code d'integration Google Maps ou OpenStreetMap
        </p>

        <div className="space-y-2">
          <Label htmlFor="map_embed">Code embed de la carte</Label>
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
