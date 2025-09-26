# Configuration examples in import.yml

Here are some complete configuration examples in import.yml for different API scenarios:

## 1. API with API key in the header (e.g., Endemia)

```yaml
taxonomy:
  type: csv
  path: "imports/occurrences.csv"
  source: "occurrences"
  ranks: "family,genus,species,infra"
  occurrence_columns:
    taxon_id: "id_taxonref"
    family: "family"
    genus: "genus"
    species: "species"
    infra: "infra"
    authors: "taxonref"

  # API configuration with API key in the header
  api_enrichment:
    enabled: true
    plugin: "api_taxonomy_enricher"
    api_url: "https://api.endemia.nc/v1/taxons"

    # Authentication with API key
    auth_method: "api_key"
    auth_params:
      key: "<YOUR_API_KEY>"    # Direct API key (replace with your actual API key)
      # or with reference to environment variable
      # key: "$ENV:ENDEMIA_API_KEY"
      location: "header"          # Where to place the key
      name: "X-API-Key"           # Header name

    # Additional query parameters
    query_params:
      section: "flore"
      limit: "1"

    # Field to use for the query
    query_field: "full_name"

    # Limits and optimizations
    rate_limit: 2.0
    cache_results: true

    # Mapping of API fields to extra_data
    response_mapping:
      external_id: "id"
      scientific_name: "nom_scientifique"
      common_name: "nom_commun"
      description: "description"
      image_url: "images.0.url"     # Access to the first element of the images array
      link_url: "permalink"
      conservation_status: "statut_conservation"
      native: "indigenat"
      endemism: "endemicite"
```

## 2. API with OAuth2 (client credentials)

```yaml
taxonomy:
  type: csv
  path: "imports/taxonomy.csv"
  source: "file"
  identifier: "id_taxon"
  ranks: "id_famille,id_genre,id_espèce,id_sous-espèce"

  # API configuration with OAuth2
  api_enrichment:
    enabled: true
    plugin: "api_taxonomy_enricher"
    api_url: "https://api.gbif.org/v1/species"

    # OAuth2 authentication
    auth_method: "oauth2"
    auth_params:
      # Endpoint to obtain the token
      token_url: "https://auth.gbif.org/oauth/token"
      # Client credentials (stored securely)
      client_id: "$ENV:GBIF_CLIENT_ID"
      client_secret: "$ENV:GBIF_CLIENT_SECRET"
      # Type and scope of access
      grant_type: "client_credentials"
      scope: "species:read"

    # Additional query parameters
    query_params:
      rank: "SPECIES"
      datasetKey: "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"  # Catalogue of Life

    # Field to use for the query
    query_field: "full_name"

    # Limits and optimizations
    rate_limit: 5.0
    cache_results: true

    # Mapping of API fields to extra_data
    response_mapping:
      gbif_id: "speciesKey"
      taxonomic_status: "taxonomicStatus"
      kingdom: "kingdom"
      scientific_name: "scientificName"
      canonical_name: "canonicalName"
      authorship: "authorship"
      name_published_in: "namePublishedIn"
      citation: "citation"
      source: "source"
      vernacular_names: "vernacularNames.0.vernacularName"  # First vernacular name
      classification_taxonomic_rank: "classificationTaxonomicRank"
      habitat: "habitatPreferences.0.name"  # First preferred habitat
```

## 3. API with Basic authentication

