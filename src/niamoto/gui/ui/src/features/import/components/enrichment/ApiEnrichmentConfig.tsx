import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import {
  Info,
  Globe,
  Loader2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Plus,
  X,
  ArrowRight,
  ExternalLink,
  Plug,
  KeyRound,
  SlidersHorizontal,
  Braces,
} from 'lucide-react'
import axios from 'axios'
import { cn } from '@/lib/utils'
import { openExternalUrl } from '@/shared/desktop/openExternalUrl'
import {
  buildColSearchUrl,
  COL_DEFAULT_DATASET_KEY,
  getPresetsByCategory,
  PRESET_APIS_ALL,
  type ApiCategory,
} from './apiEnrichmentPresets'

interface ApiEnrichmentConfigProps {
  config: ApiConfig
  onChange: (config: ApiConfig) => void
  onPresetSelect?: (presetName: string) => void
  category?: ApiCategory
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
  query_param_name?: string  // Name of the query parameter (default: 'q')
  profile?: string
  use_name_verifier?: boolean
  name_verifier_preferred_sources?: string[]
  name_verifier_threshold?: number
  taxonomy_source?: string
  dataset_key?: number
  include_taxonomy?: boolean
  include_occurrences?: boolean
  include_media?: boolean
  include_places?: boolean
  include_references?: boolean
  include_vernaculars?: boolean
  include_distributions?: boolean
  media_limit?: number
  observation_limit?: number
  reference_limit?: number
  include_publication_details?: boolean
  include_page_preview?: boolean
  title_limit?: number
  page_limit?: number
  sample_mode?: string
  sample_count?: number
  include_bbox_summary?: boolean
  include_nearby_places?: boolean
  geometry_field?: string
  rate_limit: number
  cache_results: boolean
  response_mapping?: Record<string, string>
  chained_endpoints?: Array<{
    url_template: string
    params?: Record<string, string>
    mapping: Record<string, string>
  }>
}

interface ApiField {
  path: string
  type: string
  example?: unknown
}

export type { ApiCategory } from './apiEnrichmentPresets'

function normalizeApiUrl(value?: string): string {
  if (!value) return ''

  try {
    const url = new URL(value)
    return `${url.origin}${url.pathname}`.replace(/\/+$/, '').toLowerCase()
  } catch {
    return value.trim().replace(/\/+$/, '').toLowerCase()
  }
}

