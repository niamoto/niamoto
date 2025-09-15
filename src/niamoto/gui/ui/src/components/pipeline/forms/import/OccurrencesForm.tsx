import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { FileUpload } from '@/components/import/FileUpload'
import { ColumnMapping } from '@/components/import/ColumnMapping'
import { BaseImportForm } from '../BaseImportForm'
import { FileText } from 'lucide-react'
import type { ImportConfig } from '../../types'

interface OccurrencesFormProps {
  config: ImportConfig
  onConfigChange: (config: ImportConfig) => void
}

export function OccurrencesForm({ config, onConfigChange }: OccurrencesFormProps) {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [fields, setFields] = useState<string[]>([])
  const [mappingConfig, setMappingConfig] = useState<any>({})

  // Required fields for occurrences
  const requiredFields = [
    { key: 'id_occurrence', label: 'Occurrence ID', required: true },
    { key: 'taxon_id', label: 'Taxon ID', required: true },
    { key: 'location_id', label: 'Location ID', required: false },
    { key: 'plot_id', label: 'Plot ID', required: false },
    { key: 'date', label: 'Date', required: false },
    { key: 'longitude', label: 'Longitude', required: false },
    { key: 'latitude', label: 'Latitude', required: false },
    { key: 'elevation', label: 'Elevation', required: false },
    { key: 'dbh', label: 'DBH', required: false },
    { key: 'height', label: 'Height', required: false },
    { key: 'status', label: 'Status', required: false },
    { key: 'phenology', label: 'Phenology', required: false },
  ]

  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile)

    // Detect fields from file
    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch('/api/imports/detect-fields', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        setFields(data.fields || [])
      }
    } catch (error) {
      console.error('Error detecting fields:', error)
    }
  }

  const handleMappingChange = (mapping: any) => {
    setMappingConfig(mapping)
    onConfigChange({
      ...config,
      file: file?.name || '',
      mapping,
    })
  }

  return (
    <BaseImportForm
      config={config}
      onConfigChange={onConfigChange}
    >
      <div className="space-y-4">
        {/* File selection */}
        <div className="space-y-2">
          <Label>{t('pipeline.import.occurrences.file', 'Occurrences File')}</Label>
          {!file ? (
            <FileUpload
              onFileSelect={handleFileSelect}
              accept=".csv,.xlsx,.xls,.geojson,.gpkg,.shp"
              maxSize={100 * 1024 * 1024} // 100MB
            />
          ) : (
            <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/50">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span className="text-sm font-medium">{file.name}</span>
                <span className="text-xs text-muted-foreground">
                  ({(file.size / 1024).toFixed(1)} KB)
                </span>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setFile(null)
                  setFields([])
                  setMappingConfig({})
                }}
              >
                {t('common.change', 'Change')}
              </Button>
            </div>
          )}
        </div>

        {/* Column mapping */}
        {fields.length > 0 && (
          <div className="space-y-2">
            <Label>{t('pipeline.import.occurrences.mapping', 'Field Mapping')}</Label>
            <ColumnMapping
              sourceColumns={fields}
              targetFields={requiredFields}
              mapping={mappingConfig}
              onMappingChange={handleMappingChange}
            />
          </div>
        )}

        {/* Import options */}
        <div className="space-y-2">
          <Label>{t('pipeline.import.occurrences.options', 'Import Options')}</Label>

          <div className="flex items-center space-x-2">
            <Switch
              id="update-existing"
              checked={config.updateExisting || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, updateExisting: checked })
              }
            />
            <Label htmlFor="update-existing" className="text-sm font-normal">
              {t('pipeline.import.occurrences.updateExisting', 'Update existing occurrences')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="validate-geometry"
              checked={config.validateGeometry !== false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, validateGeometry: checked })
              }
            />
            <Label htmlFor="validate-geometry" className="text-sm font-normal">
              {t('pipeline.import.occurrences.validateGeometry', 'Validate geometry')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="match-taxon-name"
              checked={config.matchTaxonByName || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, matchTaxonByName: checked })
              }
            />
            <Label htmlFor="match-taxon-name" className="text-sm font-normal">
              {t('pipeline.import.occurrences.matchTaxonName', 'Match taxon by name if ID not found')}
            </Label>
          </div>
        </div>

        {/* Coordinate system */}
        <div className="space-y-2">
          <Label htmlFor="crs">
            {t('pipeline.import.occurrences.crs', 'Coordinate Reference System')}
          </Label>
          <Select
            value={config.crs || 'EPSG:4326'}
            onValueChange={(value) => onConfigChange({ ...config, crs: value })}
          >
            <SelectTrigger id="crs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="EPSG:4326">WGS 84 (EPSG:4326)</SelectItem>
              <SelectItem value="EPSG:3857">Web Mercator (EPSG:3857)</SelectItem>
              <SelectItem value="EPSG:32758">UTM Zone 58S (EPSG:32758)</SelectItem>
              <SelectItem value="RGNC91-93">RGNC91-93 Lambert NC</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Encoding */}
        <div className="space-y-2">
          <Label htmlFor="encoding">
            {t('pipeline.import.encoding', 'File Encoding')}
          </Label>
          <Select
            value={config.encoding || 'utf-8'}
            onValueChange={(value) => onConfigChange({ ...config, encoding: value })}
          >
            <SelectTrigger id="encoding">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="utf-8">UTF-8</SelectItem>
              <SelectItem value="latin1">Latin-1</SelectItem>
              <SelectItem value="cp1252">Windows-1252</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </BaseImportForm>
  )
}
