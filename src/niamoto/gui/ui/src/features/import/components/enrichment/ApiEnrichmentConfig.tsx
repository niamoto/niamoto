import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
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
  ArrowRight,
  ExternalLink
} from 'lucide-react'
import axios from 'axios'
import { cn } from '@/lib/utils'
import { buildColSearchUrl } from './enrichmentSources'

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
  taxonomy_source?: string
  dataset_key?: number
  include_taxonomy?: boolean
  include_occurrences?: boolean
  include_media?: boolean
  include_references?: boolean
  include_vernaculars?: boolean
  include_distributions?: boolean
  media_limit?: number
  reference_limit?: number
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
  example?: any
}

interface PresetAPI {
  name: string
  iconSrc?: string
  websiteUrl?: string
  docsUrl?: string
  config: {
    api_url: string
    auth_method: 'none' | 'api_key' | 'bearer' | 'basic'
    auth_params?: {
      key?: string
      location?: 'header' | 'query'
      name?: string
    }
    query_params?: Record<string, string>
    query_param_name?: string
    profile?: string
    taxonomy_source?: string
    dataset_key?: number
    include_taxonomy?: boolean
    include_occurrences?: boolean
    include_media?: boolean
    include_references?: boolean
    include_vernaculars?: boolean
    include_distributions?: boolean
    media_limit?: number
    reference_limit?: number
    response_mapping?: Record<string, string>
  }
}

// API Categories for filtering presets
export type ApiCategory = 'taxonomy' | 'elevation' | 'spatial' | 'all'

const COL_DEFAULT_DATASET_KEY = 314774

interface PresetAPIWithCategory extends PresetAPI {
  category: ApiCategory
  descriptionKey?: string
}

