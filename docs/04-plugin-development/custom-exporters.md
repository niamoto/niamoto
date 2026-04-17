# Custom Exporters

Exporters turn validated `export.yml` targets into files, folders, or API payloads. `ExporterService` passes the whole target config to the plugin, not a loose `data/config/output_path` triple.

## Runtime Contract

Write exporters against `TargetConfig`.

```python
import json
from pathlib import Path
from typing import Optional

from pydantic import Field

from niamoto.core.plugins.base import ExporterPlugin, PluginType, register
from niamoto.core.plugins.models import BasePluginParams, TargetConfig


class ManifestExporterParams(BasePluginParams):
    output_dir: str = Field(default="exports/manifest")
    filename: str = Field(default="manifest.json")


@register("manifest_exporter", PluginType.EXPORTER)
class ManifestExporter(ExporterPlugin):
    param_schema = ManifestExporterParams

    def export(
        self,
        target_config: TargetConfig,
        repository,
        group_filter: Optional[str] = None,
    ) -> None:
        params = ManifestExporterParams.model_validate(target_config.params)
        output_dir = Path(params.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        groups = target_config.groups or []
        if group_filter:
            groups = [group for group in groups if group.group_by == group_filter]

        payload = {
            "target": target_config.name,
            "exporter": target_config.exporter,
            "groups": [group.group_by for group in groups],
        }

        output_file = output_dir / params.filename
        output_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
```

## What Niamoto Passes To The Exporter

`ExporterService` calls:

```python
exporter.export(target_config=target, repository=self.db, group_filter=group_filter)
```

That means a custom exporter should accept:

- `target_config`
- `repository`
- `group_filter=None`

If your method only accepts `data, config, output_path`, the current runtime will not call it correctly.

## `export.yml` Shape

Export targets live under `exports:`. Each target declares one exporter and zero or more groups.

```yaml
exports:
  - name: analytics_api
    exporter: json_api_exporter
    params:
      output_dir: exports/api
      detail_output_pattern: "{group}/{id}.json"
    groups:
      - group_by: plots
        index:
          fields:
            - id
            - name
```

The canonical target shape is:

- `name`
- `enabled`
- `exporter`
- `params`
- `static_pages`
- `groups`

The old `export.exporters[*].type/config` shape is no longer the runtime contract.

## Where To Read Data

Most exporters do one or both of these:

- iterate over `target_config.groups`
- read transformed tables or source tables through `repository`

For working examples, inspect:

- `src/niamoto/core/plugins/exporters/html_page_exporter.py`
- `src/niamoto/core/plugins/exporters/json_api_exporter.py`
- `src/niamoto/core/plugins/exporters/dwc_archive_exporter.py`

## Validation

Use a params model for `target_config.params`. Let Niamoto validate the target structure, then validate exporter-specific params inside the plugin.

```python
params = ManifestExporterParams.model_validate(target_config.params)
```

## Static Pages And Widgets

If your exporter behaves like `html_page_exporter`, it will also need to interpret:

- `target_config.static_pages`
- `target_config.groups[*].widgets`

If your exporter does not use them, ignore them. Do not invent a second config schema.

## Tests

Put exporter tests under `tests/core/plugins/exporters/`. The built-in exporter tests show the current pattern:

- build a `TargetConfig`
- instantiate the exporter
- call `export(target_config, repository, group_filter=None)`
- assert on generated files or stats

## Practical Rules

- Accept `group_filter` even if your exporter does not use it yet.
- Parse `target_config.params` with a Pydantic model.
- Create output directories with `Path(...).mkdir(parents=True, exist_ok=True)`.
- Keep one exporter focused on one output family.
- Reuse existing target and group models instead of inventing parallel YAML shapes.
