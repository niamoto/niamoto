/**
 * ReferenceConfigEditor - Edit reference entity configuration
 *
 * Allows editing:
 * - Kind (hierarchical, flat, spatial)
 * - Connector settings (path, format)
 * - Hierarchy configuration (levels, id_column, name_column)
 * - API Enrichment configuration
 * - Schema fields
 */

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Plus,
  X,
  FileText,
  Leaf,
  Map,
  Zap,
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'
import { ApiEnrichmentConfig, type ApiConfig, type ApiCategory } from './ApiEnrichmentConfig'

interface ReferenceConfigEditorProps {
  referenceName: string
  onSaved?: () => void
}

interface EnrichmentConfig {
  plugin?: string
  enabled?: boolean
  config?: {
    api_url?: string
    auth_method?: 'none' | 'api_key' | 'bearer' | 'basic'
    auth_params?: {
      key?: string
      location?: 'header' | 'query'
      name?: string
      username?: string
      password?: string
    }
    query_params?: Record<string, string>
    query_field?: string
    query_param_name?: string
    rate_limit?: number
    cache_results?: boolean
    response_mapping?: Record<string, string>
  }
}

// Convert from EnrichmentConfig (YAML structure) to ApiConfig (form structure)
function enrichmentToApiConfig(enrichment?: EnrichmentConfig): ApiConfig {
  return {
    enabled: enrichment?.enabled ?? false,
    plugin: enrichment?.plugin ?? 'api_taxonomy_enricher',
    api_url: enrichment?.config?.api_url ?? '',
    auth_method: (enrichment?.config?.auth_method as ApiConfig['auth_method']) ?? 'none',
    auth_params: enrichment?.config?.auth_params,
    query_params: enrichment?.config?.query_params,
    query_field: enrichment?.config?.query_field ?? 'full_name',
    query_param_name: enrichment?.config?.query_param_name ?? 'q',
    rate_limit: enrichment?.config?.rate_limit ?? 2,
    cache_results: enrichment?.config?.cache_results ?? true,
    response_mapping: enrichment?.config?.response_mapping,
  }
}

// Convert from ApiConfig (form structure) to EnrichmentConfig (YAML structure)
function apiConfigToEnrichment(apiConfig: ApiConfig): EnrichmentConfig {
  return {
    plugin: apiConfig.plugin,
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
  }
}

interface ReferenceConfig {
  kind?: string
  description?: string
  connector?: {
    type?: string
    format?: string
    path?: string
    sources?: Array<{ name: string; path: string; name_field: string }>
  }
  hierarchy?: {
    strategy?: string
    levels?: string[]
    incomplete_rows?: string
    id_strategy?: string
    id_column?: string
    name_column?: string
  }
  schema?: {
    id_field?: string
    fields?: Record<string, string>
  }
  enrichment?: EnrichmentConfig[]
}

async function fetchReferenceConfig(name: string): Promise<{ name: string; config: ReferenceConfig }> {
  const response = await apiClient.get(`/config/references/${name}/config`)
  return response.data
}

async function saveReferenceConfig(name: string, config: ReferenceConfig): Promise<void> {
  await apiClient.put(`/config/references/${name}/config`, config)
}

