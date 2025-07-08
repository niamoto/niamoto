import { useState } from 'react'
import { useImportV2 } from './ImportContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { FileUpload } from '@/components/import-wizard/FileUpload'
import { ColumnMapper } from '@/components/import-wizard/ColumnMapper'
import { analyzeFile } from '@/lib/api/import'
import {
  MapPin,
  Map,
  Info,
  Plus,
  Trash2,
  CheckCircle
} from 'lucide-react'

export function AggregationStep() {
  const { state, setAggregationType, updatePlots, updateShapes, addShape, removeShape } = useImportV2()
  const { aggregationType, plots, shapes } = state
  const [isAnalyzing, setIsAnalyzing] = useState<Record<string, boolean>>({})

  const handleAggregationTypeChange = (value: string) => {
    if (value !== aggregationType) {
      setAggregationType(value as 'none' | 'plots' | 'shapes' | 'both')
    }
  }

  const handlePlotFileSelect = async (file: File) => {
    // Initialiser complètement l'objet plots
    updatePlots({
      file,
      fileAnalysis: null,
      fieldMappings: {},
      linkField: 'locality',
      occurrenceLinkField: 'plot_name'
    })
    setIsAnalyzing(prev => ({ ...prev, plots: true }))

    try {
      const analysis = await analyzeFile(file, 'plots')
      updatePlots({ fileAnalysis: analysis })

      // Auto-apply suggestions
      if (analysis.suggestions) {
        const autoMappings: Record<string, string> = {}
        const fields = ['identifier', 'location', 'locality']
        fields.forEach(field => {
          if (analysis.suggestions[field]?.[0]) {
            autoMappings[field] = analysis.suggestions[field][0]
          }
        })
        updatePlots({ fieldMappings: autoMappings })
      }
    } catch (error) {
      console.error('Plot file analysis failed:', error)
    } finally {
      setIsAnalyzing(prev => ({ ...prev, plots: false }))
    }
  }

  const handleShapeFileSelect = async (file: File, index: number) => {
    updateShapes(index, { file, fileAnalysis: null })
    const key = `shape-${index}`
    setIsAnalyzing(prev => ({ ...prev, [key]: true }))

    try {
      const analysis = await analyzeFile(file, 'shapes')
      updateShapes(index, { fileAnalysis: analysis })

      // Auto-apply name field
      if (analysis.suggestions?.name?.[0]) {
        updateShapes(index, {
          fieldMappings: { name: analysis.suggestions.name[0] }
        })
      }
    } catch (error) {
      console.error('Shape file analysis failed:', error)
    } finally {
      setIsAnalyzing(prev => ({ ...prev, [key]: false }))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Agrégations spatiales</h2>
        <p className="text-muted-foreground mt-2">
          Optionnel : Ajoutez des regroupements spatiaux pour organiser et analyser vos données
        </p>
      </div>

      <Alert>
        <Info className="w-4 h-4" />
        <AlertDescription>
          Les agrégations permettent de regrouper vos occurrences par zones géographiques
          et de générer des statistiques par regroupement. Cette étape est facultative.
        </AlertDescription>
      </Alert>

      {/* Aggregation type selection */}
      <Card>
        <CardHeader>
          <CardTitle>Type d'agrégation</CardTitle>
          <CardDescription>
            Choisissez comment vous souhaitez regrouper vos données
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup value={aggregationType} onValueChange={handleAggregationTypeChange}>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <RadioGroupItem value="none" id="none" />
                <div className="flex-1">
                  <Label htmlFor="none" className="font-medium cursor-pointer">
                    Pas d'agrégation pour le moment
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Vous pourrez toujours ajouter des agrégations plus tard
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <RadioGroupItem value="plots" id="plots" />
                <div className="flex-1">
                  <Label htmlFor="plots" className="font-medium cursor-pointer flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    Par plots/parcelles
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Importez un fichier de plots pour regrouper les occurrences par parcelles,
                    localités ou sites d'étude
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <RadioGroupItem value="shapes" id="shapes" />
                <div className="flex-1">
                  <Label htmlFor="shapes" className="font-medium cursor-pointer flex items-center gap-2">
                    <Map className="w-4 h-4" />
                    Par zones géographiques (shapes)
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Importez des fichiers de formes (shapefile, GeoJSON, GPKG) pour regrouper
                    par communes, régions, etc.
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Formats acceptés : .shp, .geojson, .gpkg, .zip (contenant des shapefiles)
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <RadioGroupItem value="both" id="both" />
                <div className="flex-1">
                  <Label htmlFor="both" className="font-medium cursor-pointer">
                    Les deux
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Utilisez à la fois des plots et des shapes pour une analyse complète
                  </p>
                </div>
              </div>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {/* Plots configuration */}
      {(aggregationType === 'plots' || aggregationType === 'both') && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="w-5 h-5" />
              Configuration des plots
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!plots?.file ? (
              <FileUpload
                onFileSelect={handlePlotFileSelect}
                acceptedFormats={['.csv']}
                isAnalyzing={isAnalyzing.plots}
              />
            ) : (
              <div className="space-y-4">
                <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <AlertDescription>
                    Fichier chargé : {plots.file.name}
                  </AlertDescription>
                </Alert>

                {plots.fileAnalysis && (
                  <ColumnMapper
                    importType="plots"
                    fileAnalysis={plots.fileAnalysis}
                    onMappingComplete={(mappings) => {
                      // Only update if mappings have actually changed
                      const currentMappings = plots.fieldMappings || {}
                      const hasChanged = JSON.stringify(mappings) !== JSON.stringify(currentMappings)
                      if (hasChanged) {
                        updatePlots({ fieldMappings: mappings })
                      }
                    }}
                  />
                )}

                {/* Link configuration */}
                {plots.fieldMappings?.identifier && (
                  <div className="space-y-2 pt-4 border-t">
                    <h4 className="font-medium text-sm">Configuration des liens</h4>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label htmlFor="linkField" className="text-sm">
                          Champ de liaison dans plots
                        </Label>
                        <select
                          id="linkField"
                          className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                          value={plots?.linkField || 'locality'}
                          onChange={(e) => updatePlots({ linkField: e.target.value })}
                        >
                          <option value="id">ID</option>
                          <option value="plot_id">Plot ID</option>
                          <option value="locality">Locality</option>
                        </select>
                      </div>
                      <div>
                        <Label htmlFor="occurrenceLinkField" className="text-sm">
                          Champ correspondant dans occurrences
                        </Label>
                        <input
                          id="occurrenceLinkField"
                          type="text"
                          className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                          placeholder="ex: plot_name"
                          value={plots?.occurrenceLinkField || ''}
                          onChange={(e) => updatePlots({ occurrenceLinkField: e.target.value })}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Shapes configuration */}
      {(aggregationType === 'shapes' || aggregationType === 'both') && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Map className="w-5 h-5" />
              Shapes géographiques
            </h3>
            <Button
              variant="outline"
              size="sm"
              onClick={addShape}
            >
              <Plus className="w-4 h-4 mr-2" />
              Ajouter un shape
            </Button>
          </div>

          {(!shapes || shapes.length === 0) && (
            <Alert>
              <AlertDescription>
                Cliquez sur "Ajouter un shape" pour importer des zones géographiques
              </AlertDescription>
            </Alert>
          )}

          {shapes?.map((shape, index) => (
            <Card key={index}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    Shape {index + 1}
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeShape(index)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {!shape.file ? (
                  <FileUpload
                    onFileSelect={(file: File) => handleShapeFileSelect(file, index)}
                    acceptedFormats={['.shp', '.geojson', '.json', '.gpkg', '.zip']}
                    isAnalyzing={isAnalyzing[`shape-${index}`]}
                  />
                ) : (
                  <div className="space-y-4">
                    <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <AlertDescription>
                        Fichier chargé : {shape.file.name}
                      </AlertDescription>
                    </Alert>

                    <div>
                      <Label htmlFor={`shape-type-${index}`} className="text-sm">
                        Type de shape
                      </Label>
                      <input
                        id={`shape-type-${index}`}
                        type="text"
                        className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                        placeholder="ex: commune, province, région"
                        value={shape.type}
                        onChange={(e) => updateShapes(index, { type: e.target.value })}
                      />
                    </div>

                    {shape.fileAnalysis && (
                      <ColumnMapper
                        importType="shapes"
                        fileAnalysis={shape.fileAnalysis}
                        onMappingComplete={(mappings) => {
                          // Only update if mappings have actually changed
                          const currentMappings = shape.fieldMappings || {}
                          const hasChanged = JSON.stringify(mappings) !== JSON.stringify(currentMappings)
                          if (hasChanged) {
                            updateShapes(index, { fieldMappings: mappings })
                          }
                        }}
                      />
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
