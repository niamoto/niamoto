import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Info,
  Key,
  Globe,
  Loader2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Plus,
  X,
  ArrowRight
} from 'lucide-react'
import axios from 'axios'

interface ApiEnrichmentConfigProps {
  config: ApiConfig
  onChange: (config: ApiConfig) => void
}

export interface ApiConfig {
  enabled: boolean
  plugin: string
  api_url?: string
  api_key?: string  // For Tropicos direct config
  auth_method?: 'none' | 'api_key' | 'bearer' | 'basic'
  auth_params?: {
    key?: string
    location?: 'header' | 'query'
    name?: string
    username?: string
    password?: string
  }
  query_params?: Record<string, string>
  query_field: string
  rate_limit: number
  cache_results: boolean
  response_mapping?: Record<string, string>
  // Tropicos specific options
  include_images?: boolean
  include_synonyms?: boolean
  include_distributions?: boolean
  include_references?: boolean
}

interface ApiField {
  path: string
  type: string
  example?: any
}

interface PresetAPI {
  name: string
  config: {
    api_url: string
    auth_method: 'none' | 'api_key' | 'bearer' | 'basic'
    query_params: Record<string, string>
    response_mapping: Record<string, string>
  }
}

const PRESET_APIS: PresetAPI[] = [
  {
    name: 'Endemia NC',
    config: {
      api_url: 'https://api.endemia.nc/v1/taxons',
      auth_method: 'api_key',
      query_params: {
        section: 'flore',
        maxitem: '1',
        excludes: 'meta,links',
        includes: 'images'
      },
      response_mapping: {
        id_endemia: 'id',
        id_florical: 'id_florical',
        endemia_url: 'endemia_url',
        endemic: 'endemique',
        protected: 'protected',
        redlist_cat: 'categorie_uicn',
        image_small_thumb: 'image.small_thumb',
        image_big_thumb: 'image.big_thumb'
      }
    }
  },
  {
    name: 'GBIF',
    config: {
      api_url: 'https://api.gbif.org/v1/species/match',
      auth_method: 'none',
      query_params: {
        kingdom: 'Plantae'
      },
      response_mapping: {
        gbif_key: 'usageKey',
        gbif_status: 'status',
        gbif_confidence: 'confidence',
        canonical_name: 'canonicalName',
        authorship: 'authorship',
        family: 'family',
        genus: 'genus',
        species: 'species'
      }
    }
  },
  {
    name: 'WFO (World Flora Online)',
    config: {
      api_url: 'https://list.worldfloraonline.org/matching_rest',
      auth_method: 'none',
      query_params: {
        limit: '1',
        matching_includes: 'higher_taxa'
      },
      response_mapping: {
        wfo_id: 'id',
        wfo_name: 'full_name_plain',
        wfo_status: 'taxonomic_status',
        wfo_family: 'family',
        wfo_genus: 'genus',
        wfo_authors: 'authors'
      }
    }
  },
  {
    name: 'IPNI',
    config: {
      api_url: 'https://www.ipni.org/api/1/search',
      auth_method: 'none',
      query_params: {
        perPage: '1'
      },
      response_mapping: {
        ipni_id: 'id',
        ipni_authors: 'authors',
        ipni_publication: 'publishedIn',
        ipni_year: 'publicationYear',
        ipni_family: 'family'
      }
    }
  },
  {
    name: 'iNaturalist',
    config: {
      api_url: 'https://api.inaturalist.org/v1/taxa',
      auth_method: 'none',
      query_params: {
        q: '',  // Will be filled with search term
        is_active: 'true',
        taxon_id: '47126',  // Plantae
        per_page: '1'
      },
      response_mapping: {
        inat_id: 'results[0].id',
        inat_name: 'results[0].name',
        inat_rank: 'results[0].rank',
        inat_conservation_status: 'results[0].conservation_status.status',
        inat_photo: 'results[0].default_photo.medium_url',
        inat_observations_count: 'results[0].observations_count'
      }
    }
  },
  {
    name: 'Tropicos',
    config: {
      api_url: 'http://services.tropicos.org/Name/Search',
      auth_method: 'api_key',
      query_params: {
        format: 'json',
        type: 'exact'
      },
      response_mapping: {
        tropicos_id: '[0].NameId',
        tropicos_name: '[0].ScientificName',
        tropicos_author: '[0].ScientificNameWithAuthors',
        tropicos_family: '[0].Family',
        tropicos_nomenclatural_status: '[0].NomenclaturalStatus',
        tropicos_symbol: '[0].Symbol',
        tropicos_rank: '[0].RankAbbreviation',
        tropicos_accepted_id: '[0].AcceptedNameId',
        tropicos_accepted_name: '[0].AcceptedName'
      }
    }
  },
  {
    name: 'Tropicos Extended (Images & Details)',
    config: {
      api_url: 'http://services.tropicos.org/Name/Search',
      auth_method: 'api_key',
      query_params: {
        format: 'json',
        type: 'exact'
      },
      response_mapping: {
        // Basic info
        tropicos_id: '[0].NameId',
        tropicos_name: '[0].ScientificName',
        tropicos_author: '[0].ScientificNameWithAuthors',
        tropicos_family: '[0].Family',
        tropicos_nomenclatural_status: '[0].NomenclaturalStatus',
        tropicos_symbol: '[0].Symbol',
        tropicos_rank: '[0].RankAbbreviation',
        tropicos_accepted_id: '[0].AcceptedNameId',
        tropicos_accepted_name: '[0].AcceptedName',
        // Note: Pour récupérer les images, il faut faire un appel séparé à:
        // http://services.tropicos.org/Name/{NameId}/Images?apikey={key}&format=json
        // Les images seront dans: [0].ImageKindText, [0].ImageURL, [0].LowResolutionURL
        // Pour la distribution: http://services.tropicos.org/Name/{NameId}/Distributions
        // Pour les synonymes: http://services.tropicos.org/Name/{NameId}/Synonyms
        external_id: '[0].NameId',
        external_url: '[0].Source'
      }
    }
  }
]

