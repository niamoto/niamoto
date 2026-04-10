import type { ApiCategory, ApiConfig } from './ApiEnrichmentConfig'

export interface ReferenceEnrichmentConfig {
  id?: string
  label?: string
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
    profile?: string
    use_name_verifier?: boolean
    name_verifier_preferred_sources?: string[]
    name_verifier_threshold?: number
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
    include_publication_details?: boolean
    include_page_preview?: boolean
    title_limit?: number
    page_limit?: number
    rate_limit?: number
    cache_results?: boolean
    response_mapping?: Record<string, string>
    chained_endpoints?: Array<{
      url_template: string
      params?: Record<string, string>
      mapping: Record<string, string>
    }>
  }
}

export interface NormalizedEnrichmentSource {
  id: string
  label: string
  plugin: string
  enabled: boolean
  config: ApiConfig
}

const DEFAULT_PLUGIN_BY_CATEGORY: Record<ApiCategory, string> = {
  taxonomy: 'api_taxonomy_enricher',
  elevation: 'api_elevation_enricher',
  spatial: 'api_spatial_enricher',
  all: 'api_taxonomy_enricher',
}

const GBIF_RICH_MATCH_URL = 'https://api.gbif.org/v2/species/match'
const TROPICOS_RICH_SEARCH_URL = 'https://services.tropicos.org/Name/Search'
const COL_DEFAULT_DATASET_KEY = 314774
const BHL_API_ENDPOINT = 'https://www.biodiversitylibrary.org/api3'

export function buildColSearchUrl(datasetKey: number): string {
  return `https://api.checklistbank.org/dataset/${datasetKey}/nameusage/search`
}

function isLegacyGbifEnrichment(enrichment: ReferenceEnrichmentConfig | undefined): boolean {
  if (!enrichment) return false
  if (enrichment.config?.profile) return false

  const apiUrl = (enrichment.config?.api_url || '').toLowerCase()
  if (apiUrl.includes('api.gbif.org') && apiUrl.includes('/species/match')) {
    return true
  }

  const label = (enrichment.label || enrichment.id || '').toLowerCase()
  return label === 'gbif'
}

function isLegacyTropicosEnrichment(enrichment: ReferenceEnrichmentConfig | undefined): boolean {
  if (!enrichment) return false
  if (enrichment.config?.profile) return false

  const plugin = (enrichment.plugin || '').toLowerCase()
  if (plugin === 'tropicos_enricher') {
    return true
  }

  const apiUrl = (enrichment.config?.api_url || '').toLowerCase()
  if (apiUrl.includes('services.tropicos.org') && apiUrl.includes('/name/search')) {
    return true
  }

  const label = (enrichment.label || enrichment.id || '').toLowerCase()
  return label === 'tropicos'
}

export function slugifyEnrichmentSourceId(value: string, fallback: string): string {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug || fallback
}

