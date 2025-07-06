import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Info, AlertCircle, Database, Globe, GitBranch } from 'lucide-react'
import type { ImportConfig, ImportType } from './ImportWizard'
import { TaxonomyHierarchyEditor } from './TaxonomyHierarchyEditor'
import { ApiEnrichmentConfig, type ApiConfig } from './ApiEnrichmentConfig'
import { PlotHierarchyConfig, type HierarchyConfig } from './PlotHierarchyConfig'
import { PropertySelector } from './PropertySelector'

interface AdvancedOptionsProps {
  config: ImportConfig
  onUpdate: (updates: Partial<ImportConfig>) => void
}

interface TaxonomyOptions {
  ranks: string[]
  apiEnrichment?: ApiConfig
  updateExisting: boolean
}

interface PlotOptions {
  hierarchy: HierarchyConfig
  linkField?: string
  occurrenceLinkField?: string
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
  type: string
  properties: string[]
}

export function AdvancedOptions({ config, onUpdate }: AdvancedOptionsProps) {
  const [taxonomyOptions, setTaxonomyOptions] = useState<TaxonomyOptions>({
    ranks: ['family', 'genus', 'species', 'infra'],
    apiEnrichment: {
      enabled: false,
      plugin: 'api_taxonomy_enricher',
      api_url: '',
      auth_method: 'none',
      query_field: 'full_name',
      rate_limit: 2.0,
      cache_results: true,
      query_params: {},
      response_mapping: {}
    },
    updateExisting: true,
  })

  const [plotOptions, setPlotOptions] = useState<PlotOptions>({
    hierarchy: {
      enabled: false,
      levels: [],
      aggregate_geometry: true
    },
    linkField: 'locality',
    occurrenceLinkField: 'plot_name',
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
    type: 'default',
    properties: [],
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

  // Initialize advanced options on mount
  useEffect(() => {
    if (config.importType && !config.advancedOptions?.[config.importType]) {
      // Set default options based on import type
      switch (config.importType) {
        case 'taxonomy':
          updateOptions('taxonomy', taxonomyOptions)
          break
        case 'plots':
          updateOptions('plots', plotOptions)
          break
        case 'occurrences':
          updateOptions('occurrences', occurrenceOptions)
          break
        case 'shapes':
          updateOptions('shapes', shapeOptions)
          break
      }
    }
  }, [config.importType]) // Only run when import type changes

  const renderTaxonomyOptions = () => (
    <div className="space-y-6">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Taxonomy will be extracted from the occurrence data file. Make sure your file contains
          the necessary taxonomy columns (family, genus, species, etc.)
        </AlertDescription>
      </Alert>

      <div className="space-y-6">
        {/* Hierarchy Configuration */}
        <TaxonomyHierarchyEditor
          ranks={taxonomyOptions.ranks}
          fileColumns={config.fileAnalysis?.columns || []}
          fieldMappings={config.fieldMappings || {}}
          onChange={({ ranks, mappings }) => {
            // Update taxonomy options with new ranks
            const newOptions = { ...taxonomyOptions, ranks }
            setTaxonomyOptions(newOptions)
            updateOptions('taxonomy', newOptions)

            // Update field mappings with hierarchy mappings
            if (config.fieldMappings) {
              const updatedMappings = { ...config.fieldMappings }
              // Remove old rank mappings
              taxonomyOptions.ranks.forEach(rank => {
                delete updatedMappings[rank]
              })
              // Add new mappings
              Object.assign(updatedMappings, mappings)
              onUpdate({ fieldMappings: updatedMappings })
            }
          }}
        />

        {/* API Enrichment */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="api-enrichment">API Enrichment</Label>
              <p className="text-sm text-muted-foreground">
                Enrich taxonomy data using external biodiversity APIs
              </p>
            </div>
            <Switch
              id="api-enrichment"
              checked={taxonomyOptions.apiEnrichment?.enabled || false}
              onCheckedChange={(checked) => {
                const newOptions = {
                  ...taxonomyOptions,
                  apiEnrichment: {
                    ...taxonomyOptions.apiEnrichment!,
                    enabled: checked
                  }
                }
                setTaxonomyOptions(newOptions)
                updateOptions('taxonomy', newOptions)
              }}
            />
          </div>

          {taxonomyOptions.apiEnrichment?.enabled && (
            <div className="mt-4">
              <ApiEnrichmentConfig
                config={taxonomyOptions.apiEnrichment}
                onChange={(apiConfig) => {
                  const newOptions = {
                    ...taxonomyOptions,
                    apiEnrichment: apiConfig
                  }
                  setTaxonomyOptions(newOptions)
                  updateOptions('taxonomy', newOptions)
                }}
              />
            </div>
          )}
        </div>

        {/* Update Existing */}
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
      {/* Hierarchy Configuration */}
      <PlotHierarchyConfig
        hierarchy={plotOptions.hierarchy}
        availableColumns={config.fileAnalysis?.columns || []}
        onChange={(hierarchy) => {
          const newOptions = { ...plotOptions, hierarchy }
          setPlotOptions(newOptions)
          updateOptions('plots', newOptions)
        }}
      />

      {/* Linking Fields */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Occurrence Linking</CardTitle>
          <CardDescription>
            Configure how occurrences will be linked to plots
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="link-field">Plot Link Field</Label>
            <Select
              value={plotOptions.linkField}
              onValueChange={(value) => {
                const newOptions = { ...plotOptions, linkField: value }
                setPlotOptions(newOptions)
                updateOptions('plots', newOptions)
              }}
            >
              <SelectTrigger id="link-field">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="id">ID</SelectItem>
                <SelectItem value="plot_id">Plot ID</SelectItem>
                <SelectItem value="locality">Locality</SelectItem>
                {config.fieldMappings && Object.keys(config.fieldMappings).map(field => (
                  <SelectItem key={field} value={field}>{field}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Field in plot_ref table used for linking with occurrences
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="occurrence-link-field">Occurrence Link Field</Label>
            <Input
              id="occurrence-link-field"
              value={plotOptions.occurrenceLinkField}
              onChange={(e) => {
                const newOptions = { ...plotOptions, occurrenceLinkField: e.target.value }
                setPlotOptions(newOptions)
                updateOptions('plots', newOptions)
              }}
              placeholder="e.g., plot_name, locality_name"
            />
            <p className="text-xs text-muted-foreground">
              Corresponding field in occurrences table
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Other Options */}
      <div className="space-y-4">
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
        <div className="space-y-2">
          <Label htmlFor="shape-type">Shape Type</Label>
          <p className="text-sm text-muted-foreground">
            A unique identifier for this shape category (e.g., country, province, region)
          </p>
          <Input
            id="shape-type"
            value={shapeOptions.type}
            onChange={(e) => {
              const newOptions = { ...shapeOptions, type: e.target.value }
              setShapeOptions(newOptions)
              updateOptions('shapes', newOptions)
            }}
            placeholder="e.g., country, province, commune"
          />
        </div>

        <div className="space-y-2">
          <Label>Additional Properties</Label>
          <p className="text-sm text-muted-foreground">
            Select attribute fields to import from the shape file
          </p>
          {config.fileAnalysis?.columns && config.fieldMappings && (
            <PropertySelector
              availableColumns={config.fileAnalysis.columns}
              selectedProperties={shapeOptions.properties}
              excludeColumns={[
                config.fieldMappings.name || 'name',
                config.fieldMappings.id || '',
                'geometry',
              ].filter(Boolean)}
              onSelectionChange={(properties) => {
                const newOptions = { ...shapeOptions, properties }
                setShapeOptions(newOptions)
                updateOptions('shapes', newOptions)
              }}
            />
          )}
          {!config.fileAnalysis?.columns && (
            <p className="text-sm text-muted-foreground italic">
              Upload a file first to see available properties
            </p>
          )}
        </div>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertTitle>Multiple Shape Types</AlertTitle>
        <AlertDescription>
          You can import multiple shape types by running the import wizard again after this import completes.
          Each shape type will be added to your configuration.
        </AlertDescription>
      </Alert>
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
