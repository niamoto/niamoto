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

interface ShapeFormProps {
  config: ImportConfig
  onConfigChange: (config: ImportConfig) => void
}

export function ShapeForm({ config, onConfigChange }: ShapeFormProps) {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [fields, setFields] = useState<string[]>([])
  const [mappingConfig, setMappingConfig] = useState<any>({})

  // Required fields for shapes
  const requiredFields = [
    { key: 'id_shape', label: 'Shape ID', required: true },
    { key: 'name', label: 'Shape Name', required: false },
    { key: 'type', label: 'Shape Type', required: false },
    { key: 'category', label: 'Category', required: false },
    { key: 'area', label: 'Area (m²)', required: false },
    { key: 'perimeter', label: 'Perimeter (m)', required: false },
    { key: 'elevation_min', label: 'Min Elevation', required: false },
    { key: 'elevation_max', label: 'Max Elevation', required: false },
    { key: 'elevation_mean', label: 'Mean Elevation', required: false },
    { key: 'province', label: 'Province', required: false },
    { key: 'municipality', label: 'Municipality', required: false },
    { key: 'protection_status', label: 'Protection Status', required: false },
    { key: 'habitat_type', label: 'Habitat Type', required: false },
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
          <Label>{t('pipeline.import.shapes.file', 'Shapes File')}</Label>
          {!file ? (
            <FileUpload
              onFileSelect={handleFileSelect}
              accept=".geojson,.gpkg,.shp,.kml,.kmz"
              maxSize={500 * 1024 * 1024} // 500MB
            />
          ) : (
            <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/50">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span className="text-sm font-medium">{file.name}</span>
                <span className="text-xs text-muted-foreground">
                  ({(file.size / (1024 * 1024)).toFixed(1)} MB)
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
            <Label>{t('pipeline.import.shapes.mapping', 'Field Mapping')}</Label>
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
          <Label>{t('pipeline.import.shapes.options', 'Import Options')}</Label>

          <div className="flex items-center space-x-2">
            <Switch
              id="update-existing"
              checked={config.updateExisting || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, updateExisting: checked })
              }
            />
            <Label htmlFor="update-existing" className="text-sm font-normal">
              {t('pipeline.import.shapes.updateExisting', 'Update existing shapes')}
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
              {t('pipeline.import.shapes.validateGeometry', 'Validate geometry')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="fix-geometry"
              checked={config.fixGeometry || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, fixGeometry: checked })
              }
            />
            <Label htmlFor="fix-geometry" className="text-sm font-normal">
              {t('pipeline.import.shapes.fixGeometry', 'Auto-fix invalid geometries')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="calculate-metrics"
              checked={config.calculateMetrics !== false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, calculateMetrics: checked })
              }
            />
            <Label htmlFor="calculate-metrics" className="text-sm font-normal">
              {t('pipeline.import.shapes.calculateMetrics', 'Calculate area and perimeter')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="simplify-geometry"
              checked={config.simplifyGeometry || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, simplifyGeometry: checked })
              }
            />
            <Label htmlFor="simplify-geometry" className="text-sm font-normal">
              {t('pipeline.import.shapes.simplifyGeometry', 'Simplify complex geometries')}
            </Label>
          </div>
        </div>

        {/* Shape type filter */}
        <div className="space-y-2">
          <Label htmlFor="geometry-filter">
            {t('pipeline.import.shapes.geometryFilter', 'Geometry Type Filter')}
          </Label>
          <Select
            value={config.geometryFilter || 'all'}
            onValueChange={(value) => onConfigChange({ ...config, geometryFilter: value })}
          >
            <SelectTrigger id="geometry-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All geometries</SelectItem>
              <SelectItem value="polygon">Polygons only</SelectItem>
              <SelectItem value="multipolygon">Multi-polygons only</SelectItem>
              <SelectItem value="point">Points only</SelectItem>
              <SelectItem value="linestring">Lines only</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Coordinate system */}
        <div className="space-y-2">
          <Label htmlFor="crs">
            {t('pipeline.import.shapes.crs', 'Coordinate Reference System')}
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

        {/* Target CRS */}
        <div className="space-y-2">
          <Label htmlFor="target-crs">
            {t('pipeline.import.shapes.targetCrs', 'Target CRS (optional transform)')}
          </Label>
          <Select
            value={config.targetCrs || 'none'}
            onValueChange={(value) => onConfigChange({ ...config, targetCrs: value === 'none' ? undefined : value })}
          >
            <SelectTrigger id="target-crs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No transformation</SelectItem>
              <SelectItem value="EPSG:4326">WGS 84 (EPSG:4326)</SelectItem>
              <SelectItem value="EPSG:3857">Web Mercator (EPSG:3857)</SelectItem>
              <SelectItem value="EPSG:32758">UTM Zone 58S (EPSG:32758)</SelectItem>
              <SelectItem value="RGNC91-93">RGNC91-93 Lambert NC</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </BaseImportForm>
  )
}
