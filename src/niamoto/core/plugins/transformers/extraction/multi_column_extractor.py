"""
Plugin for extracting values from multiple columns and transforming them into a categorical distribution.
"""

from typing import Dict, Any
from pydantic import Field, field_validator
import os
import pandas as pd
import geopandas as gpd

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
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
            return self.config_model(**config).dict()
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
                    # Replace column names with actual values from dataframe
                    for col in df.columns:
                        if col in formula:
                            formula = formula.replace(col, str(df[col].iloc[0]))
                    try:
                        # Evaluate the formula
                        value = eval(formula)
                        # Add the derived column to the dataframe
                        df[derived["name"]] = value
                    except Exception as e:
                        raise ValueError(
                            f"Error evaluating formula {formula}: {str(e)}"
                        )

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

            return result

        except Exception as e:
            raise ValueError(f"Error transforming data: {str(e)}")
