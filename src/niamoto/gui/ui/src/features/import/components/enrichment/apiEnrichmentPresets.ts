import { buildColSearchUrl } from './enrichmentSources'

export type ApiCategory = 'taxonomy' | 'elevation' | 'spatial' | 'all'

interface PresetAPI {
  name: string
  iconSrc?: string
  websiteUrl?: string
  docsUrl?: string
  keyFormUrl?: string
  config: {
    api_url: string
    auth_method: 'none' | 'api_key' | 'bearer' | 'basic'
    auth_params?: {
      key?: string
      location?: 'header' | 'query'
      name?: string
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
    response_mapping?: Record<string, string>
  }
}

export interface PresetAPIWithCategory extends PresetAPI {
  category: ApiCategory
  descriptionKey?: string
}

export const COL_DEFAULT_DATASET_KEY = 314774
const BHL_API_ENDPOINT = 'https://www.biodiversitylibrary.org/api3'

export const PRESET_APIS_ALL: PresetAPIWithCategory[] = [
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
      query_params: { kingdom: 'Plantae', verbose: 'true' },
      query_param_name: 'scientificName',
      response_mapping: {},
    },
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
      auth_params: { location: 'query', name: 'apikey', key: '' },
      query_params: { format: 'json', type: 'exact' },
      query_param_name: 'name',
      include_references: true,
      include_distributions: true,
      include_media: true,
      media_limit: 3,
      response_mapping: {},
    },
  },
  {
    name: 'Endemia NC',
    iconSrc: '/provider-logos/endemia.ico',
    websiteUrl: 'https://endemia.nc/',
    category: 'taxonomy',
    descriptionKey: 'apiEnrichment.presets.endemia.description',
    config: {
      api_url: 'https://api.endemia.nc/v1/taxons',
      auth_method: 'none',
      query_params: {
        section: 'flore',
        maxitem: '1',
        excludes: 'meta,links',
        includes: 'images',
      },
      response_mapping: {
        id_endemia: 'id',
        id_florical: 'id_florical',
        endemia_url: 'endemia_url',
        endemic: 'endemique',
        protected: 'protected',
        redlist_cat: 'categorie_uicn',
        image_small_thumb: 'image.small_thumb',
        image_big_thumb: 'image.big_thumb',
      },
    },
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
      response_mapping: {},
    },
  },
  {
    name: 'BHL',
    iconSrc: '/provider-logos/bhl.ico',
    websiteUrl: 'https://www.biodiversitylibrary.org/',
    docsUrl: 'https://www.biodiversitylibrary.org/docs/api3.html',
    keyFormUrl: 'https://www.biodiversitylibrary.org/getapikey.aspx',
    category: 'taxonomy',
    descriptionKey: 'apiEnrichment.presets.bhl.description',
    config: {
      api_url: BHL_API_ENDPOINT,
      auth_method: 'api_key',
      auth_params: { location: 'query', name: 'apikey', key: '' },
      profile: 'bhl_references',
      query_param_name: 'name',
      query_params: { op: 'NameSearch', format: 'json' },
      include_publication_details: true,
      include_page_preview: true,
      title_limit: 5,
      page_limit: 5,
      response_mapping: {},
    },
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
      query_params: { perPage: '1' },
      response_mapping: {
        ipni_id: 'id',
        ipni_authors: 'authors',
        ipni_publication: 'publishedIn',
        ipni_year: 'publicationYear',
        ipni_family: 'family',
      },
    },
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
      profile: 'inaturalist_rich',
      query_params: { is_active: 'true' },
      query_param_name: 'q',
      include_occurrences: true,
      include_media: true,
      include_places: true,
      media_limit: 3,
      observation_limit: 5,
      response_mapping: {},
    },
  },
  {
    name: 'Open-Meteo Elevation',
    iconSrc: '/provider-logos/open-meteo.ico',
    websiteUrl: 'https://open-meteo.com/',
    docsUrl: 'https://open-meteo.com/en/docs/elevation-api',
    category: 'elevation',
    descriptionKey: 'apiEnrichment.presets.openMeteo.description',
    config: {
      api_url: 'https://api.open-meteo.com/v1/elevation',
      auth_method: 'none',
      profile: 'openmeteo_elevation_v1',
      query_params: {},
      query_field: 'geometry',
      query_param_name: 'latitude',
      sample_mode: 'bbox_grid',
      sample_count: 9,
      include_bbox_summary: true,
      response_mapping: {},
    },
  },
  {
    name: 'GeoNames',
    iconSrc: '/provider-logos/geonames.gif',
    websiteUrl: 'https://www.geonames.org/',
    docsUrl: 'https://www.geonames.org/export/web-services.html',
    category: 'spatial',
    descriptionKey: 'apiEnrichment.presets.geoNames.description',
    config: {
      api_url: 'https://secure.geonames.org/countrySubdivisionJSON',
      auth_method: 'api_key',
      profile: 'geonames_spatial_v1',
      auth_params: { location: 'query', name: 'username', key: '' },
      query_params: {},
      query_field: 'geometry',
      query_param_name: 'lat',
      sample_mode: 'bbox_grid',
      sample_count: 9,
      include_bbox_summary: true,
      include_nearby_places: true,
      response_mapping: {},
    },
  },
]

export function getPresetsByCategory(category: ApiCategory): PresetAPIWithCategory[] {
  if (category === 'all') return PRESET_APIS_ALL
  if (category === 'spatial') {
    return PRESET_APIS_ALL.filter(
      (preset) => preset.category === 'spatial' || preset.category === 'elevation'
    )
  }
  return PRESET_APIS_ALL.filter((preset) => preset.category === category)
}

export { buildColSearchUrl }
