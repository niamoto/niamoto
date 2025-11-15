"""
Plugin for extracting values from multiple columns and transforming them into a categorical distribution.
"""

from typing import Dict, Any, List, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
import pandas as pd
import re
from sqlalchemy import text

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.config import Config
from niamoto.core.imports.registry import EntityRegistry


class DerivedColumnConfig(BaseModel):
    """Configuration for a derived column."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Configuration for creating a derived column from a formula",
            "examples": [{"name": "total_count", "formula": "col1 + col2 + col3"}],
        }
    )

    name: str = Field(..., description="Name of the derived column to create")
    formula: str = Field(
        ...,
        description="Formula to calculate the derived column (can reference other column names)",
    )


class MultiColumnExtractorParams(BasePluginParams):
    """Parameters for multi-column extraction.

    This plugin extracts values from multiple columns and can transform them
    into a categorical distribution with labels, counts, and percentages.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Extract values from multiple columns and create categorical distributions",
            "examples": [
                {
                    "source": "plots",
                    "columns": ["species_a", "species_b", "species_c"],
                    "labels": ["Species A", "Species B", "Species C"],
                    "include_percentages": True,
                },
                {
                    "source": "biodiversity_data",
                    "columns": ["mammals", "birds", "reptiles"],
                    "labels": ["Mammals", "Birds", "Reptiles"],
                    "include_percentages": False,
                    "create_named_fields": True,
                    "field_names": ["mammal_count", "bird_count", "reptile_count"],
                },
            ],
        }
    )

    source: str = Field(
        default="occurrences",
        description="Data source entity name",
        json_schema_extra={
            "ui:widget": "entity-select",
            # No filter - allow all entities (datasets + references)
        },
    )
    columns: List[str] = Field(
        ...,
        min_length=1,
        description="List of column names to extract values from",
        json_schema_extra={"ui:widget": "multi-field-select", "ui:depends": "source"},
    )
    labels: Optional[List[str]] = Field(
        None, description="Custom labels for the columns (must match number of columns)"
    )
    include_percentages: bool = Field(
        default=False,
        description="Whether to include percentage calculations in the result",
    )
    derived_columns: List[DerivedColumnConfig] = Field(
        default_factory=list,
        description="List of derived columns to calculate before extraction",
    )
    create_named_fields: bool = Field(
        default=False,
        description="Whether to create individual named fields for each count",
    )
    field_names: Optional[List[str]] = Field(
        None, description="Custom field names when create_named_fields is True"
    )

    @field_validator("labels")
    @classmethod
    def validate_labels_length(
        cls, v: Optional[List[str]], info
    ) -> Optional[List[str]]:
        """Ensure labels length matches columns length if provided."""
        if v is not None and hasattr(info, "data") and "columns" in info.data:
            if len(v) != len(info.data["columns"]):
                raise ValueError("Number of labels must equal number of columns")
        return v

    @field_validator("field_names")
    @classmethod
    def validate_field_names_length(
        cls, v: Optional[List[str]], info
    ) -> Optional[List[str]]:
        """Ensure field_names length matches columns length if provided."""
        if v is not None and hasattr(info, "data") and "columns" in info.data:
            if len(v) != len(info.data["columns"]):
                raise ValueError("Number of field_names must equal number of columns")
        return v


class MultiColumnExtractorConfig(PluginConfig):
    """Complete configuration for multi-column extractor plugin."""

    plugin: Literal["multi_column_extractor"] = "multi_column_extractor"
    params: MultiColumnExtractorParams


@register("multi_column_extractor", PluginType.TRANSFORMER)
class MultiColumnExtractor(TransformerPlugin):
    """Plugin for extracting values from multiple columns"""

    config_model = MultiColumnExtractorConfig

    def __init__(self, db, registry=None):
        super().__init__(db, registry)
        self.config = Config()
        # Use registry from parent if provided, otherwise create new instance
        if not self.registry:
            self.registry = EntityRegistry(db)

    def validate_config(self, config: Dict[str, Any]) -> MultiColumnExtractorConfig:
        """Validate configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def _get_data_from_source(self, source: str, id_value: int = None) -> pd.DataFrame:
        """Get data from a source using registry."""
        try:
            # Resolve source table name from registry
            entity_info = self.registry.get(source)
            table_name = entity_info.table_name if entity_info else source

            # Get ID field name from entity metadata
            id_field = "id"  # Default
            if entity_info:
                id_field = entity_info.config.get("schema", {}).get("id_field", "id")

            # Query the database table
            base_query = f"SELECT * FROM {table_name}"
            params: Dict[str, Any] = {}
            if id_value is not None:
                base_query += f" WHERE {id_field} = :id_value"
                params["id_value"] = id_value

            # Use pd.read_sql with bound parameters for cleaner DataFrame creation
            df = pd.read_sql(text(base_query), self.db.engine, params=params)
            return df

        except Exception as e:
            raise ValueError(f"Error getting data from {source}: {str(e)}")

    def transform(
        self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Get group_id before validation
            group_id = config.get("group_id")
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get source data
            source = params.source
            columns = params.columns

            # Get data from source
            df = self._get_data_from_source(source, group_id)

            if df.empty:
                return {
                    "labels": params.labels if params.labels is not None else columns,
                    "counts": [0] * len(columns),
                }

            # Process derived columns if any
            for derived in params.derived_columns:
                formula = derived.formula
                derived_name = derived.name

                # Find potential variable names used in the formula
                potential_vars = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", formula))
                # Check if these exist in the DataFrame columns
                missing_cols = [var for var in potential_vars if var not in df.columns]
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
                    truly_missing = [m for m in missing_cols if m not in known_non_cols]
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
                        temp_formula = temp_formula.replace(col, str(df[col].iloc[0]))
                try:
                    # Evaluate the formula
                    value = eval(temp_formula)
                    # Add the derived column to the dataframe
                    df[derived_name] = value
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
            labels = params.labels if params.labels is not None else columns

            # Prepare result
            result = {
                "labels": labels,
                "counts": counts,
            }

            # Calculate percentages if requested
            if params.include_percentages:
                total = sum(counts)
                if total > 0:
                    percentages = [round((count / total) * 100, 2) for count in counts]
                else:
                    percentages = [0] * len(counts)
                result["percentages"] = percentages

            if params.create_named_fields:
                # Get field names from the config or generate from labels
                field_names = (
                    params.field_names if params.field_names is not None else []
                )
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
