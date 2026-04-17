# Building Widgets

Widgets render HTML for `html_page_exporter`. Niamoto validates widget params, calls `render(data, params)`, then wraps the result in the standard widget container.

## Runtime Contract

Use `WidgetPlugin` and a typed params model.

```python
import html
from typing import Any, Optional

from pydantic import Field

from niamoto.core.plugins.base import PluginType, WidgetPlugin, register
from niamoto.core.plugins.models import BasePluginParams


class SpeciesCardsParams(BasePluginParams):
    label_field: str = Field(default="species")
    value_field: str = Field(default="count")
    empty_message: str = Field(default="No data available")


@register("species_cards", PluginType.WIDGET)
class SpeciesCardsWidget(WidgetPlugin):
    param_schema = SpeciesCardsParams

    def render(self, data: Optional[Any], params: SpeciesCardsParams) -> str:
        if data is None:
            return f"<p>{html.escape(params.empty_message)}</p>"

        rows = data.to_dict(orient="records") if hasattr(data, "to_dict") else data
        items = []

        for row in rows:
            label = html.escape(str(row.get(params.label_field, "")))
            value = html.escape(str(row.get(params.value_field, "")))
            items.append(f"<li><strong>{label}</strong>: {value}</li>")

        return "<ul>" + "".join(items) + "</ul>"
```

## What Goes In `param_schema`

Put widget-specific options in the params model:

- field names
- display switches
- formatting options
- chart behavior

Do not put `title`, `description`, or `layout` in the params model unless the widget needs its own internal title. `WidgetConfig` already handles those fields.

## `export.yml` Shape

Widgets belong inside an export target and inside a group.

```yaml
exports:
  - name: web_pages
    exporter: html_page_exporter
    params:
      template_dir: templates
      output_dir: exports/web
    groups:
      - group_by: plots
        widgets:
          - plugin: species_cards
            title: Dominant species
            description: Top species for this plot
            data_source: top_species
            params:
              label_field: species
              value_field: count
              empty_message: No species data
```

The runtime validates each widget entry as:

- `plugin`
- `data_source`
- `title`
- `description`
- `params`
- `layout`

The old `type/config` shape is no longer the canonical widget format.

## Dependencies

If your widget needs external CSS or JavaScript, override `get_dependencies()`.

```python
def get_dependencies(self) -> set[str]:
    return {
        "https://cdn.jsdelivr.net/npm/chart.js",
    }
```

`html_page_exporter` collects those dependencies and injects them into the page.

## HTML Safety

Escape every value that comes from the database or from config before you interpolate it into HTML.

```python
import html

title = html.escape(str(user_value))
tooltip = html.escape(str(description), quote=True)
```

Use the same rule for:

- entity names
- labels
- field values
- exception messages

## Preview

The GUI preview engine uses the same widget plugins. If your widget renders correctly in exports and does not rely on browser globals outside its own markup, preview usually works with no extra code.

## Tests

Put widget tests under `tests/core/plugins/widgets/`. Built-in widgets such as `bar_plot`, `info_grid`, and `raw_data_widget` show the current pattern:

- validate params with `param_schema`
- call `render(data, params_model)`
- assert on the returned HTML

## Practical Rules

- Keep `render()` pure. Return HTML. Do not write files from a widget.
- Read input data from `data_source`, not from the filesystem.
- Validate config with `param_schema`, not manual `dict.get(...)` chains.
- Return a useful empty state when `data` is missing or empty.
- Escape dynamic values before embedding them in HTML.
