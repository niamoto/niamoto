/**
 * ReferenceConfigForm - Edit reference configuration
 *
 * Handles three types of references:
 * 1. Derived (hierarchical) - Extracted from dataset with taxonomy hierarchy
 * 2. File - Simple CSV reference
 * 3. Spatial (file_multi_feature) - Multiple GeoPackage sources
 *
 * Includes API enrichment section for hierarchical references
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Network,
  Map,
  FileSpreadsheet,
  Sparkles,
  Plus,
  X,
  Check,
  ChevronDown,
  GripVertical,
  Link2,
  List,
  ChevronRight,
} from 'lucide-react'
import { TaxonomyHierarchyEditor } from './TaxonomyHierarchyEditor'
import { ApiEnrichmentConfig, type ApiConfig } from '@/components/config/ApiEnrichmentConfig'
import type { ReferenceConfig } from './EntityConfigEditor'

interface ReferenceConfigFormProps {
  name: string
  config: ReferenceConfig
  detectedColumns: string[]
  availableDatasets: string[]
  onSave: (updated: ReferenceConfig) => void
  onCancel?: () => void
}

// Default enrichment config
const defaultEnrichmentConfig: ApiConfig = {
  enabled: false,
  plugin: 'api_taxonomy_enricher',
  api_url: '',
  auth_method: 'none',
  query_field: 'full_name',
  query_param_name: 'q',
  rate_limit: 2,
  cache_results: true,
  response_mapping: {},
}

export function ReferenceConfigForm({
  name: _name,
  config,
  detectedColumns,
  availableDatasets,
  onSave,
  onCancel,
}: ReferenceConfigFormProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [localConfig, setLocalConfig] = useState<ReferenceConfig>({
    ...config,
    description: config.description || '',
  })

  const [enrichmentOpen, setEnrichmentOpen] = useState(
    config.enrichment?.[0]?.enabled || false
  )

  // Update description
  const updateDescription = (value: string) => {
    setLocalConfig({
      ...localConfig,
      description: value,
    })
  }

  const connectorType = localConfig.connector?.type || 'file'
  const isHierarchical = localConfig.kind === 'hierarchical' || connectorType === 'derived'
  const isSpatial = connectorType === 'file_multi_feature'

  // Get enrichment config
  const enrichmentConfig: ApiConfig = localConfig.enrichment?.[0]?.config
    ? {
        ...defaultEnrichmentConfig,
        ...localConfig.enrichment[0].config,
        enabled: localConfig.enrichment[0].enabled,
      }
    : defaultEnrichmentConfig

  const updateConnector = (key: string, value: any) => {
    setLocalConfig({
      ...localConfig,
      connector: {
        ...localConfig.connector,
        [key]: value,
      },
    })
  }

  const updateExtraction = (key: string, value: any) => {
    setLocalConfig({
      ...localConfig,
      connector: {
        ...localConfig.connector,
        extraction: {
          levels: [],
          ...localConfig.connector.extraction,
          [key]: value,
        },
      },
    })
  }

  const handleHierarchyChange = (hierarchyConfig: {
    ranks: string[]
    mappings: Record<string, string>
  }) => {
    // Update both extraction levels and hierarchy levels
    const levels = hierarchyConfig.ranks.map((rank) => ({
      name: rank,
      column: hierarchyConfig.mappings[rank] || '',
    }))

    setLocalConfig({
      ...localConfig,
      connector: {
        ...localConfig.connector,
        extraction: {
          ...localConfig.connector.extraction,
          levels,
        },
      },
      hierarchy: {
        strategy: localConfig.hierarchy?.strategy || 'adjacency_list',
        levels: hierarchyConfig.ranks,
      },
    })
  }

  const handleEnrichmentChange = (apiConfig: ApiConfig) => {
    setLocalConfig({
      ...localConfig,
      enrichment: [
        {
          plugin: 'api_taxonomy_enricher',
          enabled: apiConfig.enabled,
          config: {
            api_url: apiConfig.api_url,
            auth_method: apiConfig.auth_method,
            auth_params: apiConfig.auth_params,
            query_params: apiConfig.query_params,
            query_field: apiConfig.query_field,
            query_param_name: apiConfig.query_param_name,
            rate_limit: apiConfig.rate_limit,
            cache_results: apiConfig.cache_results,
            response_mapping: apiConfig.response_mapping,
          },
        },
      ],
    })
  }

  const toggleEnrichment = (enabled: boolean) => {
    handleEnrichmentChange({
      ...enrichmentConfig,
      enabled,
    })
    setEnrichmentOpen(enabled)
  }

  // Spatial sources management
  const addSource = () => {
    const sources = localConfig.connector.sources || []
    setLocalConfig({
      ...localConfig,
      connector: {
        ...localConfig.connector,
        sources: [
          ...sources,
          { name: '', path: '', name_field: '' },
        ],
      },
    })
  }

  const updateSource = (index: number, field: string, value: string) => {
    const sources = [...(localConfig.connector.sources || [])]
    sources[index] = { ...sources[index], [field]: value }
    setLocalConfig({
      ...localConfig,
      connector: {
        ...localConfig.connector,
        sources,
      },
    })
  }

  const removeSource = (index: number) => {
    const sources = localConfig.connector.sources?.filter((_, i) => i !== index) || []
    setLocalConfig({
      ...localConfig,
      connector: {
        ...localConfig.connector,
        sources,
      },
    })
  }

  // Schema fields management
  const addSchemaField = () => {
    const fields = localConfig.schema?.fields || []
    setLocalConfig({
      ...localConfig,
      schema: {
        ...localConfig.schema,
        fields: [...fields, { name: '', type: 'string', description: '' }],
      },
    })
  }

  const updateSchemaField = (index: number, key: string, value: string) => {
    const fields = [...(localConfig.schema?.fields || [])]
    fields[index] = { ...fields[index], [key]: value }
    setLocalConfig({
      ...localConfig,
      schema: {
        ...localConfig.schema,
        fields,
      },
    })
  }

  const removeSchemaField = (index: number) => {
    const fields = localConfig.schema?.fields?.filter((_, i) => i !== index) || []
    setLocalConfig({
      ...localConfig,
      schema: {
        ...localConfig.schema,
        fields,
      },
    })
  }

  // Links management (for file-based references)
  const addLink = () => {
    const links = localConfig.links || []
    setLocalConfig({
      ...localConfig,
      links: [...links, { entity: '', field: '', target_field: '' }],
    })
  }

  const updateLink = (index: number, key: string, value: string) => {
    const links = [...(localConfig.links || [])]
    links[index] = { ...links[index], [key]: value }
    setLocalConfig({
      ...localConfig,
      links,
    })
  }

  const removeLink = (index: number) => {
    const links = localConfig.links?.filter((_, i) => i !== index) || []
    setLocalConfig({
      ...localConfig,
      links,
    })
  }

  const handleSave = () => {
    onSave(localConfig)
  }

  // Extract current hierarchy config for TaxonomyHierarchyEditor
  const currentRanks = localConfig.hierarchy?.levels || ['family', 'genus', 'species']
  const currentMappings: Record<string, string> = {}
  localConfig.connector.extraction?.levels?.forEach((level) => {
    if (level.column) {
      currentMappings[level.name] = level.column
    }
  })

  return (
    <div className="space-y-4 pt-4">
      {/* Type indicator */}
      <div className="flex items-center gap-2">
        <Badge variant="secondary">
          {isHierarchical ? t('reference.hierarchical') : isSpatial ? t('reference.spatial') : t('reference.file')}
        </Badge>
        {localConfig.kind && (
          <Badge variant="outline">{localConfig.kind}</Badge>
        )}
      </div>

      {/* Description field - common to all types */}
      <div className="space-y-1.5">
        <Label className="text-xs">{t('common:labels.description')}</Label>
        <Input
          className="h-8 text-sm"
          value={localConfig.description || ''}
          onChange={(e) => updateDescription(e.target.value)}
          placeholder={t('reference.descriptionPlaceholder')}
        />
      </div>

      {/* Derived/Hierarchical Reference */}
      {isHierarchical && (
        <>
          {/* Source Dataset */}
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Network className="h-4 w-4" />
                {t('common:labels.source')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs">{t('reference.sourceDataset')}</Label>
                <Select
                  value={localConfig.connector.source || 'none'}
                  onValueChange={(v) => updateConnector('source', v === 'none' ? '' : v)}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder={t('common:placeholders.selectOption')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">
                      <span className="text-muted-foreground">--</span>
                    </SelectItem>
                    {availableDatasets.map((ds) => (
                      <SelectItem key={ds} value={ds}>
                        {ds}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {t('reference.selectDatasetForHierarchy')}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('reference.idColumn')}</Label>
                  <Select
                    value={localConfig.connector.extraction?.id_column || 'none'}
                    onValueChange={(v) =>
                      updateExtraction('id_column', v === 'none' ? '' : v)
                    }
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue placeholder="Auto" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">
                        <span className="text-muted-foreground">Auto (hash)</span>
                      </SelectItem>
                      {detectedColumns.map((col) => (
                        <SelectItem key={col} value={col}>
                          {col}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">{t('reference.nameColumn')}</Label>
                  <Select
                    value={localConfig.connector.extraction?.name_column || 'none'}
                    onValueChange={(v) =>
                      updateExtraction('name_column', v === 'none' ? '' : v)
                    }
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue placeholder={t('common:placeholders.selectOption')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">
                        <span className="text-muted-foreground">--</span>
                      </SelectItem>
                      {detectedColumns.map((col) => (
                        <SelectItem key={col} value={col}>
                          {col}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('reference.idStrategy')}</Label>
                  <Select
                    value={localConfig.connector.extraction?.id_strategy || 'hash'}
                    onValueChange={(v) => updateExtraction('id_strategy', v)}
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hash">hash</SelectItem>
                      <SelectItem value="auto">auto</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">{t('reference.incompleteRows')}</Label>
                  <Select
                    value={localConfig.connector.extraction?.incomplete_rows || 'skip'}
                    onValueChange={(v) => updateExtraction('incomplete_rows', v)}
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="skip">skip (ignorer)</SelectItem>
                      <SelectItem value="keep">keep (conserver)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Hierarchy Editor */}
          <TaxonomyHierarchyEditor
            ranks={currentRanks}
            fileColumns={detectedColumns}
            fieldMappings={currentMappings}
            onChange={handleHierarchyChange}
          />

          {/* Schema Fields for hierarchical */}
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <List className="h-4 w-4" />
                {t('reference.schemaFields')} ({localConfig.schema?.fields?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {localConfig.schema?.fields?.map((field, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 rounded border bg-accent/30 p-2"
                >
                  <div className="flex-1 space-y-2">
                    <div className="grid grid-cols-3 gap-2">
                      <Input
                        className="h-8 text-sm"
                        value={field.name}
                        onChange={(e) => updateSchemaField(idx, 'name', e.target.value)}
                        placeholder={t('form.fieldNamePlaceholder')}
                      />
                      <Select
                        value={field.type || 'string'}
                        onValueChange={(v) => updateSchemaField(idx, 'type', v)}
                      >
                        <SelectTrigger className="h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="string">string</SelectItem>
                          <SelectItem value="integer">integer</SelectItem>
                          <SelectItem value="float">float</SelectItem>
                          <SelectItem value="boolean">boolean</SelectItem>
                          <SelectItem value="date">date</SelectItem>
                          <SelectItem value="geometry">geometry</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input
                        className="h-8 text-sm"
                        value={field.description || ''}
                        onChange={(e) => updateSchemaField(idx, 'description', e.target.value)}
                        placeholder={t('form.fieldDescriptionPlaceholder')}
                      />
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => removeSchemaField(idx)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}

              <Button
                variant="outline"
                size="sm"
                onClick={addSchemaField}
                className="w-full"
              >
                <Plus className="mr-1 h-3 w-3" />
                {t('form.addField')}
              </Button>

              <p className="text-xs text-muted-foreground">
                {t('form.defineSchemaHint')}
              </p>
            </CardContent>
          </Card>

          {/* API Enrichment */}
          <Card>
            <Collapsible open={enrichmentOpen} onOpenChange={setEnrichmentOpen}>
              <CardHeader className="py-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Sparkles className="h-4 w-4" />
                    {t('reference.apiEnrichment')}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={enrichmentConfig.enabled}
                      onCheckedChange={toggleEnrichment}
                    />
                    <CollapsibleTrigger asChild>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        <ChevronDown
                          className={`h-4 w-4 transition-transform ${
                            enrichmentOpen ? 'rotate-180' : ''
                          }`}
                        />
                      </Button>
                    </CollapsibleTrigger>
                  </div>
                </div>
              </CardHeader>
              <CollapsibleContent>
                <CardContent className="pt-0">
                  <ApiEnrichmentConfig
                    config={enrichmentConfig}
                    onChange={handleEnrichmentChange}
                  />
                </CardContent>
              </CollapsibleContent>
            </Collapsible>
          </Card>
        </>
      )}

      {/* File Reference */}
      {!isHierarchical && !isSpatial && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <FileSpreadsheet className="h-4 w-4" />
              {t('reference.sourceFile')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">{t('reference.format')}</Label>
                <Select
                  value={localConfig.connector.format || 'csv'}
                  onValueChange={(v) => updateConnector('format', v)}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="xlsx">Excel</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs">{t('reference.path')}</Label>
                <Input
                  className="h-8 text-sm"
                  value={localConfig.connector.path || ''}
                  onChange={(e) => updateConnector('path', e.target.value)}
                  placeholder="imports/reference.csv"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">{t('reference.idColumn')}</Label>
              <Select
                value={localConfig.schema?.id_field || 'none'}
                onValueChange={(v) =>
                  setLocalConfig({
                    ...localConfig,
                    schema: {
                      ...localConfig.schema,
                      id_field: v === 'none' ? '' : v,
                    },
                  })
                }
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="Auto-detection" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">
                    <span className="text-muted-foreground">Auto-detection</span>
                  </SelectItem>
                  {detectedColumns.map((col) => (
                    <SelectItem key={col} value={col}>
                      {col}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Schema Fields - for file-based references */}
      {!isHierarchical && !isSpatial && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <List className="h-4 w-4" />
              {t('reference.schemaFields')} ({localConfig.schema?.fields?.length || 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {localConfig.schema?.fields?.map((field, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 rounded border bg-accent/30 p-2"
              >
                <div className="flex-1 space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <Input
                      className="h-8 text-sm"
                      value={field.name}
                      onChange={(e) => updateSchemaField(idx, 'name', e.target.value)}
                      placeholder={t('form.fieldNamePlaceholder')}
                    />
                    <Select
                      value={field.type || 'string'}
                      onValueChange={(v) => updateSchemaField(idx, 'type', v)}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="string">string</SelectItem>
                        <SelectItem value="integer">integer</SelectItem>
                        <SelectItem value="float">float</SelectItem>
                        <SelectItem value="boolean">boolean</SelectItem>
                        <SelectItem value="date">date</SelectItem>
                        <SelectItem value="geometry">geometry</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      className="h-8 text-sm"
                      value={field.description || ''}
                      onChange={(e) => updateSchemaField(idx, 'description', e.target.value)}
                      placeholder={t('form.fieldDescriptionPlaceholder')}
                    />
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => removeSchemaField(idx)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              onClick={addSchemaField}
              className="w-full"
            >
              <Plus className="mr-1 h-3 w-3" />
              {t('form.addField')}
            </Button>

            <p className="text-xs text-muted-foreground">
              {t('form.defineSchemaHint')}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Links - for file-based references */}
      {!isHierarchical && !isSpatial && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Link2 className="h-4 w-4" />
              {t('form.relations')} ({localConfig.links?.length || 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {localConfig.links?.map((link, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 rounded border bg-accent/30 p-2"
              >
                <div className="flex flex-1 items-center gap-2">
                  <Input
                    className="h-8 w-28 text-sm"
                    value={link.entity}
                    onChange={(e) => updateLink(idx, 'entity', e.target.value)}
                    placeholder={t('form.entity')}
                  />
                  <span className="text-xs text-muted-foreground">.</span>
                  <Input
                    className="h-8 w-28 text-sm"
                    value={link.field}
                    onChange={(e) => updateLink(idx, 'field', e.target.value)}
                    placeholder={t('form.localField')}
                  />
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  <Input
                    className="h-8 w-28 text-sm"
                    value={link.target_field}
                    onChange={(e) => updateLink(idx, 'target_field', e.target.value)}
                    placeholder={t('form.targetField')}
                  />
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => removeLink(idx)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              onClick={addLink}
              className="w-full"
            >
              <Plus className="mr-1 h-3 w-3" />
              {t('form.addRelation')}
            </Button>

            <p className="text-xs text-muted-foreground">
              {t('form.defineSchemaHint')}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Spatial Multi-Source Reference */}
      {isSpatial && (
        <>
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Map className="h-4 w-4" />
                {t('reference.spatialSources')} ({localConfig.connector.sources?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {localConfig.connector.sources?.map((source, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 rounded border bg-accent/30 p-2"
                >
                  <GripVertical className="mt-2 h-4 w-4 text-muted-foreground" />
                  <div className="flex-1 space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        className="h-8 text-sm"
                        value={source.name}
                        onChange={(e) => updateSource(idx, 'name', e.target.value)}
                        placeholder={t('form.sourceName')}
                      />
                      <Input
                        className="h-8 text-sm"
                        value={source.path}
                        onChange={(e) => updateSource(idx, 'path', e.target.value)}
                        placeholder={t('form.sourceFile')}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        className="h-8 text-sm"
                        value={source.name_field || ''}
                        onChange={(e) => updateSource(idx, 'name_field', e.target.value)}
                        placeholder={t('form.nameField')}
                      />
                      <Input
                        className="h-8 text-sm"
                        value={source.layer || ''}
                        onChange={(e) => updateSource(idx, 'layer', e.target.value)}
                        placeholder={t('form.layerOptional')}
                      />
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => removeSource(idx)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}

              <Button
                variant="outline"
                size="sm"
                onClick={addSource}
                className="w-full"
              >
                <Plus className="mr-1 h-3 w-3" />
                {t('form.addSource')}
              </Button>
            </CardContent>
          </Card>

          {/* Schema for spatial */}
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <List className="h-4 w-4" />
                Schema
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs">{t('reference.idColumn')}</Label>
                <Input
                  className="h-8 text-sm"
                  value={localConfig.schema?.id_field || ''}
                  onChange={(e) =>
                    setLocalConfig({
                      ...localConfig,
                      schema: {
                        ...localConfig.schema,
                        id_field: e.target.value,
                      },
                    })
                  }
                  placeholder="id"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs">{t('form.fields')} ({localConfig.schema?.fields?.length || 0})</Label>
                {localConfig.schema?.fields?.map((field, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 rounded border bg-accent/30 p-2"
                  >
                    <div className="flex-1 space-y-2">
                      <div className="grid grid-cols-3 gap-2">
                        <Input
                          className="h-8 text-sm"
                          value={field.name}
                          onChange={(e) => updateSchemaField(idx, 'name', e.target.value)}
                          placeholder={t('form.fieldNamePlaceholder')}
                        />
                        <Select
                          value={field.type || 'string'}
                          onValueChange={(v) => updateSchemaField(idx, 'type', v)}
                        >
                          <SelectTrigger className="h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="string">string</SelectItem>
                            <SelectItem value="integer">integer</SelectItem>
                            <SelectItem value="float">float</SelectItem>
                            <SelectItem value="boolean">boolean</SelectItem>
                            <SelectItem value="geometry">geometry</SelectItem>
                          </SelectContent>
                        </Select>
                        <Input
                          className="h-8 text-sm"
                          value={field.description || ''}
                          onChange={(e) => updateSchemaField(idx, 'description', e.target.value)}
                          placeholder={t('form.fieldDescriptionPlaceholder')}
                        />
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={() => removeSchemaField(idx)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={addSchemaField}
                  className="w-full"
                >
                  <Plus className="mr-1 h-3 w-3" />
                  {t('form.addField')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <Button variant="outline" size="sm" onClick={onCancel}>
            {t('common:actions.cancel')}
          </Button>
        )}
        <Button size="sm" onClick={handleSave}>
          <Check className="mr-1 h-3 w-3" />
          {t('common:actions.confirm')}
        </Button>
      </div>
    </div>
  )
}
