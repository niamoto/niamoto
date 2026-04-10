import { useState, useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface KeyValueEntry {
  id: number
  key: string
  value: string
}

interface JsonKeyValueEditorProps {
  value: Record<string, string> | undefined
  onChange: (value: Record<string, string> | undefined) => void
  placeholder?: string
  keyPlaceholder?: string
  valuePlaceholder?: string
  suggestedKeys?: string[]
}

let nextId = 1

/**
 * Editor for JSON key-value objects like labels
 * Example: { "x_axis": "Mois", "y_axis": "Frequence (%)" }
 */
export function JsonKeyValueEditor({
  value,
  onChange,
  placeholder,
  keyPlaceholder,
  valuePlaceholder,
  suggestedKeys = []
}: JsonKeyValueEditorProps) {
  const { t } = useTranslation(['widgets'])

  const effectiveKeyPlaceholder = keyPlaceholder ?? t('recipe.key')
  const effectiveValuePlaceholder = valuePlaceholder ?? t('recipe.value')
  // Convert object to array with stable IDs
  const [entries, setEntries] = useState<KeyValueEntry[]>(() => {
    if (!value) return []
    return Object.entries(value).map(([key, val]) => ({
      id: nextId++,
      key,
      value: val,
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
      setEntries(Object.entries(value).map(([key, val]) => ({
        id: nextId++,
        key,
        value: val,
      })))
    }
  }, [entries, value])

  // Emit changes to parent
  const emitChange = useCallback((newEntries: KeyValueEntry[]) => {
    isEditingRef.current = true
    setEntries(newEntries)
    if (newEntries.length === 0) {
      onChange(undefined)
    } else {
      const obj: Record<string, string> = {}
      for (const entry of newEntries) {
        if (entry.key) {
          obj[entry.key] = entry.value
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

  const handleValueChange = useCallback((id: number, newVal: string) => {
    const newEntries = entries.map(e =>
      e.id === id ? { ...e, value: newVal } : e
    )
    emitChange(newEntries)
  }, [entries, emitChange])

  const handleAdd = useCallback(() => {
    // Find first unused suggested key, or create a generic one
    const usedKeys = entries.map(e => e.key)
    const nextKey = suggestedKeys.find(k => !usedKeys.includes(k)) || `key${entries.length + 1}`
    const newEntry: KeyValueEntry = {
      id: nextId++,
      key: nextKey,
      value: '',
    }
    emitChange([...entries, newEntry])
  }, [entries, suggestedKeys, emitChange])

  const handleDelete = useCallback((id: number) => {
    const newEntries = entries.filter(e => e.id !== id)
    emitChange(newEntries)
  }, [entries, emitChange])

  return (
    <div className="space-y-2 p-2 bg-background rounded border">
      {entries.length === 0 ? (
        <p className="text-xs text-muted-foreground text-center py-2">
          {placeholder || t('recipe.noValueConfigured')}
        </p>
      ) : (
        entries.map((entry) => (
          <div key={entry.id} className="flex gap-2 items-center">
            <Input
              className="h-7 w-28"
              placeholder={effectiveKeyPlaceholder}
              value={entry.key}
              onChange={(e) => handleKeyChange(entry.id, e.target.value)}
            />
            <span className="text-xs text-muted-foreground">:</span>
            <Input
              className="h-7 flex-1"
              placeholder={effectiveValuePlaceholder}
              value={entry.value}
              onChange={(e) => handleValueChange(entry.id, e.target.value)}
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
        {t('recipe.add')}
      </Button>
    </div>
  )
}
