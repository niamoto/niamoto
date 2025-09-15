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

interface PlotFormProps {
  config: ImportConfig
  onConfigChange: (config: ImportConfig) => void
}

export function PlotForm({ config, onConfigChange }: PlotFormProps) {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [fields, setFields] = useState<string[]>([])
  const [mappingConfig, setMappingConfig] = useState<any>({})

  // Required fields for plots
  const requiredFields = [
    { key: 'id_plot', label: 'Plot ID', required: true },
    { key: 'name', label: 'Plot Name', required: false },
    { key: 'locality', label: 'Locality', required: false },
    { key: 'longitude', label: 'Longitude', required: true },
    { key: 'latitude', label: 'Latitude', required: true },
    { key: 'elevation', label: 'Elevation', required: false },
    { key: 'slope', label: 'Slope', required: false },
    { key: 'aspect', label: 'Aspect', required: false },
    { key: 'area', label: 'Plot Area (m²)', required: false },
    { key: 'shape', label: 'Plot Shape', required: false },
    { key: 'substrate', label: 'Substrate', required: false },
    { key: 'forest_type', label: 'Forest Type', required: false },
    { key: 'date_created', label: 'Date Created', required: false },
    { key: 'notes', label: 'Notes', required: false },
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
          <Label>{t('pipeline.import.plots.file', 'Plots File')}</Label>
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
            <Label>{t('pipeline.import.plots.mapping', 'Field Mapping')}</Label>
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
          <Label>{t('pipeline.import.plots.options', 'Import Options')}</Label>

          <div className="flex items-center space-x-2">
            <Switch
              id="update-existing"
              checked={config.updateExisting || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, updateExisting: checked })
              }
            />
            <Label htmlFor="update-existing" className="text-sm font-normal">
              {t('pipeline.import.plots.updateExisting', 'Update existing plots')}
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
              {t('pipeline.import.plots.validateGeometry', 'Validate plot coordinates')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="calculate-area"
              checked={config.calculateArea || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, calculateArea: checked })
              }
            />
            <Label htmlFor="calculate-area" className="text-sm font-normal">
              {t('pipeline.import.plots.calculateArea', 'Auto-calculate plot area from coordinates')}
            </Label>
          </div>
        </div>

        {/* Plot type */}
        <div className="space-y-2">
          <Label htmlFor="plot-type">
            {t('pipeline.import.plots.type', 'Default Plot Type')}
          </Label>
          <Select
            value={config.defaultPlotType || 'circular'}
            onValueChange={(value) => onConfigChange({ ...config, defaultPlotType: value })}
          >
            <SelectTrigger id="plot-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="circular">Circular</SelectItem>
              <SelectItem value="square">Square</SelectItem>
              <SelectItem value="rectangular">Rectangular</SelectItem>
              <SelectItem value="transect">Transect</SelectItem>
              <SelectItem value="irregular">Irregular</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Coordinate system */}
        <div className="space-y-2">
          <Label htmlFor="crs">
            {t('pipeline.import.plots.crs', 'Coordinate Reference System')}
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
