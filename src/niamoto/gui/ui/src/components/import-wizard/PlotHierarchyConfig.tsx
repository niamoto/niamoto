import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  GitBranch,
  Plus,
  X,
  ArrowUp,
  ArrowDown,
  Info,
  MapPin
} from 'lucide-react'

interface PlotHierarchyConfigProps {
  hierarchy: HierarchyConfig
  availableColumns: string[]
  onChange: (hierarchy: HierarchyConfig) => void
}

export interface HierarchyConfig {
  enabled: boolean
  levels: string[]
  aggregate_geometry: boolean
}

export function PlotHierarchyConfig({ hierarchy, availableColumns, onChange }: PlotHierarchyConfigProps) {
  const [newLevel, setNewLevel] = useState('')

  const addLevel = () => {
    if (newLevel && !hierarchy.levels.includes(newLevel)) {
      onChange({
        ...hierarchy,
        levels: [...hierarchy.levels, newLevel]
      })
      setNewLevel('')
    }
  }

  const removeLevel = (level: string) => {
    onChange({
      ...hierarchy,
      levels: hierarchy.levels.filter(l => l !== level)
    })
  }

  const moveLevel = (index: number, direction: 'up' | 'down') => {
    const newLevels = [...hierarchy.levels]
    const newIndex = direction === 'up' ? index - 1 : index + 1

    if (newIndex >= 0 && newIndex < newLevels.length) {
      [newLevels[index], newLevels[newIndex]] = [newLevels[newIndex], newLevels[index]]
      onChange({
        ...hierarchy,
        levels: newLevels
      })
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GitBranch className="h-5 w-5" />
          Plot Hierarchy Configuration
        </CardTitle>
        <CardDescription>
          Configure hierarchical relationships between plots, localities, and countries
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Enable/Disable Hierarchy */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="enable-hierarchy">Enable Hierarchical Import</Label>
            <p className="text-sm text-muted-foreground">
              Create a nested structure of plots within localities and countries
            </p>
          </div>
          <Switch
            id="enable-hierarchy"
            checked={hierarchy.enabled}
            onCheckedChange={(checked) => onChange({ ...hierarchy, enabled: checked })}
          />
        </div>

        {hierarchy.enabled && (
          <>
            {/* Hierarchy Levels */}
            <div className="space-y-4">
              <div>
                <Label>Hierarchy Levels</Label>
                <p className="text-sm text-muted-foreground mb-3">
                  Define levels from lowest to highest (e.g., plot → locality → country)
                </p>
              </div>

              <div className="space-y-2">
                {hierarchy.levels.map((level, index) => (
                  <div key={level} className="flex items-center gap-2">
                    <Badge variant="secondary" className="min-w-[100px] justify-center">
                      Level {index + 1}
                    </Badge>
                    <div className="flex-1 flex items-center gap-2 rounded-md border bg-background px-3 py-2">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1">{level}</span>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => moveLevel(index, 'up')}
                        disabled={index === 0}
                      >
                        <ArrowUp className="h-3 w-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => moveLevel(index, 'down')}
                        disabled={index === hierarchy.levels.length - 1}
                      >
                        <ArrowDown className="h-3 w-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => removeLevel(level)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add new level */}
              <div className="flex gap-2">
                <Select value={newLevel} onValueChange={setNewLevel}>
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="Select a column for hierarchy level" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableColumns
                      .filter(col => !hierarchy.levels.includes(col))
                      .map(col => (
                        <SelectItem key={col} value={col}>
                          {col}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <Button
                  onClick={addLevel}
                  disabled={!newLevel}
                  size="sm"
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add Level
                </Button>
              </div>
            </div>

            {/* Aggregate Geometry */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="aggregate-geometry">Aggregate Geometry</Label>
                <p className="text-sm text-muted-foreground">
                  Combine geometries of child plots for parent levels
                </p>
              </div>
              <Switch
                id="aggregate-geometry"
                checked={hierarchy.aggregate_geometry}
                onCheckedChange={(checked) =>
                  onChange({ ...hierarchy, aggregate_geometry: checked })
                }
              />
            </div>

            {/* Example visualization */}
            {hierarchy.levels.length > 0 && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <p className="mb-2">Example hierarchy structure:</p>
                  <div className="ml-4 text-sm font-mono">
                    {hierarchy.levels.map((level, index) => (
                      <div key={level} style={{ marginLeft: `${index * 20}px` }}>
                        {index > 0 && '└─ '}{level}
                      </div>
                    ))}
                  </div>
                  {hierarchy.aggregate_geometry && (
                    <p className="mt-2 text-xs">
                      Parent geometries will be automatically calculated from their children.
                    </p>
                  )}
                </AlertDescription>
              </Alert>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
