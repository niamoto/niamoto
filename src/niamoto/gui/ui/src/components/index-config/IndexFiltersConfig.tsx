/**
 * IndexFiltersConfig - Filter configuration component
 *
 * Allows adding/editing/removing filters for the index generator.
 * Each filter specifies a field, operator, and allowed values.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Trash2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import type { IndexFilterConfig } from './useIndexConfig'

interface IndexFiltersConfigProps {
  filters: IndexFilterConfig[]
  onAdd: (filter: IndexFilterConfig) => void
  onUpdate: (index: number, filter: IndexFilterConfig) => void
  onRemove: (index: number) => void
}

export function IndexFiltersConfig({
  filters,
  onAdd,
  onUpdate,
  onRemove,
}: IndexFiltersConfigProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [newValueInput, setNewValueInput] = useState<Record<number, string>>({})

  // Add a new empty filter
  const handleAddFilter = () => {
    onAdd({
      field: '',
      operator: 'in',
      values: [],
    })
  }

  // Add value to a filter
  const handleAddValue = (index: number) => {
    const value = newValueInput[index]?.trim()
    if (!value) return

    const filter = filters[index]
    onUpdate(index, {
      ...filter,
      values: [...filter.values, value],
    })
    setNewValueInput(prev => ({ ...prev, [index]: '' }))
  }

  // Remove value from a filter
  const handleRemoveValue = (filterIndex: number, valueIndex: number) => {
    const filter = filters[filterIndex]
    onUpdate(filterIndex, {
      ...filter,
      values: filter.values.filter((_, i) => i !== valueIndex),
    })
  }

  // Update field path
  const handleUpdateField = (index: number, field: string) => {
    const filter = filters[index]
    onUpdate(index, { ...filter, field })
  }

  // Update operator
  const handleUpdateOperator = (index: number, operator: string) => {
    const filter = filters[index]
    onUpdate(index, { ...filter, operator: operator as 'in' | 'not_in' | 'equals' })
  }

  if (filters.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-sm text-muted-foreground mb-4">
          {t('indexConfig.filters.noFilters')}
        </p>
        <Button variant="outline" size="sm" onClick={handleAddFilter}>
          <Plus className="mr-2 h-4 w-4" />
          {t('indexConfig.filters.addFilter')}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {filters.map((filter, index) => (
        <div
          key={index}
          className="relative p-4 rounded-lg border bg-muted/30"
        >
          {/* Delete button */}
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-2 right-2 h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={() => onRemove(index)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>

          <div className="space-y-4 pr-10">
            {/* Field path */}
            <div className="space-y-2">
              <Label>{t('indexConfig.filters.fieldPath')}</Label>
              <Input
                value={filter.field}
                onChange={(e) => handleUpdateField(index, e.target.value)}
                placeholder="general_info.rank.value"
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                {t('indexConfig.filters.pathHint')}
              </p>
            </div>

            {/* Operator */}
            <div className="space-y-2">
              <Label>{t('indexConfig.filters.operator')}</Label>
              <Select
                value={filter.operator}
                onValueChange={(value) => handleUpdateOperator(index, value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="in">{t('indexConfig.filters.operatorIn')}</SelectItem>
                  <SelectItem value="not_in">{t('indexConfig.filters.operatorNotIn')}</SelectItem>
                  <SelectItem value="equals">{t('indexConfig.filters.operatorEquals')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Values */}
            <div className="space-y-2">
              <Label>{t('indexConfig.filters.allowedValues')}</Label>
              <div className="flex flex-wrap gap-2 min-h-[32px]">
                {filter.values.map((value, valueIndex) => (
                  <Badge
                    key={valueIndex}
                    variant="secondary"
                    className="pl-2 pr-1 py-1 flex items-center gap-1"
                  >
                    <span className="font-mono text-xs">{String(value)}</span>
                    <button
                      type="button"
                      className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20"
                      onClick={() => handleRemoveValue(index, valueIndex)}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>

              {/* Add value input */}
              <div className="flex gap-2">
                <Input
                  value={newValueInput[index] || ''}
                  onChange={(e) => setNewValueInput(prev => ({ ...prev, [index]: e.target.value }))}
                  placeholder={t('indexConfig.filters.addValue')}
                  className="flex-1"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddValue(index)
                    }
                  }}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleAddValue(index)}
                  disabled={!newValueInput[index]?.trim()}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      ))}

      <Button variant="outline" size="sm" onClick={handleAddFilter}>
        <Plus className="mr-2 h-4 w-4" />
        {t('indexConfig.filters.addFilter')}
      </Button>
    </div>
  )
}
