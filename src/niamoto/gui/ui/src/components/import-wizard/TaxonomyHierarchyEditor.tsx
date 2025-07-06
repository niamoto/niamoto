import { useState } from 'react'
import { DragDropContext, Droppable, Draggable, type DropResult } from '@hello-pangea/dnd'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { GripVertical, Plus, X, AlertCircle, Check } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { cn } from '@/lib/utils'

interface TaxonomyLevel {
  name: string
  column?: string
}

interface TaxonomyHierarchyEditorProps {
  ranks?: string[]
  fileColumns?: string[]
  fieldMappings?: Record<string, string>
  onChange: (config: { ranks: string[], mappings: Record<string, string> }) => void
}

const DEFAULT_RANKS = ['family', 'genus', 'species', 'infra']

export function TaxonomyHierarchyEditor({
  ranks = DEFAULT_RANKS,
  fileColumns = [],
  fieldMappings = {},
  onChange
}: TaxonomyHierarchyEditorProps) {
  const [levels, setLevels] = useState<TaxonomyLevel[]>(() =>
    ranks.map(rank => ({
      name: rank,
      column: fieldMappings[rank]
    }))
  )
  const [newRankName, setNewRankName] = useState('')
  const [error, setError] = useState('')

  const notifyChange = (newLevels: TaxonomyLevel[]) => {
    const newRanks = newLevels.map(level => level.name)
    const newMappings = newLevels.reduce((acc, level) => {
      if (level.column) {
        acc[level.name] = level.column
      }
      return acc
    }, {} as Record<string, string>)

    onChange({ ranks: newRanks, mappings: newMappings })
  }

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return

    const items = Array.from(levels)
    const [reorderedItem] = items.splice(result.source.index, 1)
    items.splice(result.destination.index, 0, reorderedItem)

    setLevels(items)
    notifyChange(items)
  }

  const addLevel = () => {
    const rankName = newRankName.trim().toLowerCase()

    if (!rankName) {
      setError('Please enter a rank name')
      return
    }

    if (levels.some(level => level.name === rankName)) {
      setError('This rank already exists')
      return
    }

    const newLevels = [...levels, { name: rankName }]
    setLevels(newLevels)
    notifyChange(newLevels)
    setNewRankName('')
    setError('')
  }

  const removeLevel = (index: number) => {
    const newLevels = levels.filter((_, i) => i !== index)
    setLevels(newLevels)
    notifyChange(newLevels)
  }

  const updateLevelColumn = (index: number, column: string) => {
    const newLevels = [...levels]
    newLevels[index] = { ...newLevels[index], column }
    setLevels(newLevels)
    notifyChange(newLevels)
  }

  const usedColumns = levels.map(level => level.column).filter(Boolean)
  const availableColumns = fileColumns.filter(col => !usedColumns.includes(col))

  const isValid = levels.length >= 2 && levels.slice(0, 2).every(level => level.column)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Taxonomy Hierarchy Configuration</CardTitle>
        <CardDescription>
          Define the hierarchical levels and map them to columns in your file
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Define taxonomy levels from most general (e.g., family) to most specific (e.g., subspecies).
            At least the first two levels must be mapped to columns.
          </AlertDescription>
        </Alert>

        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="levels">
            {(provided) => (
              <div
                {...provided.droppableProps}
                ref={provided.innerRef}
                className="space-y-2"
              >
                {levels.map((level, index) => {
                  const isRequired = index < 2
                  const isMapped = Boolean(level.column)

                  return (
                    <Draggable key={level.name} draggableId={level.name} index={index}>
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={cn(
                            "flex items-center gap-3 p-3 bg-background border rounded-lg transition-all",
                            snapshot.isDragging && "shadow-lg",
                            isMapped && "bg-accent/20 border-accent"
                          )}
                        >
                          <div {...provided.dragHandleProps}>
                            <GripVertical className="h-4 w-4 text-muted-foreground" />
                          </div>

                          <Badge variant={isRequired ? "default" : "secondary"}>
                            {index + 1}
                          </Badge>

                          <div className="flex-1 space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">
                                {level.name}
                                {isRequired && <span className="text-destructive ml-1">*</span>}
                              </span>
                              {isMapped && (
                                <Badge variant="outline" className="text-xs">
                                  <Check className="h-3 w-3 mr-1" />
                                  Mapped
                                </Badge>
                              )}
                            </div>

                            {fileColumns.length > 0 && (
                              <Select
                                value={level.column || "none"}
                                onValueChange={(value) => updateLevelColumn(index, value === "none" ? "" : value)}
                              >
                                <SelectTrigger className="h-8 text-sm">
                                  <SelectValue placeholder="Select column..." />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="none">
                                    <span className="text-muted-foreground">No mapping</span>
                                  </SelectItem>
                                  {level.column && !availableColumns.includes(level.column) && (
                                    <SelectItem value={level.column}>
                                      {level.column} (current)
                                    </SelectItem>
                                  )}
                                  {availableColumns.map(col => (
                                    <SelectItem key={col} value={col}>
                                      {col}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeLevel(index)}
                            disabled={levels.length <= 1}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      )}
                    </Draggable>
                  )
                })}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>

        <div className="space-y-2 pt-4 border-t">
          <Label htmlFor="new-rank">Add Custom Level</Label>
          <div className="flex gap-2">
            <Input
              id="new-rank"
              value={newRankName}
              onChange={(e) => {
                setNewRankName(e.target.value)
                setError('')
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  addLevel()
                }
              }}
              placeholder="e.g., subfamily, tribe, subspecies"
              className="flex-1"
            />
            <Button onClick={addLevel} size="sm">
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>

        {!isValid && levels.length > 0 && fileColumns.length > 0 && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Please map at least the first two levels to columns in your file.
            </AlertDescription>
          </Alert>
        )}

        <div className="text-sm text-muted-foreground">
          <p>Hierarchy order: <code className="text-xs bg-muted px-2 py-1 rounded ml-1">
            {levels.map(l => l.name).join(' → ')}
          </code></p>
        </div>
      </CardContent>
    </Card>
  )
}
