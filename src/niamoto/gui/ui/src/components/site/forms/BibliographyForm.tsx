/**
 * BibliographyForm - Dedicated form for bibliography.html template
 *
 * Manages:
 * - Title and introduction
 * - References list (authors, year, title, journal, doi, url, type)
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
  title?: string
  introduction?: string
  references?: ReferenceItem[]
  [key: string]: unknown // Allow additional fields for compatibility
}

interface BibliographyFormProps {
  context: BibliographyPageContext
  onChange: (context: BibliographyPageContext) => void
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

export function BibliographyForm({ context, onChange }: BibliographyFormProps) {
  const { t } = useTranslation('site')

  const updateField = useCallback(
    <K extends keyof BibliographyPageContext>(field: K, value: BibliographyPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.bibliography.header')}</h3>

        <div className="space-y-2">
          <Label htmlFor="title">{t('forms.bibliography.pageTitle')}</Label>
          <Input
            id="title"
            value={context.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder={t('forms.bibliography.pageTitlePlaceholder')}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="introduction">{t('forms.bibliography.introduction')}</Label>
          <Textarea
            id="introduction"
            value={context.introduction || ''}
            onChange={(e) => updateField('introduction', e.target.value)}
            placeholder={t('forms.bibliography.introPlaceholder')}
            rows={3}
          />
        </div>
      </div>

      <Separator />

      {/* References Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('forms.bibliography.references')}</h3>
        <p className="text-sm text-muted-foreground">
          {t('forms.bibliography.referenceCount', { count: context.references?.length || 0 })}
        </p>

        <RepeatableField<ReferenceItem>
          items={context.references || []}
          onChange={(references) => updateField('references', references)}
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