const PRESET_APIS_ALL: PresetAPIWithCategory[] = [
  // === TAXONOMY APIs ===
  {
    name: 'GBIF',
    iconSrc: '/provider-logos/gbif.ico',
    websiteUrl: 'https://www.gbif.org/',
    docsUrl: 'https://techdocs.gbif.org/en/openapi/',
    category: 'taxonomy',
    descriptionKey: 'apiEnrichment.presets.gbif.description',
    config: {
      api_url: 'https://api.gbif.org/v2/species/match',
      auth_method: 'none',
      profile: 'gbif_rich',
      taxonomy_source: 'col_xr',
      include_taxonomy: true,
      include_occurrences: true,
      include_media: true,
      media_limit: 3,
      query_params: {
        kingdom: 'Plantae',
        verbose: 'true'
      },
      query_param_name: 'scientificName',
      response_mapping: {}
    }
  },
  {
    name: 'Tropicos',
    iconSrc: '/provider-logos/tropicos.ico',
    websiteUrl: 'https://www.tropicos.org/home',
    docsUrl: 'https://services.tropicos.org/help',
    category: 'taxonomy',
    descriptionKey: 'apiEnrichment.presets.tropicos.description',
    config: {
      api_url: 'https://services.tropicos.org/Name/Search',
      auth_method: 'api_key',
      profile: 'tropicos_rich',
      auth_params: {
        location: 'query',
        name: 'apikey',
        key: ''
      },
      query_params: {
        format: 'json',
        type: 'exact'
      },
      query_param_name: 'name',
      include_references: true,
      include_distributions: true,
      include_media: true,
      media_limit: 3,
      response_mapping: {}
    }
  },
  {
    name: 'Endemia NC',
    iconSrc: '/provider-logos/endemia.ico',
    websiteUrl: 'https://endemia.nc/',
    category: 'taxonomy',
    descriptionKey: 'apiEnrichment.presets.endemia.description',
    config: {
      api_url: 'https://api.endemia.nc/v1/taxons',
      auth_method: 'api_key',
      auth_params: {
        location: 'query',
        name: 'apiKey',
        key: ''
      },
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
    name: 'Catalogue of Life',
    iconSrc: '/provider-logos/col.jpg',
    websiteUrl: 'https://www.catalogueoflife.org/',
    docsUrl: 'https://api.checklistbank.org/',
    category: 'taxonomy',
    descriptionKey: 'apiEnrichment.presets.col.description',
    config: {
      api_url: buildColSearchUrl(COL_DEFAULT_DATASET_KEY),
      auth_method: 'none',
      profile: 'col_rich',
      dataset_key: COL_DEFAULT_DATASET_KEY,
      include_vernaculars: true,
      include_distributions: true,
      include_references: true,
      reference_limit: 5,
      query_param_name: 'q',
      query_params: {},
      response_mapping: {}
    }
  },
  {
    name: 'IPNI',
    iconSrc: '/provider-logos/ipni.png',
    websiteUrl: 'https://www.ipni.org/',
    category: 'taxonomy',
    descriptionKey: 'apiEnrichment.presets.ipni.description',
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
    iconSrc: '/provider-logos/inaturalist.png',
    websiteUrl: 'https://www.inaturalist.org/',
    docsUrl: 'https://www.inaturalist.org/pages/api+reference',
    category: 'taxonomy',
    descriptionKey: 'apiEnrichment.presets.inaturalist.description',
    config: {
      api_url: 'https://api.inaturalist.org/v1/taxa',
      auth_method: 'none',
      query_params: {
        q: '',
        is_active: 'true',
        taxon_id: '47126',
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
  // === ELEVATION APIs (for plots) ===
  {
    name: 'Open-Elevation',
    category: 'elevation',
    descriptionKey: 'apiEnrichment.presets.openElevation.description',
    config: {
      api_url: 'https://api.open-elevation.com/api/v1/lookup',
      auth_method: 'none',
      query_params: {},
      query_param_name: 'locations',
      response_mapping: {
        elevation: 'results[0].elevation',
        elevation_lat: 'results[0].latitude',
        elevation_lng: 'results[0].longitude'
      }
    }
  },
  {
    name: 'Open Topo Data',
    category: 'elevation',
    descriptionKey: 'apiEnrichment.presets.openTopoData.description',
    config: {
      api_url: 'https://api.opentopodata.org/v1/srtm90m',
      auth_method: 'none',
      query_params: {},
      query_param_name: 'locations',
      response_mapping: {
        elevation: 'results[0].elevation',
        dataset: 'results[0].dataset'
      }
    }
  },
  {
    name: 'Open-Meteo Elevation',
    category: 'elevation',
    descriptionKey: 'apiEnrichment.presets.openMeteo.description',
    config: {
      api_url: 'https://api.open-meteo.com/v1/elevation',
      auth_method: 'none',
      query_params: {},
      response_mapping: {
        elevation: 'elevation[0]'
      }
    }
  },

  // === SPATIAL APIs (for shapes/plots) ===
  {
    name: 'GeoNames',
    category: 'spatial',
    descriptionKey: 'apiEnrichment.presets.geoNames.description',
    config: {
      api_url: 'http://api.geonames.org/countrySubdivisionJSON',
      auth_method: 'api_key',
      auth_params: {
        location: 'query',
        name: 'username',
        key: ''
      },
      query_params: {},
      query_param_name: 'username',
      response_mapping: {
        country_code: 'countryCode',
        country_name: 'countryName',
        admin_code1: 'adminCode1',
        admin_name1: 'adminName1',
        admin_code2: 'adminCode2',
        admin_name2: 'adminName2'
      }
    }
  },
  {
    name: 'GeoNames FindNearby',
    category: 'spatial',
    descriptionKey: 'apiEnrichment.presets.geoNamesNearby.description',
    config: {
      api_url: 'http://api.geonames.org/findNearbyJSON',
      auth_method: 'api_key',
      auth_params: {
        location: 'query',
        name: 'username',
        key: ''
      },
      query_params: {
        featureClass: 'P',
        maxRows: '5'
      },
      query_param_name: 'username',
      response_mapping: {
        nearby_name: 'geonames[0].name',
        nearby_distance: 'geonames[0].distance',
        nearby_country: 'geonames[0].countryName',
        nearby_admin1: 'geonames[0].adminName1',
        nearby_population: 'geonames[0].population'
      }
    }
  },
  {
    name: 'Nominatim (OSM)',
    category: 'spatial',
    descriptionKey: 'apiEnrichment.presets.nominatim.description',
    config: {
      api_url: 'https://nominatim.openstreetmap.org/reverse',
      auth_method: 'none',
      query_params: {
        format: 'json',
        addressdetails: '1'
      },
      response_mapping: {
        display_name: 'display_name',
        osm_type: 'osm_type',
        osm_id: 'osm_id',
        address_country: 'address.country',
        address_state: 'address.state',
        address_county: 'address.county',
        address_city: 'address.city'
      }
    }
  },
  {
    name: 'geoBoundaries',
    category: 'spatial',
    descriptionKey: 'apiEnrichment.presets.geoBoundaries.description',
    config: {
      api_url: 'https://www.geoboundaries.org/api/current/gbOpen',
      auth_method: 'none',
      query_params: {
        adm: 'ADM1'
      },
      response_mapping: {
        boundary_name: 'boundaryName',
        boundary_iso: 'boundaryISO',
        boundary_type: 'boundaryType',
        geojson_url: 'gjDownloadURL'
      }
    }
  }
]

// Helper to get presets by category
export function getPresetsByCategory(category: ApiCategory): PresetAPIWithCategory[] {
  if (category === 'all') return PRESET_APIS_ALL
  return PRESET_APIS_ALL.filter(p => p.category === category)
}

// Export all presets for external use
export { PRESET_APIS_ALL }

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
  // Filter presets by category
  const filteredPresets = category === 'all'
    ? PRESET_APIS_ALL
    : PRESET_APIS_ALL.filter(p => p.category === category)
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
  const isStructuredProfile = isGbifRichProfile || isTropicosRichProfile || isColRichProfile
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
  }, [config.api_url, filteredPresets])

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
        query_param_name: preset.config.query_param_name || 'q',
        profile: preset.config.profile,
        taxonomy_source: preset.config.taxonomy_source,
        dataset_key: preset.config.dataset_key,
        include_taxonomy: preset.config.include_taxonomy ?? true,
        include_occurrences: preset.config.include_occurrences ?? true,
        include_media: preset.config.include_media ?? true,
        include_references: preset.config.include_references ?? true,
        include_vernaculars: preset.config.include_vernaculars ?? true,
        include_distributions: preset.config.include_distributions ?? true,
        media_limit: preset.config.media_limit ?? 3,
        reference_limit: preset.config.reference_limit ?? 5,
        response_mapping: preset.config.response_mapping ? { ...preset.config.response_mapping } : {},
      })
      onPresetSelect?.(preset.name)
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
      params[config.query_param_name || 'q'] = 'Pinus'

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
        <TabsList className="flex h-auto w-full flex-wrap items-stretch justify-start gap-1 rounded-lg bg-muted p-1">
          <TabsTrigger
            value="connection"
            className="min-h-10 flex-1 min-w-[120px] whitespace-normal px-3 py-2 text-center leading-tight"
          >
            {t('apiEnrichment.sections.connection')}
          </TabsTrigger>
          <TabsTrigger
            value="authentication"
            className="min-h-10 flex-1 min-w-[120px] whitespace-normal px-3 py-2 text-center leading-tight"
          >
            {t('apiEnrichment.sections.authentication')}
          </TabsTrigger>
          <TabsTrigger
            value="mapping"
            className="min-h-10 flex-1 min-w-[140px] whitespace-normal px-3 py-2 text-center leading-tight"
          >
            {t('apiEnrichment.sections.fieldMapping')}
          </TabsTrigger>
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
                          {selectedPreset.websiteUrl ? (
                            <a
                              href={selectedPreset.websiteUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1.5 text-primary hover:underline"
                            >
                              {t('apiEnrichment.connection.links.website')}
                              <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                          ) : null}
                          {selectedPreset.docsUrl ? (
                            <a
                              href={selectedPreset.docsUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1.5 text-primary hover:underline"
                            >
                              {t('apiEnrichment.connection.links.apiDocs')}
                              <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
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

              {isGbifRichProfile ? (
                <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                  <div className="space-y-1">
                    <Label>GBIF Rich</Label>
                    <p className="text-xs text-muted-foreground">
                      Utilise un pipeline structuré GBIF au lieu d&apos;un simple mapping plat.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="taxonomy-source">Taxonomy source</Label>
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
                        <div className="text-sm font-medium">Taxonomy</div>
                        <div className="text-xs text-muted-foreground">Match, synonymes, vernaculaires</div>
                      </div>
                      <Switch
                        checked={config.include_taxonomy ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_taxonomy: checked })}
                      />
                    </div>

                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">Occurrences</div>
                        <div className="text-xs text-muted-foreground">Résumé de distribution et de preuves</div>
                      </div>
                      <Switch
                        checked={config.include_occurrences ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_occurrences: checked })}
                      />
                    </div>

                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">Media</div>
                        <div className="text-xs text-muted-foreground">Miniatures et crédits GBIF</div>
                      </div>
                      <Switch
                        checked={config.include_media ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_media: checked })}
                      />
                    </div>

                    <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                      <Label htmlFor="media-limit">Media limit</Label>
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
              ) : isTropicosRichProfile ? (
                <div className="space-y-3 rounded-lg border border-border/70 bg-muted/20 p-4">
                  <div className="space-y-1">
                    <Label>Tropicos Rich</Label>
                    <p className="text-xs text-muted-foreground">
                      Utilise un pipeline structuré Tropicos avec nom accepté, références,
                      distributions et médias.
                    </p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">Références</div>
                        <div className="text-xs text-muted-foreground">Résumé bibliographique Tropicos</div>
                      </div>
                      <Switch
                        checked={config.include_references ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_references: checked })}
                      />
                    </div>

                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">Distributions</div>
                        <div className="text-xs text-muted-foreground">Pays et régions résumés</div>
                      </div>
                      <Switch
                        checked={config.include_distributions ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_distributions: checked })}
                      />
                    </div>

                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">Media</div>
                        <div className="text-xs text-muted-foreground">Images et crédits Tropicos</div>
                      </div>
                      <Switch
                        checked={config.include_media ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_media: checked })}
                      />
                    </div>

                    <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                      <Label htmlFor="media-limit">Media limit</Label>
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
                    <Label>Catalogue of Life Rich</Label>
                    <p className="text-xs text-muted-foreground">
                      Utilise un pipeline structuré ChecklistBank avec taxonomie,
                      synonymes, noms vernaculaires, distributions et références.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="col-dataset-key">ChecklistBank dataset key</Label>
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
                      Clé de release ChecklistBank utilisée pour la recherche et les détails du taxon.
                    </p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">Vernaculars</div>
                        <div className="text-xs text-muted-foreground">Noms vernaculaires par langue</div>
                      </div>
                      <Switch
                        checked={config.include_vernaculars ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_vernaculars: checked })}
                      />
                    </div>

                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">Distributions</div>
                        <div className="text-xs text-muted-foreground">Régions et pays quand disponibles</div>
                      </div>
                      <Switch
                        checked={config.include_distributions ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_distributions: checked })}
                      />
                    </div>

                    <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                      <div className="space-y-0.5">
                        <div className="text-sm font-medium">References</div>
                        <div className="text-xs text-muted-foreground">Citations ChecklistBank résumées</div>
                      </div>
                      <Switch
                        checked={config.include_references ?? true}
                        onCheckedChange={(checked) => onChange({ ...config, include_references: checked })}
                      />
                    </div>

                    <div className="space-y-2 rounded-md border bg-background px-3 py-2">
                      <Label htmlFor="reference-limit">Reference limit</Label>
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
              ) : null}

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
              {isStructuredProfile ? (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    {isGbifRichProfile
                      ? "GBIF Rich produit un résumé structuré par blocs (`Match`, `Taxonomy`, `Occurrences`, `Media`). Le mapping manuel n'est pas requis pour ce preset."
                      : isTropicosRichProfile
                        ? "Tropicos Rich produit un résumé structuré par blocs (`Match`, `Nomenclature`, `Taxonomy`, `References`, `Distribution`, `Media`). Le mapping manuel n'est pas requis pour ce preset."
                        : "Catalogue of Life Rich produit un résumé structuré par blocs (`Match`, `Taxonomy`, `Nomenclature`, `Vernaculars`, `Distribution`, `References`). Le mapping manuel n'est pas requis pour ce preset."}
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
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
