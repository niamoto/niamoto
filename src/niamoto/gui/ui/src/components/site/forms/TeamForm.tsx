/**
 * TeamForm - Dedicated form for team.html template
 *
 * Manages:
 * - Title and introduction
 * - Team members (name, role, institution, photo, email, etc.)
 * - Partners (name, logo, url, description)
 * - Funders (name, logo, url)
 */

import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Users, Building2, Wallet } from 'lucide-react'
import { RepeatableField } from './RepeatableField'
import { ImagePickerField } from './ImagePickerField'

// Types for team.html context
interface SocialLink {
  label: string
  url: string
}

interface TeamMember {
  name: string
  role: string
  institution?: string
  photo?: string
  email?: string
  orcid?: string
  links?: SocialLink[]
}

interface Partner {
  name: string
  logo?: string
  url?: string
  description?: string
}

interface Funder {
  name: string
  logo?: string
  url?: string
}

export interface TeamPageContext {
  title?: string
  introduction?: string
  team?: TeamMember[]
  partners?: Partner[]
  funders?: Funder[]
  [key: string]: unknown // Allow additional fields for compatibility
}

interface TeamFormProps {
  context: TeamPageContext
  onChange: (context: TeamPageContext) => void
}

export function TeamForm({ context, onChange }: TeamFormProps) {
  const { t } = useTranslation('site')

  const updateField = useCallback(
    <K extends keyof TeamPageContext>(field: K, value: TeamPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.team.header')}</h3>

        <div className="space-y-2">
          <Label htmlFor="title">{t('forms.team.pageTitle')}</Label>
          <Input
            id="title"
            value={context.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder={t('forms.team.pageTitlePlaceholder')}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="introduction">{t('forms.team.introduction')}</Label>
          <Textarea
            id="introduction"
            value={context.introduction || ''}
            onChange={(e) => updateField('introduction', e.target.value)}
            placeholder={t('forms.team.introPlaceholder')}
            rows={3}
          />
        </div>
      </div>

      <Separator />

      {/* Tabs for Team, Partners, Funders */}
      <Tabs defaultValue="team" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="team" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            {t('forms.team.tabTeam')} ({context.team?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="partners" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            {t('forms.team.tabPartners')} ({context.partners?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="funders" className="flex items-center gap-2">
            <Wallet className="h-4 w-4" />
            {t('forms.team.tabFunders')} ({context.funders?.length || 0})
          </TabsTrigger>
        </TabsList>

        {/* Team Members Tab */}
        <TabsContent value="team" className="mt-4">
          <RepeatableField<TeamMember>
            items={context.team || []}
            onChange={(team) => updateField('team', team)}
            createItem={() => ({
              name: '',
              role: '',
              institution: '',
              email: '',
            })}
            addLabel={t('forms.team.addMember')}
            renderItem={(item, _index, onItemChange) => (
              <div className="space-y-3">
                {/* Row 1: Name, Role */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.name')}</Label>
                    <Input
                      value={item.name}
                      onChange={(e) => onItemChange({ ...item, name: e.target.value })}
                      placeholder={t('forms.team.namePlaceholder')}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.role')}</Label>
                    <Input
                      value={item.role}
                      onChange={(e) => onItemChange({ ...item, role: e.target.value })}
                      placeholder={t('forms.team.rolePlaceholder')}
                    />
                  </div>
                </div>

                {/* Row 2: Institution, Photo */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.institution')}</Label>
                    <Input
                      value={item.institution || ''}
                      onChange={(e) => onItemChange({ ...item, institution: e.target.value })}
                      placeholder={t('forms.team.organizationPlaceholder')}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.photo')}</Label>
                    <ImagePickerField
                      value={item.photo || ''}
                      onChange={(photo) => onItemChange({ ...item, photo })}
                      folder="files/team"
                      placeholder={t('forms.team.selectPhoto')}
                    />
                  </div>
                </div>

                {/* Row 3: Email, ORCID */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.email')}</Label>
                    <Input
                      value={item.email || ''}
                      onChange={(e) => onItemChange({ ...item, email: e.target.value })}
                      placeholder={t('forms.team.emailPlaceholder')}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.orcid')}</Label>
                    <Input
                      value={item.orcid || ''}
                      onChange={(e) => onItemChange({ ...item, orcid: e.target.value })}
                      placeholder={t('forms.team.orcidPlaceholder')}
                    />
                  </div>
                </div>

                {/* Row 4: Social/Web links */}
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.team.links')}</Label>
                  <div className="border rounded-md p-2 bg-muted/20">
                    {(item.links || []).map((link, linkIndex) => (
                      <div key={linkIndex} className="flex gap-2 mb-2 last:mb-0">
                        <Input
                          value={link.label}
                          onChange={(e) => {
                            const newLinks = [...(item.links || [])]
                            newLinks[linkIndex] = { ...link, label: e.target.value }
                            onItemChange({ ...item, links: newLinks })
                          }}
                          placeholder={t('forms.team.linkLabel')}
                          className="w-32"
                        />
                        <Input
                          value={link.url}
                          onChange={(e) => {
                            const newLinks = [...(item.links || [])]
                            newLinks[linkIndex] = { ...link, url: e.target.value }
                            onItemChange({ ...item, links: newLinks })
                          }}
                          placeholder="https://..."
                          className="flex-1"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const newLinks = (item.links || []).filter((_, i) => i !== linkIndex)
                            onItemChange({ ...item, links: newLinks })
                          }}
                          className="text-muted-foreground hover:text-destructive px-2"
                        >
                          x
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => {
                        const newLinks = [...(item.links || []), { label: '', url: '' }]
                        onItemChange({ ...item, links: newLinks })
                      }}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      {t('forms.team.addLink')}
                    </button>
                  </div>
                </div>
              </div>
            )}
          />
        </TabsContent>

        {/* Partners Tab */}
        <TabsContent value="partners" className="mt-4">
          <RepeatableField<Partner>
            items={context.partners || []}
            onChange={(partners) => updateField('partners', partners)}
            createItem={() => ({
              name: '',
              logo: '',
              url: '',
              description: '',
            })}
            addLabel={t('forms.team.addPartner')}
            renderItem={(item, _index, onItemChange) => (
              <div className="space-y-3">
                {/* Row 1: Name, Logo */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.name')}</Label>
                    <Input
                      value={item.name}
                      onChange={(e) => onItemChange({ ...item, name: e.target.value })}
                      placeholder={t('forms.team.partnerNamePlaceholder')}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.partnerLogo')}</Label>
                    <ImagePickerField
                      value={item.logo || ''}
                      onChange={(logo) => onItemChange({ ...item, logo })}
                      folder="files/logos"
                      placeholder={t('forms.team.selectPartnerLogo')}
                    />
                  </div>
                </div>

                {/* Row 2: URL */}
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.team.website')}</Label>
                  <Input
                    value={item.url || ''}
                    onChange={(e) => onItemChange({ ...item, url: e.target.value })}
                    placeholder={t('forms.team.websitePlaceholder')}
                  />
                </div>

                {/* Row 3: Description */}
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.team.description')}</Label>
                  <Input
                    value={item.description || ''}
                    onChange={(e) => onItemChange({ ...item, description: e.target.value })}
                    placeholder={t('forms.team.descriptionPlaceholder')}
                  />
                </div>
              </div>
            )}
          />
        </TabsContent>

        {/* Funders Tab */}
        <TabsContent value="funders" className="mt-4">
          <RepeatableField<Funder>
            items={context.funders || []}
            onChange={(funders) => updateField('funders', funders)}
            createItem={() => ({
              name: '',
              logo: '',
              url: '',
            })}
            addLabel={t('forms.team.addFunder')}
            renderItem={(item, _index, onItemChange) => (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.name')}</Label>
                    <Input
                      value={item.name}
                      onChange={(e) => onItemChange({ ...item, name: e.target.value })}
                      placeholder={t('forms.team.funderNamePlaceholder')}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('forms.team.partnerLogo')}</Label>
                    <ImagePickerField
                      value={item.logo || ''}
                      onChange={(logo) => onItemChange({ ...item, logo })}
                      folder="files/logos"
                      placeholder={t('forms.team.selectPartnerLogo')}
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.team.website')}</Label>
                  <Input
                    value={item.url || ''}
                    onChange={(e) => onItemChange({ ...item, url: e.target.value })}
                    placeholder={t('forms.team.funderWebsitePlaceholder')}
                  />
                </div>
              </div>
            )}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default TeamForm
