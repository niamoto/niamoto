"""
Plugin for extracting values from multiple columns and transforming them into a categorical distribution.
"""

from typing import Dict, Any
from pydantic import Field, field_validator
import os
import pandas as pd
import geopandas as gpd
import re

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.config import Config


class MultiColumnExtractorConfig(PluginConfig):
    """Configuration for multi column extractor plugin"""

    plugin: str = "multi_column_extractor"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "columns": [],
            "labels": [],
            "include_percentages": False,
            "derived_columns": [],
        }
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        required_fields = ["source", "columns"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(v["source"], str):
            raise ValueError("source must be a string")

        if not isinstance(v["columns"], list):
            raise ValueError("columns must be a list")

        if "labels" in v:
            if not isinstance(v["labels"], list):
                raise ValueError("labels must be a list")
            if len(v["labels"]) != len(v["columns"]):
                raise ValueError("number of labels must be equal to number of columns")

        return v


@register("multi_column_extractor", PluginType.TRANSFORMER)
class MultiColumnExtractor(TransformerPlugin):
    """Plugin for extracting values from multiple columns"""

    config_model = MultiColumnExtractorConfig

    def __init__(self, db):
        super().__init__(db)
        self.config = Config()
        self.imports_config = self.config.get_imports_config

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration."""
        try:
            return self.config_model(**config).model_dump()
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def _get_data_from_source(self, source: str, id_value: int = None) -> pd.DataFrame:
        """Get data from a source (table or import)."""
        try:
            # Check if source is in import.yml
            if source in self.imports_config:
                import_config = self.imports_config[source]

                # Build full file path
                file_path = os.path.join(
                    os.path.dirname(self.config.config_dir), import_config["path"]
                )

                # Load data according to type
                if import_config["type"] == "csv":
                    df = pd.read_csv(file_path)
                elif import_config["type"] == "vector":
                    df = gpd.read_file(file_path)
                else:
                    raise ValueError(
                        f"Unsupported import type: {import_config['type']}"
                    )

                # Filter data if id_value is provided
                if id_value is not None:
                    identifier = import_config["identifier"]
                    df = df[df[identifier] == id_value]

                return df

            # Otherwise, it's a database table
            query = f"""
                SELECT * FROM {source}
            """
            if id_value is not None:
                query += f" WHERE id = {id_value}"

            result = self.db.execute_select(query)
            df = pd.DataFrame(
                result.fetchall(),
                columns=[desc[0] for desc in result.cursor.description],
            )
            return df

        except Exception as e:
            raise ValueError(f"Error getting data from {source}: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Get group_id before validation
            group_id = config.get("group_id")
            validated_config = self.validate_config(config)
            params = validated_config["params"]

            # Get source data
            source = params["source"]
            columns = params["columns"]

            # Get data from source
            df = self._get_data_from_source(source, group_id)

            if df.empty:
                return {
                    "labels": params.get("labels", columns),
                    "counts": [0] * len(columns),
                }

            # Process derived columns if any
            derived_columns = params.get("derived_columns", [])
            for derived in derived_columns:
                if "name" in derived and "formula" in derived:
                    formula = derived["formula"]

                    # Find potential variable names used in the formula
                    potential_vars = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", formula))
                    # Check if these exist in the DataFrame columns
                    missing_cols = [
                        var for var in potential_vars if var not in df.columns
                    ]
                    # Note: Basic check, might flag built-ins. Refine if needed.
                    if missing_cols:
                        # Filter out known non-columns before raising error - basic example
                        known_non_cols = {
                            "True",
                            "False",
                            "None",
                            "abs",
                            "round",
                            "min",
                            "max",
                            "pow",
                            "len",
                        }  # Add more if needed
                        truly_missing = [
                            m for m in missing_cols if m not in known_non_cols
                        ]
                        if truly_missing:
                            raise ValueError(
                                f"Column(s) '{', '.join(truly_missing)}' referenced in formula '{formula}' but not found in dataframe columns: {list(df.columns)}"
                            )

                    # Replace column names with actual values from dataframe (iloc[0] logic)
                    # Warning: This logic likely calculates based only on the first row.
                    temp_formula = formula
                    for col in df.columns:
                        if col in temp_formula:  # Simple substring check
                            # Using str() might have issues depending on data types
                            temp_formula = temp_formula.replace(
                                col, str(df[col].iloc[0])
                            )
                    try:
                        # Evaluate the formula
                        value = eval(temp_formula)
                        # Add the derived column to the dataframe
                        df[derived["name"]] = value
                    except Exception as e:
                        # Catch runtime evaluation errors
                        raise ValueError(
                            f"Error evaluating formula '{formula}' (evaluated as '{temp_formula}'): {str(e)}"
                        ) from e

            # Extract values from columns
            counts = []
            for column in columns:
                if column in df.columns:
                    value = df[column].iloc[0]
                    counts.append(int(value) if pd.notna(value) else 0)
                else:
                    counts.append(0)

            # Use provided labels or use column names
            labels = params.get("labels", columns)

            # Prepare result
            result = {
                "labels": labels,
                "counts": counts,
            }

            # Calculate percentages if requested
            if params.get("include_percentages", False):
                total = sum(counts)
                if total > 0:
                    percentages = [round((count / total) * 100, 2) for count in counts]
                else:
                    percentages = [0] * len(counts)
                result["percentages"] = percentages

            if params.get("create_named_fields", False):
                # Get field names from the config or generate from labels
                field_names = params.get("field_names", [])
                if not field_names and labels:
                    # Convert labels to field names (lowercase and replace spaces with underscores)
                    field_names = [label.lower().replace(" ", "_") for label in labels]

                # Create fields with value objects
                for i, field_name in enumerate(field_names):
                    if i < len(counts):
                        result[field_name] = {"value": counts[i], "units": ""}

            return result

        except Exception as e:
            raise ValueError(f"Error transforming data: {str(e)}")
