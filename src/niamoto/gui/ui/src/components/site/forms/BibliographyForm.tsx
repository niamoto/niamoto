/**
 * BibliographyForm - Dedicated form for bibliography.html template
 *
 * Manages:
 * - Title and introduction
 * - References list (authors, year, title, journal, doi, url, type)
 */

import { useCallback } from 'react'
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

const REFERENCE_TYPES = [
  { value: 'article', label: 'Article scientifique' },
  { value: 'book', label: 'Livre' },
  { value: 'chapter', label: 'Chapitre de livre' },
  { value: 'thesis', label: 'These' },
  { value: 'report', label: 'Rapport' },
  { value: 'conference', label: 'Conference' },
  { value: 'other', label: 'Autre' },
]

export function BibliographyForm({ context, onChange }: BibliographyFormProps) {
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
        <h3 className="text-lg font-semibold">En-tete</h3>

        <div className="space-y-2">
          <Label htmlFor="title">Titre de la page</Label>
          <Input
            id="title"
            value={context.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="References bibliographiques"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="introduction">Introduction</Label>
          <Textarea
            id="introduction"
            value={context.introduction || ''}
            onChange={(e) => updateField('introduction', e.target.value)}
            placeholder="Liste des publications scientifiques..."
            rows={3}
          />
        </div>
      </div>

      <Separator />

      {/* References Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">References</h3>
        <p className="text-sm text-muted-foreground">
          {context.references?.length || 0} reference(s)
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
          addLabel="Ajouter une reference"
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              {/* Row 1: Authors, Year, Type */}
              <div className="grid grid-cols-[1fr_100px_150px] gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">Auteurs</Label>
                  <Input
                    value={item.authors}
                    onChange={(e) => onItemChange({ ...item, authors: e.target.value })}
                    placeholder="Smith, J. & Johnson, M."
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Annee</Label>
                  <Input
                    value={item.year}
                    onChange={(e) => onItemChange({ ...item, year: e.target.value })}
                    placeholder="2023"
                    maxLength={4}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Type</Label>
                  <Select
                    value={item.type}
                    onValueChange={(value) => onItemChange({ ...item, type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {REFERENCE_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 2: Title */}
              <div className="space-y-1">
                <Label className="text-xs">Titre</Label>
                <Input
                  value={item.title}
                  onChange={(e) => onItemChange({ ...item, title: e.target.value })}
                  placeholder="Titre de la publication"
                />
              </div>

              {/* Row 3: Journal, Volume, Pages */}
              <div className="grid grid-cols-[1fr_100px_100px] gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">Journal / Editeur</Label>
                  <Input
                    value={item.journal || ''}
                    onChange={(e) => onItemChange({ ...item, journal: e.target.value })}
                    placeholder="Journal of Ecology"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Volume</Label>
                  <Input
                    value={item.volume || ''}
                    onChange={(e) => onItemChange({ ...item, volume: e.target.value })}
                    placeholder="26(5)"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Pages</Label>
                  <Input
                    value={item.pages || ''}
                    onChange={(e) => onItemChange({ ...item, pages: e.target.value })}
                    placeholder="234-245"
                  />
                </div>
              </div>

              {/* Row 4: DOI, URL */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">DOI</Label>
                  <Input
                    value={item.doi || ''}
                    onChange={(e) => onItemChange({ ...item, doi: e.target.value })}
                    placeholder="10.1111/ele.13234"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">URL</Label>
                  <Input
                    value={item.url || ''}
                    onChange={(e) => onItemChange({ ...item, url: e.target.value })}
                    placeholder="https://..."
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
