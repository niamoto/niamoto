# Creating Plugins with Niamoto Binary

This guide explains how to create custom plugins when using the Niamoto standalone binary.

## 🎯 Two Distribution Modes

### Binary Mode (End Users)
- ✅ No Python installation required
- ✅ Simple download and run
- ⚠️ Limited to bundled libraries
- 🎯 Best for: End users, GUI usage, standard workflows

### pip Install Mode (Developers)
- ✅ Full Python ecosystem access
- ✅ Install any library with pip
- ✅ Unlimited plugin extensibility
- 🎯 Best for: Developers, custom plugins, advanced workflows

## 📚 Available Libraries in Binary

The Niamoto binary includes these libraries (available for your plugins):

### Data Processing
- **pandas** 2.x - DataFrame manipulation
- **numpy** 1.x - Numerical computing
- **polars** - Fast DataFrame library (if included)

### Geospatial
- **geopandas** 0.x - Geospatial data handling
- **shapely** 2.x - Geometric operations
- **fiona** 1.x - File I/O
- **pyproj** 3.x - Coordinate transformations

### Database
- **duckdb** 0.x - Analytical database
- **sqlalchemy** 2.x - ORM and SQL toolkit
- **geoalchemy2** - Spatial extensions

### Web & API
- **fastapi** 0.x - Web framework
- **uvicorn** 0.x - ASGI server
- **httpx** 0.x - HTTP client
- **requests** - HTTP library

### Utilities
- **pyyaml** - YAML parsing
- **jinja2** - Templates
- **click** - CLI framework
- **pydantic** - Data validation

### Visualization (if included)
- **matplotlib** - Plotting (check if available)

## ✅ Creating a Plugin (Binary Compatible)

### Example: Simple Transformer

```python
# plugins/transformers/count_species.py
import pandas as pd  # ✅ Available in binary
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

@register("count_species_by_plot", PluginType.TRANSFORMER)
class CountSpeciesByPlot(TransformerPlugin):
    """Count species occurrences per plot."""

    def transform(self, data, config):
        # Uses pandas - available in binary
        df = pd.DataFrame(data)
        counts = df.groupby('plot_id')['taxon_id'].nunique()
        return counts.to_dict()
```

**Result**: ✅ Works with binary!

### Example: Geospatial Plugin

```python
# plugins/transformers/calculate_area.py
import geopandas as gpd  # ✅ Available in binary
from shapely.geometry import Point  # ✅ Available
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

@register("calculate_plot_area", PluginType.TRANSFORMER)
class CalculatePlotArea(TransformerPlugin):
    """Calculate area of plots."""

    def transform(self, data, config):
        gdf = gpd.GeoDataFrame(data)
        gdf['area_m2'] = gdf.geometry.area
        return gdf
```

**Result**: ✅ Works with binary!

## ❌ What DOESN'T Work

### Example: Machine Learning Plugin

```python
# plugins/transformers/cluster_species.py
from sklearn.cluster import KMeans  # ❌ NOT in binary!
import plotly.express as px  # ❌ NOT in binary!
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

@register("cluster_species", PluginType.TRANSFORMER)
class ClusterSpecies(TransformerPlugin):
    def transform(self, data, config):
        # This will FAIL with binary
        model = KMeans(n_clusters=5)
        # ModuleNotFoundError: No module named 'sklearn'
```

**Result**: ❌ Crashes with binary!

**Solution**: Use pip install mode instead.

## 🔧 Checking Available Libraries

### From Python Code

```python
import importlib.util

def is_library_available(name):
    """Check if a library is available."""
    return importlib.util.find_spec(name) is not None

# In your plugin
if is_library_available('sklearn'):
    from sklearn.cluster import KMeans
    # Use scikit-learn
else:
    # Use alternative approach with pandas/numpy
    print("Warning: scikit-learn not available, using basic clustering")
```

### From Command Line

