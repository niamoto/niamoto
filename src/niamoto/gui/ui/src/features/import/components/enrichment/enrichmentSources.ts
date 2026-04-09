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
  return {
    enabled: enrichment?.enabled ?? false,
    plugin: enrichment?.plugin ?? DEFAULT_PLUGIN_BY_CATEGORY[category],
    api_url: enrichment?.config?.api_url ?? '',
    auth_method: (enrichment?.config?.auth_method as ApiConfig['auth_method']) ?? 'none',
    auth_params: enrichment?.config?.auth_params,
    query_params: enrichment?.config?.query_params,
    query_field: enrichment?.config?.query_field ?? 'full_name',
    query_param_name: enrichment?.config?.query_param_name ?? 'q',
    rate_limit: enrichment?.config?.rate_limit ?? 2,
    cache_results: enrichment?.config?.cache_results ?? true,
    response_mapping: enrichment?.config?.response_mapping,
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
      rate_limit: 2,
      cache_results: true,
      response_mapping: {},
      chained_endpoints: [],
    },
  }
}
