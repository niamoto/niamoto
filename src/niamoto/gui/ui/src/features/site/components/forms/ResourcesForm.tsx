/**
 * ResourcesForm - Dedicated form for resources.html template
 *
 * Manages:
 * - Title and introduction
 * - Resources list (title, description, type, url, size, format, license)
 * - Supports externalizing resources to a JSON file for large lists
 */

import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
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
import { renderLucideIcon } from './lucideIconRegistry'
import { FilePickerField } from './FilePickerField'
import { MarkdownContentField } from './MarkdownContentField'
import { ExternalizableListField } from './ExternalizableListField'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import {
  type DataContentResponse,
  useDataContent,
  useUpdateDataContent,
} from '@/shared/hooks/useSiteConfig'
import { siteConfigQueryKeys } from '@/shared/hooks/site-config/queryKeys'

// Types for resources.html context
interface ResourceItem {
  title: string
  description: string
  type: string
  url: string
  license?: string
}

export interface ResourcesPageContext {
  title?: LocalizedString
  introduction?: LocalizedString
  content_source?: string | null
  resources?: ResourceItem[]
  resources_source?: string | null  // Path to external JSON file
  [key: string]: unknown
}

interface ResourcesFormProps {
  context: ResourcesPageContext
  onChange: (context: ResourcesPageContext) => void
  pageName: string
}

const RESOURCE_TYPE_KEYS = [
  { value: 'dataset', icon: 'database' },
  { value: 'document', icon: 'file-text' },
  { value: 'tool', icon: 'settings' },
  { value: 'api', icon: 'zap' },
  { value: 'code', icon: 'files' },
  { value: 'image', icon: 'eye' },
  { value: 'other', icon: 'folder' },
]

const COMMON_LICENSES = ['CC-BY-4.0', 'CC-BY-SA-4.0', 'CC-BY-NC-4.0', 'CC0', 'MIT', 'GPL-3.0', 'Proprietary']

export function ResourcesForm({
  context,
  onChange,
  pageName,
}: ResourcesFormProps) {
  const { t } = useTranslation('site')
  const queryClient = useQueryClient()

  // Check if using external file for resources
  const isExternalMode = !!context.resources_source
  const externalFilePath = context.resources_source || null

  // Fetch external data when in external mode
  const { data: externalData } = useDataContent(externalFilePath)
  const updateDataMutation = useUpdateDataContent()

  const resources = isExternalMode
    ? ((externalData?.data as ResourceItem[] | undefined) ?? [])
    : (context.resources || [])

  const updateField = useCallback(
    <K extends keyof ResourcesPageContext>(field: K, value: ResourcesPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  // Handle resources change (for both inline and external modes)
  const handleResourcesChange = useCallback(
    async (resources: ResourceItem[]) => {
      if (isExternalMode && externalFilePath) {
        const queryKey = siteConfigQueryKeys.dataContent(externalFilePath)
        const previousData = queryClient.getQueryData<DataContentResponse>(queryKey)

        queryClient.setQueryData<DataContentResponse>(queryKey, {
          data: resources,
          path: externalFilePath,
          count: resources.length,
        })

        try {
          await updateDataMutation.mutateAsync({
            path: externalFilePath,
            data: resources,
          })
        } catch (error) {
          queryClient.setQueryData(queryKey, previousData)
          throw error
        }
      } else {
        updateField('resources', resources)
      }
    },
    [externalFilePath, isExternalMode, queryClient, updateDataMutation, updateField]
  )

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.resources.header')}</h3>

        <LocalizedInput
          value={context.title}
          onChange={(val) => updateField('title', val)}
          placeholder={t('forms.resources.pageTitlePlaceholder')}
          label={t('forms.resources.pageTitle')}
        />

        <LocalizedInput
          value={context.introduction}
          onChange={(val) => updateField('introduction', val)}
          placeholder={t('forms.resources.introPlaceholder')}
          label={t('forms.resources.introduction')}
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

      {/* Resources Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.resources.resources')}</h3>

        {/* Externalization controls */}
        <ExternalizableListField<ResourceItem>
          pageName={pageName}
          listName="resources"
          dataSource={context.resources_source}
          onDataSourceChange={(source) => updateField('resources_source', source)}
          inlineData={context.resources || []}
          onInlineDataChange={(data) => updateField('resources', data)}
          description={t('forms.resources.resourceCount', { count: resources.length })}
        />

        <RepeatableField<ResourceItem>
          items={resources}
          onChange={handleResourcesChange}
          createItem={() => ({
            title: '',
            description: '',
            type: 'dataset',
            url: '',
            license: 'CC-BY-4.0',
          })}
          addLabel={t('forms.resources.addResource')}
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              {/* Row 1: Title, Type */}
              <div className="grid grid-cols-[1fr_150px] gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.resources.resourceTitle')}</Label>
                  <Input
                    value={item.title}
                    onChange={(e) => onItemChange({ ...item, title: e.target.value })}
                    placeholder={t('forms.resources.resourceTitlePlaceholder')}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.resources.resourceType')}</Label>
                  <Select
                    value={item.type}
                    onValueChange={(value) => onItemChange({ ...item, type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RESOURCE_TYPE_KEYS.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          <span className="flex items-center gap-2">
                            {renderLucideIcon(type.icon, 'h-4 w-4')}
                            <span>{t(`forms.resources.types.${type.value}`)}</span>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 2: Description */}
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.resources.resourceDescription')}</Label>
                <Textarea
                  value={item.description}
                  onChange={(e) => onItemChange({ ...item, description: e.target.value })}
                  placeholder={t('forms.resources.resourceDescPlaceholder')}
                  rows={2}
                />
              </div>

              {/* Row 3: File/URL */}
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.resources.fileOrUrl')}</Label>
                <FilePickerField
                  value={item.url}
                  onChange={(url) => onItemChange({ ...item, url })}
                  folder="files/data"
                  placeholder={t('forms.resources.fileOrUrlPlaceholder')}
                />
              </div>

              {/* Row 4: License */}
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.resources.license')}</Label>
                <Select
                  value={item.license || ''}
                  onValueChange={(value) => onItemChange({ ...item, license: value })}
                >
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder={t('forms.resources.licensePlaceholder')} />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_LICENSES.map((license) => (
                      <SelectItem key={license} value={license}>
                        {license}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        />
      </div>
    </div>
  )
}

export default ResourcesForm
