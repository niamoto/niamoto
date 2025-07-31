import { useState } from 'react'
import { DragDropContext, Droppable, Draggable, type DropResult } from '@hello-pangea/dnd'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { GripVertical, Plus, X, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface TaxonomyRankEditorProps {
  value: string[]
  onChange: (ranks: string[]) => void
}

const DEFAULT_RANKS = ['family', 'genus', 'species', 'infra']

export function TaxonomyRankEditor({ value = DEFAULT_RANKS, onChange }: TaxonomyRankEditorProps) {
  const [ranks, setRanks] = useState<string[]>(value)
  const [newRank, setNewRank] = useState('')
  const [error, setError] = useState('')

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return

    const items = Array.from(ranks)
    const [reorderedItem] = items.splice(result.source.index, 1)
    items.splice(result.destination.index, 0, reorderedItem)

    setRanks(items)
    onChange(items)
  }

  const addRank = () => {
    const rankName = newRank.trim().toLowerCase()

    if (!rankName) {
      setError('Please enter a rank name')
      return
    }

    if (ranks.includes(rankName)) {
      setError('This rank already exists')
      return
    }

    const newRanks = [...ranks, rankName]
    setRanks(newRanks)
    onChange(newRanks)
    setNewRank('')
    setError('')
  }

  const removeRank = (index: number) => {
    const newRanks = ranks.filter((_, i) => i !== index)
    setRanks(newRanks)
    onChange(newRanks)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Taxonomy Rank Order</CardTitle>
        <CardDescription>
          Define the hierarchical order of taxonomy ranks from highest to lowest
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            The order matters! Ranks should be ordered from most general (e.g., family)
            to most specific (e.g., infra or subspecies)
          </AlertDescription>
        </Alert>

        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="ranks">
            {(provided) => (
              <div
                {...provided.droppableProps}
                ref={provided.innerRef}
                className="space-y-2"
              >
                {ranks.map((rank, index) => (
                  <Draggable key={rank} draggableId={rank} index={index}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        className={`flex items-center gap-2 p-3 bg-background border rounded-lg ${
                          snapshot.isDragging ? 'shadow-lg' : ''
                        }`}
                      >
                        <div {...provided.dragHandleProps}>
                          <GripVertical className="h-4 w-4 text-muted-foreground" />
                        </div>

                        <Badge variant="secondary" className="mr-2">
                          {index + 1}
                        </Badge>

                        <span className="flex-1 font-medium">{rank}</span>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeRank(index)}
                          disabled={ranks.length <= 1}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>

        <div className="space-y-2 pt-4 border-t">
          <Label htmlFor="new-rank">Add Custom Rank</Label>
          <div className="flex gap-2">
            <Input
              id="new-rank"
              value={newRank}
              onChange={(e) => {
                setNewRank(e.target.value)
                setError('')
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  addRank()
                }
              }}
              placeholder="e.g., subfamily, tribe, subspecies"
              className="flex-1"
            />
            <Button onClick={addRank} size="sm">
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>

        <div className="text-sm text-muted-foreground">
          Current order: <code className="text-xs bg-muted px-2 py-1 rounded">
            {ranks.join(', ')}
          </code>
        </div>
      </CardContent>
    </Card>
  )
}
