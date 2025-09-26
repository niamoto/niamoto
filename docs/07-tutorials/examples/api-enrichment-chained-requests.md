# API Enrichment with Chained Requests

## Overview

The `api_taxonomy_enricher` plugin now supports chained requests, allowing you to fetch additional data from multiple API endpoints based on the initial response.

## Configuration Example for Tropicos

```yaml
api_enrichment:
  enabled: true
  plugin: api_taxonomy_enricher
  api_url: "http://services.tropicos.org/Name/Search"
  query_field: full_name
  query_params:
    type: "exact"
    format: "json"
  query_param_name: "name"  # The parameter name for the search query
  auth_method: "api_key"
  auth_params:
    key: "YOUR_API_KEY"
    location: "query"
    name: "apikey"
  rate_limit: 1
  cache_results: true

  # Mapping for the main response
  response_mapping:
    tropicos_id: "NameId"
    tropicos_name: "ScientificName"
    tropicos_author: "ScientificNameWithAuthors"
    tropicos_family: "Family"

  # Chained requests for additional data
  chained_endpoints:
    # Images endpoint
    - url_template: "http://services.tropicos.org/Name/{tropicos_id}/Images"
      params:
        format: "json"
      mapping:
        images: "$max:5:"  # Limit to 5 images
        image_count: "$count"
        first_image_url: "$first:DetailJpgUrl"
        first_image_thumb: "$first:ThumbnailUrl"

    # Synonyms endpoint
    - url_template: "http://services.tropicos.org/Name/{tropicos_id}/Synonyms"
      params:
        format: "json"
      mapping:
        synonyms: "$max:10:"
        synonym_count: "$count"
        synonym_names: "$unique:ScientificName"

    # Distributions endpoint
    - url_template: "http://services.tropicos.org/Name/{tropicos_id}/Distributions"
      params:
        format: "json"
      mapping:
        distributions: "$all"
        distribution_countries: "$unique:Country"
```

## Mapping Operators

### Basic Field Extraction
- Direct field: `"FieldName"`
- Nested field: `"parent.child"`
- Array index: `"0.FieldName"` or `"results.0.name"`

### Special Operators for Chained Requests
- `$all` or `$array`: Store the entire response
- `$count`: Count the number of items in array
- `$first:fieldName`: Extract field from first item in array
- `$unique:fieldName`: Extract unique values of a field from all items
- `$max:N:`: Limit array to first N items
- `$max:N:fieldName`: Extract field from first N items

## URL Template Variables

In `url_template`, you can use placeholders that will be replaced with values from the initial response:

- `{field_name}`: Will be replaced with the value of `field_name` from the mapped response
- `{apikey}`: Special placeholder for API key (if using api_key auth method)

Example:
```yaml
url_template: "http://api.example.com/taxon/{taxon_id}/details"
```

If the initial response mapping includes `taxon_id: "123"`, the URL becomes:
```
http://api.example.com/taxon/123/details
```

## Configuration via UI

The web interface supports basic configuration but doesn't yet have a visual editor for chained requests. To add chained requests:

1. Configure the basic API connection in the UI
2. Edit the `import.yml` file directly to add the `chained_endpoints` section
3. Use the test connection feature to verify everything works

## Migration from tropicos_enricher

If you were using the `tropicos_enricher` plugin, simply:

1. Change `plugin: tropicos_enricher` to `plugin: api_taxonomy_enricher`
2. Add the configuration shown above
3. Remove any `include_images`, `include_synonyms`, etc. flags as they're now handled by chained endpoints

## Benefits

- **Generic**: Works with any REST API, not just Tropicos
- **Flexible**: Configure any number of chained requests
- **Efficient**: Respects rate limits and caches results
- **No coding required**: Everything is configured via YAML
