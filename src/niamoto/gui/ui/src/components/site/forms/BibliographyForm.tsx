/**
 * BibliographyForm - Dedicated form for bibliography.html template
 *
 * Manages:
 * - Title and introduction (with optional markdown content)
 * - References list (authors, year, title, journal, doi, url, type)
 * - Supports externalizing references to a JSON file for large lists
 */

import { useCallback, useEffect, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FileUp, FileDown } from 'lucide-react'
import { toast } from 'sonner'
import { RepeatableField } from './RepeatableField'
import { MarkdownContentField } from './MarkdownContentField'
import { ExternalizableListField } from './ExternalizableListField'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import {
  useDataContent,
  useUpdateDataContent,
  useImportBibtex,
  exportBibtex,
} from '@/features/site/hooks/useSiteConfig'

// Types for bibliography.html context
interface ReferenceItem {
  authors: string
  year: string
  title: string
  journal?: string
  volume?: string
  pages?: string
  doi?: string
  url?: string
  type: string
}

export interface BibliographyPageContext {
  title?: LocalizedString
  introduction?: LocalizedString
  content_source?: string | null
  references?: ReferenceItem[]
  references_source?: string | null  // Path to external JSON file
  [key: string]: unknown // Allow additional fields for compatibility
}

interface BibliographyFormProps {
  context: BibliographyPageContext
  onChange: (context: BibliographyPageContext) => void
  pageName: string
}

const REFERENCE_TYPE_KEYS = [
  'article',
  'book',
  'chapter',
  'thesis',
  'report',
  'conference',
  'other',
] as const

