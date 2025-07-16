import { useState } from 'react'
import { useImport } from './ImportContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { FileUpload } from '@/components/import-wizard/FileUpload'
import { ColumnMapper } from '@/components/import-wizard/ColumnMapper'
import { PlotHierarchyConfig } from './components/PlotHierarchyConfig'
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
  const { state, setAggregationType, updatePlots, updateShapes, addShape, removeShape } = useImport()
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
          Ajoutez des regroupements spatiaux pour organiser et analyser vos données
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
                <div className="flex items-center justify-between">
                  <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20 flex-1">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <AlertDescription>
                      Fichier chargé : {plots.file.name}
                    </AlertDescription>
                  </Alert>
                  <Button
                    variant="outline"
                    size="sm"
                    className="ml-2"
                    onClick={() => updatePlots({
                      file: null,
                      fileAnalysis: null,
                      fieldMappings: {},
                      hierarchy: undefined
                    })}
                  >
                    Changer de fichier
                  </Button>
                </div>

                {plots.fileAnalysis && (
                  <ColumnMapper
                    importType="plots"
                    fileAnalysis={{
                      ...plots.fileAnalysis,
                      occurrenceColumns: state.occurrences.fileAnalysis?.columns || []
                    }}
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
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Configuration de la hiérarchie des plots */}
      {(aggregationType === 'plots' || aggregationType === 'both') && plots?.file && plots.fileAnalysis && (
        <PlotHierarchyConfig
          hierarchy={plots.hierarchy || { enabled: false, levels: [], aggregate_geometry: false }}
          availableColumns={plots.fileAnalysis.columns || []}
          onChange={(hierarchy) => updatePlots({ hierarchy })}
        />
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
                    <div className="flex items-center justify-between">
                      <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20 flex-1">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <AlertDescription>
                          Fichier chargé : {shape.file.name}
                        </AlertDescription>
                      </Alert>
                      <Button
                        variant="outline"
                        size="sm"
                        className="ml-2"
                        onClick={() => updateShapes(index, {
                          file: null,
                          fileAnalysis: null,
                          fieldMappings: {},
                          type: ''
                        })}
                      >
                        Changer de fichier
                      </Button>
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
