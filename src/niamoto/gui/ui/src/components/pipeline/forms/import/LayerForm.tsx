import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { FileUpload } from '@/components/import/FileUpload'
import { BaseImportForm } from '../BaseImportForm'
import { FileText } from 'lucide-react'
import type { ImportConfig } from '../../types'

interface LayerFormProps {
  config: ImportConfig
  onConfigChange: (config: ImportConfig) => void
}

export function LayerForm({ config, onConfigChange }: LayerFormProps) {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [layerInfo, setLayerInfo] = useState<any>(null)

  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile)

    // Analyze layer information
    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch('/api/imports/analyze-layer', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        setLayerInfo(data)
      }
    } catch (error) {
      console.error('Error analyzing layer:', error)
    }
  }

  const getFileTypeFromExtension = (fileName: string) => {
    const ext = fileName.toLowerCase().split('.').pop()
    if (['tif', 'tiff', 'geotiff'].includes(ext || '')) return 'raster'
    if (['nc', 'netcdf'].includes(ext || '')) return 'netcdf'
    if (['geojson', 'gpkg', 'shp'].includes(ext || '')) return 'vector'
    return 'unknown'
  }

  return (
    <BaseImportForm
      config={config}
      onConfigChange={onConfigChange}
    >
      <div className="space-y-4">
        {/* File selection */}
        <div className="space-y-2">
          <Label>{t('pipeline.import.layers.file', 'Layer File')}</Label>
          {!file ? (
            <FileUpload
              onFileSelect={handleFileSelect}
              accept=".tif,.tiff,.geotiff,.nc,.netcdf,.geojson,.gpkg,.shp,.asc,.xyz"
              maxSize={1024 * 1024 * 1024} // 1GB
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
                  setLayerInfo(null)
                }}
              >
                {t('common.change', 'Change')}
              </Button>
            </div>
          )}
        </div>

        {/* Layer information display */}
        {layerInfo && (
          <div className="space-y-2">
            <Label>{t('pipeline.import.layers.info', 'Layer Information')}</Label>
            <div className="p-3 border rounded-lg bg-muted/30 space-y-2 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <span className="font-medium">Type:</span>
                <span>{layerInfo.type || getFileTypeFromExtension(file?.name || '')}</span>
              </div>
              {layerInfo.crs && (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <span className="font-medium">CRS:</span>
                    <span>{layerInfo.crs}</span>
                  </div>
                </>
              )}
              {layerInfo.bounds && (
                <div className="grid grid-cols-2 gap-2">
                  <span className="font-medium">Bounds:</span>
                  <span className="text-xs">
                    [{layerInfo.bounds.map((b: number) => b.toFixed(6)).join(', ')}]
                  </span>
                </div>
              )}
              {layerInfo.dimensions && (
                <div className="grid grid-cols-2 gap-2">
                  <span className="font-medium">Dimensions:</span>
                  <span>{layerInfo.dimensions.width} x {layerInfo.dimensions.height}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Layer configuration */}
        <div className="space-y-2">
          <Label htmlFor="layer-name">
            {t('pipeline.import.layers.layerName', 'Layer Name')}
          </Label>
          <Input
            id="layer-name"
            value={config.layerName || ''}
            onChange={(e) => onConfigChange({ ...config, layerName: e.target.value })}
            placeholder={t('pipeline.import.layers.layerNamePlaceholder', 'Enter layer name')}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="layer-category">
            {t('pipeline.import.layers.category', 'Layer Category')}
          </Label>
          <Select
            value={config.layerCategory || 'environmental'}
            onValueChange={(value) => onConfigChange({ ...config, layerCategory: value })}
          >
            <SelectTrigger id="layer-category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="environmental">Environmental</SelectItem>
              <SelectItem value="climatic">Climatic</SelectItem>
              <SelectItem value="topographic">Topographic</SelectItem>
              <SelectItem value="soil">Soil</SelectItem>
              <SelectItem value="vegetation">Vegetation</SelectItem>
              <SelectItem value="administrative">Administrative</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Processing options */}
        <div className="space-y-2">
          <Label>{t('pipeline.import.layers.options', 'Processing Options')}</Label>

          <div className="flex items-center space-x-2">
            <Switch
              id="clip-to-bounds"
              checked={config.clipToBounds || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, clipToBounds: checked })
              }
            />
            <Label htmlFor="clip-to-bounds" className="text-sm font-normal">
              {t('pipeline.import.layers.clipToBounds', 'Clip to study area bounds')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="resample"
              checked={config.resample || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, resample: checked })
              }
            />
            <Label htmlFor="resample" className="text-sm font-normal">
              {t('pipeline.import.layers.resample', 'Resample to target resolution')}
            </Label>
          </div>

          {config.resample && (
            <div className="ml-6 space-y-2">
              <Label htmlFor="target-resolution">
                {t('pipeline.import.layers.targetResolution', 'Target Resolution (meters)')}
              </Label>
              <Input
                id="target-resolution"
                type="number"
                value={config.targetResolution || ''}
                onChange={(e) => onConfigChange({ ...config, targetResolution: e.target.value })}
                placeholder="30"
              />
            </div>
          )}

          <div className="flex items-center space-x-2">
            <Switch
              id="generate-pyramids"
              checked={config.generatePyramids !== false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, generatePyramids: checked })
              }
            />
            <Label htmlFor="generate-pyramids" className="text-sm font-normal">
              {t('pipeline.import.layers.generatePyramids', 'Generate pyramids for faster display')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="calculate-stats"
              checked={config.calculateStats !== false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, calculateStats: checked })
              }
            />
            <Label htmlFor="calculate-stats" className="text-sm font-normal">
              {t('pipeline.import.layers.calculateStats', 'Calculate layer statistics')}
            </Label>
          </div>
        </div>

        {/* Resampling method */}
        {config.resample && (
          <div className="space-y-2">
            <Label htmlFor="resampling-method">
              {t('pipeline.import.layers.resamplingMethod', 'Resampling Method')}
            </Label>
            <Select
              value={config.resamplingMethod || 'bilinear'}
              onValueChange={(value) => onConfigChange({ ...config, resamplingMethod: value })}
            >
              <SelectTrigger id="resampling-method">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="nearest">Nearest Neighbor</SelectItem>
                <SelectItem value="bilinear">Bilinear</SelectItem>
                <SelectItem value="cubic">Cubic</SelectItem>
                <SelectItem value="lanczos">Lanczos</SelectItem>
                <SelectItem value="average">Average</SelectItem>
                <SelectItem value="mode">Mode</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Coordinate system */}
        <div className="space-y-2">
          <Label htmlFor="crs">
            {t('pipeline.import.layers.crs', 'Coordinate Reference System')}
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
            {t('pipeline.import.layers.targetCrs', 'Target CRS (optional transform)')}
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

        {/* NoData value */}
        <div className="space-y-2">
          <Label htmlFor="nodata-value">
            {t('pipeline.import.layers.nodataValue', 'NoData Value (optional)')}
          </Label>
          <Input
            id="nodata-value"
            type="number"
            value={config.nodataValue || ''}
            onChange={(e) => onConfigChange({ ...config, nodataValue: e.target.value })}
            placeholder="-9999"
          />
        </div>
      </div>
    </BaseImportForm>
  )
}
