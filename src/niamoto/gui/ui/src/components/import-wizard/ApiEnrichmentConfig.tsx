import { useState } from 'react'
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
  api_url: string
  auth_method: 'none' | 'api_key' | 'bearer' | 'basic'
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
      api_url: 'https://services.tropicos.org/Name/Search',
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
        tropicos_nomenclatural_status: '[0].NomenclaturalStatus'
      }
    }
  }
]

export function ApiEnrichmentConfig({ config, onChange }: ApiEnrichmentConfigProps) {
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
        message: 'Please enter an API URL'
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
          message: 'API connection successful!',
          fields
        })
      } else {
        setTestResult({
          success: false,
          message: response.data.error || 'API test failed'
        })
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: `Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`
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
          <TabsTrigger value="connection">Connection</TabsTrigger>
          <TabsTrigger value="authentication">Authentication</TabsTrigger>
          <TabsTrigger value="mapping">Field Mapping</TabsTrigger>
        </TabsList>

        <TabsContent value="connection" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                API Connection
              </CardTitle>
              <CardDescription>
                Configure the API endpoint and test the connection
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Preset APIs */}
              <div className="space-y-2">
                <Label>Quick Setup</Label>
                <div className="flex gap-2">
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

              <Separator />

              {/* API URL */}
              <div className="space-y-2">
                <Label htmlFor="api-url">API URL</Label>
                <Input
                  id="api-url"
                  type="url"
                  value={config.api_url}
                  onChange={(e) => onChange({ ...config, api_url: e.target.value })}
                  placeholder="https://api.example.com/v1/taxons"
                />
              </div>

              {/* Query Field */}
              <div className="space-y-2">
                <Label htmlFor="query-field">Query Field Name</Label>
                <Input
                  id="query-field"
                  value={config.query_field}
                  onChange={(e) => onChange({ ...config, query_field: e.target.value })}
                  placeholder="e.g., name, q, query"
                />
                <p className="text-xs text-muted-foreground">
                  The parameter name used to send the taxon name to the API
                </p>
              </div>

              {/* Query Parameters */}
              <div className="space-y-2">
                <Label>Additional Query Parameters</Label>
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
                      placeholder="Parameter name"
                      value={newQueryParam.key}
                      onChange={(e) => setNewQueryParam({ ...newQueryParam, key: e.target.value })}
                      className="flex-1"
                    />
                    <Input
                      placeholder="Value"
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
                      Testing...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Test Connection
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
                Authentication
              </CardTitle>
              <CardDescription>
                Configure how to authenticate with the API
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Auth Method */}
              <div className="space-y-2">
                <Label htmlFor="auth-method">Authentication Method</Label>
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
                    <SelectItem value="none">No Authentication</SelectItem>
                    <SelectItem value="api_key">API Key</SelectItem>
                    <SelectItem value="bearer">Bearer Token</SelectItem>
                    <SelectItem value="basic">Basic Auth</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* API Key Configuration */}
              {config.auth_method === 'api_key' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="api-key">API Key</Label>
                    <Input
                      id="api-key"
                      type="password"
                      value={config.auth_params?.key || ''}
                      onChange={(e) => onChange({
                        ...config,
                        auth_params: { ...config.auth_params, key: e.target.value }
                      })}
                      placeholder="Your API key"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="key-location">Key Location</Label>
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
                        <SelectItem value="header">HTTP Header</SelectItem>
                        <SelectItem value="query">Query Parameter</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="key-name">Parameter/Header Name</Label>
                    <Input
                      id="key-name"
                      value={config.auth_params?.name || 'apiKey'}
                      onChange={(e) => onChange({
                        ...config,
                        auth_params: { ...config.auth_params, name: e.target.value }
                      })}
                      placeholder="e.g., apiKey, X-API-Key"
                    />
                  </div>
                </>
              )}

              {/* Bearer Token */}
              {config.auth_method === 'bearer' && (
                <div className="space-y-2">
                  <Label htmlFor="bearer-token">Bearer Token</Label>
                  <Input
                    id="bearer-token"
                    type="password"
                    value={config.auth_params?.key || ''}
                    onChange={(e) => onChange({
                      ...config,
                      auth_params: { ...config.auth_params, key: e.target.value }
                    })}
                    placeholder="Your bearer token"
                  />
                </div>
              )}

              {/* Basic Auth */}
              {config.auth_method === 'basic' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="username">Username</Label>
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
                    <Label htmlFor="password">Password</Label>
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
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="mapping" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Response Field Mapping</CardTitle>
              <CardDescription>
                Map API response fields to Niamoto database fields
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {testResult?.fields && testResult.fields.length > 0 && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    Available fields detected from API test. Click to add to mapping.
                  </AlertDescription>
                </Alert>
              )}

              {/* Current Mappings */}
              <div className="space-y-2">
                <Label>Current Mappings</Label>
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
                <Label>Add New Mapping</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Niamoto field (e.g., endemic)"
                    value={newMapping.target}
                    onChange={(e) => setNewMapping({ ...newMapping, target: e.target.value })}
                    className="flex-1"
                  />
                  <Input
                    placeholder="API path (e.g., endemique)"
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
                  <Label>Available API Fields</Label>
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
                  <p className="mb-2">Common Niamoto fields you might want to map:</p>
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
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
