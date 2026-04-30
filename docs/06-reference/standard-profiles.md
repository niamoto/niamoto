# Standard Profiles

Standard profiles describe publication-ready biodiversity outputs separately
from ordinary collection JSON APIs. They live in `config/export.yml` under the
top-level `standard_profiles` key.

Use a standard profile when the output must follow a known biodiversity
standard, such as Darwin Core Occurrence or Humboldt/Event. Use a simple JSON
API export when the output should expose Niamoto's transformed collection data
without a standard-specific grain or mapping contract.

## Configuration Shape

```yaml
exports:
  - name: json_api
    exporter: json_api_exporter
    params:
      output_dir: exports/api
      detail_output_pattern: "{group}/{id}.json"
    groups: []

standard_profiles:
  - name: dwc_occurrences
    enabled: true
    standard: darwin_core_occurrence
    target_grain: occurrence
    source:
      type: dataset
      name: occurrences
    context:
      type: collection
      name: taxons
    validation_status: draft
    mappings:
      occurrenceID:
        generator: unique_occurrence_id
        params:
          prefix: niaocc_
      scientificName:
        source: scientific_name
    outputs:
      - type: api_json
        enabled: true
        params:
          output_dir: exports/profiles/dwc_occurrences
      - type: dwc_archive
        enabled: false
        params:
          output_dir: exports/dwc/archive
          archive_name: dwc-occurrences.zip
```

`standard_profiles` is a sibling of `exports`, not an exporter target inside
`exports`. Regular export jobs still read `exports`; profile outputs are
generated through the standard profile API and UI.

## Supported Standards

| Standard | `standard` value | Expected target grain | Current outputs |
| --- | --- | --- | --- |
| Darwin Core Occurrence | `darwin_core_occurrence` | `occurrence` | `api_json`, `dwc_archive` |
| Humboldt/Event | `humboldt_event` | `event` or `inventory` | `api_json`, `standard_files` |

## Sources and Grain Compatibility

A profile source can be:

- `collection`: a reviewed collection from the Collections catalog
- `reference`: a reference entity from `import.yml`
- `dataset`: a raw dataset from `import.yml`
- `transform_group`: a group from `transform.yml`

Compatibility is computed before validation:

- Darwin Core Occurrence requires occurrence-grain data, or a relation from the
  selected source or context to an occurrence dataset.
- Humboldt/Event requires event, inventory, site, or sampling evidence. Site
  sources can be plausible, but still need review.
- Aggregate transform groups are not enough for standard publication unless
  they are connected to the expected standard grain.

The compatibility report can return `compatible`, `plausible`, or `blocked`.

## Validation States

Validation is report-based. The stored `validation_status` is only the
last-known display value; the API recomputes a full report from the current
profile and project config.

| Status | Meaning |
| --- | --- |
| `draft` | The profile exists but does not yet have enough mappings to be judged conformant. |
| `partial` | The profile has no critical errors, but warnings or recommended mappings remain. |
| `invalid` | A critical compatibility or mapping issue blocks publication files. |
| `conformant` | Required compatibility and mappings pass for the implemented rules. |

Current validation checks include:

- mapping shape: each term maps to a source string, a `source` object, or a
  `generator` object
- Darwin Core Occurrence requires `occurrenceID`
- Humboldt/Event requires `eventID`
- Humboldt/Event recommends `eventDate`, `samplingProtocol`, and `locationID`

## Mapping Values

Mappings can point to a source path:

```yaml
mappings:
  scientificName:
    source: scientific_name
  eventDate: event.date
```

Mappings can also use supported generators:

```yaml
mappings:
  occurrenceID:
    generator: unique_occurrence_id
    params:
      prefix: niaocc_
  datasetName:
    generator: constant
    params:
      value: Niamoto export
  modified:
    generator: current_date
```

Generators available through profile output generation are `constant`,
`current_date`, and `unique_occurrence_id`. The legacy
`niamoto_to_dwc_occurrence` transformer supports additional Darwin Core
generators inside legacy `exports` targets.

## Outputs

Profile output types are configured in `outputs`.

- `api_json`: writes `{profile_name}.json` with profile metadata and mapped
  records.
- `dwc_archive`: Darwin Core Occurrence only. Generates a Darwin Core Archive
  using `dwc_archive_exporter`.
- `standard_files`: Humboldt/Event only. Generates `event.csv` and
  `metadata.json`.

The GUI lets draft JSON be generated even when validation has critical issues.
Publication files are blocked when critical validation issues are present.

## API Surface

The GUI backend exposes:

- `GET /api/standard-profiles`
- `GET /api/standard-profiles/{profile_name}`
- `POST /api/standard-profiles`
- `PATCH /api/standard-profiles/{profile_name}`
- `DELETE /api/standard-profiles/{profile_name}`
- `GET /api/standard-profiles/{profile_name}/compatibility`
- `GET /api/standard-profiles/{profile_name}/validation`
- `POST /api/standard-profiles/{profile_name}/outputs/{output_type}`

The list endpoint also returns `legacy_hints` for existing
`dwc_occurrence_json` targets.

## Legacy Darwin Core JSON

Existing projects may still contain an `exports` target named
`dwc_occurrence_json`, or a `json_api_exporter` group using
`niamoto_to_dwc_occurrence`.

This remains valid legacy behavior. Niamoto reports it as a Darwin Core
Occurrence-like hint, but does not rewrite it into `standard_profiles`
automatically. Keep legacy targets in fixtures when the goal is regression
coverage for old exports.

## Related

- [api-export-guide.md](api-export-guide.md)
- [../02-user-guide/collections.md](../02-user-guide/collections.md)
- [../04-plugin-development/examples/darwin-core-export.md](../04-plugin-development/examples/darwin-core-export.md)
