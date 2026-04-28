import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Check, FileSpreadsheet } from 'lucide-react'
import type { AuxiliarySource } from '@/features/import/api/smart-config'

interface AuxiliarySourceConfigFormProps {
  source: AuxiliarySource
  detectedColumns: string[]
  availableTargets: string[]
  onSave: (updated: AuxiliarySource) => void
  onCancel?: () => void
}

export function AuxiliarySourceConfigForm({
  source,
  detectedColumns,
  availableTargets,
  onSave,
  onCancel,
}: AuxiliarySourceConfigFormProps) {
  const [localSource, setLocalSource] = useState<AuxiliarySource>({
    ...source,
    relation: {
      plugin: source.relation?.plugin || 'stats_loader',
      key: source.relation?.key || 'id',
      ref_field: source.relation?.ref_field || 'id',
      match_field: source.relation?.match_field || 'id',
    },
  })
  const matchFieldOptions = localSource.relation.match_field
    ? Array.from(new Set([localSource.relation.match_field, ...detectedColumns]))
    : detectedColumns

  const updateSource = (key: 'name' | 'data' | 'grouping' | 'source_entity', value: string) => {
    setLocalSource((current) => ({
      ...current,
      [key]: value,
    }))
  }

  const updateRelation = (key: keyof AuxiliarySource['relation'], value: string) => {
    setLocalSource((current) => ({
      ...current,
      relation: {
        ...current.relation,
        [key]: value,
      },
    }))
  }

  return (
    <div className="space-y-4 pt-4">
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <FileSpreadsheet className="h-4 w-4" />
            Source auxiliaire
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Nom</Label>
              <Input
                className="h-8 text-sm"
                value={localSource.name}
                onChange={(event) => updateSource('name', event.target.value)}
                placeholder="plot_stats"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Cible</Label>
              <Select
                value={localSource.grouping || 'none'}
                onValueChange={(value) => updateSource('grouping', value === 'none' ? '' : value)}
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="Sélectionner une cible" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">
                    <span className="text-muted-foreground">--</span>
                  </SelectItem>
                  {availableTargets.map((target) => (
                    <SelectItem key={target} value={target}>
                      {target}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Chemin</Label>
            <Input
              className="h-8 text-sm"
              value={localSource.data}
              onChange={(event) => updateSource('data', event.target.value)}
              placeholder="imports/raw_plot_stats.csv"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <FileSpreadsheet className="h-4 w-4" />
            Relation stats_loader
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Clé</Label>
              <Input
                className="h-8 text-sm"
                value={localSource.relation.key}
                onChange={(event) => updateRelation('key', event.target.value)}
                placeholder="id"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Champ référence</Label>
              <Input
                className="h-8 text-sm"
                value={localSource.relation.ref_field}
                onChange={(event) => updateRelation('ref_field', event.target.value)}
                placeholder="id_liste_plots"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Champ source</Label>
            <Select
              value={localSource.relation.match_field || 'none'}
              onValueChange={(value) =>
                updateRelation('match_field', value === 'none' ? '' : value)
              }
            >
              <SelectTrigger className="h-8">
                <SelectValue placeholder="Sélectionner un champ" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">
                  <span className="text-muted-foreground">--</span>
                </SelectItem>
                {matchFieldOptions.map((column) => (
                  <SelectItem key={column} value={column}>
                    {column}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {detectedColumns.length === 0 && (
              <Input
                className="h-8 text-sm"
                value={localSource.relation.match_field}
                onChange={(event) => updateRelation('match_field', event.target.value)}
                placeholder="plot_id"
              />
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <Button variant="outline" size="sm" onClick={onCancel}>
            Annuler
          </Button>
        )}
        <Button size="sm" onClick={() => onSave(localSource)}>
          <Check className="mr-1 h-3 w-3" />
          Appliquer
        </Button>
      </div>
    </div>
  )
}
