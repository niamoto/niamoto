"""Data access utilities for widgets and exporters.

This module provides generic data access and conversion utilities.
Widget-specific transformations have been moved to their respective widget classes.
"""

from typing import Any, Dict, Optional
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def get_nested_data(data: Dict, key_path: str) -> Any:
    """Access nested dictionary data using dot notation.

    Args:
        data: The dictionary to access
        key_path: Path to the data using dot notation (e.g., 'meff.value')

    Returns:
        The value at the specified path or None if not found
    """
    if not key_path or not isinstance(data, dict):
        return None

    parts = key_path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


def convert_to_dataframe(
    data: Any,
    x_field: str,
    y_field: str,
    color_field: Optional[str] = None,
    mapping: Optional[Dict[str, str]] = None,
) -> Optional[pd.DataFrame]:
    """Convert various data structures to a DataFrame suitable for plotting.

    Args:
        data: Input data (dictionary, list, etc.)
        x_field: Field name for x-axis values
        y_field: Field name for y-axis values
        color_field: Optional field name for color/category
        mapping: Optional mapping of input field names to output column names

    Returns:
        Pandas DataFrame or None if conversion fails
    """
    # Initialize result
    df = None

    # Case 1: Already a DataFrame
    if isinstance(data, pd.DataFrame):
        df = data.copy()

    # Case 2: Dict with direct keys for x and y fields
    elif isinstance(data, dict):
        # Try to extract data using the field names as direct keys
        x_data = None
        y_data = None
        color_data = None

        # Try nested access first
        if "." in x_field:
            x_data = get_nested_data(data, x_field)
        elif x_field in data:
            x_data = data[x_field]

        if "." in y_field:
            y_data = get_nested_data(data, y_field)
        elif y_field in data:
            y_data = data[y_field]

        if color_field:
            if "." in color_field:
                color_data = get_nested_data(data, color_field)
            elif color_field in data:
                color_data = data[color_field]

        # If we have both x and y data, create a DataFrame
        if x_data is not None and y_data is not None:
            if (
                isinstance(x_data, list)
                and isinstance(y_data, list)
                and len(x_data) == len(y_data)
            ):
                df_data = {x_field: x_data, y_field: y_data}

                # Add color field if available and matching length
                if (
                    color_data is not None
                    and isinstance(color_data, list)
                    and len(color_data) == len(x_data)
                ):
                    df_data[color_field] = color_data

                df = pd.DataFrame(df_data)

    # Case 3: List of dicts
    elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
        try:
            df = pd.DataFrame(data)
        except Exception:
            pass

    # Apply column mapping if provided
    if df is not None and mapping:
        df = df.rename(columns=mapping)

    return df
