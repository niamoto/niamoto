# Custom Plugin Development Guide

This guide walks through the process of creating custom plugins for the Niamoto platform. By developing custom plugins, you can extend Niamoto's functionality to meet your specific needs without modifying the core codebase.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Plugin Directory Structure](#plugin-directory-structure)
- [Creating a New Plugin](#creating-a-new-plugin)
  - [Step 1: Choose a Plugin Type](#step-1-choose-a-plugin-type)
  - [Step 2: Create the Plugin Class](#step-2-create-the-plugin-class)
  - [Step 3: Implement Required Methods](#step-3-implement-required-methods)
  - [Step 4: Register the Plugin](#step-4-register-the-plugin)
  - [Step 5: Configure and Test](#step-5-configure-and-test)
- [Plugin Configuration Models](#plugin-configuration-models)
- [Advanced Topics](#advanced-topics)
  - [Plugin Chains](#plugin-chains)
  - [Error Handling](#error-handling)
  - [Testing Plugins](#testing-plugins)

## Prerequisites

Before developing custom plugins, ensure you have:

1. A working Niamoto installation
2. Basic understanding of Python and object-oriented programming
3. Familiarity with Niamoto's configuration files
4. Knowledge of the data you want to process

## Plugin Directory Structure

Custom plugins should be placed in your project's `plugins` directory, organized by plugin type:

```bash
project/
  ├── plugins/
  │   ├── transformers/
  │   │   └── my_transformer.py
  │   ├── loaders/
  │   │   └── my_loader.py
  │   ├── exporters/
  │   │   └── my_exporter.py
  │   └── widgets/
  │       └── my_widget.py
  └── ...
```

## Creating a New Plugin

### Step 1: Choose a Plugin Type

First, determine which type of plugin you need based on your requirements:

- **Loader Plugin**: For importing data from custom sources
- **Transformer Plugin**: For performing calculations or analysis
- **Exporter Plugin**: For exporting data in custom formats
- **Widget Plugin**: For creating custom visualizations

### Step 2: Create the Plugin Class

Create a new Python file in the appropriate plugin directory. Your plugin class should inherit from the base class for the chosen plugin type:

```python
# plugins/transformers/custom_analysis.py
from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig
)
from pydantic import Field
import pandas as pd

# Define a configuration model using Pydantic
class CustomAnalysisConfig(PluginConfig):
    """Configuration for custom analysis plugin"""
    plugin: str = "custom_analysis"
    params: dict = Field(default_factory=lambda: {
        "source": "",
        "field": None,
        "threshold": 0.5
    })

# Create the plugin class
class CustomAnalysis(TransformerPlugin):
    """Plugin for performing custom analysis"""

    # Specify the configuration model
    config_model = CustomAnalysisConfig
```

### Step 3: Implement Required Methods

Each plugin type requires specific methods to be implemented. For a Transformer plugin, you need to implement at least:

```python
def validate_config(self, config):
    """Validate plugin configuration"""
    try:
        validated_config = self.config_model(**config)

        # Additional validation if needed
        if validated_config.params.get("threshold") < 0:
            raise ValueError("Threshold must be non-negative")

        return validated_config
    except Exception as e:
        raise ValueError(f"Invalid configuration: {str(e)}")

def transform(self, data, config):
    """Transform data according to configuration"""
    try:
        # Validate configuration
        validated_config = self.validate_config(config)

        # Get parameters
        source = validated_config.params.get("source", "occurrences")
        field = validated_config.params.get("field")
        threshold = validated_config.params.get("threshold", 0.5)

        # Get source data if different from occurrences
        if source != "occurrences":
            result = self.db.execute_select(f"""
                SELECT * FROM {source}
            """)
            data = pd.DataFrame(result.fetchall(),
                               columns=[desc[0] for desc in result.cursor.description])

        # Perform analysis
        if field and field in data.columns:
            field_data = data[field].dropna()

            # Example calculation: find values above threshold
            above_threshold = field_data[field_data > threshold]
            count_above = len(above_threshold)
            percent_above = (count_above / len(field_data)) * 100 if len(field_data) > 0 else 0

            return {
                "threshold": threshold,
                "count_above": count_above,
                "percent_above": round(percent_above, 2),
                "max_value": field_data.max() if not field_data.empty else None
            }

        return {"error": "Invalid field or no data"}

    except Exception as e:
        return {"error": str(e)}
```

### Step 4: Register the Plugin

Register your plugin with the system using the `@register` decorator:

```python
@register("custom_analysis", PluginType.TRANSFORMER)
class CustomAnalysis(TransformerPlugin):
    """Plugin for performing custom analysis"""
    # ... implementation ...
```

The complete plugin should look like:

```python
from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig
)
from pydantic import Field
import pandas as pd

class CustomAnalysisConfig(PluginConfig):
    """Configuration for custom analysis plugin"""
    plugin: str = "custom_analysis"
    params: dict = Field(default_factory=lambda: {
        "source": "",
        "field": None,
        "threshold": 0.5
    })

@register("custom_analysis", PluginType.TRANSFORMER)
class CustomAnalysis(TransformerPlugin):
    """Plugin for performing custom analysis"""

    config_model = CustomAnalysisConfig

    def validate_config(self, config):
        """Validate plugin configuration"""
        try:
            validated_config = self.config_model(**config)

            # Additional validation if needed
            if validated_config.params.get("threshold") < 0:
                raise ValueError("Threshold must be non-negative")

            return validated_config
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data, config):
        """Transform data according to configuration"""
        try:
            # Validate configuration
            validated_config = self.validate_config(config)

            # Get parameters
            source = validated_config.params.get("source", "occurrences")
            field = validated_config.params.get("field")
            threshold = validated_config.params.get("threshold", 0.5)

            # Get source data if different from occurrences
            if source != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {source}
                """)
                data = pd.DataFrame(result.fetchall(),
                                   columns=[desc[0] for desc in result.cursor.description])

            # Perform analysis
            if field and field in data.columns:
                field_data = data[field].dropna()

                # Example calculation: find values above threshold
                above_threshold = field_data[field_data > threshold]
                count_above = len(above_threshold)
                percent_above = (count_above / len(field_data)) * 100 if len(field_data) > 0 else 0

                return {
                    "threshold": threshold,
                    "count_above": count_above,
                    "percent_above": round(percent_above, 2),
                    "max_value": field_data.max() if not field_data.empty else None
                }

            return {"error": "Invalid field or no data"}

        except Exception as e:
            return {"error": str(e)}
```

### Step 5: Configure and Test

Once your plugin is implemented, you can configure it in the appropriate YAML file. For a transformer plugin, add it to `transform.yml`:

```yaml
- group_by: taxon
  widgets_data:
    threshold_analysis:
      plugin: custom_analysis
      params:
        source: occurrences
        field: dbh
        threshold: 30.0
```

## Plugin Configuration Models

Using Pydantic models for configuration validation is recommended as it provides:

1. Automatic type checking and validation
2. Default values for optional parameters
3. Clear documentation of configuration options
4. Custom validation rules via validators

Example configuration model with validators:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional

class MyPluginConfig(PluginConfig):
    """Configuration for my custom plugin"""
    plugin: str = "my_plugin"
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "source": "",
        "fields": [],
        "min_value": 0,
        "max_value": 100
    })

    @field_validator("params")
    @classmethod
    def validate_params(cls, v):
        """Validate plugin parameters"""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        # Validate required fields
        if "source" not in v:
            raise ValueError("source is required")

        # Validate types
        if "fields" in v and not isinstance(v["fields"], list):
            raise ValueError("fields must be a list")

        # Validate value ranges
        if "min_value" in v and "max_value" in v:
            if v["min_value"] >= v["max_value"]:
                raise ValueError("min_value must be less than max_value")

        return v
```

## Advanced Topics

### Plugin Chains

For complex analysis, you can create a chain of transformations using the built-in `transform_chain` plugin:

```yaml
phenology:
  plugin: "transform_chain"
  params:
    steps:
      - plugin: "time_series_analysis"
        params:
          source: occurrences
          fields:
            fleur: flower
            fruit: fruit
          time_field: month_obs
        output_key: "phenology_raw"

      - plugin: "custom_analysis"
        params:
          operation: "peak_detection"
          time_series: "@phenology_raw.month_data"
        output_key: "phenology_peaks"
```

This allows you to reference outputs from previous steps using the `@step.field` syntax.

### Error Handling

Proper error handling is important for debugging and maintaining your plugins. Use Niamoto's exception classes for consistent error reporting:

```python
from niamoto.common.exceptions import DataTransformError

def transform(self, data, config):
    try:
        # Plugin logic here
    except ValueError as e:
        raise DataTransformError(
            f"Configuration error: {str(e)}",
            details={"config": config}
        )
    except Exception as e:
        raise DataTransformError(
            f"Error during transformation: {str(e)}",
            details={"plugin": "custom_analysis"}
        )
```

### Testing Plugins

Create tests for your plugins to ensure they work correctly:

```python
import pytest
import pandas as pd
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType

def test_custom_analysis():
    # Get the plugin from the registry
    plugin_class = PluginRegistry.get_plugin("custom_analysis", PluginType.TRANSFORMER)
    plugin = plugin_class(db=None)  # Mock the database if needed

    # Create test data
    data = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "dbh": [10.5, 25.3, 32.1, 18.7, 45.9]
    })

    # Create test configuration
    config = {
        "params": {
            "field": "dbh",
            "threshold": 30.0
        }
    }

    # Execute the plugin
    result = plugin.transform(data, config)

    # Assert results
    assert "count_above" in result
    assert result["count_above"] == 2
    assert result["percent_above"] == 40.0
    assert result["max_value"] == 45.9
```

Run tests to validate your plugins:

```bash
pytest plugins/tests/test_custom_plugins.py -v
```

By following these guidelines, you can create robust and maintainable custom plugins that extend Niamoto's functionality to meet your specific needs.
