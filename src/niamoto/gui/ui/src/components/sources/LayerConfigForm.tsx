/**
 * LayerConfigForm - Edit metadata layer configuration
 *
 * For raster and vector layers used in transformations
 */

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Layers, Globe2, Check } from 'lucide-react'
import type { LayerConfig } from './EntityConfigEditor'

interface LayerConfigFormProps {
  config: LayerConfig
  onSave: (updated: LayerConfig) => void
  onCancel?: () => void
}

export function LayerConfigForm({ config, onSave, onCancel }: LayerConfigFormProps) {
  const [localConfig, setLocalConfig] = useState<LayerConfig>({ ...config })

  const update = (key: keyof LayerConfig, value: string) => {
    setLocalConfig({
      ...localConfig,
      [key]: value,
    })
  }

  const handleSave = () => {
    onSave(localConfig)
  }

  const isRaster = localConfig.type === 'raster'

  return (
    <div className="space-y-4 pt-4">
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            {isRaster ? (
              <Globe2 className="h-4 w-4 text-orange-500" />
            ) : (
              <Layers className="h-4 w-4 text-purple-500" />
            )}
            Couche {isRaster ? 'Raster' : 'Vecteur'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Nom</Label>
              <Input
                className="h-8 text-sm"
                value={localConfig.name}
                onChange={(e) => update('name', e.target.value)}
                placeholder="elevation"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Type</Label>
              <Select
                value={localConfig.type}
                onValueChange={(v) => update('type', v as 'raster' | 'vector')}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="raster">Raster (TIF, GeoTIFF)</SelectItem>
                  <SelectItem value="vector">Vecteur (GPKG, SHP)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Chemin</Label>
            <Input
              className="h-8 text-sm"
              value={localConfig.path}
              onChange={(e) => update('path', e.target.value)}
              placeholder={isRaster ? 'imports/layers/file.tif' : 'imports/layers/file.gpkg'}
            />
          </div>

          {!isRaster && (
            <div className="space-y-1.5">
              <Label className="text-xs">Format</Label>
              <Select
                value={localConfig.format || 'geopackage'}
                onValueChange={(v) => update('format', v)}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="geopackage">GeoPackage</SelectItem>
                  <SelectItem value="shapefile">Shapefile</SelectItem>
                  <SelectItem value="geojson">GeoJSON</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-1.5">
            <Label className="text-xs">Description</Label>
            <Textarea
              className="min-h-[60px] text-sm"
              value={localConfig.description || ''}
              onChange={(e) => update('description', e.target.value)}
              placeholder="Description de la couche..."
            />
          </div>
        </CardContent>
      </Card>

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
