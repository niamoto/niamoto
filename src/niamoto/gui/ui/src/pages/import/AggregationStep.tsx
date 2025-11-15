import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useImport } from './ImportContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { FileUpload } from '@/components/import-wizard/FileUpload'
import { MultiFileUpload } from '@/components/import-wizard/MultiFileUpload'
import { ColumnMapper } from '@/components/import-wizard/ColumnMapper'
import { PlotHierarchyConfig } from './components/PlotHierarchyConfig'
import { analyzeFile } from '@/lib/api/import'
import {
  MapPin,
  Map,
  Info,
  Plus,
  Trash2,
  CheckCircle,
  Loader2,
  AlertCircle
} from 'lucide-react'

export function AggregationStep() {
  const { t } = useTranslation(['import', 'common'])
  const { state, updatePlots, updateShapes, addShape, removeShape } = useImport()
  const { occurrences, plots, shapes } = state
  const [isAnalyzing, setIsAnalyzing] = useState<Record<string, boolean>>({})

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
    // Extract filename without extension as default type
    const defaultType = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ')

    updateShapes(index, { file, fileAnalysis: null })
    const key = `shape-${index}`
    setIsAnalyzing(prev => ({ ...prev, [key]: true }))

    try {
      const analysis = await analyzeFile(file, 'shapes')

      // Add default type to suggestions if not already present
      if (!analysis.suggestions?.type || analysis.suggestions.type.length === 0) {
        analysis.suggestions = {
          ...analysis.suggestions,
          type: [defaultType]
        }
      }

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

  const handleMultipleShapeFiles = async (files: File[]) => {
    // Add shapes for each file
    const currentShapesCount = shapes?.length || 0

    // Create a shape entry for each file
    for (let i = 0; i < files.length; i++) {
      addShape()
    }

    // Process each file
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const index = currentShapesCount + i
      await handleShapeFileSelect(file, index)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">{t('aggregations.title')}</h2>
        <p className="text-muted-foreground mt-2">
          {t('aggregations.description')}
        </p>
      </div>

      <Alert>
        <Info className="w-4 h-4" />
        <AlertDescription>
          {t('aggregations.info')}
        </AlertDescription>
      </Alert>

      {/* Plots configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="w-5 h-5" />
            {t('aggregations.plots.title')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!plots?.file && !plots?.fileAnalysis?.fromConfig ? (
            <FileUpload
              onFileSelect={handlePlotFileSelect}
              acceptedFormats={['.csv']}
              isAnalyzing={isAnalyzing.plots}
            />
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Alert className={plots?.fileAnalysis?.fromConfig ? "border-blue-200 bg-blue-50 dark:bg-blue-900/20 flex-1" : "border-green-200 bg-green-50 dark:bg-green-900/20 flex-1"}>
                  {plots?.fileAnalysis?.fromConfig ? (
                    <>
                      <Info className="w-4 h-4 text-blue-600" />
                      <AlertDescription>
                        <div className="space-y-1">
                          <div>Configuration loaded from: <span className="font-medium">{plots?.fileAnalysis?.configInfo?.path}</span></div>
                          <div className="text-xs text-muted-foreground">Please re-upload the file to continue or keep existing configuration</div>
                        </div>
                      </AlertDescription>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <AlertDescription>
                        {t('common:file.loaded', { fileName: plots.file?.name || 'Unknown' })}
                      </AlertDescription>
                    </>
                  )}
                </Alert>
                <Button
                  variant="outline"
                  size="sm"
                  className="ml-2"
                  onClick={() => updatePlots({
                    file: null,
                    fileAnalysis: null,
                    fieldMappings: {},
                    linkField: 'locality',
                    occurrenceLinkField: 'plot_name'
                  })}
                >
                  {t('aggregations.plots.changeFile')}
                </Button>
              </div>

              {(plots.fileAnalysis || plots.fieldMappings) && (
                plots.fileAnalysis?.fromConfig ? (
                  <div className="space-y-3">
                    <h3 className="font-medium text-sm">Current field mappings:</h3>
                    <div className="rounded-lg border bg-muted/50 p-3 space-y-2">
                      {Object.entries(plots.fieldMappings || {}).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm">
                          <span className="font-medium">{key}:</span>
                          <span className="text-muted-foreground">{value as string}</span>
                        </div>
                      ))}
                      {plots.linkField && (
                        <div className="flex justify-between text-sm">
                          <span className="font-medium">link_field:</span>
                          <span className="text-muted-foreground">{plots.linkField}</span>
                        </div>
                      )}
                      {plots.occurrenceLinkField && (
                        <div className="flex justify-between text-sm">
                          <span className="font-medium">occurrence_link_field:</span>
                          <span className="text-muted-foreground">{plots.occurrenceLinkField}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <ColumnMapper
                    importType="plots"
                    fileAnalysis={{
                      ...plots.fileAnalysis,
                      occurrenceColumns: occurrences.fileAnalysis?.columns || []
                    }}
                    onMappingComplete={(mappings) => {
                      // Preserve link fields when updating mappings
                      const fullMappings = {
                        ...mappings,
                        ...(plots.linkField && { link_field: plots.linkField }),
                        ...(plots.occurrenceLinkField && { occurrence_link_field: plots.occurrenceLinkField })
                      }
                      updatePlots({ fieldMappings: fullMappings })
                    }}
                  />
                )
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Configuration de la hiérarchie des plots */}
      {plots?.file && plots.fileAnalysis && (
        <PlotHierarchyConfig
          hierarchy={plots.hierarchy || { enabled: false, levels: [], aggregate_geometry: false }}
          onChange={(hierarchy) => updatePlots({ hierarchy })}
          availableColumns={plots.fileAnalysis.columns || []}
        />
      )}

      {/* Shapes configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Map className="w-5 h-5" />
            {t('aggregations.shapes.title')}
          </CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            {t('aggregations.shapes.description')}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {(!shapes || shapes.length === 0) ? (
            <>
              <MultiFileUpload
                onFilesSelect={handleMultipleShapeFiles}
                acceptedFormats={['.shp', '.geojson', '.json', '.gpkg', '.zip']}
                isAnalyzing={Object.values(isAnalyzing).some(v => v)}
              />
              <Alert>
                <Info className="w-4 h-4" />
                <AlertDescription>
                  You can select multiple shape files at once. Each file will be processed as a separate shape layer.
                </AlertDescription>
              </Alert>
            </>
          ) : (
            <div className="space-y-4">
              {shapes.some(s => s.fileAnalysis && (!s.fieldMappings?.type || !s.fieldMappings?.name)) && (
                <Alert className="mb-4">
                  <AlertCircle className="w-4 h-4" />
                  <AlertDescription>
                    Some shapes are missing required field mappings (type and name). Please map these fields before proceeding.
                  </AlertDescription>
                </Alert>
              )}
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-muted-foreground">
                  {shapes.length} file{shapes.length > 1 ? 's' : ''} loaded
                </p>
                <div className="space-x-2">
                  <Button
                    onClick={() => {
                      // Clear all shapes
                      const count = shapes.length
                      for (let i = 0; i < count; i++) {
                        removeShape(0)
                      }
                    }}
                    size="sm"
                    variant="outline"
                  >
                    Clear All
                  </Button>
                  <Button onClick={addShape} size="sm" variant="outline">
                    <Plus className="w-4 h-4 mr-2" />
                    Add More
                  </Button>
                </div>
              </div>

              {shapes.map((shape, index) => {
                const hasRequiredFields = shape.fieldMappings?.type && shape.fieldMappings?.name
                const isFromConfig = shape.fileAnalysis?.fromConfig

                return (
                  <Card key={index} className="relative">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {isFromConfig ? (
                            <Info className="w-4 h-4 text-blue-600" />
                          ) : hasRequiredFields ? (
                            <CheckCircle className="w-4 h-4 text-green-600" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-orange-500" />
                          )}
                          <span className="font-medium text-sm">
                            {isFromConfig ? (
                              shape.fileAnalysis?.configInfo?.path || `Shape ${index + 1}`
                            ) : (
                              shape.file?.name || `Shape ${index + 1}`
                            )}
                          </span>
                          {!hasRequiredFields && shape.fileAnalysis && !isFromConfig && (
                            <span className="text-xs text-orange-500">(Missing required fields)</span>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeShape(index)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </CardHeader>

                  {shape.file && !shape.fileAnalysis && isAnalyzing[`shape-${index}`] && (
                    <CardContent>
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm text-muted-foreground">Analyzing...</span>
                      </div>
                    </CardContent>
                  )}

                  {shape.fileAnalysis && (
                    <CardContent className="space-y-4 pt-0">
                      {shape.fileAnalysis.fromConfig ? (
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <Alert className="border-blue-200 bg-blue-50/50 dark:bg-blue-900/20 flex-1">
                              <Info className="w-4 h-4" />
                              <AlertDescription>
                                <div className="text-xs">
                                  Configuration loaded. Re-upload the file to update or keep existing settings.
                                </div>
                              </AlertDescription>
                            </Alert>
                            <Button
                              variant="outline"
                              size="sm"
                              className="ml-2"
                              onClick={() => {
                                // Reset the shape to allow re-upload
                                updateShapes(index, {
                                  file: null,
                                  fileAnalysis: null,
                                  // Keep existing mappings
                                  fieldMappings: shape.fieldMappings,
                                  properties: shape.properties
                                })
                              }}
                            >
                              Change File
                            </Button>
                          </div>
                          <div className="rounded-lg border bg-muted/50 p-3 space-y-2">
                            <div className="text-sm font-medium mb-2">Field mappings:</div>
                            {Object.entries(shape.fieldMappings || {}).map(([key, value]) => (
                              <div key={key} className="flex justify-between text-sm">
                                <span className="font-medium">{key}:</span>
                                <span className="text-muted-foreground">{value as string}</span>
                              </div>
                            ))}
                            {shape.properties && shape.properties.length > 0 && (
                              <>
                                <div className="text-sm font-medium mt-3 mb-1">Properties:</div>
                                <div className="text-sm text-muted-foreground">
                                  {shape.properties.join(', ')}
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex justify-end mb-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                // Reset the shape to allow re-upload
                                updateShapes(index, {
                                  file: null,
                                  fileAnalysis: null,
                                  fieldMappings: {},
                                  properties: []
                                })
                              }}
                            >
                              Change File
                            </Button>
                          </div>
                          <ColumnMapper
                            importType="shapes"
                            fileAnalysis={shape.fileAnalysis}
                            onMappingComplete={(mappings) => {
                              const currentMappings = shape.fieldMappings || {}
                              const hasChanged = Object.keys(mappings).some(
                                key => mappings[key] !== currentMappings[key]
                              ) || Object.keys(currentMappings).some(
                                key => mappings[key] !== currentMappings[key]
                              )

                              if (hasChanged) {
                                updateShapes(index, { fieldMappings: mappings })
                              }
                            }}
                          />
                        </>
                      )}

                      {shape.fileAnalysis.summary && !shape.fileAnalysis.fromConfig && (
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">{t('aggregations.shapes.featureCount')}:</span>
                            <span className="font-medium">{shape.fileAnalysis.summary.feature_count}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">{t('aggregations.shapes.crs')}:</span>
                            <span className="font-medium">{shape.fileAnalysis.summary.crs}</span>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  )}

                  {!shape.file && !shape.fileAnalysis && (
                    <CardContent>
                      <FileUpload
                        onFileSelect={(file: File) => handleShapeFileSelect(file, index)}
                        acceptedFormats={['.shp', '.geojson', '.json', '.gpkg', '.zip']}
                        isAnalyzing={isAnalyzing[`shape-${index}`]}
                      />
                    </CardContent>
                  )}
                  </Card>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