export function ApiEnrichmentConfig({
  config,
  onChange,
  onPresetSelect,
  category = 'taxonomy',
}: ApiEnrichmentConfigProps) {
  const filteredPresets = getPresetsByCategory(category)
  const { t } = useTranslation(['import', 'common'])
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
    fields?: ApiField[]
  } | null>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [newQueryParam, setNewQueryParam] = useState({ key: '', value: '' })
  const [newMapping, setNewMapping] = useState({ target: '', source: '' })
  const isGbifRichProfile = config.profile === 'gbif_rich'
  const isTropicosRichProfile = config.profile === 'tropicos_rich'
  const isColRichProfile = config.profile === 'col_rich'
  const isBhlReferencesProfile = config.profile === 'bhl_references'
  const isInaturalistRichProfile = config.profile === 'inaturalist_rich'
  const isOpenMeteoElevationProfile = config.profile === 'openmeteo_elevation_v1'
  const isGeoNamesSpatialProfile = config.profile === 'geonames_spatial_v1'
  const isStructuredProfile =
    isGbifRichProfile ||
    isTropicosRichProfile ||
    isColRichProfile ||
    isBhlReferencesProfile ||
    isInaturalistRichProfile ||
    isOpenMeteoElevationProfile ||
    isGeoNamesSpatialProfile
  const supportsNameResolution =
    isGbifRichProfile || isTropicosRichProfile || isColRichProfile
  const selectedPreset = useMemo(() => {
    const structuredPreset = filteredPresets.find((preset) => (
      preset.config.profile && preset.config.profile === config.profile
    ))
    if (structuredPreset) return structuredPreset

    const currentUrl = normalizeApiUrl(config.api_url)
    if (!currentUrl) return null

    const matchingPreset = filteredPresets.find((preset) => (
      normalizeApiUrl(preset.config.api_url) === currentUrl
    ))

    return matchingPreset ?? null
  }, [config.api_url, config.profile, filteredPresets])

  const [showPresetPicker, setShowPresetPicker] = useState(() => !selectedPreset)

  useEffect(() => {
    if (!selectedPreset) {
      setShowPresetPicker(true)
    }
  }, [selectedPreset])

  const handlePresetSelect = (presetName: string) => {
    const preset = PRESET_APIS_ALL.find(p => p.name === presetName)
    if (preset) {
      // Choose plugin based on category
      const plugin = preset.category === 'taxonomy'
        ? 'api_taxonomy_enricher'
        : preset.category === 'elevation'
          ? 'api_elevation_enricher'
          : 'api_spatial_enricher'
      onChange({
        ...config,
        plugin,
        api_url: preset.config.api_url,
        auth_method: preset.config.auth_method,
        auth_params: preset.config.auth_params ? { ...preset.config.auth_params } : undefined,
        query_params: preset.config.query_params ? { ...preset.config.query_params } : {},
        query_field: preset.config.query_field || config.query_field,
        query_param_name: preset.config.query_param_name || 'q',
        profile: preset.config.profile,
        use_name_verifier: preset.config.use_name_verifier ?? false,
        name_verifier_preferred_sources: preset.config.name_verifier_preferred_sources ?? [],
        name_verifier_threshold: preset.config.name_verifier_threshold,
        taxonomy_source: preset.config.taxonomy_source,
        dataset_key: preset.config.dataset_key,
        include_taxonomy: preset.config.include_taxonomy ?? true,
        include_occurrences: preset.config.include_occurrences ?? true,
        include_media: preset.config.include_media ?? true,
        include_places: preset.config.include_places ?? true,
        include_references: preset.config.include_references ?? true,
        include_vernaculars: preset.config.include_vernaculars ?? true,
        include_distributions: preset.config.include_distributions ?? true,
        media_limit: preset.config.media_limit ?? 3,
        observation_limit: preset.config.observation_limit ?? 5,
        reference_limit: preset.config.reference_limit ?? 5,
        include_publication_details: preset.config.include_publication_details ?? true,
        include_page_preview: preset.config.include_page_preview ?? true,
        title_limit: preset.config.title_limit ?? 5,
        page_limit: preset.config.page_limit ?? 5,
        sample_mode: preset.config.sample_mode ?? 'bbox_grid',
        sample_count: preset.config.sample_count ?? 9,
        include_bbox_summary: preset.config.include_bbox_summary ?? true,
        include_nearby_places: preset.config.include_nearby_places ?? true,
        geometry_field: preset.config.geometry_field,
        response_mapping: preset.config.response_mapping ? { ...preset.config.response_mapping } : {},
      })
      setShowPresetPicker(false)
      onPresetSelect?.(preset.name)
    }
  }

  const renderPresetLink = (label: string, url?: string) => {
    if (!url) return null

    return (
      <button
        type="button"
        onClick={() => void openExternalUrl(url)}
        className="inline-flex items-center gap-1.5 text-primary hover:underline"
      >
        {label}
        <ExternalLink className="h-3.5 w-3.5" />
      </button>
    )
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

      if (isOpenMeteoElevationProfile) {
        params.latitude = '-22.274'
        params.longitude = '166.458'
      } else if (isGeoNamesSpatialProfile) {
        params.lat = '-22.274'
        params.lng = '166.458'
      } else {
        params[config.query_param_name || 'q'] = 'Pinus'
      }

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

  const extractFieldsFromResponse = (data: unknown, prefix = ''): ApiField[] => {
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
    <div className="space-y-2">
      <Accordion type="multiple" defaultValue={['connection', 'profile-options']} className="space-y-2">
        {/* ---- Connexion ---- */}
        <AccordionItem value="connection" className="border rounded-lg">
          <AccordionTrigger className="px-4 py-3 hover:no-underline">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 border border-blue-200">
                <Plug className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-left">{t('apiEnrichment.connection.title')}</p>
                <p className="text-xs text-muted-foreground text-left">{t('apiEnrichment.connection.description')}</p>
              </div>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-4 pb-4">
            <div className="space-y-4">
              {/* Preset APIs */}
              <div className="space-y-2">
                <Label>{t('apiEnrichment.connection.quickSetup')}</Label>
                {selectedPreset && !showPresetPicker ? (
                  <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 items-start gap-3">
                        {selectedPreset.iconSrc ? (
                          <img
                            src={selectedPreset.iconSrc}
                            alt=""
                            aria-hidden="true"
                            className="mt-0.5 h-5 w-5 shrink-0 rounded-[3px] object-contain"
                          />
                        ) : (
                          <Globe className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
                        )}
                        <div className="min-w-0 space-y-1">
                          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            {t('apiEnrichment.connection.selectedPreset')}
                          </p>
                          <p className="text-sm font-medium">{selectedPreset.name}</p>
                          {selectedPreset.descriptionKey ? (
                            <p className="text-sm text-muted-foreground">
                              {t(selectedPreset.descriptionKey)}
                            </p>
                          ) : null}
                          <div className="flex flex-wrap gap-x-4 gap-y-2 pt-1 text-sm">
                            {renderPresetLink(
                              t('apiEnrichment.connection.links.website'),
                              selectedPreset.websiteUrl,
                            )}
                            {renderPresetLink(
                              t('apiEnrichment.connection.links.apiDocs'),
                              selectedPreset.docsUrl,
                            )}
                            {renderPresetLink(
                              t('apiEnrichment.connection.links.apiKeyForm'),
                              selectedPreset.keyFormUrl,
                            )}
                          </div>
                        </div>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="shrink-0"
                        onClick={() => setShowPresetPicker(true)}
                      >
                        {t('common:actions.change')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap gap-2">
                      {filteredPresets.map(preset => (
                        <Button
                          key={preset.name}
                          variant="outline"
                          size="sm"
                          className={cn(
                            'hover:border-primary/30 hover:bg-primary/5 hover:text-foreground',
                            selectedPreset?.name === preset.name &&
                              'border-primary/40 bg-primary/10 text-primary hover:border-primary/45 hover:bg-primary/15 hover:text-primary'
                          )}
                          onClick={() => handlePresetSelect(preset.name)}
                          title={preset.descriptionKey ? t(preset.descriptionKey) : undefined}
                        >
                          {preset.iconSrc ? (
                            <img
                              src={preset.iconSrc}
                              alt=""
                              aria-hidden="true"
                              className="h-4 w-4 shrink-0 rounded-[2px] object-contain"
                            />
                          ) : null}
                          {preset.name}
                        </Button>
                      ))}
                    </div>
                    {selectedPreset ? (
                      <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
                        <div className="flex items-start gap-3">
                          {selectedPreset.iconSrc ? (
                            <img
                              src={selectedPreset.iconSrc}
                              alt=""
                              aria-hidden="true"
                              className="mt-0.5 h-5 w-5 shrink-0 rounded-[3px] object-contain"
                            />
                          ) : (
                            <Globe className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
                          )}
                          <div className="min-w-0 space-y-2">
                            <div className="space-y-1">
                              <p className="text-sm font-medium">{selectedPreset.name}</p>
                              {selectedPreset.descriptionKey ? (
                                <p className="text-sm text-muted-foreground">
                                  {t(selectedPreset.descriptionKey)}
                                </p>
                              ) : null}
                            </div>
                            <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
                              {renderPresetLink(
                                t('apiEnrichment.connection.links.website'),
                                selectedPreset.websiteUrl,
                              )}
                              {renderPresetLink(
                                t('apiEnrichment.connection.links.apiDocs'),
                                selectedPreset.docsUrl,
                              )}
                              {renderPresetLink(
                                t('apiEnrichment.connection.links.apiKeyForm'),
                                selectedPreset.keyFormUrl,
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </>
                )}
              </div>

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

              {/* Query Parameter Name */}
              <div className="space-y-2">
                <Label htmlFor="query-param-name">{t('apiEnrichment.connection.queryParamName')}</Label>
                <Input
                  id="query-param-name"
                  value={config.query_param_name || 'q'}
                  onChange={(e) => onChange({ ...config, query_param_name: e.target.value })}
                  placeholder={t('apiEnrichment.connection.queryParamPlaceholder')}
                />
                <p className="text-xs text-muted-foreground">
                  {t('apiEnrichment.connection.queryParamDescription')}
                </p>
              </div>

              {/* Query Parameters */}
              <div className="space-y-2">
                <Label>{t('apiEnrichment.connection.additionalParams')}</Label>
                <div className="space-y-2 rounded-lg border p-3">
                  {Object.entries(config.query_params || {}).map(([key, value]) => (
                    <div key={key} className="grid gap-2 sm:grid-cols-[auto_auto_minmax(0,1fr)_auto] sm:items-center">
                      <code className="break-all rounded bg-muted px-2 py-1 text-sm">{key}</code>
                      <span className="hidden text-sm sm:block">=</span>
                      <code className="break-all rounded bg-muted px-2 py-1 text-sm">{value}</code>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeQueryParam(key)}
                        className="justify-self-start sm:justify-self-end"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}

                  <div className="mt-2 grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
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
                    <Button onClick={addQueryParam} size="sm" className="sm:self-stretch">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Test Connection */}
              <div>
                <Button
                  type="button"
                  onClick={testApiConnection}
                  disabled={isTesting || !config.api_url}
                  aria-busy={isTesting}
                  className="w-full"
                >
                  <span className="inline-flex w-full items-center justify-center gap-2 text-center">
                    {isTesting ? (
                      <>
                        <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                        <span>{t('common:status.testing')}</span>
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4 shrink-0" />
                        <span>{t('common:actions.testConnection')}</span>
                      </>
                    )}
                  </span>
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
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* ---- Authentification ---- */}
        <AccordionItem value="authentication" className="border rounded-lg">
          <AccordionTrigger className="px-4 py-3 hover:no-underline">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 border border-amber-200">
                <KeyRound className="h-4 w-4 text-amber-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-left">{t('apiEnrichment.authentication.title')}</p>
                <p className="text-xs text-muted-foreground text-left">{t('apiEnrichment.authentication.description')}</p>
              </div>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-4 pb-4">
            <div className="space-y-4">
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
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* ---- Options profil ---- */}
        {isStructuredProfile ? (
          <AccordionItem value="profile-options" className="border rounded-lg">
            <AccordionTrigger className="px-4 py-3 hover:no-underline">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-50 border border-green-200">
                  <SlidersHorizontal className="h-4 w-4 text-green-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-left">{t('apiEnrichment.profileOptions.title')}</p>
                  <p className="text-xs text-muted-foreground text-left">{t('apiEnrichment.profileOptions.description')}</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <div className="space-y-4">
                {isGbifRichProfile ? (
                  <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                    <div className="space-y-1">
                      <Label>{t('apiEnrichment.profileOptions.providers.gbif.title')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.profileOptions.providers.gbif.description')}
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="taxonomy-source">{t('apiEnrichment.profileOptions.common.taxonomySource')}</Label>
                      <Input
                        id="taxonomy-source"
                        value={config.taxonomy_source || 'col_xr'}
                        onChange={(e) => onChange({ ...config, taxonomy_source: e.target.value })}
                        placeholder="col_xr"
                      />
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.taxonomy')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.common.taxonomyDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_taxonomy ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_taxonomy: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.occurrences')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.common.occurrencesDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_occurrences ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_occurrences: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.media')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.gbif.mediaDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_media ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_media: checked })}
                        />
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="media-limit">{t('apiEnrichment.profileOptions.common.mediaLimit')}</Label>
                        <Input
                          id="media-limit"
                          type="number"
                          min={0}
                          value={String(config.media_limit ?? 3)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              media_limit: Number.parseInt(e.target.value || '0', 10),
                            })
                          }
                        />
                      </div>
                    </div>
                  </div>
                ) : isOpenMeteoElevationProfile ? (
                  <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                    <div className="space-y-1">
                      <Label>{t('apiEnrichment.profileOptions.providers.openMeteo.title')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.profileOptions.providers.openMeteo.description')}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="sample-mode">{t('apiEnrichment.profileOptions.common.sampleMode')}</Label>
                        <Select
                          value={config.sample_mode || 'bbox_grid'}
                          onValueChange={(value) => onChange({ ...config, sample_mode: value })}
                        >
                          <SelectTrigger id="sample-mode">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="bbox_grid">{t('apiEnrichment.profileOptions.common.sampleModeOptions.bboxGrid')}</SelectItem>
                            <SelectItem value="boundary">{t('apiEnrichment.profileOptions.common.sampleModeOptions.boundary')}</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="sample-count">{t('apiEnrichment.profileOptions.common.sampleCount')}</Label>
                        <Input
                          id="sample-count"
                          type="number"
                          min={1}
                          max={100}
                          value={String(config.sample_count ?? 9)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              sample_count: Number.parseInt(e.target.value || '1', 10),
                            })
                          }
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2 sm:col-span-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.bboxSummary')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.common.bboxSummaryDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_bbox_summary ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_bbox_summary: checked })}
                        />
                      </div>
                    </div>
                  </div>
                ) : isGeoNamesSpatialProfile ? (
                  <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                    <div className="space-y-1">
                      <Label>{t('apiEnrichment.profileOptions.providers.geoNames.title')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.profileOptions.providers.geoNames.description')}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="sample-mode">{t('apiEnrichment.profileOptions.common.sampleMode')}</Label>
                        <Select
                          value={config.sample_mode || 'bbox_grid'}
                          onValueChange={(value) => onChange({ ...config, sample_mode: value })}
                        >
                          <SelectTrigger id="sample-mode">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="bbox_grid">{t('apiEnrichment.profileOptions.common.sampleModeOptions.bboxGrid')}</SelectItem>
                            <SelectItem value="boundary">{t('apiEnrichment.profileOptions.common.sampleModeOptions.boundary')}</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="sample-count">{t('apiEnrichment.profileOptions.common.sampleCount')}</Label>
                        <Input
                          id="sample-count"
                          type="number"
                          min={1}
                          max={100}
                          value={String(config.sample_count ?? 9)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              sample_count: Number.parseInt(e.target.value || '1', 10),
                            })
                          }
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.bboxSummary')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.common.bboxSummaryDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_bbox_summary ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_bbox_summary: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.nearbyPlaces')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.common.nearbyPlacesDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_nearby_places ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_nearby_places: checked })}
                        />
                      </div>
                    </div>
                  </div>
                ) : isTropicosRichProfile ? (
                  <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                    <div className="space-y-1">
                      <Label>{t('apiEnrichment.profileOptions.providers.tropicos.title')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.profileOptions.providers.tropicos.description')}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.references')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.tropicos.referencesDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_references ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_references: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.distributions')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.tropicos.distributionsDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_distributions ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_distributions: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.media')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.tropicos.mediaDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_media ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_media: checked })}
                        />
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="media-limit">{t('apiEnrichment.profileOptions.common.mediaLimit')}</Label>
                        <Input
                          id="media-limit"
                          type="number"
                          min={0}
                          value={String(config.media_limit ?? 3)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              media_limit: Number.parseInt(e.target.value || '0', 10),
                            })
                          }
                        />
                      </div>
                    </div>
                  </div>
                ) : isColRichProfile ? (
                  <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                    <div className="space-y-1">
                      <Label>{t('apiEnrichment.profileOptions.providers.col.title')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.profileOptions.providers.col.description')}
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="col-dataset-key">{t('apiEnrichment.profileOptions.common.datasetKey')}</Label>
                      <Input
                        id="col-dataset-key"
                        type="number"
                        min={1}
                        value={String(config.dataset_key ?? COL_DEFAULT_DATASET_KEY)}
                        onChange={(e) => {
                          const datasetKey = Number.parseInt(e.target.value || '0', 10) || COL_DEFAULT_DATASET_KEY
                          onChange({
                            ...config,
                            dataset_key: datasetKey,
                            api_url: buildColSearchUrl(datasetKey),
                          })
                        }}
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.profileOptions.common.datasetKeyDescription')}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.vernaculars')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.col.vernacularsDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_vernaculars ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_vernaculars: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.distributions')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.col.distributionsDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_distributions ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_distributions: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.references')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.col.referencesDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_references ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_references: checked })}
                        />
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="reference-limit">{t('apiEnrichment.profileOptions.common.referenceLimit')}</Label>
                        <Input
                          id="reference-limit"
                          type="number"
                          min={0}
                          value={String(config.reference_limit ?? 5)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              reference_limit: Number.parseInt(e.target.value || '0', 10),
                            })
                          }
                        />
                      </div>
                    </div>
                  </div>
                ) : isBhlReferencesProfile ? (
                  <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                    <div className="space-y-1">
                      <Label>{t('apiEnrichment.profileOptions.providers.bhl.title')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.profileOptions.providers.bhl.description')}
                      </p>
                    </div>

                    <div className="rounded-md border bg-background px-3 py-3 text-xs text-muted-foreground">
                      {t('apiEnrichment.profileOptions.providers.bhl.apiKeyRequired')}
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.publicationDetails')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.common.publicationDetailsDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_publication_details ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_publication_details: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.pagePreview')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.common.pagePreviewDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_page_preview ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_page_preview: checked })}
                        />
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="bhl-title-limit">{t('apiEnrichment.profileOptions.common.titleLimit')}</Label>
                        <Input
                          id="bhl-title-limit"
                          type="number"
                          min={0}
                          value={String(config.title_limit ?? 5)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              title_limit: Number.parseInt(e.target.value || '0', 10),
                            })
                          }
                        />
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="bhl-page-limit">{t('apiEnrichment.profileOptions.common.pageLimit')}</Label>
                        <Input
                          id="bhl-page-limit"
                          type="number"
                          min={0}
                          value={String(config.page_limit ?? 5)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              page_limit: Number.parseInt(e.target.value || '0', 10),
                            })
                          }
                        />
                      </div>
                    </div>
                  </div>
                ) : isInaturalistRichProfile ? (
                  <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                    <div className="space-y-1">
                      <Label>{t('apiEnrichment.profileOptions.providers.inaturalist.title')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.profileOptions.providers.inaturalist.description')}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.observations')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.inaturalist.observationsDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_occurrences ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_occurrences: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.media')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.providers.inaturalist.mediaDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_media ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_media: checked })}
                        />
                      </div>

                      <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium">{t('apiEnrichment.profileOptions.common.places')}</div>
                          <div className="text-xs text-muted-foreground">{t('apiEnrichment.profileOptions.common.placesDescription')}</div>
                        </div>
                        <Switch
                          checked={config.include_places ?? true}
                          onCheckedChange={(checked) => onChange({ ...config, include_places: checked })}
                        />
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                        <Label htmlFor="inat-observation-limit">{t('apiEnrichment.profileOptions.common.observationLimit')}</Label>
                        <Input
                          id="inat-observation-limit"
                          type="number"
                          min={0}
                          value={String(config.observation_limit ?? 5)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              observation_limit: Number.parseInt(e.target.value || '0', 10),
                            })
                          }
                        />
                      </div>

                      <div className="space-y-2 rounded-md border bg-background px-3 py-2 sm:col-span-2">
                        <Label htmlFor="inat-media-limit">{t('apiEnrichment.profileOptions.common.mediaLimit')}</Label>
                        <Input
                          id="inat-media-limit"
                          type="number"
                          min={0}
                          value={String(config.media_limit ?? 3)}
                          onChange={(e) =>
                            onChange({
                              ...config,
                              media_limit: Number.parseInt(e.target.value || '0', 10),
                            })
                          }
                        />
                      </div>
                    </div>
                  </div>
                ) : null}

                {supportsNameResolution ? (
                  <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                    <div className="space-y-1">
                      <Label>{t('apiEnrichment.connection.nameResolution.title')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('apiEnrichment.connection.nameResolution.description')}
                      </p>
                    </div>

                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">
                          {t('apiEnrichment.connection.nameResolution.enable')}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {t('apiEnrichment.connection.nameResolution.enableDescription')}
                        </div>
                      </div>
                      <Switch
                        checked={config.use_name_verifier ?? false}
                        onCheckedChange={(checked) => onChange({ ...config, use_name_verifier: checked })}
                      />
                    </div>
                  </div>
                ) : null}
              </div>
            </AccordionContent>
          </AccordionItem>
        ) : null}

        {/* ---- Mapping avancé ---- */}
        <AccordionItem value="mapping" className="border rounded-lg">
          <AccordionTrigger className="px-4 py-3 hover:no-underline">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-50 border border-purple-200">
                <Braces className="h-4 w-4 text-purple-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-left">{t('apiEnrichment.fieldMapping.advancedTitle')}</p>
                <p className="text-xs text-muted-foreground text-left">{t('apiEnrichment.fieldMapping.advancedDescription')}</p>
              </div>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-4 pb-4">
            <div className="space-y-4">
              {isStructuredProfile ? (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    {isGbifRichProfile
                      ? t('apiEnrichment.fieldMapping.structuredPresetInfo.gbif')
                      : isOpenMeteoElevationProfile
                        ? t('apiEnrichment.fieldMapping.structuredPresetInfo.openMeteo')
                        : isGeoNamesSpatialProfile
                          ? t('apiEnrichment.fieldMapping.structuredPresetInfo.geoNames')
                      : isTropicosRichProfile
                        ? t('apiEnrichment.fieldMapping.structuredPresetInfo.tropicos')
                        : isColRichProfile
                          ? t('apiEnrichment.fieldMapping.structuredPresetInfo.col')
                          : isBhlReferencesProfile
                            ? t('apiEnrichment.fieldMapping.structuredPresetInfo.bhl')
                            : t('apiEnrichment.fieldMapping.structuredPresetInfo.inaturalist')}
                  </AlertDescription>
                </Alert>
              ) : null}

              {!isStructuredProfile ? (
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
              ) : null}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