```bash
# With binary
./niamoto --help  # This works

# Try importing a library
python3 -c "import sklearn"  # This checks SYSTEM Python, not binary!
```

## 🎯 Best Practices

### 1. Design for Binary First

Use only bundled libraries when possible:

```python
# ✅ Good - uses bundled libs
import pandas as pd
import numpy as np
from scipy import stats  # If scipy is bundled

# ❌ Avoid if possible
import tensorflow as tf
import torch
```

### 2. Provide Fallbacks

```python
try:
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class MyPlugin(TransformerPlugin):
    def transform(self, data, config):
        if HAS_SKLEARN:
            # Use sklearn
            scaler = StandardScaler()
            return scaler.fit_transform(data)
        else:
            # Fallback using pandas/numpy
            return (data - data.mean()) / data.std()
```

### 3. Document Dependencies

```python
"""
My Advanced Plugin

Requirements:
- Binary mode: Works with standard libs (pandas, numpy)
- pip mode: Requires scikit-learn, plotly (pip install scikit-learn plotly)

Usage:
    If using binary: Use basic mode
    If using pip install: Full features available
"""
```

## 🚀 When to Use Each Mode

### Use Binary When:
- ✅ End users without Python knowledge
- ✅ Simple GUI-based workflows
- ✅ Standard ecological analyses
- ✅ Using only core plugins
- ✅ Need offline capability
- ✅ Want zero setup

### Use pip install When:
- ✅ Developing custom plugins
- ✅ Need specific Python libraries
- ✅ Advanced machine learning
- ✅ Custom visualizations
- ✅ Research & development
- ✅ Integration with other tools

## 📦 Migrating from Binary to pip

If you start with binary and need more libraries:

```bash
# 1. Install Python 3.11+
python3 --version  # Should be 3.11 or higher

# 2. Install Niamoto via pip
pip install niamoto

# 3. Install additional dependencies
pip install scikit-learn plotly seaborn

# 4. Use same instance directory
niamoto gui --instance /path/to/your/instance/

# 5. Your plugins now have access to all installed libraries!
```

## 🔍 Checking What's Bundled

To see exactly what's in your binary:

```bash
# Extract the binary contents (advanced)
./niamoto --version  # Check it works

# The binary extracts to /tmp/_MEI* when running
# You can inspect this directory while the binary runs
```

Or check the build spec:

```python
# In build_scripts/niamoto.spec
hiddenimports = [
    'pandas',  # ✅ Included
    'numpy',   # ✅ Included
    'geopandas',  # ✅ Included
    # ... check this list
]
```

## 💡 Future: Plugin Bundles

**Coming soon**: Ability to distribute plugins with their dependencies:

```yaml
# transform.yml (future)
plugins:
  - name: my_ml_plugin
    type: transformer
    bundle: https://example.com/niamoto-ml-plugin-v1.0.tar.gz
    # Bundle contains plugin + dependencies
```

This would allow using any library even with the binary!

## 🆘 Troubleshooting

### "ModuleNotFoundError" when running plugin

**Cause**: Plugin imports a library not in the binary.

**Solutions**:
1. Check if library is in bundled list above
2. Rewrite plugin to use available libraries
3. Switch to pip install mode

### Plugin works with `pip install` but not binary

**Cause**: Plugin uses non-bundled library.

**Solution**: This is expected! Document that your plugin requires pip mode.

```python
# In your plugin
"""
Advanced ML Plugin

⚠️ REQUIRES: pip install niamoto
This plugin uses scikit-learn which is not available in the binary.

Installation:
    pip install niamoto scikit-learn

Usage:
    niamoto gui --instance my-project/
"""
```

## 📚 Resources

- [Binary Distribution Guide](BINARY_DISTRIBUTION.md)
- [Plugin Development Guide](../src/niamoto/core/plugins/README.md)
- [Python Package Index](https://pypi.org/) - Find libraries
