/**
 * GlossaryForm - Dedicated form for glossary.html template
 *
 * Manages:
 * - Title and introduction
 * - Terms list (term, definition, category, related)
 */

import { useCallback, useMemo } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { RepeatableField } from './RepeatableField'

// Types for glossary.html context
interface TermItem {
  term: string
  definition: string
  category?: string
  related?: string[] | string // Can be array or comma-separated string
}

export interface GlossaryPageContext {
  title?: string
  introduction?: string
  terms?: TermItem[]
  [key: string]: unknown
}

interface GlossaryFormProps {
  context: GlossaryPageContext
  onChange: (context: GlossaryPageContext) => void
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

export function GlossaryForm({ context, onChange }: GlossaryFormProps) {
  const updateField = useCallback(
    <K extends keyof GlossaryPageContext>(field: K, value: GlossaryPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  // Extract unique categories from existing terms
  const existingCategories = useMemo(() => {
    const categories = new Set<string>()
    context.terms?.forEach((t) => {
      if (t.category) categories.add(t.category)
    })
    return Array.from(categories)
  }, [context.terms])

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
        <h3 className="text-lg font-semibold">En-tete</h3>

        <div className="space-y-2">
          <Label htmlFor="title">Titre de la page</Label>
          <Input
            id="title"
            value={context.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="Glossaire"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="introduction">Introduction</Label>
          <Textarea
            id="introduction"
            value={context.introduction || ''}
            onChange={(e) => updateField('introduction', e.target.value)}
            placeholder="Definitions des termes ecologiques utilises dans Niamoto..."
            rows={3}
          />
        </div>
      </div>

      <Separator />

      {/* Terms Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Termes</h3>
            <p className="text-sm text-muted-foreground">
              {context.terms?.length || 0} terme(s) defini(s)
            </p>
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

        <RepeatableField<TermItem>
          items={context.terms || []}
          onChange={(terms) => updateField('terms', terms)}
          createItem={() => ({
            term: '',
            definition: '',
            category: '',
            related: [],
          })}
          addLabel="Ajouter un terme"
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              {/* Row 1: Term, Category */}
              <div className="grid grid-cols-[1fr_150px] gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">Terme</Label>
                  <Input
                    value={item.term}
                    onChange={(e) => onItemChange({ ...item, term: e.target.value })}
                    placeholder="Endemique"
                    className="font-medium"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Categorie</Label>
                  <Input
                    value={item.category || ''}
                    onChange={(e) => onItemChange({ ...item, category: e.target.value })}
                    placeholder="Ecologie"
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
                <Label className="text-xs">Definition</Label>
                <Textarea
                  value={item.definition}
                  onChange={(e) => onItemChange({ ...item, definition: e.target.value })}
                  placeholder="Espece presente uniquement dans une region geographique donnee..."
                  rows={3}
                />
              </div>

              {/* Row 3: Related terms */}
              <div className="space-y-1">
                <Label className="text-xs">Termes lies (separes par des virgules)</Label>
                <Input
                  value={parseRelated(item.related)}
                  onChange={(e) =>
                    onItemChange({ ...item, related: toRelatedArray(e.target.value) })
                  }
                  placeholder="Aire de repartition, Biodiversite, Conservation"
                />
                <p className="text-xs text-muted-foreground">
                  Termes associes pour la navigation croisee
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
