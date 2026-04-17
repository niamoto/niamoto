# Plugin Development

Build custom plugins for Niamoto without patching the core runtime.

## Plugin Types

| Type | Register with | Where Niamoto uses it | What it does |
| --- | --- | --- | --- |
| Loader | `PluginType.LOADER` | `transform.yml` source relations and some enrichment flows | Fetch rows before a transform runs |
| Transformer | `PluginType.TRANSFORMER` | `transform.yml` | Compute derived data |
| Widget | `PluginType.WIDGET` | `export.yml` widget lists | Render HTML for exported pages |
| Exporter | `PluginType.EXPORTER` | `export.yml` targets | Generate files or sites |
| Deployer | `PluginType.DEPLOYER` | `deploy.yml` and `niamoto deploy` | Publish generated exports |

## Start Here

- [architecture.md](architecture.md) explains registry, loading, and config surfaces.
- [creating-transformers.md](creating-transformers.md) shows how to write a transformer and validate its config.
- [building-widgets.md](building-widgets.md) covers widget params, rendering, and `export.yml`.
- [custom-exporters.md](custom-exporters.md) covers exporter params, target configs, and output generation.
- [database-aggregator-guide.md](database-aggregator-guide.md) documents the SQL-based transformer that ships with Niamoto.

## Minimal Transformer

```python
from typing import Any, Dict, Literal

import pandas as pd
from pydantic import Field

from niamoto.core.plugins.base import PluginType, TransformerPlugin, register
from niamoto.core.plugins.models import BasePluginParams, PluginConfig


class MeanDbhParams(BasePluginParams):
    field: str = Field(default="dbh")


class MeanDbhConfig(PluginConfig):
    plugin: Literal["mean_dbh"] = "mean_dbh"
    params: MeanDbhParams


@register("mean_dbh", PluginType.TRANSFORMER)
class MeanDbhTransformer(TransformerPlugin):
    config_model = MeanDbhConfig
    param_schema = MeanDbhParams

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, float]:
        validated = self.config_model(**config)
        params = validated.params
        return {"mean_dbh": float(data[params.field].dropna().mean())}
```

## Workflow

1. Pick the plugin type.
2. Define a params model with `BasePluginParams`.
3. Define a config model that wraps `plugin` and `params`.
4. Register the class with `@register("name", PluginType.X)`.
5. Wire it into `transform.yml`, `export.yml`, or `deploy.yml`.
6. Add tests under the matching tree in `tests/core/plugins/`.

## Test Locations

- Transformers: `tests/core/plugins/transformers/`
- Widgets: `tests/core/plugins/widgets/`
- Exporters: `tests/core/plugins/exporters/`
- Loaders: `tests/core/plugins/loaders/`
- Deployers: `tests/core/plugins/deployers/`

## Related

- [../06-reference/README.md](../06-reference/README.md)
- [../05-ml-detection/README.md](../05-ml-detection/README.md)
- [../07-architecture/README.md](../07-architecture/README.md)

```{toctree}
:hidden:

architecture
creating-transformers
building-widgets
custom-exporters
database-aggregator
database-aggregator-guide
examples/darwin-core-export
examples/taxonomy-enricher
```
