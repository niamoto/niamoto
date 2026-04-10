/**
 * GlossaryForm - Dedicated form for glossary.html template
 *
 * Manages:
 * - Title and introduction
 * - Terms list (term, definition, category, related)
 * - Supports externalizing terms to a JSON file for large glossaries
 */

import { useCallback, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { RepeatableField } from './RepeatableField'
import { MarkdownContentField } from './MarkdownContentField'
import { ExternalizableListField } from './ExternalizableListField'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import {
  type DataContentResponse,
  useDataContent,
  useUpdateDataContent,
} from '@/shared/hooks/useSiteConfig'
import { siteConfigQueryKeys } from '@/shared/hooks/site-config/queryKeys'

// Types for glossary.html context
interface TermItem {
  term: string
  definition: string
  category?: string
  related?: string[] | string // Can be array or comma-separated string
}

export interface GlossaryPageContext {
  title?: LocalizedString
  introduction?: LocalizedString
  content_source?: string | null
  terms?: TermItem[]
  terms_source?: string | null  // Path to external JSON file for terms
  [key: string]: unknown
}

interface GlossaryFormProps {
  context: GlossaryPageContext
  onChange: (context: GlossaryPageContext) => void
  pageName: string
}

// Common categories for ecological glossary
const SUGGESTED_CATEGORIES = [
  'Ecologie',
  'Botanique',
  'Methodologie',
  'Donnees',
  'Geographie',
  'Taxonomie',
  'Conservation',
]

export function GlossaryForm({
  context,
  onChange,
  pageName,
}: GlossaryFormProps) {
  const { t } = useTranslation('site')
  const queryClient = useQueryClient()

  // Check if using external file for terms
  const isExternalMode = !!context.terms_source
  const externalFilePath = context.terms_source || null

  // Fetch external data when in external mode
  const { data: externalData } = useDataContent(externalFilePath)
  const updateDataMutation = useUpdateDataContent()

  const terms = useMemo(
    () =>
      isExternalMode
        ? ((externalData?.data as TermItem[] | undefined) ?? [])
        : (context.terms ?? []),
    [context.terms, externalData?.data, isExternalMode]
  )

  const updateField = useCallback(
    <K extends keyof GlossaryPageContext>(field: K, value: GlossaryPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  // Handle terms change (for both inline and external modes)
  const handleTermsChange = useCallback(
    async (terms: TermItem[]) => {
      if (isExternalMode && externalFilePath) {
        const queryKey = siteConfigQueryKeys.dataContent(externalFilePath)
        const previousData = queryClient.getQueryData<DataContentResponse>(queryKey)

        queryClient.setQueryData<DataContentResponse>(queryKey, {
          data: terms,
          path: externalFilePath,
          count: terms.length,
        })

        try {
          await updateDataMutation.mutateAsync({
            path: externalFilePath,
            data: terms,
          })
        } catch (error) {
          queryClient.setQueryData(queryKey, previousData)
          throw error
        }
      } else {
        updateField('terms', terms)
      }
    },
    [externalFilePath, isExternalMode, queryClient, updateDataMutation, updateField]
  )

  // Extract unique categories from existing terms
  const existingCategories = useMemo(() => {
    const categories = new Set<string>()
    terms.forEach((term) => {
      if (term.category) categories.add(term.category)
    })
    return Array.from(categories)
  }, [terms])

  // Combine suggested and existing categories
  const allCategories = useMemo(() => {
    const combined = new Set([...SUGGESTED_CATEGORIES, ...existingCategories])
    return Array.from(combined).sort()
  }, [existingCategories])

  // Parse related terms (handle both array and string)
  const parseRelated = (related: string[] | string | undefined): string => {
    if (!related) return ''
    if (Array.isArray(related)) return related.join(', ')
    return related
  }

  // Convert string back to array
  const toRelatedArray = (str: string): string[] => {
    return str
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.glossary.header')}</h3>

        <LocalizedInput
          value={context.title}
          onChange={(val) => updateField('title', val)}
          placeholder={t('forms.glossary.pageTitlePlaceholder')}
          label={t('forms.glossary.pageTitle')}
        />

        <LocalizedInput
          value={context.introduction}
          onChange={(val) => updateField('introduction', val)}
          placeholder={t('forms.glossary.introPlaceholder')}
          label={t('forms.glossary.introduction')}
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

      {/* Terms Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">{t('forms.glossary.terms')}</h3>
          </div>
          {existingCategories.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {existingCategories.map((cat) => (
                <Badge key={cat} variant="secondary" className="text-xs">
                  {cat}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Externalization controls */}
        <ExternalizableListField<TermItem>
          pageName={pageName}
          listName="terms"
          dataSource={context.terms_source}
          onDataSourceChange={(source) => updateField('terms_source', source)}
          inlineData={context.terms || []}
          onInlineDataChange={(data) => updateField('terms', data)}
          description={t('forms.glossary.termsDefined', { count: terms.length })}
        />

        <RepeatableField<TermItem>
          items={terms}
          onChange={handleTermsChange}
          createItem={() => ({
            term: '',
            definition: '',
            category: '',
            related: [],
          })}
          addLabel={t('forms.glossary.addTerm')}
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              {/* Row 1: Term, Category */}
              <div className="grid grid-cols-[1fr_150px] gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.glossary.term')}</Label>
                  <Input
                    value={item.term}
                    onChange={(e) => onItemChange({ ...item, term: e.target.value })}
                    placeholder={t('forms.glossary.termPlaceholder')}
                    className="font-medium"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.glossary.category')}</Label>
                  <Input
                    value={item.category || ''}
                    onChange={(e) => onItemChange({ ...item, category: e.target.value })}
                    placeholder={t('forms.glossary.categoryPlaceholder')}
                    list="categories-list"
                  />
                  <datalist id="categories-list">
                    {allCategories.map((cat) => (
                      <option key={cat} value={cat} />
                    ))}
                  </datalist>
                </div>
              </div>

              {/* Row 2: Definition */}
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.glossary.definition')}</Label>
                <Textarea
                  value={item.definition}
                  onChange={(e) => onItemChange({ ...item, definition: e.target.value })}
                  placeholder={t('forms.glossary.definitionPlaceholder')}
                  rows={3}
                />
              </div>

              {/* Row 3: Related terms */}
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.glossary.relatedTerms')}</Label>
                <Input
                  value={parseRelated(item.related)}
                  onChange={(e) =>
                    onItemChange({ ...item, related: toRelatedArray(e.target.value) })
                  }
                  placeholder={t('forms.glossary.relatedTermsPlaceholder')}
                />
                <p className="text-xs text-muted-foreground">
                  {t('forms.glossary.relatedTermsHint')}
                </p>
              </div>
            </div>
          )}
        />
      </div>
    </div>
  )
}

export default GlossaryForm
