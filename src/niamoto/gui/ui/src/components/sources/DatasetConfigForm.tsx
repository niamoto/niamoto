/**
 * DatasetConfigForm - Edit dataset configuration
 *
 * For datasets, only the connector is needed:
 * - type: file
 * - format: csv, xlsx, parquet, etc.
 * - path: relative path to the file
 *
 * Schema and links are NOT part of datasets - they belong to references.
 */

import { useState } from 'react'
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FileSpreadsheet, Check } from 'lucide-react'
import type { DatasetConfig } from './EntityConfigEditor'

interface DatasetConfigFormProps {
  name: string
  config: DatasetConfig
  detectedColumns: string[]
  availableReferences: Array<{
    name: string
    columns: string[]
  }>
  onSave: (updated: DatasetConfig) => void
  onCancel?: () => void
}

export function DatasetConfigForm({
  name: _name,
  config,
  detectedColumns: _detectedColumns,
  availableReferences: _availableReferences,
  onSave,
  onCancel,
}: DatasetConfigFormProps) {
  // For datasets, we only keep the connector - no schema or links
  const [localConfig, setLocalConfig] = useState<DatasetConfig>({
    connector: config.connector,
  })

  const updateConnector = (key: string, value: string) => {
    setLocalConfig({
      ...localConfig,
      connector: {
        ...localConfig.connector,
        [key]: value,
      },
    })
  }

  const handleSave = () => {
    // Only save connector, strip out any schema or links
    onSave({
      connector: localConfig.connector,
    })
  }

  return (
    <div className="space-y-4 pt-4">
      {/* Connector Settings - the only thing datasets need */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <FileSpreadsheet className="h-4 w-4" />
            Connecteur
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Type</Label>
            <Input
              className="h-8 text-sm bg-muted"
              value={localConfig.connector.type || 'file'}
              disabled
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Format</Label>
              <Select
                value={localConfig.connector.format || 'csv'}
                onValueChange={(v) => updateConnector('format', v)}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="csv">CSV</SelectItem>
                  <SelectItem value="xlsx">Excel</SelectItem>
                  <SelectItem value="parquet">Parquet</SelectItem>
                  <SelectItem value="geojson">GeoJSON</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Chemin</Label>
              <Input
                className="h-8 text-sm"
                value={localConfig.connector.path}
                onChange={(e) => updateConnector('path', e.target.value)}
                placeholder="imports/file.csv"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Les datasets contiennent uniquement les donnees brutes.
        Pour definir un schema ou des relations, utilisez une <strong>reference</strong>.
      </p>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <Button variant="outline" size="sm" onClick={onCancel}>
            Annuler
          </Button>
        )}
        <Button size="sm" onClick={handleSave}>
          <Check className="mr-1 h-3 w-3" />
          Appliquer
        </Button>
      </div>
    </div>
  )
}
