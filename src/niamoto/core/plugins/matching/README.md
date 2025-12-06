# Pattern Matching System for Transformer-Widget Auto-Discovery

This module implements a simple, effective pattern matching system that automatically discovers compatible widgets for transformers based on their data structure patterns.

## Philosophy

**Keep it simple.** Instead of complex Pydantic schemas and type validation, we use plain dictionary patterns to match transformer outputs with widget inputs. If you can describe the data structure in 30 seconds to a botanist, it's the right approach.

## How It Works

### 1. Transformers Declare Output Structure

Transformers specify what keys they return in their output dictionaries:

```python
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

@register("binned_distribution", PluginType.TRANSFORMER)
class BinnedDistribution(TransformerPlugin):
    """Plugin for creating binned distributions."""

    # Declare what this transformer returns
    output_structure = {
        "bins": "list",
        "counts": "list",
        "labels": "list",      # optional
        "percentages": "list"  # optional
    }

    def transform(self, data, params):
        return {
            "bins": [0, 100, 200, 500],
            "counts": [56, 24, 10],
            "percentages": [59.57, 25.53, 14.89]
        }
```

### 2. Widgets Declare Compatible Structures

Widgets specify what input patterns they can handle:

```python
from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

@register("bar_plot", PluginType.WIDGET)
class BarPlotWidget(WidgetPlugin):
    """Widget to display bar plots."""

    # Declare what input patterns this widget accepts
    compatible_structures = [
        {"bins": "list", "counts": "list"},              # minimal binned data
        {"bins": "list", "counts": "list", "percentages": "list"},  # with percentages
        {"categories": "list", "values": "list"},        # categorical data
        {"labels": "list", "values": "list"},           # generic labeled data
    ]

    def render(self, data, params):
        # Widget handles transformation internally via data_access.py
        return "<div>...</div>"
```

### 3. SmartMatcher Finds Compatibility

The `SmartMatcher` uses a three-tier scoring system:

| Score | Match Type | Description | Example |
|-------|-----------|-------------|---------|
| 1.0 | Exact Match | Output keys exactly match one pattern | Transformer has `{bins, counts}`, widget needs `{bins, counts}` |
| 0.8 | Superset Match | Output has all required keys + extras | Transformer has `{bins, counts, percentages}`, widget needs `{bins, counts}` |
| 0.6 | Partial Match | Output has at least 50% of required keys | Transformer has `{bins, counts}`, widget needs `{bins, counts, labels, percentages}` |
| 0.0 | Incompatible | Not enough overlap | Transformer has `{x, y}`, widget needs `{bins, counts}` |

## Usage Example

```python
from niamoto.core.plugins.matching import SmartMatcher
from niamoto.core.plugins.transformers.distribution.binned_distribution import BinnedDistribution

# Create matcher
matcher = SmartMatcher()

# Find compatible widgets
suggestions = matcher.find_compatible_widgets(BinnedDistribution)

for suggestion in suggestions:
    print(f"{suggestion.widget_name}: {suggestion.score} ({suggestion.reason})")

# Output:
# bar_plot: 0.8 (superset_match)
# histogram: 1.0 (exact_match)
```

## Creating Custom Plugins

### For Transformer Authors

1. Define your output structure with the keys your transformer returns:

```python
@register("my_transformer", PluginType.TRANSFORMER)
class MyTransformer(TransformerPlugin):
    output_structure = {
        "categories": "list",
        "values": "list",
        "metadata": "dict"
    }

    def transform(self, data, params):
        return {
            "categories": ["A", "B", "C"],
            "values": [10, 20, 30],
            "metadata": {"source": "field_study"}
        }
```

2. **The type values (`"list"`, `"dict"`) are currently for documentation only.** The matcher only checks key presence, not value types.

### For Widget Authors

1. Define compatible input patterns:

```python
@register("my_widget", PluginType.WIDGET)
class MyWidget(WidgetPlugin):
    compatible_structures = [
        {"categories": "list", "values": "list"},     # Pattern 1
        {"bins": "list", "counts": "list"},           # Pattern 2
        {"x": "list", "y": "list", "z": "list"}       # Pattern 3
    ]

    def render(self, data, params):
        # Your rendering logic
        return "<div>...</div>"
```

2. **List patterns from most specific to least specific.** The matcher will find the best match.

3. **Handle data transformation inside your widget** using `data_access.py` utilities (see `bar_plot.py` for examples).

## Legacy Support

Plugins without `output_structure` or `compatible_structures` fall back to a legacy mapping system. This ensures backward compatibility during migration:

```python
# Transformer without output_structure
class LegacyTransformer(TransformerPlugin):
    # No output_structure - uses legacy fallback

    def transform(self, data, params):
        return {"data": [...]}
```

## Testing Your Patterns

```python
from niamoto.core.plugins.matching import SmartMatcher

# Get your transformer class
from my_module import MyTransformer

# Create matcher
matcher = SmartMatcher()

# Check exact match
output = MyTransformer.output_structure
pattern = {"categories": "list", "values": "list"}
assert matcher._exact_match(output, pattern)

# Check superset match
output = {"categories": "list", "values": "list", "extra": "dict"}
pattern = {"categories": "list", "values": "list"}
assert matcher._superset_match(output, pattern)
```

## Design Decisions

### Why not Pydantic contracts?

1. **Simplicity**: Pattern matching is easier to understand and maintain
2. **Flexibility**: Transformers return plain dicts, no schema enforcement needed
3. **No overengineering**: We don't need complex type validation for key presence checks
4. **Golden Rule**: "If you can explain it to a botanist in 2 minutes, it's the right solution"

### Why three scoring tiers?

- **1.0 (Exact)**: Perfect match, high confidence
- **0.8 (Superset)**: Transformer provides everything needed + extras (safe)
- **0.6 (Partial)**: Some keys missing, might work but needs verification (low confidence)

### What about type checking?

Currently, we only check key presence. The type strings (`"list"`, `"dict"`) are documentation. This keeps the system simple and works for 99% of cases. If you need strict type validation, add it in your transformer's `transform()` method.

## Migration from Contracts

The old Pydantic contract system in `src/niamoto/core/plugins/contracts/` is still present for reference but **optional**. You can:

1. **Use pattern matching only** (recommended for new plugins)
2. **Use both** (pattern matching + contracts for extra validation)
3. **Use contracts only** (legacy mode, will be deprecated)

## Performance

Pattern matching is fast:
- O(1) key lookup using sets
- No Pydantic model instantiation overhead
- No reflection or metaclass magic
- Typical matching: <1ms for 100 widgets

## Examples

See:
- `/Users/julienbarbe/Dev/Niamoto/Niamoto/src/niamoto/core/plugins/transformers/distribution/binned_distribution.py` - Transformer example
- `/Users/julienbarbe/Dev/Niamoto/Niamoto/src/niamoto/core/plugins/widgets/bar_plot.py` - Widget example
- `/Users/julienbarbe/Dev/Niamoto/Niamoto/tests/core/plugins/matching/test_pattern_matching.py` - Comprehensive test suite

## Questions?

- **Q: Can I use nested structures?**
  A: Not yet. Keep it flat. If you need nested data, flatten it in your transformer.

- **Q: What if my transformer returns different structures based on config?**
  A: Declare the superset of all possible keys. Partial matches (0.6 score) will catch compatible widgets.

- **Q: How do I debug matching issues?**
  A: Enable debug logging: `logger.setLevel(logging.DEBUG)`. SmartMatcher logs all match attempts.

- **Q: Can widgets transform data internally?**
  A: Yes! See `bar_plot.py` for examples of internal data transformation via `data_access.py`.