export function BibliographyForm({
  context,
  onChange,
  pageName,
}: BibliographyFormProps) {
  const { t } = useTranslation('site')

  // Check if using external file for references
  const isExternalMode = !!context.references_source
  const externalFilePath = context.references_source || null

  // Fetch external data when in external mode
  const { data: externalData } = useDataContent(externalFilePath)
  const updateDataMutation = useUpdateDataContent()
  const importBibtexMutation = useImportBibtex()

  // File input ref for BibTeX import
  const bibtexInputRef = useRef<HTMLInputElement>(null)

  // Local state for references (either from inline or external)
  const [localReferences, setLocalReferences] = useState<ReferenceItem[]>(
    context.references || []
  )

  // Sync local references with external data when it changes
  useEffect(() => {
    if (isExternalMode && externalData?.data) {
      setLocalReferences(externalData.data as ReferenceItem[])
    } else if (!isExternalMode) {
      setLocalReferences(context.references || [])
    }
  }, [isExternalMode, externalData?.data, context.references])

  const updateField = useCallback(
    <K extends keyof BibliographyPageContext>(field: K, value: BibliographyPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  // Handle references change (for both inline and external modes)
  const handleReferencesChange = useCallback(
    async (references: ReferenceItem[]) => {
      setLocalReferences(references)

      if (isExternalMode && externalFilePath) {
        // Save to external file
        await updateDataMutation.mutateAsync({
          path: externalFilePath,
          data: references,
        })
      } else {
        // Save inline
        updateField('references', references)
      }
    },
    [isExternalMode, externalFilePath, updateDataMutation, updateField]
  )

  // Handle BibTeX import
  const handleBibtexImport = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (!file) return

      try {
        const result = await importBibtexMutation.mutateAsync(file)

        if (result.success && result.data.length > 0) {
          // Merge with existing references
          const newReferences = [...localReferences, ...(result.data as ReferenceItem[])]
          await handleReferencesChange(newReferences)

          toast.success(t('forms.common.importBibtexSuccess'), {
            description: t('forms.common.referencesImported', { count: result.count }),
          })

          if (result.errors.length > 0) {
            toast.warning(t('forms.common.importWarnings', { count: result.errors.length }), {
              description: result.errors.slice(0, 3).join('\n'),
            })
          }
        } else {
          toast.error(t('forms.common.importBibtexError'), {
            description: result.errors[0] || 'No references found',
          })
        }
      } catch (error) {
        toast.error(t('forms.common.importBibtexError'), {
          description: String(error),
        })
      }

      // Reset input
      event.target.value = ''
    },
    [importBibtexMutation, localReferences, handleReferencesChange, t]
  )

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.bibliography.header')}</h3>

        <LocalizedInput
          value={context.title}
          onChange={(val) => updateField('title', val)}
          placeholder={t('forms.bibliography.pageTitlePlaceholder')}
          label={t('forms.bibliography.pageTitle')}
        />

        <LocalizedInput
          value={context.introduction}
          onChange={(val) => updateField('introduction', val)}
          placeholder={t('forms.bibliography.introPlaceholder')}
          label={t('forms.bibliography.introduction')}
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

      {/* References Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.bibliography.references')}</h3>

        {/* Externalization controls */}
        <ExternalizableListField<ReferenceItem>
          pageName={pageName}
          listName="references"
          dataSource={context.references_source}
          onDataSourceChange={(source) => updateField('references_source', source)}
          inlineData={context.references || []}
          onInlineDataChange={(data) => updateField('references', data)}
          description={t('forms.bibliography.referenceCount', { count: localReferences.length })}
        />

        {/* BibTeX Import / Export */}
        <div className="flex items-center gap-2">
          <input
            ref={bibtexInputRef}
            type="file"
            accept=".bib"
            onChange={handleBibtexImport}
            className="hidden"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => bibtexInputRef.current?.click()}
            disabled={importBibtexMutation.isPending}
          >
            <FileUp className="h-4 w-4 mr-2" />
            {t('forms.common.importBibtex')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                await exportBibtex(localReferences as unknown as Record<string, unknown>[])
                toast.success(t('forms.common.exportBibtexSuccess'))
              } catch (error) {
                toast.error(t('forms.common.exportBibtexError'), {
                  description: String(error),
                })
              }
            }}
            disabled={localReferences.length === 0}
          >
            <FileDown className="h-4 w-4 mr-2" />
            {t('forms.common.exportBibtex')}
          </Button>
          <span className="text-xs text-muted-foreground">
            {t('forms.bibliography.referenceCount', { count: localReferences.length })}
          </span>
        </div>

        <RepeatableField<ReferenceItem>
          items={localReferences}
          onChange={handleReferencesChange}
          createItem={() => ({
            authors: '',
            year: new Date().getFullYear().toString(),
            title: '',
            journal: '',
            doi: '',
            url: '',
            type: 'article',
          })}
          addLabel={t('forms.bibliography.addReference')}
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              {/* Row 1: Authors, Year, Type */}
              <div className="grid grid-cols-[1fr_100px_150px] gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.bibliography.authors')}</Label>
                  <Input
                    value={item.authors}
                    onChange={(e) => onItemChange({ ...item, authors: e.target.value })}
                    placeholder={t('forms.bibliography.authorsPlaceholder')}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.bibliography.year')}</Label>
                  <Input
                    value={item.year}
                    onChange={(e) => onItemChange({ ...item, year: e.target.value })}
                    placeholder={t('forms.bibliography.yearPlaceholder')}
                    maxLength={4}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.bibliography.refType')}</Label>
                  <Select
                    value={item.type}
                    onValueChange={(value) => onItemChange({ ...item, type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {REFERENCE_TYPE_KEYS.map((typeKey) => (
                        <SelectItem key={typeKey} value={typeKey}>
                          {t(`forms.bibliography.refTypes.${typeKey}`)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 2: Title */}
              <div className="space-y-1">
                <Label className="text-xs">{t('forms.bibliography.title')}</Label>
                <Input
                  value={item.title}
                  onChange={(e) => onItemChange({ ...item, title: e.target.value })}
                  placeholder={t('forms.bibliography.titlePlaceholder')}
                />
              </div>

              {/* Row 3: Journal, Volume, Pages */}
              <div className="grid grid-cols-[1fr_100px_100px] gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.bibliography.journal')}</Label>
                  <Input
                    value={item.journal || ''}
                    onChange={(e) => onItemChange({ ...item, journal: e.target.value })}
                    placeholder={t('forms.bibliography.journalPlaceholder')}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.bibliography.volume')}</Label>
                  <Input
                    value={item.volume || ''}
                    onChange={(e) => onItemChange({ ...item, volume: e.target.value })}
                    placeholder={t('forms.bibliography.volumePlaceholder')}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.bibliography.pages')}</Label>
                  <Input
                    value={item.pages || ''}
                    onChange={(e) => onItemChange({ ...item, pages: e.target.value })}
                    placeholder={t('forms.bibliography.pagesPlaceholder')}
                  />
                </div>
              </div>

              {/* Row 4: DOI, URL */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.bibliography.doi')}</Label>
                  <Input
                    value={item.doi || ''}
                    onChange={(e) => onItemChange({ ...item, doi: e.target.value })}
                    placeholder={t('forms.bibliography.doiPlaceholder')}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('forms.bibliography.url')}</Label>
                  <Input
                    value={item.url || ''}
                    onChange={(e) => onItemChange({ ...item, url: e.target.value })}
                    placeholder={t('forms.bibliography.urlPlaceholder')}
                  />
                </div>
              </div>
            </div>
          )}
        />
      </div>
    </div>
  )
}

export default BibliographyForm
