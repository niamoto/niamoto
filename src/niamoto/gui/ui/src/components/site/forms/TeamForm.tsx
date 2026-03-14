/**
 * TeamForm - Dedicated form for team.html template
 *
 * Manages:
 * - Title and introduction
 * - Team members (name, role, institution, photo, email, etc.)
 * - Partners (name, logo, url, description)
 * - Funders (name, logo, url)
 * - Supports externalizing team members to a JSON file for large teams
 */

import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Users, Building2, Wallet } from 'lucide-react'
import { RepeatableField } from './RepeatableField'
import { ImagePickerField } from './ImagePickerField'
import { MarkdownContentField } from './MarkdownContentField'
import { ExternalizableListField } from './ExternalizableListField'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import { useDataContent, useUpdateDataContent } from '@/hooks/useSiteConfig'

// Types for team.html context
interface SocialLink {
  label: string
  url: string
}

interface TeamMember {
  name: string
  role: string
  group?: string
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
  title?: LocalizedString
  introduction?: LocalizedString
  content_source?: string | null
  team?: TeamMember[]
  team_source?: string | null  // Path to external JSON file for team members
  partners?: Partner[]
  funders?: Funder[]
  [key: string]: unknown // Allow additional fields for compatibility
}

interface TeamFormProps {
  context: TeamPageContext
  onChange: (context: TeamPageContext) => void
  pageName: string
}

export function TeamForm({
  context,
  onChange,
  pageName,
}: TeamFormProps) {
  const { t } = useTranslation('site')

  // Check if using external file for team members
  const isExternalMode = !!context.team_source
  const externalFilePath = context.team_source || null

  // Fetch external data when in external mode
  const { data: externalData } = useDataContent(externalFilePath)
  const updateDataMutation = useUpdateDataContent()

  // Local state for team members (either from inline or external)
  const [localTeam, setLocalTeam] = useState<TeamMember[]>(context.team || [])

  // Sync local team with external data when it changes
  useEffect(() => {
    if (isExternalMode && externalData?.data) {
      setLocalTeam(externalData.data as TeamMember[])
    } else if (!isExternalMode) {
      setLocalTeam(context.team || [])
    }
  }, [isExternalMode, externalData?.data, context.team])

  const updateField = useCallback(
    <K extends keyof TeamPageContext>(field: K, value: TeamPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  // Handle team change (for both inline and external modes)
  const handleTeamChange = useCallback(
    async (team: TeamMember[]) => {
      setLocalTeam(team)

      if (isExternalMode && externalFilePath) {
        // Save to external file
        await updateDataMutation.mutateAsync({
          path: externalFilePath,
          data: team,
        })
      } else {
        // Save inline
        updateField('team', team)
      }
    },
    [isExternalMode, externalFilePath, updateDataMutation, updateField]
  )

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.team.header')}</h3>

        <LocalizedInput
          value={context.title}
          onChange={(val) => updateField('title', val)}
          placeholder={t('forms.team.pageTitlePlaceholder')}
          label={t('forms.team.pageTitle')}
        />

        <LocalizedInput
          value={context.introduction}
          onChange={(val) => updateField('introduction', val)}
          placeholder={t('forms.team.introPlaceholder')}
          label={t('forms.team.introduction')}
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
        <TabsContent value="team" className="mt-4 space-y-4">
          {/* Externalization controls */}
          <ExternalizableListField<TeamMember>
            pageName={pageName}
            listName="team"
            dataSource={context.team_source}
            onDataSourceChange={(source) => updateField('team_source', source)}
            inlineData={context.team || []}
            onInlineDataChange={(data) => updateField('team', data)}
          />

          <RepeatableField<TeamMember>
            items={localTeam}
            onChange={handleTeamChange}
            createItem={() => ({
              name: '',
              role: '',
              institution: '',
              email: '',
            })}
            addLabel={t('forms.team.addMember')}
            renderItem={(item, _index, onItemChange) => (
              <div className="space-y-3">
                {/* Row 1: Name, Role, Group */}
                <div className="grid grid-cols-[1fr_1fr_auto] gap-2">
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
                  <div className="space-y-1 w-40">
                    <Label className="text-xs">{t('forms.team.group')}</Label>
                    <Input
                      value={item.group || ''}
                      onChange={(e) => onItemChange({ ...item, group: e.target.value })}
                      placeholder={t('forms.team.groupPlaceholder')}
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