```yaml
taxonomy:
  type: csv
  path: "imports/species_list.csv"
  source: "file"
  identifier: "id_taxon"
  ranks: "family,genus,species,infra"

  # API configuration with Basic Auth
  api_enrichment:
    enabled: true
    plugin: "api_taxonomy_enricher"
    api_url: "https://api.inaturalist.org/v1/taxa"

    # Basic authentication
    auth_method: "basic"
    auth_params:
      username: "$ENV:INATURALIST_USERNAME"
      password: "$FILE:/etc/niamoto/secrets/inaturalist.txt"

    # Additional query parameters
    query_params:
      locale: "fr"
      preferred_place_id: "6855"  # New Caledonia

    # Field to use for the query
    query_field: "full_name"

    # Limits and optimizations
    rate_limit: 1.0  # Strict limit for iNaturalist
    cache_results: true

    # Mapping of API fields to extra_data
    response_mapping:
      inaturalist_id: "results.0.id"
      scientific_name: "results.0.name"
      common_name: "results.0.preferred_common_name"
      wikipedia_url: "results.0.wikipedia_url"
      observations_count: "results.0.observations_count"
      is_active: "results.0.is_active"
      ancestry: "results.0.ancestry"
      rank: "results.0.rank"
      ancestors: "results.0.ancestor_ids"
      iconic_taxon: "results.0.iconic_taxon_name"
      photo_url: "results.0.default_photo.medium_url"
      threatened: "results.0.threatened"
      introduced: "results.0.introduced"
      native: "results.0.native"
```

## 4. API with Bearer Token (e.g., an internal API)

```yaml
taxonomy:
  type: csv
  path: "imports/plant_inventory.csv"
  source: "file"
  identifier: "id_taxon"
  ranks: "family,genus,species,infra"

  # API configuration with Bearer Token
  api_enrichment:
    enabled: true
    plugin: "api_taxonomy_enricher"
    api_url: "https://api.internal-taxonomy-service.org/species"

    # Bearer Token authentication
    auth_method: "bearer"
    auth_params:
      token: "$ENV:INTERNAL_API_TOKEN"

    # Additional query parameters
    query_params:
      region: "new-caledonia"
      dataSource: "primary"

    # Field to use for the query
    query_field: "full_name"

    # Limits and optimizations
    rate_limit: 10.0  # Internal API, higher limit
    cache_results: true

    # Mapping of API fields to extra_data
    response_mapping:
      internal_id: "id"
      validated: "validationStatus"
      reviewed_by: "reviewerName"
      review_date: "reviewDate"
      genome_size: "genomeData.size"
      chromosome_count: "genomeData.chromosomeCount"
      habitat_types: "habitatData.types"
      conservation_plans: "conservationData.activePlans"
      restoration_projects: "restorationProjects"
      seed_availability: "propagationData.seedAvailability"
      propagation_methods: "propagationData.methods"
```

## 5. API without authentication (public API)

```yaml
taxonomy:
  type: csv
  path: "imports/occurrences.csv"
  source: "occurrences"
  ranks: "family,genus,species,infra"
  occurrence_columns:
    taxon_id: "id_taxonref"
    family: "family"
    genus: "genus"
    species: "species"
    infra: "infra"
    authors: "taxonref"

  # Public API configuration (no authentication)
  api_enrichment:
    enabled: true
    plugin: "api_taxonomy_enricher"
    api_url: "https://api.trefle.io/api/v1/plants/search"

    # No authentication
    auth_method: "none"

    # Additional query parameters
    query_params:
      token: "$ENV:TREFLE_TOKEN"  # Token as query parameter, not as authentication

    # Field to use for the query
    query_field: "full_name"

    # Limits and optimizations
    rate_limit: 1.0  # Low limit for public API
    cache_results: true

    # Mapping of API fields to extra_data
    response_mapping:
      trefle_id: "data.0.id"
      common_name: "data.0.common_name"
      slug: "data.0.slug"
      scientific_name: "data.0.scientific_name"
      year: "data.0.year"
      family: "data.0.family"
      image_url: "data.0.image_url"
      genus: "data.0.genus"
      growth_form: "data.0.specifications.growth_form"
      growth_habit: "data.0.specifications.growth_habit"
      edible_parts: "data.0.specifications.edible_part"
      vegetable: "data.0.specifications.vegetable"
      edible: "data.0.specifications.edible"
      medicinal: "data.0.specifications.medicinal"
      flower_color: "data.0.flower.color"
      flower_conspicuous: "data.0.flower.conspicuous"
```

These examples cover a wide range of authentication scenarios and should allow you to connect to most available taxonomy APIs. The plugin is designed to be flexible and easily configurable via the import.yml file, in line with your "Configuration over code" philosophy.
