# API Export Guide

Niamoto can publish machine-readable outputs alongside the website export. There
are now two configuration surfaces:

- simple static JSON APIs, stored as ordinary `json_api_exporter` targets under
  `exports`
- standard publication profiles, stored under the top-level
  `standard_profiles` section in `config/export.yml`

Keep these workflows separate. A JSON API exposes transformed collection data.
A standard profile describes a biodiversity publication standard, a target
grain, validation rules, and profile-owned outputs.

## Main exporters

- `src/niamoto/core/plugins/exporters/json_api_exporter.py`
- `src/niamoto/core/plugins/exporters/dwc_archive_exporter.py`

## Export configuration surface

- `exports[*].exporter`: exporter plugin name
- `exports[*].params`: exporter-specific settings
- `exports[*].groups`: exported group targets
- `standard_profiles[*]`: standard publication profile definitions

The `exports` list is still the only surface used by ordinary website and JSON
API export jobs. `standard_profiles` is a sibling top-level section. It is read
by the standard profile API and UI, and its outputs are generated explicitly
from profile actions.

## Simple JSON API workflow

Open **Collections > API** to manage static API targets for one collection.
Each export card keeps the saved `export.yml` configuration separate from the
local draft shown in the interface.

Use **Auto-configure** to ask Niamoto for a suggested configuration. The
proposal is review-only: it analyzes the current transformed data and prepares
sections for index fields, detail fields, JSON options, and Darwin Core mapping
when relevant. Nothing is written to `export.yml` until the proposal is applied
to the card and the card is saved.

Simple JSON exports always keep **Export all transformed data** available for
detail files. This is the low-friction API mode: the listing can stay compact
through index fields while individual detail files continue to expose the full
transformed payload. Applying the **Detail JSON fields** auto-configuration
section switches pass-through off automatically because the card is now using a
curated detail payload. Re-enable pass-through from the card toggle to return to
the full transformed detail output.

Static API index rows always include a `detail_url` generated from the detail
file pattern. A client can load the index JSON first, then follow each
`detail_url` to fetch the complete individual JSON file.

Index fields, curated detail fields, Darwin Core mappings, and JSON output
options use visual editors by default. Source paths in field mappings are
selected from detected transformed fields to avoid invalid paths. Field
sections show a read-only JSON preview generated from a representative
transformed entity next to the form, and every synchronized section also
provides a JSON view for advanced edits. Invalid JSON remains in the editor as
a visible error and does not replace the last valid visual configuration.

Darwin Core auto-configuration is conservative. Niamoto pre-fills safe
identifiers and generated values, but uncertain terms are surfaced as items to
review before publishing to external biodiversity networks. This is not a
Darwin Core or GBIF validator: users must still map the relevant occurrence
terms and controlled values for their source data.

## Standard profile workflow

Open **Collections > Standards** to configure publication profiles for Darwin
Core Occurrence and Humboldt/Event outputs.

A profile has:

- `name`: stable profile identifier
- `standard`: `darwin_core_occurrence` or `humboldt_event`
- `target_grain`: expected standard grain, such as `occurrence`, `event`, or
  `inventory`
- `source`: collection, reference, dataset, or transform group used as input
- `context`: optional related source, for example taxon context for occurrence
  data
- `mappings`: standard terms mapped to source paths or generators
- `outputs`: profile-owned output targets, such as `api_json`, `dwc_archive`,
  or `standard_files`
- `validation_status`: persisted last-known status for display

The backend exposes profile management under `/api/standard-profiles`.
Compatibility and validation are computed from the current import and transform
configuration before publication files are generated.

Standard profile JSON output is intentionally separate from simple JSON API
exports. It writes standard-shaped records with profile metadata, not the raw
transformed collection payload.

## Legacy Darwin Core JSON targets

Existing `dwc_occurrence_json` entries under `exports` remain valid. They are
treated as legacy JSON API targets using `niamoto_to_dwc_occurrence`.

The standard profile store reports these targets as legacy Darwin Core
Occurrence hints. It does not migrate or delete them automatically. This keeps
older projects reproducible while making the intended profile interpretation
visible in the GUI and documentation.

## Related docs

- [Publish](../02-user-guide/publish.md): user-facing publication flow
- [standard-profiles.md](standard-profiles.md): standard profile configuration
  reference
- [api/modules.rst](api/modules.rst): autogenerated Python reference
- [external-apis.md](external-apis.md): surrounding integration context