export function ReferenceConfigEditor({ referenceName, onSaved }: ReferenceConfigEditorProps) {
  const queryClient = useQueryClient()
  const [localConfig, setLocalConfig] = useState<ReferenceConfig | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['reference-config', referenceName],
    queryFn: () => fetchReferenceConfig(referenceName),
  })

  const mutation = useMutation({
    mutationFn: (config: ReferenceConfig) => saveReferenceConfig(referenceName, config),
    onSuccess: () => {
      setHasChanges(false)
      queryClient.invalidateQueries({ queryKey: ['references'] })
      queryClient.invalidateQueries({ queryKey: ['reference-config', referenceName] })
      onSaved?.()
    },
  })

  useEffect(() => {
    if (data?.config) {
      setLocalConfig(data.config)
      setHasChanges(false)
    }
  }, [data])

  const updateConfig = (updates: Partial<ReferenceConfig>) => {
    if (!localConfig) return
    setLocalConfig({ ...localConfig, ...updates })
    setHasChanges(true)
  }

  const updateHierarchy = (updates: Partial<NonNullable<ReferenceConfig['hierarchy']>>) => {
    if (!localConfig) return
    setLocalConfig({
      ...localConfig,
      hierarchy: { ...localConfig.hierarchy, ...updates },
    })
    setHasChanges(true)
  }

  const updateConnector = (updates: Partial<NonNullable<ReferenceConfig['connector']>>) => {
    if (!localConfig) return
    setLocalConfig({
      ...localConfig,
      connector: { ...localConfig.connector, ...updates },
    })
    setHasChanges(true)
  }

  // Get first enrichment config (we only support one for now)
  const enrichment = localConfig?.enrichment?.[0]

  // Handle changes from ApiEnrichmentConfig component
  const handleEnrichmentChange = (apiConfig: ApiConfig) => {
    if (!localConfig) return
    setLocalConfig({
      ...localConfig,
      enrichment: [apiConfigToEnrichment(apiConfig)],
    })
    setHasChanges(true)
  }

  const addHierarchyLevel = () => {
    if (!localConfig?.hierarchy) return
    const levels = localConfig.hierarchy.levels || []
    updateHierarchy({ levels: [...levels, ''] })
  }

  const updateHierarchyLevel = (index: number, value: string) => {
    if (!localConfig?.hierarchy?.levels) return
    const levels = [...localConfig.hierarchy.levels]
    levels[index] = value
    updateHierarchy({ levels })
  }

  const removeHierarchyLevel = (index: number) => {
    if (!localConfig?.hierarchy?.levels) return
    const levels = localConfig.hierarchy.levels.filter((_, i) => i !== index)
    updateHierarchy({ levels })
  }

  const handleSave = () => {
    if (localConfig) {
      mutation.mutate(localConfig)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Erreur lors du chargement de la configuration
        </AlertDescription>
      </Alert>
    )
  }

  if (!localConfig) return null

  const isHierarchical = localConfig.kind === 'hierarchical'
  const isSpatial = localConfig.kind === 'spatial'

  // Determine API category based on reference kind
  const getApiCategory = (): ApiCategory => {
    if (isHierarchical) return 'taxonomy'
    if (isSpatial) return 'spatial'
    return 'all'  // For flat references, show all options
  }

  return (
    <div className="space-y-6">
      {/* Save status */}
      {mutation.isSuccess && (
        <Alert className="bg-success/10 border-success/30">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <AlertDescription className="text-success">
            Configuration sauvegardee avec succes
          </AlertDescription>
        </Alert>
      )}

      {mutation.isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Erreur lors de la sauvegarde
          </AlertDescription>
        </Alert>
      )}

      {/* Basic Info */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Informations generales</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Nom</Label>
              <Input value={referenceName} disabled />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={localConfig.kind || 'flat'}
                onValueChange={(value) => updateConfig({ kind: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="flat">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Flat (simple)
                    </div>
                  </SelectItem>
                  <SelectItem value="hierarchical">
                    <div className="flex items-center gap-2">
                      <Leaf className="h-4 w-4" />
                      Hierarchique
                    </div>
                  </SelectItem>
                  <SelectItem value="spatial">
                    <div className="flex items-center gap-2">
                      <Map className="h-4 w-4" />
                      Spatial
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Description</Label>
            <Input
              value={localConfig.description || ''}
              onChange={(e) => updateConfig({ description: e.target.value })}
              placeholder="Description de la reference..."
            />
          </div>
        </CardContent>
      </Card>

      {/* Connector Settings */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Source de donnees</CardTitle>
          <CardDescription>Configuration du connecteur</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Type de connecteur</Label>
              <Select
                value={localConfig.connector?.type || 'file'}
                onValueChange={(value) => updateConnector({ type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="file">Fichier</SelectItem>
                  <SelectItem value="derived">Derive</SelectItem>
                  <SelectItem value="file_multi_feature">Multi-feature (spatial)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {localConfig.connector?.type === 'file' && (
              <div className="space-y-2">
                <Label>Format</Label>
                <Select
                  value={localConfig.connector?.format || 'csv'}
                  onValueChange={(value) => updateConnector({ format: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="excel">Excel</SelectItem>
                    <SelectItem value="json">JSON</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          {localConfig.connector?.type !== 'derived' && (
            <div className="space-y-2">
              <Label>Chemin du fichier</Label>
              <Input
                value={localConfig.connector?.path || ''}
                onChange={(e) => updateConnector({ path: e.target.value })}
                placeholder="data/fichier.csv"
                className="font-mono text-sm"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Hierarchy Settings (only for hierarchical) */}
      {isHierarchical && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Leaf className="h-4 w-4" />
              Configuration hierarchique
            </CardTitle>
            <CardDescription>Niveaux et colonnes de la hierarchie</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Strategie</Label>
                <Select
                  value={localConfig.hierarchy?.strategy || 'adjacency_list'}
                  onValueChange={(value) => updateHierarchy({ strategy: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="adjacency_list">Liste d'adjacence</SelectItem>
                    <SelectItem value="nested_set">Nested Set</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Lignes incompletes</Label>
                <Select
                  value={localConfig.hierarchy?.incomplete_rows || 'skip'}
                  onValueChange={(value) => updateHierarchy({ incomplete_rows: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="skip">Ignorer</SelectItem>
                    <SelectItem value="keep">Conserver</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator />

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Niveaux de hierarchie</Label>
                <Button variant="outline" size="sm" onClick={addHierarchyLevel}>
                  <Plus className="h-3 w-3 mr-1" />
                  Ajouter
                </Button>
              </div>
              <div className="space-y-2">
                {(localConfig.hierarchy?.levels || []).map((level, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <Badge variant="outline" className="w-8 justify-center">
                      {index + 1}
                    </Badge>
                    <Input
                      value={level}
                      onChange={(e) => updateHierarchyLevel(index, e.target.value)}
                      placeholder={`Niveau ${index + 1}`}
                      className="flex-1"
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeHierarchyLevel(index)}
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {(!localConfig.hierarchy?.levels || localConfig.hierarchy.levels.length === 0) && (
                  <p className="text-sm text-muted-foreground py-2">
                    Aucun niveau defini. Cliquez sur "Ajouter" pour definir les niveaux.
                  </p>
                )}
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Colonne ID</Label>
                <Input
                  value={localConfig.hierarchy?.id_column || ''}
                  onChange={(e) => updateHierarchy({ id_column: e.target.value })}
                  placeholder="id_taxonref"
                />
              </div>
              <div className="space-y-2">
                <Label>Colonne Nom</Label>
                <Input
                  value={localConfig.hierarchy?.name_column || ''}
                  onChange={(e) => updateHierarchy({ name_column: e.target.value })}
                  placeholder="taxaname"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* API Enrichment Settings */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Zap className="h-4 w-4" />
                Enrichissement API
              </CardTitle>
              <CardDescription>
                Enrichir les donnees via une API externe
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="enrichment-enabled" className="text-sm">
                {enrichment?.enabled ? 'Active' : 'Desactive'}
              </Label>
              <Switch
                id="enrichment-enabled"
                checked={enrichment?.enabled || false}
                onCheckedChange={(checked) => {
                  const currentApiConfig = enrichmentToApiConfig(enrichment)
                  handleEnrichmentChange({ ...currentApiConfig, enabled: checked })
                }}
              />
            </div>
          </div>
        </CardHeader>
        {enrichment?.enabled && (
          <CardContent>
            <ApiEnrichmentConfig
              config={enrichmentToApiConfig(enrichment)}
              onChange={handleEnrichmentChange}
              category={getApiCategory()}
            />
          </CardContent>
        )}
      </Card>

      {/* Save Button */}
      <div className="flex items-center justify-between pt-4 border-t">
        <div className="text-sm text-muted-foreground">
          {hasChanges ? (
            <span className="text-warning">Modifications non sauvegardees</span>
          ) : (
            <span>Aucune modification</span>
          )}
        </div>
        <Button
          onClick={handleSave}
          disabled={!hasChanges || mutation.isPending}
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sauvegarde...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Sauvegarder
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
