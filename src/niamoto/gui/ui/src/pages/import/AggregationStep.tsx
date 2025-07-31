import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useImport } from './ImportContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
                    {t('common:file.loaded', { fileName: plots.file.name })}
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
                    linkField: 'locality',
                    occurrenceLinkField: 'plot_name'
                  })}
                >
                  {t('aggregations.plots.changeFile')}
                </Button>
              </div>

              {plots.fileAnalysis && (
                <ColumnMapper
                  importType="plots"
                  fileAnalysis={{
                    ...plots.fileAnalysis,
                    occurrenceColumns: occurrences.fileAnalysis?.columns || []
                  }}
                  onMappingComplete={(mappings) => {
                    updatePlots({ fieldMappings: mappings })
                  }}
                />
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
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Map className="w-5 h-5" />
              {t('aggregations.shapes.title')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t('aggregations.shapes.description')}
            </p>
          </div>
          <Button onClick={addShape} size="sm" variant="outline">
            <Plus className="w-4 h-4 mr-2" />
            {t('aggregations.shapes.addShape')}
          </Button>
        </div>

        {(!shapes || shapes.length === 0) && (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              {t('aggregations.shapes.noShapes')}
            </CardContent>
          </Card>
        )}

        {shapes?.map((shape, index) => (
          <Card key={index}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  {t('aggregations.shapes.shapeNumber', { number: index + 1 })}
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
                      {t('aggregations.plots.changeFile')}
                    </Button>
                  </div>

                  {shape.fileAnalysis && (
                    <ColumnMapper
                      importType="shapes"
                      fileAnalysis={shape.fileAnalysis}
                      onMappingComplete={(mappings) => {
                        // Only update if mappings have actually changed
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
                  )}

                  {shape.fileAnalysis?.summary && (
                    <Alert>
                      <AlertDescription className="space-y-1">
                        <div className="flex justify-between">
                          <span>{t('aggregations.shapes.featureCount')}</span>
                          <span className="font-medium">{shape.fileAnalysis.summary.feature_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>{t('aggregations.shapes.crs')}</span>
                          <span className="font-medium">{shape.fileAnalysis.summary.crs}</span>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
