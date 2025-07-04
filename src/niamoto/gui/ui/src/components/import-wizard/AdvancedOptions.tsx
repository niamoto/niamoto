import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Info, AlertCircle, Database, Globe, GitBranch } from 'lucide-react'
import type { ImportConfig, ImportType } from './ImportWizard'

interface AdvancedOptionsProps {
  config: ImportConfig
  onUpdate: (updates: Partial<ImportConfig>) => void
}

interface TaxonomyOptions {
  useApiEnrichment: boolean
  apiProvider: 'gbif' | 'powo' | 'none'
  rateLimit: number
  extractFromOccurrences: boolean
  updateExisting: boolean
}

interface PlotOptions {
  importHierarchy: boolean
  hierarchyDelimiter: string
  generateIds: boolean
  idPrefix: string
  validateGeometry: boolean
}

interface OccurrenceOptions {
  linkToPlots: boolean
  createMissingTaxa: boolean
  validateCoordinates: boolean
  duplicateStrategy: 'skip' | 'update' | 'error'
}

interface ShapeOptions {
  simplifyGeometry: boolean
  toleranceMeters: number
  calculateArea: boolean
  calculatePerimeter: boolean
}

export function AdvancedOptions({ config, onUpdate }: AdvancedOptionsProps) {
  const [taxonomyOptions, setTaxonomyOptions] = useState<TaxonomyOptions>({
    useApiEnrichment: false,
    apiProvider: 'none',
    rateLimit: 1,
    extractFromOccurrences: false,
    updateExisting: true,
  })

  const [plotOptions, setPlotOptions] = useState<PlotOptions>({
    importHierarchy: false,
    hierarchyDelimiter: '/',
    generateIds: false,
    idPrefix: 'PLOT_',
    validateGeometry: true,
  })

  const [occurrenceOptions, setOccurrenceOptions] = useState<OccurrenceOptions>({
    linkToPlots: true,
    createMissingTaxa: false,
    validateCoordinates: true,
    duplicateStrategy: 'skip',
  })

  const [shapeOptions, setShapeOptions] = useState<ShapeOptions>({
    simplifyGeometry: false,
    toleranceMeters: 10,
    calculateArea: true,
    calculatePerimeter: true,
  })

  const updateOptions = (type: ImportType, options: any) => {
    onUpdate({
      ...config,
      advancedOptions: {
        ...config.advancedOptions,
        [type]: options,
      },
    })
  }

  const renderTaxonomyOptions = () => (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="api-enrichment">API Enrichment</Label>
            <p className="text-sm text-muted-foreground">
              Enrich taxonomy data using external APIs
            </p>
          </div>
          <Switch
            id="api-enrichment"
            checked={taxonomyOptions.useApiEnrichment}
            onCheckedChange={(checked) => {
              const newOptions = { ...taxonomyOptions, useApiEnrichment: checked }
              setTaxonomyOptions(newOptions)
              updateOptions('taxonomy', newOptions)
            }}
          />
        </div>

        {taxonomyOptions.useApiEnrichment && (
          <div className="ml-6 space-y-4 border-l-2 border-muted pl-6">
            <div className="space-y-2">
              <Label htmlFor="api-provider">API Provider</Label>
              <Select
                value={taxonomyOptions.apiProvider}
                onValueChange={(value: 'gbif' | 'powo' | 'none') => {
                  const newOptions = { ...taxonomyOptions, apiProvider: value }
                  setTaxonomyOptions(newOptions)
                  updateOptions('taxonomy', newOptions)
                }}
              >
                <SelectTrigger id="api-provider">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gbif">GBIF - Global Biodiversity Information Facility</SelectItem>
                  <SelectItem value="powo">POWO - Plants of the World Online</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="rate-limit">Rate Limit (requests per second)</Label>
              <div className="flex items-center space-x-4">
                <Slider
                  id="rate-limit"
                  min={0.1}
                  max={5}
                  step={0.1}
                  value={[taxonomyOptions.rateLimit]}
                  onValueChange={([value]) => {
                    const newOptions = { ...taxonomyOptions, rateLimit: value }
                    setTaxonomyOptions(newOptions)
                    updateOptions('taxonomy', newOptions)
                  }}
                  className="flex-1"
                />
                <span className="w-12 text-sm font-medium">{taxonomyOptions.rateLimit}</span>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="extract-occurrences">Extract from Occurrences</Label>
            <p className="text-sm text-muted-foreground">
              Build taxonomy from occurrence data instead of file
            </p>
          </div>
          <Switch
            id="extract-occurrences"
            checked={taxonomyOptions.extractFromOccurrences}
            onCheckedChange={(checked) => {
              const newOptions = { ...taxonomyOptions, extractFromOccurrences: checked }
              setTaxonomyOptions(newOptions)
              updateOptions('taxonomy', newOptions)
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="update-existing">Update Existing Taxa</Label>
            <p className="text-sm text-muted-foreground">
              Update taxa that already exist in the database
            </p>
          </div>
          <Switch
            id="update-existing"
            checked={taxonomyOptions.updateExisting}
            onCheckedChange={(checked) => {
              const newOptions = { ...taxonomyOptions, updateExisting: checked }
              setTaxonomyOptions(newOptions)
              updateOptions('taxonomy', newOptions)
            }}
          />
        </div>
      </div>
    </div>
  )

  const renderPlotOptions = () => (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="import-hierarchy">Import Plot Hierarchy</Label>
            <p className="text-sm text-muted-foreground">
              Create hierarchical relationships between plots
            </p>
          </div>
          <Switch
            id="import-hierarchy"
            checked={plotOptions.importHierarchy}
            onCheckedChange={(checked) => {
              const newOptions = { ...plotOptions, importHierarchy: checked }
              setPlotOptions(newOptions)
              updateOptions('plots', newOptions)
            }}
          />
        </div>

        {plotOptions.importHierarchy && (
          <div className="ml-6 space-y-4 border-l-2 border-muted pl-6">
            <div className="space-y-2">
              <Label htmlFor="hierarchy-delimiter">Hierarchy Delimiter</Label>
              <Input
                id="hierarchy-delimiter"
                value={plotOptions.hierarchyDelimiter}
                onChange={(e) => {
                  const newOptions = { ...plotOptions, hierarchyDelimiter: e.target.value }
                  setPlotOptions(newOptions)
                  updateOptions('plots', newOptions)
                }}
                placeholder="e.g., / or >"
                className="w-32"
              />
              <p className="text-xs text-muted-foreground">
                Character used to separate hierarchy levels in plot names
              </p>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="generate-ids">Generate Plot IDs</Label>
            <p className="text-sm text-muted-foreground">
              Automatically generate IDs for plots without them
            </p>
          </div>
          <Switch
            id="generate-ids"
            checked={plotOptions.generateIds}
            onCheckedChange={(checked) => {
              const newOptions = { ...plotOptions, generateIds: checked }
              setPlotOptions(newOptions)
              updateOptions('plots', newOptions)
            }}
          />
        </div>

        {plotOptions.generateIds && (
          <div className="ml-6 space-y-4 border-l-2 border-muted pl-6">
            <div className="space-y-2">
              <Label htmlFor="id-prefix">ID Prefix</Label>
              <Input
                id="id-prefix"
                value={plotOptions.idPrefix}
                onChange={(e) => {
                  const newOptions = { ...plotOptions, idPrefix: e.target.value }
                  setPlotOptions(newOptions)
                  updateOptions('plots', newOptions)
                }}
                placeholder="e.g., PLOT_"
                className="w-48"
              />
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="validate-geometry">Validate Geometry</Label>
            <p className="text-sm text-muted-foreground">
              Check that plot geometries are valid
            </p>
          </div>
          <Switch
            id="validate-geometry"
            checked={plotOptions.validateGeometry}
            onCheckedChange={(checked) => {
              const newOptions = { ...plotOptions, validateGeometry: checked }
              setPlotOptions(newOptions)
              updateOptions('plots', newOptions)
            }}
          />
        </div>
      </div>
    </div>
  )

  const renderOccurrenceOptions = () => (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="link-plots">Link to Plots</Label>
            <p className="text-sm text-muted-foreground">
              Automatically link occurrences to existing plots
            </p>
          </div>
          <Switch
            id="link-plots"
            checked={occurrenceOptions.linkToPlots}
            onCheckedChange={(checked) => {
              const newOptions = { ...occurrenceOptions, linkToPlots: checked }
              setOccurrenceOptions(newOptions)
              updateOptions('occurrences', newOptions)
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="create-taxa">Create Missing Taxa</Label>
            <p className="text-sm text-muted-foreground">
              Create taxa entries for unknown taxon IDs
            </p>
          </div>
          <Switch
            id="create-taxa"
            checked={occurrenceOptions.createMissingTaxa}
            onCheckedChange={(checked) => {
              const newOptions = { ...occurrenceOptions, createMissingTaxa: checked }
              setOccurrenceOptions(newOptions)
              updateOptions('occurrences', newOptions)
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="validate-coords">Validate Coordinates</Label>
            <p className="text-sm text-muted-foreground">
              Check that coordinates are within valid ranges
            </p>
          </div>
          <Switch
            id="validate-coords"
            checked={occurrenceOptions.validateCoordinates}
            onCheckedChange={(checked) => {
              const newOptions = { ...occurrenceOptions, validateCoordinates: checked }
              setOccurrenceOptions(newOptions)
              updateOptions('occurrences', newOptions)
            }}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="duplicate-strategy">Duplicate Handling</Label>
          <Select
            value={occurrenceOptions.duplicateStrategy}
            onValueChange={(value: 'skip' | 'update' | 'error') => {
              const newOptions = { ...occurrenceOptions, duplicateStrategy: value }
              setOccurrenceOptions(newOptions)
              updateOptions('occurrences', newOptions)
            }}
          >
            <SelectTrigger id="duplicate-strategy">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="skip">Skip duplicates</SelectItem>
              <SelectItem value="update">Update existing records</SelectItem>
              <SelectItem value="error">Error on duplicates</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  )

  const renderShapeOptions = () => (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="simplify-geometry">Simplify Geometry</Label>
            <p className="text-sm text-muted-foreground">
              Reduce complexity of shape geometries
            </p>
          </div>
          <Switch
            id="simplify-geometry"
            checked={shapeOptions.simplifyGeometry}
            onCheckedChange={(checked) => {
              const newOptions = { ...shapeOptions, simplifyGeometry: checked }
              setShapeOptions(newOptions)
              updateOptions('shapes', newOptions)
            }}
          />
        </div>

        {shapeOptions.simplifyGeometry && (
          <div className="ml-6 space-y-4 border-l-2 border-muted pl-6">
            <div className="space-y-2">
              <Label htmlFor="tolerance">Simplification Tolerance (meters)</Label>
              <div className="flex items-center space-x-4">
                <Slider
                  id="tolerance"
                  min={1}
                  max={100}
                  step={1}
                  value={[shapeOptions.toleranceMeters]}
                  onValueChange={([value]) => {
                    const newOptions = { ...shapeOptions, toleranceMeters: value }
                    setShapeOptions(newOptions)
                    updateOptions('shapes', newOptions)
                  }}
                  className="flex-1"
                />
                <span className="w-12 text-sm font-medium">{shapeOptions.toleranceMeters}m</span>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="calculate-area">Calculate Area</Label>
            <p className="text-sm text-muted-foreground">
              Automatically calculate shape areas
            </p>
          </div>
          <Switch
            id="calculate-area"
            checked={shapeOptions.calculateArea}
            onCheckedChange={(checked) => {
              const newOptions = { ...shapeOptions, calculateArea: checked }
              setShapeOptions(newOptions)
              updateOptions('shapes', newOptions)
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="calculate-perimeter">Calculate Perimeter</Label>
            <p className="text-sm text-muted-foreground">
              Automatically calculate shape perimeters
            </p>
          </div>
          <Switch
            id="calculate-perimeter"
            checked={shapeOptions.calculatePerimeter}
            onCheckedChange={(checked) => {
              const newOptions = { ...shapeOptions, calculatePerimeter: checked }
              setShapeOptions(newOptions)
              updateOptions('shapes', newOptions)
            }}
          />
        </div>
      </div>
    </div>
  )

  const renderOptionsForType = () => {
    switch (config.importType) {
      case 'taxonomy':
        return renderTaxonomyOptions()
      case 'plots':
        return renderPlotOptions()
      case 'occurrences':
        return renderOccurrenceOptions()
      case 'shapes':
        return renderShapeOptions()
      default:
        return null
    }
  }

  const getIcon = () => {
    switch (config.importType) {
      case 'taxonomy':
        return <Database className="h-5 w-5" />
      case 'plots':
        return <GitBranch className="h-5 w-5" />
      case 'occurrences':
        return <Globe className="h-5 w-5" />
      case 'shapes':
        return <Info className="h-5 w-5" />
      default:
        return <AlertCircle className="h-5 w-5" />
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getIcon()}
            Advanced Options - {config.importType.charAt(0).toUpperCase() + config.importType.slice(1)}
          </CardTitle>
          <CardDescription>
            Configure additional settings for your {config.importType} import
          </CardDescription>
        </CardHeader>
        <CardContent>{renderOptionsForType()}</CardContent>
      </Card>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          These options allow you to fine-tune the import process. Default settings work well for most cases.
        </AlertDescription>
      </Alert>
    </div>
  )
}