function inferSourceLabel(enrichment: ReferenceEnrichmentConfig, index: number): string {
  if (enrichment.label?.trim()) {
    return enrichment.label.trim()
  }

  const apiUrl = enrichment.config?.api_url
  if (apiUrl) {
    try {
      const host = new URL(apiUrl).hostname.replace(/^www\./, '')
      return host.replace(/\./g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
    } catch {
      // Ignore invalid URLs and fall back to plugin naming below.
    }
  }

  if (enrichment.plugin?.trim()) {
    return enrichment.plugin.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
  }

  return `Source ${index + 1}`
}

export function enrichmentToApiConfig(
  enrichment: ReferenceEnrichmentConfig | undefined,
  category: ApiCategory = 'taxonomy'
): ApiConfig {
  const legacyGbif = isLegacyGbifEnrichment(enrichment)
  const legacyTropicos = isLegacyTropicosEnrichment(enrichment)
  const queryParams = enrichment?.config?.query_params

  return {
    enabled: enrichment?.enabled ?? false,
    plugin: legacyTropicos
      ? 'api_taxonomy_enricher'
      : (enrichment?.plugin ?? DEFAULT_PLUGIN_BY_CATEGORY[category]),
    api_url: legacyGbif
      ? GBIF_RICH_MATCH_URL
      : legacyTropicos
        ? TROPICOS_RICH_SEARCH_URL
        : enrichment?.config?.profile === 'col_rich'
          ? (enrichment?.config?.api_url ?? buildColSearchUrl(enrichment?.config?.dataset_key ?? COL_DEFAULT_DATASET_KEY))
        : enrichment?.config?.profile === 'bhl_references'
          ? (enrichment?.config?.api_url ?? BHL_API_ENDPOINT)
        : enrichment?.config?.api_url ?? '',
    auth_method: (enrichment?.config?.auth_method as ApiConfig['auth_method']) ?? 'none',
    auth_params: legacyTropicos
      ? {
          location: 'query',
          name: 'apikey',
          key: enrichment?.config?.auth_params?.key || '',
        }
      : enrichment?.config?.auth_params,
    query_params: legacyGbif
      ? {
          ...(queryParams ?? {}),
          verbose: String((queryParams ?? {}).verbose ?? 'true'),
        }
      : legacyTropicos
        ? {
            ...(queryParams ?? {}),
            format: String((queryParams ?? {}).format ?? 'json'),
            type: String((queryParams ?? {}).type ?? 'exact'),
          }
        : enrichment?.config?.profile === 'bhl_references'
          ? {
              ...(queryParams ?? {}),
              op: String((queryParams ?? {}).op ?? 'NameSearch'),
              format: String((queryParams ?? {}).format ?? 'json'),
            }
        : queryParams,
    query_field: enrichment?.config?.query_field ?? 'full_name',
    query_param_name: legacyGbif
      ? 'scientificName'
      : legacyTropicos
        ? 'name'
        : enrichment?.config?.profile === 'col_rich'
          ? 'q'
        : enrichment?.config?.profile === 'bhl_references'
          ? 'name'
        : (enrichment?.config?.query_param_name ?? 'q'),
    profile: enrichment?.config?.profile
      ?? (legacyGbif ? 'gbif_rich' : undefined)
      ?? (legacyTropicos ? 'tropicos_rich' : undefined),
    use_name_verifier: enrichment?.config?.use_name_verifier ?? false,
    name_verifier_preferred_sources: enrichment?.config?.name_verifier_preferred_sources ?? [],
    name_verifier_threshold: enrichment?.config?.name_verifier_threshold,
    taxonomy_source: enrichment?.config?.taxonomy_source ?? (legacyGbif ? 'col_xr' : undefined),
    dataset_key: enrichment?.config?.dataset_key ?? COL_DEFAULT_DATASET_KEY,
    include_taxonomy: enrichment?.config?.include_taxonomy ?? true,
    include_occurrences: enrichment?.config?.include_occurrences ?? true,
    include_media: enrichment?.config?.include_media ?? true,
    include_references: enrichment?.config?.include_references ?? true,
    include_vernaculars: enrichment?.config?.include_vernaculars ?? true,
    include_distributions: enrichment?.config?.include_distributions ?? true,
    media_limit: enrichment?.config?.media_limit ?? 3,
    reference_limit: enrichment?.config?.reference_limit ?? 5,
    include_publication_details: enrichment?.config?.include_publication_details ?? true,
    include_page_preview: enrichment?.config?.include_page_preview ?? true,
    title_limit: enrichment?.config?.title_limit ?? 5,
    page_limit: enrichment?.config?.page_limit ?? 5,
    rate_limit: enrichment?.config?.rate_limit ?? 2,
    cache_results: enrichment?.config?.cache_results ?? true,
    response_mapping: legacyGbif || legacyTropicos ? {} : enrichment?.config?.response_mapping,
    chained_endpoints: enrichment?.config?.chained_endpoints,
  }
}

export function normalizeEnrichmentSources(
  enrichments: ReferenceEnrichmentConfig[] | undefined,
  category: ApiCategory = 'taxonomy'
): NormalizedEnrichmentSource[] {
  const rawSources = enrichments ?? []
  const seenIds = new Set<string>()

  return rawSources.map((enrichment, index) => {
    const label = inferSourceLabel(enrichment, index)
    const baseId = enrichment.id || slugifyEnrichmentSourceId(label, `source-${index + 1}`)
    let sourceId = baseId
    let suffix = 2

    while (seenIds.has(sourceId)) {
      sourceId = `${baseId}-${suffix}`
      suffix += 1
    }
    seenIds.add(sourceId)

    return {
      id: sourceId,
      label,
      plugin: enrichment?.plugin ?? DEFAULT_PLUGIN_BY_CATEGORY[category],
      enabled: enrichment?.enabled ?? false,
      config: enrichmentToApiConfig({ ...enrichment, id: sourceId, label }, category),
    }
  })
}

export function apiConfigToEnrichment(
  source: Pick<NormalizedEnrichmentSource, 'id' | 'label'>,
  apiConfig: ApiConfig
): ReferenceEnrichmentConfig {
  return {
    id: source.id,
    label: source.label,
    plugin: apiConfig.plugin,
    enabled: apiConfig.enabled,
    config: {
      api_url: apiConfig.api_url,
      auth_method: apiConfig.auth_method,
      auth_params: apiConfig.auth_params,
      query_params: apiConfig.query_params,
      query_field: apiConfig.query_field,
      query_param_name: apiConfig.query_param_name,
      profile: apiConfig.profile,
      use_name_verifier: apiConfig.use_name_verifier,
      name_verifier_preferred_sources: apiConfig.name_verifier_preferred_sources,
      name_verifier_threshold: apiConfig.name_verifier_threshold,
      taxonomy_source: apiConfig.taxonomy_source,
      dataset_key: apiConfig.dataset_key,
      include_taxonomy: apiConfig.include_taxonomy,
      include_occurrences: apiConfig.include_occurrences,
      include_media: apiConfig.include_media,
      include_references: apiConfig.include_references,
      include_vernaculars: apiConfig.include_vernaculars,
      include_distributions: apiConfig.include_distributions,
      media_limit: apiConfig.media_limit,
      reference_limit: apiConfig.reference_limit,
      include_publication_details: apiConfig.include_publication_details,
      include_page_preview: apiConfig.include_page_preview,
      title_limit: apiConfig.title_limit,
      page_limit: apiConfig.page_limit,
      rate_limit: apiConfig.rate_limit,
      cache_results: apiConfig.cache_results,
      response_mapping: apiConfig.response_mapping,
      chained_endpoints: apiConfig.chained_endpoints,
    },
  }
}

export function createDefaultEnrichmentSource(
  category: ApiCategory = 'taxonomy',
  index = 0
): ReferenceEnrichmentConfig {
  const sourceId = `source-${index + 1}`
  return {
    id: sourceId,
    label: `Source ${index + 1}`,
    plugin: DEFAULT_PLUGIN_BY_CATEGORY[category],
    enabled: true,
    config: {
      api_url: '',
      auth_method: 'none',
      query_params: {},
      query_field: 'full_name',
      query_param_name: 'q',
      profile: undefined,
      use_name_verifier: false,
      name_verifier_preferred_sources: [],
      name_verifier_threshold: undefined,
      taxonomy_source: undefined,
      dataset_key: COL_DEFAULT_DATASET_KEY,
      include_taxonomy: true,
      include_occurrences: true,
      include_media: true,
      include_references: true,
      include_vernaculars: true,
      include_distributions: true,
      media_limit: 3,
      reference_limit: 5,
      include_publication_details: true,
      include_page_preview: true,
      title_limit: 5,
      page_limit: 5,
      rate_limit: 2,
      cache_results: true,
      response_mapping: {},
      chained_endpoints: [],
    },
  }
}
