/**
 * RepeatableField - Generic component for repeatable form fields
 *
 * Features:
 * - Add/remove items
 * - Drag to reorder (optional)
 * - Customizable item renderer
 */

import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Plus, Trash2, GripVertical } from 'lucide-react'
import { cn } from '@/lib/utils'

interface RepeatableFieldProps<T> {
  items: T[]
  onChange: (items: T[]) => void
  renderItem: (item: T, index: number, onChange: (value: T) => void) => React.ReactNode
  createItem: () => T
  label?: string
  addLabel?: string
  maxItems?: number
  minItems?: number
  className?: string
}

export function RepeatableField<T>({
  items,
  onChange,
  renderItem,
  createItem,
  label,
  addLabel,
  maxItems,
  minItems = 0,
  className,
}: RepeatableFieldProps<T>) {
  const { t } = useTranslation('common')
  const resolvedAddLabel = addLabel ?? t('actions.add')
  const handleAdd = useCallback(() => {
    if (maxItems && items.length >= maxItems) return
    onChange([...items, createItem()])
  }, [items, onChange, createItem, maxItems])

  const handleRemove = useCallback(
    (index: number) => {
      if (items.length <= minItems) return
      const newItems = [...items]
      newItems.splice(index, 1)
      onChange(newItems)
    },
    [items, onChange, minItems]
  )

  const handleItemChange = useCallback(
    (index: number, value: T) => {
      const newItems = [...items]
      newItems[index] = value
      onChange(newItems)
    },
    [items, onChange]
  )

  const handleMoveUp = useCallback(
    (index: number) => {
      if (index === 0) return
      const newItems = [...items]
      ;[newItems[index - 1], newItems[index]] = [newItems[index], newItems[index - 1]]
      onChange(newItems)
    },
    [items, onChange]
  )

  const handleMoveDown = useCallback(
    (index: number) => {
      if (index === items.length - 1) return
      const newItems = [...items]
      ;[newItems[index], newItems[index + 1]] = [newItems[index + 1], newItems[index]]
      onChange(newItems)
    },
    [items, onChange]
  )

  return (
    <div className={cn('space-y-3', className)}>
      {label && <label className="text-sm font-medium">{label}</label>}

      {items.length === 0 ? (
        <div className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">
          {t('empty.noItems')}. {t('empty.clickToAdd', { button: resolvedAddLabel })}
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item, index) => (
            <Card key={index} className="relative p-3">
              <div className="flex gap-2">
                {/* Drag handle and position controls */}
                <div className="flex flex-col items-center gap-1 pt-1">
                  <GripVertical className="h-4 w-4 text-muted-foreground" />
                  <div className="flex flex-col gap-0.5">
                    <button
                      type="button"
                      onClick={() => handleMoveUp(index)}
                      disabled={index === 0}
                      className="rounded p-0.5 text-xs text-muted-foreground hover:bg-muted disabled:opacity-30"
                    >
                      ▲
                    </button>
                    <button
                      type="button"
                      onClick={() => handleMoveDown(index)}
                      disabled={index === items.length - 1}
                      className="rounded p-0.5 text-xs text-muted-foreground hover:bg-muted disabled:opacity-30"
                    >
                      ▼
                    </button>
                  </div>
                </div>

                {/* Item content */}
                <div className="flex-1">
                  {renderItem(item, index, (value) => handleItemChange(index, value))}
                </div>

                {/* Remove button */}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemove(index)}
                  disabled={items.length <= minItems}
                  className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAdd}
        disabled={maxItems !== undefined && items.length >= maxItems}
        className="w-full"
      >
        <Plus className="mr-2 h-4 w-4" />
        {resolvedAddLabel}
      </Button>
    </div>
  )
}

export default RepeatableField
