import { useState, useEffect } from 'react'
import { Check } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface PropertySelectorProps {
  availableColumns: string[]
  selectedProperties: string[]
  excludeColumns?: string[]
  onSelectionChange: (properties: string[]) => void
}

export function PropertySelector({
  availableColumns,
  selectedProperties,
  excludeColumns = [],
  onSelectionChange,
}: PropertySelectorProps) {
  const [localSelection, setLocalSelection] = useState<string[]>(selectedProperties)

  useEffect(() => {
    setLocalSelection(selectedProperties)
  }, [selectedProperties])

  const toggleProperty = (property: string) => {
    const newSelection = localSelection.includes(property)
      ? localSelection.filter(p => p !== property)
      : [...localSelection, property]

    setLocalSelection(newSelection)
    onSelectionChange(newSelection)
  }

  const clearAll = () => {
    setLocalSelection([])
    onSelectionChange([])
  }

  const selectAll = () => {
    const allSelectable = availableColumns.filter(col => !excludeColumns.includes(col))
    setLocalSelection(allSelectable)
    onSelectionChange(allSelectable)
  }

  // Filter out excluded columns
  const selectableColumns = availableColumns.filter(col => !excludeColumns.includes(col))

  if (selectableColumns.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        No additional properties available
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          Select properties to import ({localSelection.length} selected)
        </span>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={selectAll}
            disabled={localSelection.length === selectableColumns.length}
          >
            Select All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAll}
            disabled={localSelection.length === 0}
          >
            Clear
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {selectableColumns.map((column) => {
          const isSelected = localSelection.includes(column)
          return (
            <Badge
              key={column}
              variant={isSelected ? "default" : "outline"}
              className={cn(
                "cursor-pointer transition-all",
                isSelected && "pr-1"
              )}
              onClick={() => toggleProperty(column)}
            >
              {column}
              {isSelected && (
                <Check className="ml-1 h-3 w-3" />
              )}
            </Badge>
          )
        })}
      </div>

      {localSelection.length > 0 && (
        <div className="mt-2 p-2 bg-muted rounded-md">
          <p className="text-xs text-muted-foreground mb-1">Selected properties:</p>
          <p className="text-sm font-mono">{localSelection.join(', ')}</p>
        </div>
      )}
    </div>
  )
}
