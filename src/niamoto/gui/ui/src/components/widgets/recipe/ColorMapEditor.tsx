import { useState, useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface ColorEntry {
  id: number
  key: string
  color: string
}

interface ColorMapEditorProps {
  value: Record<string, string> | undefined
  onChange: (value: Record<string, string> | undefined) => void
  placeholder?: string
}

let nextId = 1

/**
 * Editor for color_discrete_map - allows users to map keys to colors
 * Example: { "fleur": "#FFB74D", "fruit": "#81C784" }
 */
export function ColorMapEditor({ value, onChange, placeholder }: ColorMapEditorProps) {
  const { t } = useTranslation('widgets')

  // Convert object to array with stable IDs
  const [entries, setEntries] = useState<ColorEntry[]>(() => {
    if (!value) return []
    return Object.entries(value).map(([key, color]) => ({
      id: nextId++,
      key,
      color,
    }))
  })

  // Track if we're editing to avoid sync issues
  const isEditingRef = useRef(false)

  // Sync from external value changes (but not during editing)
  useEffect(() => {
    if (isEditingRef.current) return
    if (!value) {
      if (entries.length > 0) setEntries([])
      return
    }
    const valueKeys = Object.keys(value).sort().join(',')
    const entryKeys = entries.map(e => e.key).sort().join(',')
    if (valueKeys !== entryKeys) {
      setEntries(Object.entries(value).map(([key, color]) => ({
        id: nextId++,
        key,
        color,
      })))
    }
  }, [value])

  // Emit changes to parent
  const emitChange = useCallback((newEntries: ColorEntry[]) => {
    isEditingRef.current = true
    setEntries(newEntries)
    if (newEntries.length === 0) {
      onChange(undefined)
    } else {
      const obj: Record<string, string> = {}
      for (const entry of newEntries) {
        if (entry.key) {
          obj[entry.key] = entry.color
        }
      }
      onChange(Object.keys(obj).length > 0 ? obj : undefined)
    }
    // Reset editing flag after a short delay
    setTimeout(() => { isEditingRef.current = false }, 100)
  }, [onChange])

  const handleKeyChange = useCallback((id: number, newKey: string) => {
    const newEntries = entries.map(e =>
      e.id === id ? { ...e, key: newKey } : e
    )
    emitChange(newEntries)
  }, [entries, emitChange])

  const handleColorChange = useCallback((id: number, color: string) => {
    const newEntries = entries.map(e =>
      e.id === id ? { ...e, color } : e
    )
    emitChange(newEntries)
  }, [entries, emitChange])

  const handleAdd = useCallback(() => {
    const newEntry: ColorEntry = {
      id: nextId++,
      key: `serie${entries.length + 1}`,
      color: '#1fb99d',
    }
    emitChange([...entries, newEntry])
  }, [entries, emitChange])

  const handleDelete = useCallback((id: number) => {
    const newEntries = entries.filter(e => e.id !== id)
    emitChange(newEntries)
  }, [entries, emitChange])

  return (
    <div className="space-y-2 p-2 bg-background rounded border">
      {entries.length === 0 ? (
        <p className="text-xs text-muted-foreground text-center py-2">
          {placeholder || t('recipe.noColorConfigured')}
        </p>
      ) : (
        entries.map((entry) => (
          <div key={entry.id} className="flex gap-2 items-center">
            <Input
              className="h-7 flex-1"
              placeholder={t('recipe.keyPlaceholder')}
              value={entry.key}
              onChange={(e) => handleKeyChange(entry.id, e.target.value)}
            />
            <span className="text-xs text-muted-foreground">→</span>
            <Input
              type="color"
              className="h-7 w-10 p-1 cursor-pointer"
              value={entry.color}
              onChange={(e) => handleColorChange(entry.id, e.target.value)}
            />
            <Input
              className="h-7 w-20 font-mono text-xs"
              value={entry.color}
              onChange={(e) => handleColorChange(entry.id, e.target.value)}
              placeholder="#RRGGBB"
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-destructive hover:text-destructive"
              onClick={() => handleDelete(entry.id)}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        ))
      )}
      <Button
        variant="outline"
        size="sm"
        className="h-7 text-xs w-full"
        onClick={handleAdd}
      >
        <Plus className="h-3 w-3 mr-1" />
        {t('recipe.addColorButton')}
      </Button>
    </div>
  )
}