const SPECIAL_PLUGINS = [
  {
    name: 'Tropicos Complete (with Images)',
    plugin: 'tropicos_enricher',
    requiresApiKey: true,
    description: 'Fetches comprehensive data from Tropicos including images, synonyms, distributions, and references'
  }
]

export function ApiEnrichmentConfig({ config, onChange }: ApiEnrichmentConfigProps) {
  const { t } = useTranslation(['import', 'common'])
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
    fields?: ApiField[]
  } | null>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [newQueryParam, setNewQueryParam] = useState({ key: '', value: '' })
  const [newMapping, setNewMapping] = useState({ target: '', source: '' })

  const handlePresetSelect = (presetName: string) => {
    const preset = PRESET_APIS.find(p => p.name === presetName)
    if (preset) {
      onChange({
        ...config,
        api_url: preset.config.api_url,
        auth_method: preset.config.auth_method,
        query_params: preset.config.query_params || {},
        response_mapping: preset.config.response_mapping || {},
      })
    }
  }

  const testApiConnection = async () => {
    if (!config.api_url) {
      setTestResult({
        success: false,
        message: t('apiEnrichment.connection.urlRequired')
      })
      return
    }

    setIsTesting(true)
    setTestResult(null)

    try {
      // Build headers
      const headers: Record<string, string> = {}
      if (config.auth_method === 'api_key' && config.auth_params?.location === 'header') {
        headers[config.auth_params.name || 'apiKey'] = config.auth_params.key || ''
      } else if (config.auth_method === 'bearer') {
        headers['Authorization'] = `Bearer ${config.auth_params?.key || ''}`
      } else if (config.auth_method === 'basic') {
        const auth = btoa(`${config.auth_params?.username}:${config.auth_params?.password}`)
        headers['Authorization'] = `Basic ${auth}`
      }

      // Build query params
      const params: Record<string, string> = { ...config.query_params }
      if (config.auth_method === 'api_key' && config.auth_params?.location === 'query') {
        params[config.auth_params.name || 'apiKey'] = config.auth_params.key || ''
      }

      // Add a test query
      params[config.query_field] = 'Pinus'

      // Make test request via our backend
      const response = await axios.post('/api/files/test-api', {
        url: config.api_url,
        headers,
        params
      })

      if (response.data.success) {
        // Extract fields from response
        const fields = extractFieldsFromResponse(response.data.data)
        setTestResult({
          success: true,
          message: t('common:messages.testSuccessful'),
          fields
        })
      } else {
        setTestResult({
          success: false,
          message: response.data.error || t('apiEnrichment.connection.testFailed')
        })
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: `${t('common:messages.connectionFailed')} ${error instanceof Error ? error.message : t('common:messages.unknownError')}`
      })
    } finally {
      setIsTesting(false)
    }
  }

  const extractFieldsFromResponse = (data: any, prefix = ''): ApiField[] => {
    const fields: ApiField[] = []

    if (typeof data === 'object' && data !== null) {
      if (Array.isArray(data) && data.length > 0) {
        // For arrays, analyze the first item
        const item = data[0]
        Object.entries(item).forEach(([key, value]) => {
          const path = prefix ? `${prefix}[0].${key}` : `[0].${key}`
          if (typeof value === 'object' && value !== null) {
            fields.push(...extractFieldsFromResponse(value, path))
          } else {
            fields.push({
              path,
              type: typeof value,
              example: value
            })
          }
        })
      } else {
        // For objects
        Object.entries(data).forEach(([key, value]) => {
          const path = prefix ? `${prefix}.${key}` : key
          if (typeof value === 'object' && value !== null) {
            fields.push(...extractFieldsFromResponse(value, path))
          } else {
            fields.push({
              path,
              type: typeof value,
              example: value
            })
          }
        })
      }
    }

    return fields
  }

  const addQueryParam = () => {
    if (newQueryParam.key && newQueryParam.value) {
      onChange({
        ...config,
        query_params: {
          ...config.query_params,
          [newQueryParam.key]: newQueryParam.value
        }
      })
      setNewQueryParam({ key: '', value: '' })
    }
  }

  const removeQueryParam = (key: string) => {
    const { [key]: _, ...rest } = config.query_params || {}
    onChange({
      ...config,
      query_params: rest
    })
  }

  const addMapping = () => {
    if (newMapping.target && newMapping.source) {
      onChange({
        ...config,
        response_mapping: {
          ...config.response_mapping,
          [newMapping.target]: newMapping.source
        }
      })
      setNewMapping({ target: '', source: '' })
    }
  }

  const removeMapping = (key: string) => {
    const { [key]: _, ...rest } = config.response_mapping || {}
    onChange({
      ...config,
      response_mapping: rest
    })
  }

  return (
    <div className="space-y-6">
      <Tabs defaultValue="connection" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="connection">{t('apiEnrichment.sections.connection')}</TabsTrigger>
          <TabsTrigger value="authentication">{t('apiEnrichment.sections.authentication')}</TabsTrigger>
          <TabsTrigger value="mapping">{t('apiEnrichment.sections.fieldMapping')}</TabsTrigger>
        </TabsList>

        <TabsContent value="connection" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                {t('apiEnrichment.connection.title')}
              </CardTitle>
              <CardDescription>
                {t('apiEnrichment.connection.description')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Preset APIs */}
              <div className="space-y-2">
                <Label>{t('apiEnrichment.connection.quickSetup')}</Label>
                <div className="flex gap-2 flex-wrap">
                  {PRESET_APIS.map(preset => (
                    <Button
                      key={preset.name}
                      variant="outline"
                      size="sm"
                      onClick={() => handlePresetSelect(preset.name)}
                    >
                      {preset.name}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Special Plugins */}
              <div className="space-y-2">
                <Label>{t('apiEnrichment.connection.specialPlugins', 'Special Plugins')}</Label>
                <div className="space-y-2">
                  {SPECIAL_PLUGINS.map(plugin => (
                    <Card key={plugin.name} className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium">{plugin.name}</h4>
                          <p className="text-sm text-muted-foreground">{plugin.description}</p>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            onChange({
                              ...config,
                              plugin: plugin.plugin,
                              enabled: true,
                              query_field: 'full_name',
                              rate_limit: 1,
                              cache_results: true,
                              include_images: true,
                              include_synonyms: true,
                              include_distributions: true,
                              include_references: true
                            })
                          }}
                        >
                          Use
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              <Separator />

              {/* Special configuration for Tropicos plugin */}
              {config.plugin === 'tropicos_enricher' ? (
                <div className="space-y-4">
                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      Tropicos Complete plugin will fetch images, synonyms, distributions, and references in a single operation.
                    </AlertDescription>
                  </Alert>

                  <div className="space-y-2">
                    <Label htmlFor="tropicos-api-key">Tropicos API Key *</Label>
                    <Input
                      id="tropicos-api-key"
                      type="password"
                      value={config.api_key || ''}
                      onChange={(e) => onChange({ ...config, api_key: e.target.value })}
                      placeholder="Enter your Tropicos API key"
                    />
                    <p className="text-xs text-muted-foreground">
                      Get your API key from <a href="http://services.tropicos.org/help?requestkey" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Tropicos Services</a>
                    </p>
                  </div>

                  <div className="space-y-3">
                    <Label>Data to fetch</Label>
                    <div className="space-y-2">
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={config.include_images !== false}
                          onChange={(e) => onChange({ ...config, include_images: e.target.checked })}
                          className="rounded"
                        />
                        <span className="text-sm">Images (specimen photos)</span>
                      </label>
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={config.include_synonyms !== false}
                          onChange={(e) => onChange({ ...config, include_synonyms: e.target.checked })}
                          className="rounded"
                        />
                        <span className="text-sm">Synonyms</span>
                      </label>
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={config.include_distributions !== false}
                          onChange={(e) => onChange({ ...config, include_distributions: e.target.checked })}
                          className="rounded"
                        />
                        <span className="text-sm">Geographic distributions</span>
                      </label>
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={config.include_references !== false}
                          onChange={(e) => onChange({ ...config, include_references: e.target.checked })}
                          className="rounded"
                        />
                        <span className="text-sm">Bibliographic references</span>
                      </label>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  {/* API URL */}
                  <div className="space-y-2">
                    <Label htmlFor="api-url">{t('apiEnrichment.connection.apiUrl')}</Label>
                    <Input
                      id="api-url"
                      type="url"
                      value={config.api_url || ''}
                      onChange={(e) => onChange({ ...config, api_url: e.target.value })}
                      placeholder="https://api.example.com/v1/taxons"
                    />
                  </div>
                </>
              )}

              {/* Query Field */}
              <div className="space-y-2">
                <Label htmlFor="query-field">{t('apiEnrichment.connection.queryFieldName')}</Label>
                <Input
                  id="query-field"
                  value={config.query_field}
                  onChange={(e) => onChange({ ...config, query_field: e.target.value })}
                  placeholder={t('apiEnrichment.connection.queryFieldPlaceholder')}
                />
                <p className="text-xs text-muted-foreground">
                  {t('apiEnrichment.connection.queryFieldDescription')}
                </p>
              </div>

              {/* Query Parameters */}
              <div className="space-y-2">
                <Label>{t('apiEnrichment.connection.additionalParams')}</Label>
                <div className="space-y-2 rounded-lg border p-3">
                  {Object.entries(config.query_params || {}).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2">
                      <code className="text-sm bg-muted px-2 py-1 rounded">{key}</code>
                      <span className="text-sm">=</span>
                      <code className="text-sm bg-muted px-2 py-1 rounded flex-1">{value}</code>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeQueryParam(key)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}

                  <div className="flex gap-2 mt-2">
                    <Input
                      placeholder={t('apiEnrichment.connection.paramName')}
                      value={newQueryParam.key}
                      onChange={(e) => setNewQueryParam({ ...newQueryParam, key: e.target.value })}
                      className="flex-1"
                    />
                    <Input
                      placeholder={t('apiEnrichment.connection.value')}
                      value={newQueryParam.value}
                      onChange={(e) => setNewQueryParam({ ...newQueryParam, value: e.target.value })}
                      className="flex-1"
                    />
                    <Button onClick={addQueryParam} size="sm">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Test Connection */}
              <div className="flex items-center gap-4">
                <Button
                  onClick={testApiConnection}
                  disabled={isTesting || !config.api_url}
                  className="w-full"
                >
                  {isTesting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      {t('common:status.testing')}
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      {t('common:actions.testConnection')}
                    </>
                  )}
                </Button>
              </div>

              {testResult && (
                <Alert variant={testResult.success ? 'default' : 'destructive'}>
                  {testResult.success ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  <AlertDescription>{testResult.message}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="authentication" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                {t('apiEnrichment.authentication.title')}
              </CardTitle>
              <CardDescription>
                {t('apiEnrichment.authentication.description')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Special case for Tropicos plugin */}
              {config.plugin === 'tropicos_enricher' ? (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    Authentication for Tropicos is configured in the Connection tab.
                  </AlertDescription>
                </Alert>
              ) : (
                <>
              {/* Auth Method */}
              <div className="space-y-2">
                <Label htmlFor="auth-method">{t('apiEnrichment.authentication.method')}</Label>
                <Select
                  value={config.auth_method}
                  onValueChange={(value: 'none' | 'api_key' | 'bearer' | 'basic') =>
                    onChange({ ...config, auth_method: value })
                  }
                >
                  <SelectTrigger id="auth-method">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">{t('apiEnrichment.authentication.none')}</SelectItem>
                    <SelectItem value="api_key">{t('apiEnrichment.authentication.apiKey')}</SelectItem>
                    <SelectItem value="bearer">{t('apiEnrichment.authentication.bearerToken')}</SelectItem>
                    <SelectItem value="basic">{t('apiEnrichment.authentication.basicAuth')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* API Key Configuration */}
              {config.auth_method === 'api_key' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="api-key">{t('apiEnrichment.authentication.apiKey')}</Label>
                    <Input
                      id="api-key"
                      type="password"
                      value={config.auth_params?.key || ''}
                      onChange={(e) => onChange({
                        ...config,
                        auth_params: { ...config.auth_params, key: e.target.value }
                      })}
                      placeholder={t('apiEnrichment.authentication.apiKeyPlaceholder')}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="key-location">{t('apiEnrichment.authentication.keyLocation')}</Label>
                    <Select
                      value={config.auth_params?.location || 'header'}
                      onValueChange={(value: 'header' | 'query') =>
                        onChange({
                          ...config,
                          auth_params: { ...config.auth_params, location: value }
                        })
                      }
                    >
                      <SelectTrigger id="key-location">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="header">{t('apiEnrichment.authentication.httpHeader')}</SelectItem>
                        <SelectItem value="query">{t('apiEnrichment.authentication.queryParameter')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="key-name">{t('apiEnrichment.authentication.paramHeaderName')}</Label>
                    <Input
                      id="key-name"
                      value={config.auth_params?.name || 'apiKey'}
                      onChange={(e) => onChange({
                        ...config,
                        auth_params: { ...config.auth_params, name: e.target.value }
                      })}
                      placeholder={t('apiEnrichment.authentication.paramHeaderPlaceholder')}
                    />
                  </div>
                </>
              )}

              {/* Bearer Token */}
              {config.auth_method === 'bearer' && (
                <div className="space-y-2">
                  <Label htmlFor="bearer-token">{t('apiEnrichment.authentication.bearerToken')}</Label>
                  <Input
                    id="bearer-token"
                    type="password"
                    value={config.auth_params?.key || ''}
                    onChange={(e) => onChange({
                      ...config,
                      auth_params: { ...config.auth_params, key: e.target.value }
                    })}
                    placeholder={t('apiEnrichment.authentication.bearerTokenPlaceholder')}
                  />
                </div>
              )}

              {/* Basic Auth */}
              {config.auth_method === 'basic' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="username">{t('apiEnrichment.authentication.username')}</Label>
                    <Input
                      id="username"
                      value={config.auth_params?.username || ''}
                      onChange={(e) => onChange({
                        ...config,
                        auth_params: { ...config.auth_params, username: e.target.value }
                      })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">{t('apiEnrichment.authentication.password')}</Label>
                    <Input
                      id="password"
                      type="password"
                      value={config.auth_params?.password || ''}
                      onChange={(e) => onChange({
                        ...config,
                        auth_params: { ...config.auth_params, password: e.target.value }
                      })}
                    />
                  </div>
                </>
              )}
              </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="mapping" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('apiEnrichment.fieldMapping.title')}</CardTitle>
              <CardDescription>
                {t('apiEnrichment.fieldMapping.description')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Special case for Tropicos plugin */}
              {config.plugin === 'tropicos_enricher' ? (
                <div className="space-y-4">
                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      The Tropicos Complete plugin automatically maps the following fields:
                    </AlertDescription>
                  </Alert>

                  <div className="space-y-2 rounded-lg border p-4">
                    <h4 className="font-medium">Automatic field mappings:</h4>
                    <div className="space-y-1 text-sm">
                      <div>• <code>tropicos_id</code> - Tropicos Name ID</div>
                      <div>• <code>tropicos_name</code> - Scientific name</div>
                      <div>• <code>tropicos_author</code> - Name with authors</div>
                      <div>• <code>tropicos_family</code> - Family name</div>
                      <div>• <code>tropicos_nomenclatural_status</code> - Nomenclatural status</div>
                      <div>• <code>image_url</code> - Main specimen image URL</div>
                      <div>• <code>image_thumbnail</code> - Thumbnail image URL</div>
                      <div>• <code>images</code> - Array of all images with metadata</div>
                      <div>• <code>synonyms</code> - List of synonyms</div>
                      <div>• <code>distribution_countries</code> - List of countries</div>
                      <div>• <code>references</code> - Bibliographic references</div>
                      <div>• <code>external_id</code> - Tropicos ID for external reference</div>
                      <div>• <code>external_url</code> - Link to Tropicos page</div>
                    </div>
                  </div>

                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      All enriched data will be available in the <code>api_enrichment</code> field of each taxon.
                    </AlertDescription>
                  </Alert>
                </div>
              ) : (
                <>
              {testResult?.fields && testResult.fields.length > 0 && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    {t('apiEnrichment.fieldMapping.availableFields')}
                  </AlertDescription>
                </Alert>
              )}

              {/* Current Mappings */}
              <div className="space-y-2">
                <Label>{t('apiEnrichment.fieldMapping.currentMappings')}</Label>
                <ScrollArea className="h-[200px] rounded-lg border p-3">
                  <div className="space-y-2">
                    {Object.entries(config.response_mapping || {}).map(([target, source]) => (
                      <div key={target} className="flex items-center gap-2">
                        <Badge variant="outline">{target}</Badge>
                        <ArrowRight className="h-3 w-3" />
                        <code className="text-sm bg-muted px-2 py-1 rounded flex-1">{source}</code>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeMapping(target)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>

              {/* Add New Mapping */}
              <div className="space-y-2">
                <Label>{t('apiEnrichment.fieldMapping.addNewMapping')}</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder={t('apiEnrichment.fieldMapping.niamotoFieldPlaceholder')}
                    value={newMapping.target}
                    onChange={(e) => setNewMapping({ ...newMapping, target: e.target.value })}
                    className="flex-1"
                  />
                  <Input
                    placeholder={t('apiEnrichment.fieldMapping.apiPathPlaceholder')}
                    value={newMapping.source}
                    onChange={(e) => setNewMapping({ ...newMapping, source: e.target.value })}
                    className="flex-1"
                  />
                  <Button onClick={addMapping} size="sm">
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Detected Fields */}
              {testResult?.fields && testResult.fields.length > 0 && (
                <div className="space-y-2">
                  <Label>{t('apiEnrichment.fieldMapping.availableApiFields')}</Label>
                  <ScrollArea className="h-[200px] rounded-lg border p-3">
                    <div className="space-y-2">
                      {testResult.fields.map((field) => (
                        <div
                          key={field.path}
                          className="flex items-center justify-between p-2 hover:bg-accent rounded cursor-pointer"
                          onClick={() => setNewMapping({ ...newMapping, source: field.path })}
                        >
                          <div>
                            <code className="text-sm">{field.path}</code>
                            <span className="ml-2 text-xs text-muted-foreground">
                              ({field.type})
                            </span>
                          </div>
                          {field.example !== undefined && (
                            <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                              {String(field.example)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              )}

              {/* Common Fields Suggestions */}
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <p className="mb-2">{t('apiEnrichment.fieldMapping.commonFields')}</p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {['endemic', 'protected', 'redlist_cat', 'image_url', 'external_id', 'external_url'].map(field => (
                      <Badge
                        key={field}
                        variant="secondary"
                        className="cursor-pointer"
                        onClick={() => setNewMapping({ ...newMapping, target: field })}
                      >
                        {field}
                      </Badge>
                    ))}
                  </div>
                </AlertDescription>
              </Alert>
              </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
